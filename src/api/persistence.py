"""Tenant-scoped analysis persistence with atomic quota orchestration."""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from typing import Literal, Protocol, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, JsonValue, ValidationError

from src.api.models import AnalysisResponse, AnalyzeRequest
from src.api.service import AnalysisContractError
from src.security.config import SecurityConfigurationError, SupabaseSettings
from src.security.models import Principal
from src.security.repositories.supabase import (
    PostgrestAccessDenied,
    PostgrestQuotaExceeded,
    PostgrestRequestError,
    PostgrestUnavailable,
    SupabasePostgrestClient,
)


class AnalysisQuotaExceeded(RuntimeError):
    """Raised when the server-authoritative monthly tenant limit is exhausted."""


class AnalysisPersistenceDenied(PermissionError):
    """Raised when the database no longer authorizes the tenant operation."""


class AnalysisPersistenceUnavailable(RuntimeError):
    """Raised when analysis history cannot be changed safely."""


class PersistenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuotaReservation(PersistenceModel):
    reservation_id: UUID
    tier: Literal["free", "pro"]
    monthly_limit: int
    used: int
    remaining: int
    already_reserved: bool
    reservation_status: Literal["reserved", "consumed", "released"]
    linked_analysis_id: UUID | None
    stored_result_payload: dict[str, JsonValue] | None


class CompletedAnalysis(PersistenceModel):
    analysis_id: UUID
    stored_result_payload: dict[str, JsonValue]


class ReleasedReservation(PersistenceModel):
    released: bool


ModelT = TypeVar("ModelT", bound=BaseModel)


class AnalysisRepository(Protocol):
    def reserve(
        self,
        principal: Principal,
        *,
        idempotency_key: str,
    ) -> QuotaReservation: ...

    def complete(
        self,
        principal: Principal,
        *,
        reservation_id: UUID,
        input_payload: AnalyzeRequest,
        result: AnalysisResponse,
    ) -> CompletedAnalysis: ...

    def release(
        self,
        principal: Principal,
        *,
        reservation_id: UUID,
    ) -> None: ...


class SupabaseAnalysisRepository:
    """Persist validated reports through user-JWT-bound transactional RPCs."""

    def __init__(self, client: SupabasePostgrestClient) -> None:
        self._client = client

    def reserve(
        self,
        principal: Principal,
        *,
        idempotency_key: str,
    ) -> QuotaReservation:
        try:
            rows = self._client.rows(
                "POST",
                "rpc/reserve_analysis_quota",
                access_token=_access_token(principal),
                params={},
                payload={
                    "target_tenant_id": principal.tenant_id,
                    "target_idempotency_key": idempotency_key,
                },
            )
        except PostgrestQuotaExceeded as exc:
            raise AnalysisQuotaExceeded("monthly analysis quota exceeded") from exc
        except PostgrestAccessDenied as exc:
            raise AnalysisPersistenceDenied("analysis persistence denied") from exc
        except (PostgrestRequestError, PostgrestUnavailable) as exc:
            raise AnalysisPersistenceUnavailable("analysis quota could not be reserved") from exc
        return _one_model(rows, QuotaReservation, "quota reservation")

    def complete(
        self,
        principal: Principal,
        *,
        reservation_id: UUID,
        input_payload: AnalyzeRequest,
        result: AnalysisResponse,
    ) -> CompletedAnalysis:
        official_score = result.ranking[0].official_score if result.ranking else None
        try:
            rows = self._client.rows(
                "POST",
                "rpc/complete_analysis",
                access_token=_access_token(principal),
                params={},
                payload={
                    "target_tenant_id": principal.tenant_id,
                    "target_reservation_id": str(reservation_id),
                    "target_client_analysis_id": result.analysis_id,
                    "target_analysis_mode": result.analysis_mode,
                    "target_input_status": result.input_status,
                    "target_recommendation": result.recommendation,
                    "target_confidence": result.confidence,
                    "target_recommended_opportunity_id": result.recommended_opportunity_id,
                    "target_official_score": official_score,
                    "target_executive_summary": result.executive_summary,
                    "target_input_schema_version": input_payload.schema_version,
                    "target_output_schema_version": result.schema_version,
                    "target_score_version": result.versions.score_version,
                    "target_input_payload": input_payload.model_dump(mode="json", exclude_unset=True),
                    "target_result_payload": result.model_dump(mode="json"),
                    "target_processed_at": result.processed_at.isoformat(),
                },
            )
        except PostgrestAccessDenied as exc:
            raise AnalysisPersistenceDenied("analysis persistence denied") from exc
        except (PostgrestRequestError, PostgrestUnavailable) as exc:
            raise AnalysisPersistenceUnavailable("analysis result could not be persisted") from exc
        return _one_model(rows, CompletedAnalysis, "completed analysis")

    def release(
        self,
        principal: Principal,
        *,
        reservation_id: UUID,
    ) -> None:
        try:
            rows = self._client.rows(
                "POST",
                "rpc/release_analysis_quota",
                access_token=_access_token(principal),
                params={},
                payload={
                    "target_tenant_id": principal.tenant_id,
                    "target_reservation_id": str(reservation_id),
                },
            )
        except PostgrestAccessDenied as exc:
            raise AnalysisPersistenceDenied("analysis persistence denied") from exc
        except (PostgrestRequestError, PostgrestUnavailable) as exc:
            raise AnalysisPersistenceUnavailable("analysis quota could not be released") from exc
        released = _one_model(rows, ReleasedReservation, "released reservation")
        if not released.released:
            raise AnalysisPersistenceUnavailable("analysis quota was not released")


@lru_cache(maxsize=1)
def production_analysis_repository() -> AnalysisRepository:
    """Build one stateless production repository from public Supabase settings."""

    try:
        settings = SupabaseSettings.from_environment()
    except SecurityConfigurationError as exc:
        raise AnalysisPersistenceUnavailable("analysis persistence is not configured") from exc
    return SupabaseAnalysisRepository(SupabasePostgrestClient(settings))


def execute_persisted_analysis(
    *,
    repository: AnalysisRepository,
    principal: Principal,
    idempotency_key: str,
    payload: AnalyzeRequest,
    analyze: Callable[[AnalyzeRequest], AnalysisResponse],
) -> AnalysisResponse:
    """Reserve quota, run the core once and atomically persist its validated result."""

    reservation = repository.reserve(principal, idempotency_key=idempotency_key)
    if reservation.reservation_status == "consumed":
        if reservation.stored_result_payload is None:
            raise AnalysisPersistenceUnavailable("stored idempotent result is unavailable")
        try:
            return AnalysisResponse.model_validate(reservation.stored_result_payload)
        except ValidationError as exc:
            raise AnalysisContractError("The stored analysis violates its contract.") from exc
    if reservation.reservation_status != "reserved":
        raise AnalysisPersistenceUnavailable("analysis quota reservation is not active")

    try:
        result = analyze(payload)
    except Exception:
        try:
            repository.release(principal, reservation_id=reservation.reservation_id)
        except (AnalysisPersistenceDenied, AnalysisPersistenceUnavailable) as release_error:
            raise AnalysisPersistenceUnavailable(
                "analysis failed and its quota reservation could not be released"
            ) from release_error
        raise

    completed = repository.complete(
        principal,
        reservation_id=reservation.reservation_id,
        input_payload=payload,
        result=result,
    )
    try:
        return AnalysisResponse.model_validate(completed.stored_result_payload)
    except ValidationError as exc:
        raise AnalysisContractError("The persisted analysis violates its contract.") from exc


def _one_model(
    rows: list[dict[str, object]],
    model: type[ModelT],
    source: str,
) -> ModelT:
    if len(rows) != 1:
        raise AnalysisPersistenceUnavailable(f"{source} returned an invalid row count")
    try:
        return model.model_validate(rows[0])
    except ValidationError as exc:
        raise AnalysisPersistenceUnavailable(f"{source} returned invalid data") from exc


def _access_token(principal: Principal) -> str:
    if principal.access_token is None:
        raise AnalysisPersistenceDenied("analysis persistence requires a user access token")
    return principal.access_token

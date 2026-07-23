from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.auth import ApiSecurityDependencies
from src.api.models import (
    AnalysisDetailResponse,
    AnalysisHistoryItem,
    AnalysisHistoryResponse,
    AnalysisResponse,
    AnalyzeRequest,
    DashboardResponse,
)
from src.api.persistence import (
    AnalysisNotFound,
    AnalysisQuotaExceeded,
    AnalysisRepository,
    CompletedAnalysis,
    QuotaReservation,
)
from src.security.entitlements import StaticEntitlementResolver
from src.security.identity import StaticSessionAuthenticator
from src.security.models import Principal, TenantEntitlement


USER_ID = "11111111-1111-4111-8111-111111111111"
TENANT_ID = "22222222-2222-4222-8222-222222222222"
OTHER_TENANT_ID = "33333333-3333-4333-8333-333333333333"
ACCESS_TOKEN = "api-test-access-token"
AUTH_HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "X-Tenant-ID": TENANT_ID,
}


class MemoryAnalysisRepository:
    def __init__(self, *, monthly_limit: int = 100, tier: str = "free") -> None:
        self.monthly_limit = monthly_limit
        self.tier = tier
        self.reserve_calls = 0
        self.complete_calls = 0
        self.release_calls = 0
        self._reservations: dict[str, dict[str, object]] = {}
        self._results: dict[str, dict[str, object]] = {}

    def list_history(
        self,
        principal: Principal,
        *,
        limit: int,
        offset: int,
    ) -> AnalysisHistoryResponse:
        items = [
            self._history_item(reservation, self._results[key])
            for key, reservation in reversed(list(self._reservations.items()))
            if reservation["principal"] == principal and key in self._results
        ]
        return AnalysisHistoryResponse(
            items=items[offset : offset + limit],
            total=len(items),
            limit=limit,
            offset=offset,
        )

    def get_analysis(
        self,
        principal: Principal,
        *,
        analysis_id: UUID,
    ) -> AnalysisDetailResponse:
        for key, reservation in self._reservations.items():
            if reservation.get("analysis_id") == analysis_id and reservation["principal"] == principal:
                return AnalysisDetailResponse(
                    id=str(analysis_id),
                    tenant_id=principal.tenant_id,
                    created_at=reservation["created_at"],
                    result=AnalysisResponse.model_validate(self._results[key]),
                )
        raise AnalysisNotFound("analysis not found")

    def get_dashboard(self, principal: Principal) -> DashboardResponse:
        results = [
            AnalysisResponse.model_validate(self._results[key])
            for key, reservation in self._reservations.items()
            if reservation["principal"] == principal and key in self._results
        ]
        scores = [
            result.ranking[0].official_score
            for result in results
            if result.ranking and result.ranking[0].official_score is not None
        ]
        recommendation_counts: dict[str, int] = {}
        for result in results:
            recommendation_counts[result.recommendation] = (
                recommendation_counts.get(result.recommendation, 0) + 1
            )
        return DashboardResponse(
            tier=self.tier,
            monthly_limit=self.monthly_limit,
            quota_used=self.used,
            quota_remaining=max(self.monthly_limit - self.used, 0),
            total_analyses=len(results),
            scored_analyses=len(scores),
            average_official_score=sum(scores) / len(scores) if scores else None,
            sufficient_analyses=sum(result.input_status == "sufficient" for result in results),
            insufficient_analyses=sum(result.input_status == "insufficient" for result in results),
            rejected_analyses=sum(result.recommendation == "reject_for_now" for result in results),
            recommendation_counts=recommendation_counts,
        )

    @property
    def used(self) -> int:
        return sum(
            reservation["status"] in {"reserved", "consumed"}
            for reservation in self._reservations.values()
        )

    def reserve(
        self,
        principal: Principal,
        *,
        idempotency_key: str,
    ) -> QuotaReservation:
        self.reserve_calls += 1
        existing = self._reservations.get(idempotency_key)
        if existing is not None:
            status = str(existing["status"])
            reactivated = status == "released"
            if status == "released":
                if self.used >= self.monthly_limit:
                    raise AnalysisQuotaExceeded("monthly analysis quota exceeded")
                existing["status"] = "reserved"
                status = "reserved"
            return QuotaReservation(
                reservation_id=existing["id"],
                tier=self.tier,
                monthly_limit=self.monthly_limit,
                used=self.used,
                remaining=max(self.monthly_limit - self.used, 0),
                already_reserved=not reactivated,
                reservation_status=status,
                linked_analysis_id=existing.get("analysis_id"),
                stored_result_payload=self._results.get(idempotency_key),
            )
        if self.used >= self.monthly_limit:
            raise AnalysisQuotaExceeded("monthly analysis quota exceeded")
        reservation_id = uuid4()
        self._reservations[idempotency_key] = {
            "id": reservation_id,
            "principal": principal,
            "status": "reserved",
            "created_at": datetime.now(UTC),
        }
        return QuotaReservation(
            reservation_id=reservation_id,
            tier=self.tier,
            monthly_limit=self.monthly_limit,
            used=self.used,
            remaining=max(self.monthly_limit - self.used, 0),
            already_reserved=False,
            reservation_status="reserved",
            linked_analysis_id=None,
            stored_result_payload=None,
        )

    def complete(
        self,
        principal: Principal,
        *,
        reservation_id: UUID,
        input_payload: AnalyzeRequest,
        result: AnalysisResponse,
    ) -> CompletedAnalysis:
        del input_payload
        self.complete_calls += 1
        key, reservation = self._find(principal, reservation_id)
        analysis_id = uuid4()
        stored = result.model_dump(mode="json")
        reservation["status"] = "consumed"
        reservation["analysis_id"] = analysis_id
        self._results[key] = stored
        return CompletedAnalysis(
            analysis_id=analysis_id,
            stored_result_payload=stored,
        )

    @staticmethod
    def _history_item(
        reservation: dict[str, object],
        stored: dict[str, object],
    ) -> AnalysisHistoryItem:
        result = AnalysisResponse.model_validate(stored)
        return AnalysisHistoryItem(
            id=str(reservation["analysis_id"]),
            client_analysis_id=result.analysis_id,
            analysis_mode=result.analysis_mode,
            input_status=result.input_status,
            recommendation=result.recommendation,
            confidence=result.confidence,
            recommended_opportunity_id=result.recommended_opportunity_id,
            official_score=result.ranking[0].official_score if result.ranking else None,
            executive_summary=result.executive_summary,
            processed_at=result.processed_at,
            created_at=reservation["created_at"],
        )

    def release(
        self,
        principal: Principal,
        *,
        reservation_id: UUID,
    ) -> None:
        self.release_calls += 1
        _key, reservation = self._find(principal, reservation_id)
        reservation["status"] = "released"

    def _find(
        self,
        principal: Principal,
        reservation_id: UUID,
    ) -> tuple[str, dict[str, object]]:
        for key, reservation in self._reservations.items():
            if reservation["id"] == reservation_id and reservation["principal"] == principal:
                return key, reservation
        raise AssertionError("reservation not found")


def authenticated_app(
    *,
    tier: str = "free",
    analysis_repository: AnalysisRepository | None = None,
) -> FastAPI:
    principal = Principal(
        user_id=USER_ID,
        tenant_id=TENANT_ID,
        role="owner",
        access_token=ACCESS_TOKEN,
    )
    entitlement = TenantEntitlement(
        tier=tier,
        monthly_analysis_limit=3 if tier == "free" else 100,
        history_retention_days=30 if tier == "free" else None,
    )
    return create_app(
        security=ApiSecurityDependencies(
            authenticator=StaticSessionAuthenticator({ACCESS_TOKEN: principal}),
            entitlement_resolver=StaticEntitlementResolver({TENANT_ID: entitlement}),
        ),
        analysis_repository=analysis_repository
        or MemoryAnalysisRepository(
            monthly_limit=entitlement.monthly_analysis_limit,
            tier=entitlement.tier,
        ),
    )


def authenticated_client(
    *,
    tier: str = "free",
    analysis_repository: AnalysisRepository | None = None,
    **kwargs: object,
) -> TestClient:
    return TestClient(
        authenticated_app(tier=tier, analysis_repository=analysis_repository),
        headers=AUTH_HEADERS,
        **kwargs,
    )

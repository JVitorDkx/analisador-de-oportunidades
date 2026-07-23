from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.auth import ApiSecurityDependencies
from src.api.models import AnalysisResponse, AnalyzeRequest
from src.api.persistence import (
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
    def __init__(self, *, monthly_limit: int = 100) -> None:
        self.monthly_limit = monthly_limit
        self.reserve_calls = 0
        self.complete_calls = 0
        self.release_calls = 0
        self._reservations: dict[str, dict[str, object]] = {}
        self._results: dict[str, dict[str, object]] = {}

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
                tier="free",
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
        }
        return QuotaReservation(
            reservation_id=reservation_id,
            tier="free",
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
        or MemoryAnalysisRepository(monthly_limit=entitlement.monthly_analysis_limit),
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

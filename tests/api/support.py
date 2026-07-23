from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.auth import ApiSecurityDependencies
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


def authenticated_app(*, tier: str = "free") -> FastAPI:
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
        )
    )


def authenticated_client(*, tier: str = "free", **kwargs: object) -> TestClient:
    return TestClient(
        authenticated_app(tier=tier),
        headers=AUTH_HEADERS,
        **kwargs,
    )

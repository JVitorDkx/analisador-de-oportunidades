"""Deterministic security integration fixtures."""

from __future__ import annotations

import hashlib
import hmac

from fastapi.testclient import TestClient

from src.security.app import create_security_app
from src.security.identity import ProfileService, StaticSessionAuthenticator
from src.security.models import Plan, Principal, Profile, TenantResource
from src.security.pricing import CheckoutService, PlanCatalog
from src.security.tenancy import InMemoryTenantRepository
from src.security.webhooks import WebhookVerifier


NOW = 2_000_000_000
TEST_WEBHOOK_SECRET = b"x" * 32
TOKEN_A = "session-user-a"
TOKEN_B = "session-user-b"
AUTH_A = {"Authorization": f"Bearer {TOKEN_A}"}
AUTH_B = {"Authorization": f"Bearer {TOKEN_B}"}


def build_client() -> TestClient:
    principal_a = Principal(user_id="user-a", tenant_id="tenant-a", role="member")
    principal_b = Principal(user_id="user-b", tenant_id="tenant-b", role="member")
    catalog = PlanCatalog(
        (
            Plan(plan_id="basic-monthly", amount_minor=4900, currency="BRL"),
            Plan(plan_id="pro-monthly", amount_minor=12900, currency="BRL"),
        )
    )
    repository = InMemoryTenantRepository(
        (
            TenantResource(resource_id="resource-a", tenant_id="tenant-a", name="A resource"),
            TenantResource(resource_id="resource-b", tenant_id="tenant-b", name="B resource"),
        )
    )
    profiles = ProfileService(
        {
            "user-a": Profile(
                user_id="user-a",
                tenant_id="tenant-a",
                display_name="User A",
                role="member",
            ),
            "user-b": Profile(
                user_id="user-b",
                tenant_id="tenant-b",
                display_name="User B",
                role="member",
            ),
        }
    )
    app = create_security_app(
        checkout_service=CheckoutService(catalog),
        webhook_verifier=WebhookVerifier(TEST_WEBHOOK_SECRET, clock=lambda: NOW),
        authenticator=StaticSessionAuthenticator({TOKEN_A: principal_a, TOKEN_B: principal_b}),
        tenant_repository=repository,
        profile_service=profiles,
    )
    return TestClient(app)


def webhook_signature(body: bytes, *, timestamp: int = NOW) -> str:
    signed_payload = str(timestamp).encode("ascii") + b"." + body
    signature = hmac.new(TEST_WEBHOOK_SECRET, signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"

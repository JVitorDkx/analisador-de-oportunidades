from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Any

from src.security.config import SupabaseSettings
from src.security.identity import UnauthenticatedError
from src.security.models import Principal, ProfileUpdateRequest
from src.security.repositories.contracts import SecurityRepositoryUnavailable
from src.security.repositories.supabase import (
    SupabasePostgrestClient,
    SupabaseProfileRepository,
    SupabaseTenantEntitlementResolver,
    SupabaseTenantMembershipResolver,
    SupabaseTenantRepository,
)
from src.security.tenancy import TenantResourceNotFound


USER_ID = "11111111-1111-4111-8111-111111111111"
TENANT_ID = "22222222-2222-4222-8222-222222222222"
PROJECT_ID = "33333333-3333-4333-8333-333333333333"
ACCESS_TOKEN = "signed-user-access-token"


@dataclass
class FakeResponse:
    status_code: int
    data: Any

    def json(self) -> Any:
        return self.data


class RecordingHttpClient:
    def __init__(self, *responses: FakeResponse) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.requests.append({"method": method, "url": url, **kwargs})
        if not self.responses:
            raise AssertionError("unexpected HTTP request")
        return self.responses.pop(0)


def build_client(*responses: FakeResponse) -> tuple[SupabasePostgrestClient, RecordingHttpClient]:
    transport = RecordingHttpClient(*responses)
    config = SupabaseSettings(
        url="https://example-project.supabase.co",
        publishable_key="sb_publishable_test_public_key",
    )
    return SupabasePostgrestClient(config, http_client=transport), transport


def principal(*, access_token: str | None = ACCESS_TOKEN) -> Principal:
    return Principal(
        user_id=USER_ID,
        tenant_id=TENANT_ID,
        role="member",
        access_token=access_token,
    )


class SupabaseTenantMembershipResolverTests(unittest.TestCase):
    def test_resolves_role_with_user_jwt_and_both_identity_filters(self) -> None:
        client, transport = build_client(FakeResponse(200, [{"role": "admin"}]))
        resolver = SupabaseTenantMembershipResolver(client)

        role = resolver.resolve(
            access_token=ACCESS_TOKEN,
            user_id=USER_ID,
            tenant_id=TENANT_ID,
        )

        self.assertEqual(role, "admin")
        request = transport.requests[0]
        self.assertEqual(request["method"], "GET")
        self.assertTrue(request["url"].endswith("/rest/v1/tenant_memberships"))
        self.assertEqual(request["headers"]["Authorization"], f"Bearer {ACCESS_TOKEN}")
        self.assertEqual(request["headers"]["apikey"], "sb_publishable_test_public_key")
        self.assertEqual(request["params"]["tenant_id"], f"eq.{TENANT_ID}")
        self.assertEqual(request["params"]["user_id"], f"eq.{USER_ID}")

    def test_denies_absent_cross_tenant_membership(self) -> None:
        client, _transport = build_client(FakeResponse(200, []))

        with self.assertRaises(UnauthenticatedError):
            SupabaseTenantMembershipResolver(client).resolve(
                access_token=ACCESS_TOKEN,
                user_id=USER_ID,
                tenant_id=TENANT_ID,
            )


class SupabaseTenantEntitlementResolverTests(unittest.TestCase):
    def test_resolves_entitlement_through_user_scoped_projection(self) -> None:
        client, transport = build_client(
            FakeResponse(
                200,
                [
                    {
                        "tier": "pro",
                        "monthly_analysis_limit": 100,
                        "history_retention_days": None,
                    }
                ],
            )
        )

        entitlement = SupabaseTenantEntitlementResolver(client).resolve(principal())

        self.assertEqual(entitlement.tier, "pro")
        self.assertEqual(entitlement.monthly_analysis_limit, 100)
        request = transport.requests[0]
        self.assertEqual(request["method"], "GET")
        self.assertTrue(request["url"].endswith("/rest/v1/tenant_entitlements"))
        self.assertEqual(request["headers"]["Authorization"], f"Bearer {ACCESS_TOKEN}")
        self.assertEqual(request["params"]["tenant_id"], f"eq.{TENANT_ID}")

    def test_rejects_missing_or_invalid_entitlement_projection(self) -> None:
        missing_client, _transport = build_client(FakeResponse(200, []))
        with self.assertRaises(UnauthenticatedError):
            SupabaseTenantEntitlementResolver(missing_client).resolve(principal())

        invalid_client, _transport = build_client(
            FakeResponse(
                200,
                [
                    {
                        "tier": "enterprise",
                        "monthly_analysis_limit": 0,
                        "history_retention_days": None,
                    }
                ],
            )
        )
        with self.assertRaises(SecurityRepositoryUnavailable):
            SupabaseTenantEntitlementResolver(invalid_client).resolve(principal())


class SupabaseTenantRepositoryTests(unittest.TestCase):
    def test_get_uses_explicit_tenant_filter_in_addition_to_rls(self) -> None:
        row = {"id": PROJECT_ID, "tenant_id": TENANT_ID, "name": "Safe project"}
        client, transport = build_client(FakeResponse(200, [row]))

        resource = SupabaseTenantRepository(client).get(principal(), PROJECT_ID)

        self.assertEqual(resource.resource_id, PROJECT_ID)
        self.assertEqual(resource.tenant_id, TENANT_ID)
        request = transport.requests[0]
        self.assertEqual(request["params"]["id"], f"eq.{PROJECT_ID}")
        self.assertEqual(request["params"]["tenant_id"], f"eq.{TENANT_ID}")
        self.assertNotIn("service_role", str(request))

    def test_update_sends_only_editable_name_and_user_token(self) -> None:
        row = {"id": PROJECT_ID, "tenant_id": TENANT_ID, "name": "Updated"}
        client, transport = build_client(FakeResponse(200, [row]))

        resource = SupabaseTenantRepository(client).update(
            principal(),
            PROJECT_ID,
            name="Updated",
        )

        self.assertEqual(resource.name, "Updated")
        request = transport.requests[0]
        self.assertEqual(request["method"], "PATCH")
        self.assertEqual(request["json"], {"name": "Updated"})
        self.assertEqual(request["headers"]["Prefer"], "return=representation")
        self.assertNotIn("tenant_id", request["json"])

    def test_cross_tenant_delete_is_indistinguishable_from_missing_resource(self) -> None:
        client, _transport = build_client(FakeResponse(200, []))

        with self.assertRaisesRegex(TenantResourceNotFound, "resource not found"):
            SupabaseTenantRepository(client).delete(principal(), PROJECT_ID)

    def test_repository_requires_user_access_token(self) -> None:
        client, transport = build_client()

        with self.assertRaises(UnauthenticatedError):
            SupabaseTenantRepository(client).get(principal(access_token=None), PROJECT_ID)

        self.assertEqual(transport.requests, [])

    def test_data_api_denial_maps_to_non_disclosing_not_found(self) -> None:
        client, _transport = build_client(FakeResponse(403, {"message": "RLS details"}))

        with self.assertRaisesRegex(TenantResourceNotFound, "resource not found"):
            SupabaseTenantRepository(client).get(principal(), PROJECT_ID)

    def test_data_api_outage_maps_to_sanitized_unavailable_error(self) -> None:
        client, _transport = build_client(FakeResponse(503, {"message": "internal details"}))

        with self.assertRaisesRegex(SecurityRepositoryUnavailable, "repository is unavailable"):
            SupabaseTenantRepository(client).get(principal(), PROJECT_ID)


class SupabaseProfileRepositoryTests(unittest.TestCase):
    def test_profile_update_cannot_write_role_or_tenant(self) -> None:
        client, transport = build_client(
            FakeResponse(200, [{"user_id": USER_ID, "display_name": "Safe Name"}])
        )

        profile = SupabaseProfileRepository(client).update(
            principal(),
            ProfileUpdateRequest(display_name="Safe Name"),
        )

        self.assertEqual(profile.display_name, "Safe Name")
        self.assertEqual(profile.tenant_id, TENANT_ID)
        self.assertEqual(profile.role, "member")
        request = transport.requests[0]
        self.assertEqual(request["json"], {"display_name": "Safe Name"})
        self.assertEqual(request["params"]["user_id"], f"eq.{USER_ID}")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.auth import ApiSecurityUnavailable
from tests.api.support import (
    AUTH_HEADERS,
    OTHER_TENANT_ID,
    TENANT_ID,
    USER_ID,
    authenticated_app,
    authenticated_client,
)


class ApiAuthenticationTests(unittest.TestCase):
    def test_health_remains_public(self) -> None:
        response = TestClient(authenticated_app()).get("/api/v1/health")

        self.assertEqual(response.status_code, 200, response.text)

    def test_protected_endpoint_requires_bearer_and_tenant(self) -> None:
        response = TestClient(authenticated_app()).get("/api/v1/session")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["content-type"], "application/problem+json")
        problem = response.json()
        self.assertEqual(problem["code"], "authentication_required")
        self.assertEqual(problem["status"], 401)
        self.assertNotIn("token", problem["detail"].lower())

    def test_cross_tenant_selector_is_rejected(self) -> None:
        headers = {**AUTH_HEADERS, "X-Tenant-ID": OTHER_TENANT_ID}

        response = TestClient(authenticated_app()).get("/api/v1/session", headers=headers)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "authentication_required")

    def test_free_session_is_derived_from_server_entitlement(self) -> None:
        response = authenticated_client().get(
            "/api/v1/session",
            headers={"X-Plan": "pro", "X-Tier": "pro"},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(),
            {
                "user_id": USER_ID,
                "tenant_id": TENANT_ID,
                "role": "owner",
                "tier": "free",
                "monthly_analysis_limit": 3,
                "history_retention_days": 30,
            },
        )

    def test_pro_session_exposes_only_server_resolved_plan(self) -> None:
        response = authenticated_client(tier="pro").get("/api/v1/session")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["tier"], "pro")
        self.assertEqual(response.json()["monthly_analysis_limit"], 100)
        self.assertIsNone(response.json()["history_retention_days"])

    def test_missing_production_security_configuration_fails_closed(self) -> None:
        client = TestClient(create_app(), raise_server_exceptions=False)
        with patch(
            "src.api.app.production_api_security_dependencies",
            side_effect=ApiSecurityUnavailable("not configured"),
        ):
            response = client.get("/api/v1/session")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "authentication_unavailable")


if __name__ == "__main__":
    unittest.main()

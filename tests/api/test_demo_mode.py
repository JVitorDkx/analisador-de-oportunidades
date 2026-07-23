from __future__ import annotations

import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.config import demo_mode_enabled
from tests.api.support import authenticated_app


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = PROJECT_ROOT / "fixtures" / "cases" / "opportunity_viable.json"


class DemoModeConfigurationTests(unittest.TestCase):
    def test_flag_is_disabled_by_default_and_in_production(self) -> None:
        self.assertFalse(demo_mode_enabled({}))
        self.assertFalse(
            demo_mode_enabled(
                {"APP_ENV": "production", "ENABLE_DEMO_MODE": "true"}
            )
        )

    def test_flag_requires_explicit_true_in_local_runtime(self) -> None:
        self.assertTrue(
            demo_mode_enabled(
                {"APP_ENV": "development", "ENABLE_DEMO_MODE": "true"}
            )
        )


class DemoModeApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_demo_analyze_runs_core_without_authentication_or_database(self) -> None:
        response = TestClient(create_app(demo_mode=True)).post(
            "/api/v1/analyze",
            json=self.payload,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Demo-Mode"], "true")
        self.assertEqual(response.json()["ranking"][0]["official_score"], 90.4)
        self.assertTrue(response.json()["recommendations"])

    def test_disabled_demo_mode_keeps_authentication_fail_closed(self) -> None:
        response = TestClient(authenticated_app()).post(
            "/api/v1/analyze",
            json=self.payload,
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "authentication_required")


if __name__ == "__main__":
    unittest.main()

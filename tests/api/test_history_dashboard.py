from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.api.support import AUTH_HEADERS, OTHER_TENANT_ID, TENANT_ID, authenticated_client


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = PROJECT_ROOT / "fixtures" / "cases" / "opportunity_viable.json"


class TenantHistoryApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = authenticated_client()
        self.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_persisted_analysis_is_listed_and_retrievable(self) -> None:
        created = self.client.post("/api/v1/analyze", json=self.payload)
        self.assertEqual(created.status_code, 200)

        history = self.client.get(f"/api/v1/tenants/{TENANT_ID}/analyses?limit=10&offset=0")
        self.assertEqual(history.status_code, 200)
        body = history.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["items"][0]["client_analysis_id"], created.json()["analysis_id"])

        detail = self.client.get(
            f"/api/v1/tenants/{TENANT_ID}/analyses/{body['items'][0]['id']}"
        )
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["result"], created.json())

    def test_dashboard_uses_persisted_results_and_quota(self) -> None:
        self.client.post("/api/v1/analyze", json=self.payload)
        response = self.client.get(f"/api/v1/tenants/{TENANT_ID}/dashboard")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total_analyses"], 1)
        self.assertEqual(body["scored_analyses"], 1)
        self.assertEqual(body["quota_used"], 1)
        self.assertEqual(sum(body["recommendation_counts"].values()), 1)

    def test_path_tenant_mismatch_is_non_disclosing(self) -> None:
        response = self.client.get(
            f"/api/v1/tenants/{OTHER_TENANT_ID}/analyses",
            headers=AUTH_HEADERS,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers["content-type"], "application/problem+json")

    def test_missing_analysis_returns_problem_detail(self) -> None:
        response = self.client.get(
            f"/api/v1/tenants/{TENANT_ID}/analyses/"
            "44444444-4444-4444-8444-444444444444"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "analysis_not_found")


if __name__ == "__main__":
    unittest.main()

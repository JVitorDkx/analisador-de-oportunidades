from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.service import AnalysisContractError, analyze_payload
from tests.api.support import AUTH_HEADERS, MemoryAnalysisRepository, authenticated_app


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CASES_DIR = PROJECT_ROOT / "fixtures" / "cases"


def viable_payload() -> dict:
    return json.loads((CASES_DIR / "opportunity_viable.json").read_text(encoding="utf-8"))


class AnalysisPersistenceTests(unittest.TestCase):
    def test_successful_analysis_is_persisted_and_consumes_one_unit(self) -> None:
        repository = MemoryAnalysisRepository(monthly_limit=3)
        client = TestClient(
            authenticated_app(analysis_repository=repository),
            headers=AUTH_HEADERS,
        )

        response = client.post(
            "/api/v1/analyze",
            headers={"Idempotency-Key": "request-key-0001"},
            json=viable_payload(),
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(repository.reserve_calls, 1)
        self.assertEqual(repository.complete_calls, 1)
        self.assertEqual(repository.release_calls, 0)
        self.assertEqual(repository.used, 1)

    def test_same_idempotency_key_returns_stored_result_without_rerunning_core(self) -> None:
        repository = MemoryAnalysisRepository(monthly_limit=3)
        client = TestClient(
            authenticated_app(analysis_repository=repository),
            headers=AUTH_HEADERS,
        )
        headers = {"Idempotency-Key": "request-key-0002"}
        payload = viable_payload()

        with patch("src.api.app.analyze_payload", wraps=analyze_payload) as core:
            first = client.post("/api/v1/analyze", headers=headers, json=payload)
            second = client.post("/api/v1/analyze", headers=headers, json=payload)

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(core.call_count, 1)
        self.assertEqual(repository.complete_calls, 1)
        self.assertEqual(repository.used, 1)

    def test_monthly_quota_is_checked_before_running_core(self) -> None:
        repository = MemoryAnalysisRepository(monthly_limit=1)
        client = TestClient(
            authenticated_app(analysis_repository=repository),
            headers=AUTH_HEADERS,
        )
        first_payload = viable_payload()
        second_payload = copy.deepcopy(first_payload)
        second_payload["analysis_id"] = "ANL-CASE-VIABLE-QUOTA-002"

        first = client.post(
            "/api/v1/analyze",
            headers={"Idempotency-Key": "request-key-0003"},
            json=first_payload,
        )
        with patch("src.api.app.analyze_payload", wraps=analyze_payload) as core:
            blocked = client.post(
                "/api/v1/analyze",
                headers={"Idempotency-Key": "request-key-0004"},
                json=second_payload,
            )

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.headers["content-type"], "application/problem+json")
        self.assertEqual(blocked.json()["code"], "analysis_quota_exceeded")
        self.assertEqual(core.call_count, 0)
        self.assertEqual(repository.used, 1)

    def test_core_failure_releases_reservation_for_safe_retry(self) -> None:
        repository = MemoryAnalysisRepository(monthly_limit=1)
        client = TestClient(
            authenticated_app(analysis_repository=repository),
            headers=AUTH_HEADERS,
            raise_server_exceptions=False,
        )
        headers = {"Idempotency-Key": "request-key-0005"}

        with patch(
            "src.api.app.analyze_payload",
            side_effect=AnalysisContractError("controlled failure"),
        ):
            failed = client.post(
                "/api/v1/analyze",
                headers=headers,
                json=viable_payload(),
            )

        retried = client.post(
            "/api/v1/analyze",
            headers=headers,
            json=viable_payload(),
        )

        self.assertEqual(failed.status_code, 500)
        self.assertEqual(repository.release_calls, 1)
        self.assertEqual(retried.status_code, 200, retried.text)
        self.assertEqual(repository.used, 1)

    def test_invalid_idempotency_key_is_rejected_before_reservation(self) -> None:
        repository = MemoryAnalysisRepository(monthly_limit=3)
        client = TestClient(
            authenticated_app(analysis_repository=repository),
            headers=AUTH_HEADERS,
        )

        response = client.post(
            "/api/v1/analyze",
            headers={"Idempotency-Key": "bad key"},
            json=viable_payload(),
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(repository.reserve_calls, 0)


if __name__ == "__main__":
    unittest.main()

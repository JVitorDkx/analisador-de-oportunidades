from __future__ import annotations

import json
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from src.api.models import AnalysisResponse, AnalyzeRequest
from src.api.persistence import (
    AnalysisQuotaExceeded,
    SupabaseAnalysisRepository,
)
from src.api.service import analyze_payload
from src.security.config import SupabaseSettings
from src.security.models import Principal
from src.security.repositories.supabase import SupabasePostgrestClient
from tests.api.support import ACCESS_TOKEN, TENANT_ID, USER_ID


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VIABLE_FIXTURE = PROJECT_ROOT / "fixtures" / "cases" / "opportunity_viable.json"
RESERVATION_ID = "44444444-4444-4444-8444-444444444444"
STORED_ANALYSIS_ID = "55555555-5555-4555-8555-555555555555"


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


def principal() -> Principal:
    return Principal(
        user_id=USER_ID,
        tenant_id=TENANT_ID,
        role="owner",
        access_token=ACCESS_TOKEN,
    )


def repository(
    *responses: FakeResponse,
) -> tuple[SupabaseAnalysisRepository, RecordingHttpClient]:
    transport = RecordingHttpClient(*responses)
    settings = SupabaseSettings(
        url="https://example-project.supabase.co",
        publishable_key="sb_publishable_test_public_key",
    )
    client = SupabasePostgrestClient(settings, http_client=transport)
    return SupabaseAnalysisRepository(client), transport


def analysis_contracts() -> tuple[AnalyzeRequest, AnalysisResponse]:
    payload = AnalyzeRequest.model_validate(
        json.loads(VIABLE_FIXTURE.read_text(encoding="utf-8"))
    )
    return payload, analyze_payload(payload, processed_at="2026-07-23T12:00:00+00:00")


class SupabaseAnalysisRepositoryTests(unittest.TestCase):
    def test_reserve_uses_user_token_tenant_and_idempotency_key(self) -> None:
        repo, transport = repository(
            FakeResponse(
                200,
                [
                    {
                        "reservation_id": RESERVATION_ID,
                        "tier": "free",
                        "monthly_limit": 3,
                        "used": 1,
                        "remaining": 2,
                        "already_reserved": False,
                        "reservation_status": "reserved",
                        "linked_analysis_id": None,
                        "stored_result_payload": None,
                    }
                ],
            )
        )

        reservation = repo.reserve(principal(), idempotency_key="request-key-safe")

        self.assertEqual(reservation.reservation_id, UUID(RESERVATION_ID))
        request = transport.requests[0]
        self.assertTrue(request["url"].endswith("/rest/v1/rpc/reserve_analysis_quota"))
        self.assertEqual(request["headers"]["Authorization"], f"Bearer {ACCESS_TOKEN}")
        self.assertEqual(
            request["json"],
            {
                "target_tenant_id": TENANT_ID,
                "target_idempotency_key": "request-key-safe",
            },
        )

    def test_database_quota_error_maps_to_domain_error(self) -> None:
        repo, _transport = repository(
            FakeResponse(
                400,
                {
                    "code": "P0001",
                    "message": "analysis quota exceeded",
                },
            )
        )

        with self.assertRaises(AnalysisQuotaExceeded):
            repo.reserve(principal(), idempotency_key="request-key-full")

    def test_complete_sends_validated_contract_and_server_principal_tenant(self) -> None:
        payload, result = analysis_contracts()
        repo, transport = repository(
            FakeResponse(
                200,
                [
                    {
                        "analysis_id": STORED_ANALYSIS_ID,
                        "stored_result_payload": result.model_dump(mode="json"),
                    }
                ],
            )
        )

        completed = repo.complete(
            principal(),
            reservation_id=UUID(RESERVATION_ID),
            input_payload=payload,
            result=result,
        )

        self.assertEqual(completed.analysis_id, UUID(STORED_ANALYSIS_ID))
        request = transport.requests[0]
        self.assertTrue(request["url"].endswith("/rest/v1/rpc/complete_analysis"))
        self.assertEqual(request["json"]["target_tenant_id"], TENANT_ID)
        self.assertEqual(request["json"]["target_official_score"], 90.4)
        self.assertEqual(
            request["json"]["target_result_payload"]["analysis_id"],
            payload.analysis_id,
        )

    def test_release_is_user_token_bound(self) -> None:
        repo, transport = repository(FakeResponse(200, [{"released": True}]))

        repo.release(principal(), reservation_id=UUID(RESERVATION_ID))

        request = transport.requests[0]
        self.assertTrue(request["url"].endswith("/rest/v1/rpc/release_analysis_quota"))
        self.assertEqual(
            request["json"],
            {
                "target_tenant_id": TENANT_ID,
                "target_reservation_id": RESERVATION_ID,
            },
        )


if __name__ == "__main__":
    unittest.main()

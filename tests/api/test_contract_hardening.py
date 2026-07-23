from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from src.api.app import create_app
from src.api.service import AnalysisContractError, ServiceUnavailableError
from tests.api.support import authenticated_client


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CASES_DIR = PROJECT_ROOT / "fixtures" / "cases"


def load_fixture(name: str) -> dict:
    return json.loads((CASES_DIR / name).read_text(encoding="utf-8"))


class ApiInfrastructureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = authenticated_client()

    def test_health_reports_core_versions_and_request_id(self) -> None:
        response = self.client.get(
            "/api/v1/health",
            headers={"X-Request-ID": "health-check-001"},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["X-Request-ID"], "health-check-001")
        self.assertEqual(
            response.json(),
            {
                "status": "ok",
                "service": "opportunity-analyzer-api",
                "api_version": "1.0.0",
                "score_version": "SCORE-0.1.0",
                "checks": {"core": "ok", "score_configuration": "ok"},
            },
        )

    def test_validate_input_returns_typed_validation_without_running_analysis(self) -> None:
        response = self.client.post(
            "/api/v1/validate-input",
            json=load_fixture("opportunity_viable.json"),
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["valid"])
        self.assertEqual(response.json()["error_count"], 0)
        self.assertTrue(response.headers["X-Request-ID"])

    def test_transport_models_reject_unknown_fields_with_problem_details(self) -> None:
        payload = load_fixture("opportunity_viable.json")
        payload["unexpected_field"] = "must be rejected"

        response = self.client.post(
            "/api/v1/validate-input",
            json=payload,
            headers={"X-Request-ID": "invalid-input-001"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.headers["content-type"], "application/problem+json")
        self.assertEqual(response.headers["X-Request-ID"], "invalid-input-001")
        problem = response.json()
        self.assertEqual(problem["type"], "urn:problem:opportunity-analyzer:request_validation_error")
        self.assertEqual(problem["status"], 422)
        self.assertIsInstance(problem["detail"], str)
        self.assertEqual(problem["instance"], "urn:request:invalid-input-001")
        self.assertEqual(problem["request_id"], "invalid-input-001")
        self.assertEqual(problem["errors"][0]["pointer"], "$.unexpected_field")
        self.assertEqual(problem["errors"][0]["code"], "extra_forbidden")

    def test_invalid_request_id_is_replaced(self) -> None:
        response = self.client.get(
            "/api/v1/health",
            headers={"X-Request-ID": "invalid request id with spaces"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.headers["X-Request-ID"], "invalid request id with spaces")
        self.assertTrue(response.headers["X-Request-ID"])

    def test_contract_failure_uses_problem_json_without_internal_details(self) -> None:
        client = authenticated_client(raise_server_exceptions=False)
        with patch(
            "src.api.app.analyze_payload",
            side_effect=AnalysisContractError("sensitive internal detail"),
        ):
            response = client.post(
                "/api/v1/analyze",
                json=load_fixture("opportunity_viable.json"),
                headers={"X-Request-ID": "contract-error-001"},
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.headers["content-type"], "application/problem+json")
        self.assertEqual(response.headers["X-Request-ID"], "contract-error-001")
        problem = response.json()
        self.assertEqual(problem["code"], "analysis_contract_error")
        self.assertEqual(problem["status"], 500)
        self.assertNotIn("sensitive internal detail", problem["detail"])

    def test_health_dependency_failure_uses_documented_503_problem(self) -> None:
        with patch(
            "src.api.app.health_status",
            side_effect=ServiceUnavailableError("missing score configuration"),
        ):
            response = self.client.get(
                "/api/v1/health",
                headers={"X-Request-ID": "health-error-001"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["content-type"], "application/problem+json")
        self.assertEqual(response.headers["X-Request-ID"], "health-error-001")
        problem = response.json()
        self.assertEqual(problem["code"], "service_unavailable")
        self.assertEqual(problem["status"], 503)
        self.assertEqual(problem["instance"], "urn:request:health-error-001")


class OpenApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = create_app().openapi()

    def test_openapi_is_strict_31_with_stable_operation_ids(self) -> None:
        self.assertEqual(self.schema["openapi"], "3.1.0")
        self.assertEqual(
            {
                path: operation["operationId"]
                for path, path_item in self.schema["paths"].items()
                for operation in path_item.values()
                if isinstance(operation, dict) and "operationId" in operation
            },
            {
                "/api/v1/health": "getHealth",
                "/api/v1/session": "getSession",
                "/api/v1/validate-input": "validateOpportunityInput",
                "/api/v1/analyze": "analyzeOpportunity",
            },
        )

    def test_openapi_contains_no_unconstrained_additional_properties(self) -> None:
        offending_paths: list[str] = []

        def visit(value: object, path: str = "$") -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    child_path = f"{path}.{key}"
                    if key == "additionalProperties" and child is True:
                        offending_paths.append(child_path)
                    visit(child, child_path)
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    visit(child, f"{path}[{index}]")

        visit(self.schema)
        self.assertEqual(offending_paths, [])

    def test_analyze_documents_three_official_examples_and_problem_responses(self) -> None:
        analyze = self.schema["paths"]["/api/v1/analyze"]["post"]
        examples = analyze["requestBody"]["content"]["application/json"]["examples"]

        self.assertEqual(set(examples), {"viable", "kill_switch", "insufficient_data"})
        for status_code in ("422", "500"):
            response = analyze["responses"][status_code]
            self.assertIn("application/problem+json", response["content"])
            self.assertIn("X-Request-ID", response["headers"])
        self.assertIn("X-Request-ID", analyze["responses"]["200"]["headers"])
        self.assertEqual(
            set(analyze["responses"]),
            {"200", "401", "422", "429", "500", "503"},
        )
        self.assertEqual(analyze["security"], [{"SupabaseBearer": []}])
        self.assertTrue(
            any(parameter["name"] == "Idempotency-Key" for parameter in analyze["parameters"])
        )

        validate_input = self.schema["paths"]["/api/v1/validate-input"]["post"]
        self.assertEqual(set(validate_input["responses"]), {"200", "401", "422", "500", "503"})
        self.assertEqual(validate_input["security"], [{"SupabaseBearer": []}])
        session = self.schema["paths"]["/api/v1/session"]["get"]
        self.assertEqual(set(session["responses"]), {"200", "401", "422", "503"})
        self.assertEqual(session["security"], [{"SupabaseBearer": []}])
        self.assertTrue(
            any(parameter["name"] == "X-Tenant-ID" for parameter in session["parameters"])
        )
        health = self.schema["paths"]["/api/v1/health"]["get"]
        self.assertEqual(set(health["responses"]), {"200", "503"})
        self.assertNotIn("security", health)


class OpenApiSnapshotTests(unittest.TestCase):
    def test_generated_openapi_matches_committed_snapshot(self) -> None:
        snapshot_path = Path(__file__).with_name("snapshots") / "openapi.json"
        expected = json.loads(snapshot_path.read_text(encoding="utf-8"))

        self.assertEqual(create_app().openapi(), expected)


if __name__ == "__main__":
    unittest.main()

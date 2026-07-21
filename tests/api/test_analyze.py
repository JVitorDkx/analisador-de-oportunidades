from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.interpretation import derive_input_status
from src.pipeline import run_pipeline
from src.validation.validate_output import validate_output


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CASES_DIR = PROJECT_ROOT / "fixtures" / "cases"


def load_fixture(name: str) -> dict:
    return json.loads((CASES_DIR / name).read_text(encoding="utf-8"))


class AnalyzeEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(create_app())

    def assert_globally_valid(self, payload: dict, analysis: dict) -> None:
        pipeline = run_pipeline(payload)
        validation = validate_output(
            analysis,
            pipeline["enriched_input"],
            expected_input_status=derive_input_status(pipeline),
        )
        self.assertTrue(validation["valid"], validation["issues"])

    def test_analyze_returns_valid_v1_1_report_for_viable_opportunity(self) -> None:
        payload = load_fixture("opportunity_viable.json")

        response = self.client.post("/api/v1/analyze", json=payload)

        self.assertEqual(response.status_code, 200, response.text)
        analysis = response.json()
        self.assertEqual(analysis["schema_version"], "1.1.0")
        self.assertEqual(analysis["ranking"][0]["official_score"], 90.4)
        self.assertEqual(analysis["recommendation"], "prioritize_test")
        self.assert_globally_valid(payload, analysis)

    def test_analyze_preserves_kill_switch_rejection(self) -> None:
        payload = load_fixture("opportunity_kill_switch.json")

        response = self.client.post("/api/v1/analyze", json=payload)

        self.assertEqual(response.status_code, 200, response.text)
        analysis = response.json()
        self.assertIsNone(analysis["ranking"][0]["official_score"])
        self.assertEqual(analysis["recommendation"], "reject_for_now")
        self.assertEqual(analysis["recommendations"][0]["action"], "reject_for_now")
        self.assert_globally_valid(payload, analysis)

    def test_analyze_returns_collection_requirements_for_insufficient_data(self) -> None:
        payload = load_fixture("opportunity_insufficient_data.json")

        response = self.client.post("/api/v1/analyze", json=payload)

        self.assertEqual(response.status_code, 200, response.text)
        analysis = response.json()
        self.assertEqual(analysis["input_status"], "insufficient")
        self.assertEqual(analysis["recommendation"], "collect_more_data")
        self.assertEqual(
            analysis["recommendations"][0]["required_evidence"],
            [
                {
                    "opportunity_id": "OPP-CASE-INSUFFICIENT-001",
                    "field": "demand_signal_bundle",
                    "reason": "Falta o sinal que sustenta o CALC-* de demanda.",
                }
            ],
        )
        self.assert_globally_valid(payload, analysis)

    def test_analyze_rejects_structurally_invalid_input(self) -> None:
        payload = load_fixture("opportunity_viable.json")
        invalid_payload = copy.deepcopy(payload)
        invalid_payload.pop("analysis_id")

        response = self.client.post("/api/v1/analyze", json=invalid_payload)

        self.assertEqual(response.status_code, 422)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], "invalid_analysis_input")
        self.assertFalse(detail["validation"]["valid"])
        self.assertTrue(detail["validation"]["issues"])

    def test_analyze_rejects_non_object_json_body(self) -> None:
        response = self.client.post("/api/v1/analyze", json=[])

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()

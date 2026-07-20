from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from src.validation.validate_output import _parse_output_text, validate_output, validate_output_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = PROJECT_ROOT / "tests" / "fixtures" / "pre-test-basic.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "results" / "pre-test-basic-result.md"
INVALID_OUTPUT_PATH = PROJECT_ROOT / "tests" / "fixtures" / "invalid-output.json"


def load_input() -> dict:
    return json.loads(INPUT_PATH.read_text(encoding="utf-8"))


def load_output() -> dict:
    return _parse_output_text(OUTPUT_PATH.read_text(encoding="utf-8"))


def issue_codes(result: dict) -> set[str]:
    return {issue["code"] for issue in result["issues"]}


class ValidateOutputTests(unittest.TestCase):
    def test_valid_output(self) -> None:
        result = validate_output(load_output(), load_input())

        self.assertTrue(result["valid"])
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["issues"], [])

    def test_unknown_evidence_id(self) -> None:
        output = copy.deepcopy(load_output())
        output["ranking"][0]["evidence_ids"][0] = "OBS-FABRICATED-999"

        result = validate_output(output, load_input())

        self.assertFalse(result["valid"])
        self.assertIn("unknown_evidence_id", issue_codes(result))

    def test_changed_official_score(self) -> None:
        output = copy.deepcopy(load_output())
        output["ranking"][0]["official_score"] = 65

        result = validate_output(output, load_input())

        self.assertFalse(result["valid"])
        self.assertIn("official_score_changed", issue_codes(result))

    def test_silent_calculated_indicator_override(self) -> None:
        output = copy.deepcopy(load_output())
        output["calculated_indicators"] = [
            {
                "indicator_id": "CALC-OPPORTUNITY-SCORE-001",
                "value": 65,
            }
        ]

        result = validate_output(output, load_input())

        self.assertFalse(result["valid"])
        self.assertIn("silent_calc_override", issue_codes(result))

    def test_recommendation_incompatible_with_insufficient_data(self) -> None:
        output = copy.deepcopy(load_output())
        output["input_status"] = "insufficient"
        output["recommended_opportunity_id"] = "OPP-001"
        output["recommendation"] = "prioritize_test"
        output["confidence"] = "high"

        result = validate_output(output, load_input())

        self.assertFalse(result["valid"])
        self.assertIn("incompatible_recommendation", issue_codes(result))

    def test_unknown_recommended_opportunity(self) -> None:
        output = copy.deepcopy(load_output())
        output["recommended_opportunity_id"] = "OPP-999"

        result = validate_output(output, load_input())

        self.assertFalse(result["valid"])
        self.assertIn("unknown_recommended_opportunity", issue_codes(result))

    def test_malformed_json(self) -> None:
        result = validate_output_file(INVALID_OUTPUT_PATH, INPUT_PATH)

        self.assertFalse(result["valid"])
        self.assertIn("invalid_json", issue_codes(result))


if __name__ == "__main__":
    unittest.main()

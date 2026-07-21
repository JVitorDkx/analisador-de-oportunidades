from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.validation.validate_input import validate_input, validate_json_file


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "pre-test-basic.json"
FIXTURES_DIR = FIXTURE_PATH.parent
REFERENCES_DIR = Path(__file__).resolve().parents[2] / "references"


def load_fixture() -> dict:
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def issue_codes(result: dict) -> set[str]:
    return {issue["code"] for issue in result["issues"]}


class ValidateInputTests(unittest.TestCase):
    def test_calculated_indicator_contract(self) -> None:
        input_schema = json.loads((REFERENCES_DIR / "input-schema.json").read_text(encoding="utf-8"))
        calc_schema = json.loads((REFERENCES_DIR / "calculated-indicator-schema.json").read_text(encoding="utf-8"))

        calc_reference = input_schema["$defs"]["opportunity"]["properties"]["calculated_indicators"]["items"]["$ref"]
        self.assertEqual(calc_reference, "calculated-indicator-schema.json")
        for opportunity in load_fixture()["opportunities"]:
            for indicator in opportunity["calculated_indicators"]:
                self.assertTrue(set(calc_schema["required"]).issubset(indicator))

    def test_valid_input(self) -> None:
        payload = load_fixture()
        for opportunity in payload["opportunities"]:
            opportunity["data_quality"].update(
                {
                    "status": "complete",
                    "coverage_percent": 100,
                    "source_agreement": "high",
                }
            )

        result = validate_input(payload)

        self.assertTrue(result["valid"])
        self.assertEqual(result["status"], "sufficient")
        self.assertEqual(result["issues"], [])

    def test_partial_input(self) -> None:
        result = validate_input(load_fixture())

        self.assertTrue(result["valid"])
        self.assertEqual(result["status"], "partial")
        self.assertIn("partial_data_quality", issue_codes(result))

    def test_pre_score_input_can_omit_official_score(self) -> None:
        payload = load_fixture()
        for opportunity in payload["opportunities"]:
            opportunity["calculated_indicators"] = [
                indicator
                for indicator in opportunity["calculated_indicators"]
                if indicator["field"] != "official_score"
            ]

        result = validate_input(payload, require_official_score=False)

        self.assertTrue(result["valid"])
        self.assertNotIn("missing_official_score", issue_codes(result))

    def test_invalid_input(self) -> None:
        result = validate_json_file(FIXTURES_DIR / "invalid-input.json")

        self.assertFalse(result["valid"])
        self.assertEqual(result["status"], "invalid")
        self.assertIn("missing_required_field", issue_codes(result))
        self.assertIn("invalid_value", issue_codes(result))

    def test_duplicate_evidence_id(self) -> None:
        result = validate_json_file(FIXTURES_DIR / "duplicate-evidence.json")

        self.assertFalse(result["valid"])
        self.assertIn("duplicate_evidence_id", issue_codes(result))

    def test_missing_official_score(self) -> None:
        result = validate_json_file(FIXTURES_DIR / "missing-score.json")

        self.assertFalse(result["valid"])
        self.assertIn("missing_official_score", issue_codes(result))


if __name__ == "__main__":
    unittest.main()

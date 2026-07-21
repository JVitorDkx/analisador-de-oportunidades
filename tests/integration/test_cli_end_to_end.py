from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.interpretation import derive_input_status
from src.pipeline import run_pipeline
from src.validation.validate_output import validate_output


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CASES_DIR = PROJECT_ROOT / "fixtures" / "cases"


class CliEndToEndTests(unittest.TestCase):
    def run_fixture(self, fixture_name: str) -> tuple[dict, str, dict]:
        fixture_path = CASES_DIR / fixture_name
        with tempfile.TemporaryDirectory() as directory:
            reports_dir = Path(directory) / "reports"
            output_path = reports_dir / "analysis_result.json"
            environment = os.environ.copy()
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            environment["PYTHONUTF8"] = "1"

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.cli",
                    "--input",
                    str(fixture_path),
                    "--output",
                    str(output_path),
                ],
                cwd=PROJECT_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stderr, "")
            self.assertTrue(output_path.is_file())
            self.assertEqual(output_path.name, "analysis_result.json")
            analysis = json.loads(output_path.read_text(encoding="utf-8"))

        source = json.loads(fixture_path.read_text(encoding="utf-8"))
        pipeline = run_pipeline(source)
        validation = validate_output(
            analysis,
            pipeline["enriched_input"],
            expected_input_status=derive_input_status(pipeline),
        )
        self.assertTrue(validation["valid"], validation["issues"])
        return analysis, completed.stdout, pipeline

    def test_viable_fixture_generates_high_score_and_advance_recommendation(self) -> None:
        analysis, stdout, pipeline = self.run_fixture("opportunity_viable.json")

        self.assertEqual(pipeline["opportunity_results"][0]["status"], "scored")
        self.assertEqual(analysis["ranking"][0]["official_score"], 90.4)
        self.assertEqual(analysis["recommendation"], "prioritize_test")
        self.assertEqual(analysis["recommendations"][0]["action"], "prioritize_test")
        self.assertTrue(analysis["recommendations"][0]["evidence_ids"])
        self.assertIn("90.40", stdout)

    def test_kill_switch_fixture_is_rejected_with_corrective_recommendation(self) -> None:
        analysis, stdout, pipeline = self.run_fixture("opportunity_kill_switch.json")

        result = pipeline["opportunity_results"][0]
        self.assertEqual(result["status"], "rejected")
        self.assertIsNone(analysis["ranking"][0]["official_score"])
        self.assertEqual(analysis["recommendation"], "reject_for_now")
        self.assertEqual(analysis["recommendations"][0]["action"], "reject_for_now")
        self.assertIn(
            "CALC-CONTRIBUTION-MARGIN-AMOUNT-OPP-CASE-KILL-SWITCH-001",
            analysis["recommendations"][0]["evidence_ids"],
        )
        self.assertIn("non_positive_contribution_margin", stdout)

    def test_insufficient_fixture_lists_exact_missing_observed_evidence(self) -> None:
        analysis, stdout, pipeline = self.run_fixture("opportunity_insufficient_data.json")

        self.assertEqual(pipeline["opportunity_results"][0]["status"], "input_error")
        self.assertIsNone(analysis["ranking"][0]["official_score"])
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
        self.assertIn("collect_more_data", stdout)


if __name__ == "__main__":
    unittest.main()

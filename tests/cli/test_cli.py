from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from src.cli import run_cli
from tests.pipeline.test_pipeline import valid_pipeline_input


PROCESSED_AT = "2026-07-19T12:01:00-03:00"


class CliTests(unittest.TestCase):
    def run_case(self, payload: dict) -> tuple[int, dict, str, str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "input.json"
            output_path = root / "reports" / "analysis.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()

            code = run_cli(
                ["--input", str(input_path), "--output", str(output_path)],
                stdout=stdout,
                stderr=stderr,
                processed_at=PROCESSED_AT,
            )
            result = json.loads(output_path.read_text(encoding="utf-8"))
            return code, result, stdout.getvalue(), stderr.getvalue()

    def test_cli_writes_valid_complete_analysis_and_summary(self) -> None:
        code, result, stdout, stderr = self.run_case(valid_pipeline_input())

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(result["schema_version"], "1.1.0")
        self.assertEqual(result["ranking"][0]["official_score"], 72.0)
        self.assertEqual(result["recommendation"], "prioritize_test")
        self.assertIn("Scores oficiais:", stdout)
        self.assertIn("72.00", stdout)
        self.assertIn("REC-001", stdout)
        self.assertIn("Saída validada:", stdout)

    def test_cli_reports_kill_switch_as_valid_conclusion(self) -> None:
        payload = valid_pipeline_input()
        payload["opportunities"][0]["observed_evidence"][0]["value"]["product_cost"] = 100

        code, result, stdout, stderr = self.run_case(payload)

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(result["recommendation"], "reject_for_now")
        self.assertIn("non_positive_contribution_margin", stdout)

    def test_cli_rejects_malformed_input_without_writing_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "invalid.json"
            output_path = root / "analysis.json"
            input_path.write_text('{"schema_version":', encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()

            code = run_cli(
                ["--input", str(input_path), "--output", str(output_path)],
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(code, 1)
            self.assertFalse(output_path.exists())
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("Não foi possível concluir", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.scoring.offer_intelligence.cli import run_cli


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = PROJECT_ROOT / "fixtures" / "offer_intelligence"
EXPECTED_DIR = FIXTURES_DIR / "expected"
SCORE_CONFIG_PATH = PROJECT_ROOT / "config" / "score-v0.1.json"


class OfferIntelligenceCliTests(unittest.TestCase):
    def test_runner_isolated_from_score_engine_and_preserves_score_config(self) -> None:
        score_config_before = SCORE_CONFIG_PATH.read_bytes()
        stdout = io.StringIO()
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "nested" / "offer_intelligence.json"
            with patch(
                "src.scoring.engine.ScoreEngine.from_file",
                side_effect=AssertionError("ScoreEngine must not be invoked"),
            ) as score_engine_from_file:
                code = run_cli(
                    [
                        "--input",
                        str(FIXTURES_DIR / "offer_growth.json"),
                        "--output",
                        str(output_path),
                    ],
                    stdout=stdout,
                    stderr=stderr,
                )

            self.assertEqual(code, 0, stderr.getvalue())
            score_engine_from_file.assert_not_called()
            self.assertTrue(output_path.is_file())
            result = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(SCORE_CONFIG_PATH.read_bytes(), score_config_before)
        self.assertEqual(result["status"], "complete")
        self.assertNotIn("official_score", json.dumps(result))
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("Offer Intelligence", stdout.getvalue())
        self.assertIn("Status: complete", stdout.getvalue())
        self.assertIn("Saída validada:", stdout.getvalue())

    def test_module_cli_matches_all_committed_integration_envelopes(self) -> None:
        cases = (
            "offer_growth",
            "market_saturation",
            "insufficient_market_data",
        )
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONUTF8"] = "1"

        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                output_path = Path(directory) / "reports" / f"{case}_result.json"
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "src.scoring.offer_intelligence.cli",
                        "--input",
                        str(FIXTURES_DIR / f"{case}.json"),
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
                actual = json.loads(output_path.read_text(encoding="utf-8"))
                expected = json.loads(
                    (EXPECTED_DIR / f"{case}_result.json").read_text(encoding="utf-8")
                )
                self.assertEqual(actual, expected)
                self.assertIn(f"Status: {expected['status']}", completed.stdout)

    def test_partial_result_is_a_successful_cli_conclusion(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "partial.json"
            code = run_cli(
                [
                    "--input",
                    str(FIXTURES_DIR / "insufficient_market_data.json"),
                    "--output",
                    str(output_path),
                ],
                stdout=stdout,
                stderr=stderr,
            )
            result = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["indicators"]), 1)
        self.assertEqual(len(result["missing_inputs"]), 7)
        self.assertIn("Dados necessários:", stdout.getvalue())

    def test_invalid_json_returns_input_error_without_writing_output(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "invalid.json"
            output_path = root / "result.json"
            input_path.write_text('{"schema_version":', encoding="utf-8")

            code = run_cli(
                ["--input", str(input_path), "--output", str(output_path)],
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(code, 2)
            self.assertFalse(output_path.exists())
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Entrada inválida de Offer Intelligence", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

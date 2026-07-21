from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.pipeline import run_pipeline, run_pipeline_file, validate_pipeline_result


def observed(evidence_id: str, field: str, value, value_type: str = "number") -> dict:
    return {
        "evidence_id": evidence_id,
        "opportunity_id": "OPP-PIPE-001",
        "source_type": "synthetic_fixture",
        "source_url": "synthetic-source-1",
        "collected_at": "2026-07-18T12:00:00-03:00",
        "field": field,
        "value": value,
        "value_type": value_type,
        "collection_method": "synthetic_fixture",
        "quality": "medium",
        "notes": "Synthetic pipeline fixture."
    }


def calculated(indicator_id: str, field: str, value: int, evidence_id: str) -> dict:
    return {
        "indicator_id": indicator_id,
        "opportunity_id": "OPP-PIPE-001",
        "field": field,
        "value": value,
        "value_type": "integer",
        "unit": "0-100",
        "calculation_method": "deterministic_upstream_fixture_v1",
        "calculation_version": "UPSTREAM-FIXTURE-0.1.0",
        "calculated_at": "2026-07-19T11:55:00-03:00",
        "source_evidence_ids": [evidence_id],
        "quality": "medium",
        "warnings": []
    }


def valid_pipeline_input() -> dict:
    economics = {
        "selling_price": 100,
        "product_cost": 30,
        "variable_fees": 10,
        "taxes": 5,
        "shipping_subsidy": 5,
        "other_variable_costs": 0,
        "currency": "BRL"
    }
    evidence = [
        observed("OBS-PIPE-ECON", "economic_inputs", economics, "object"),
        observed("OBS-PIPE-MINCOST", "minimum_test_cost", 250),
        observed("OBS-PIPE-BUDGET", "operator_test_budget", 500),
        observed("OBS-PIPE-FIT", "operational_fit", "acceptable_fit", "string"),
        observed("OBS-PIPE-DEMAND", "demand_signal_bundle", "synthetic", "string"),
        observed("OBS-PIPE-COMP", "competitive_signal_bundle", "synthetic", "string"),
        observed("OBS-PIPE-LOGISTICS", "logistics_lead_time_business_days", 20, "integer"),
    ]
    indicators = [
        calculated("CALC-PIPE-DEMAND", "demand_score", 80, "OBS-PIPE-DEMAND"),
        calculated("CALC-PIPE-ECONOMICS", "economics_score", 70, "OBS-PIPE-ECON"),
        calculated(
            "CALC-PIPE-COMPETITIVE",
            "competitive_attractiveness_score",
            60,
            "OBS-PIPE-COMP",
        ),
    ]
    return {
        "schema_version": "1.0.0",
        "analysis_id": "ANL-PIPE-0001",
        "generated_at": "2026-07-19T12:00:00-03:00",
        "analysis_mode": "campaign_diagnosis",
        "user_context": {
            "country": "BR",
            "language": "pt-BR",
            "experience_level": "beginner",
            "business_model": "ecommerce",
            "primary_channel": "meta",
            "test_budget_brl": 500,
            "maximum_test_days": 7,
            "target_margin_percent": None,
            "maximum_acceptable_cpa": None,
            "available_team": [],
            "operational_constraints": [],
            "excluded_categories": [],
            "objectives": []
        },
        "opportunities": [
            {
                "opportunity_id": "OPP-PIPE-001",
                "name": "Synthetic Pipeline Opportunity",
                "category": "synthetic",
                "description": "No real person, company, or offer.",
                "source_urls": [],
                "observed_evidence": evidence,
                "calculated_indicators": indicators,
                "campaign_metrics": None,
                "data_quality": {
                    "status": "complete",
                    "coverage_percent": 80,
                    "freshness": "current",
                    "source_agreement": "medium"
                },
                "collection_errors": [],
                "risk_flags": [],
                "scoring_context": {
                    "economic_inputs_evidence_id": "OBS-PIPE-ECON",
                    "minimum_test_cost_evidence_id": "OBS-PIPE-MINCOST",
                    "operator_budget_evidence_id": "OBS-PIPE-BUDGET",
                    "operational_fit_evidence_id": "OBS-PIPE-FIT",
                    "logistics_evidence_id": "OBS-PIPE-LOGISTICS",
                    "independent_source_ids": ["synthetic-source-1"],
                    "calculation_quality": "medium"
                }
            }
        ],
        "score_configuration": {
            "version": "SCORE-0.1.0",
            "weights": {},
            "calculation_timestamp": "2026-07-19T11:59:00-03:00",
            "engine": "deterministic-score-engine"
        },
        "requested_output_language": "pt-BR"
    }


def valid_final_output() -> dict:
    return {
        "schema_version": "1.0.0",
        "analysis_id": "ANL-PIPE-0001",
        "analysis_mode": "campaign_diagnosis",
        "processed_at": "2026-07-19T12:01:00-03:00",
        "input_status": "sufficient",
        "security_status": {
            "prompt_injection_detected": False,
            "suspicious_fields": [],
            "sensitive_data_detected": False
        },
        "versions": {
            "skill_version": "1.0.1",
            "input_schema_version": "1.0.0",
            "output_schema_version": "1.0.0",
            "score_version": "SCORE-0.1.0"
        },
        "recommended_opportunity_id": "OPP-PIPE-001",
        "recommendation": "prioritize_test",
        "confidence": "moderate",
        "executive_summary": "Synthetic deterministic pipeline output.",
        "context_assessment": {
            "fit": "acceptable_fit",
            "budget_compatibility": "compatible",
            "channel_compatibility": "moderate",
            "operational_constraints": [],
            "explanation": "Synthetic fixture only."
        },
        "ranking": [
            {
                "position": 1,
                "opportunity_id": "OPP-PIPE-001",
                "official_score": 72,
                "official_score_scale": "0-100",
                "official_score_rank": 1,
                "contextual_recommendation_rank": 1,
                "context_fit": "acceptable_fit",
                "strengths": [],
                "weaknesses": [],
                "risks": [],
                "module_assessments": {},
                "evidence_ids": ["CALC-OFFICIAL-SCORE-OPP-PIPE-001"]
            }
        ],
        "favorable_evidence": [],
        "contrary_evidence": [],
        "inferences": [],
        "source_conflicts": [],
        "missing_data": [],
        "calculation_warnings": [],
        "next_experiment": {
            "experiment_id": "EXP-PIPE-001",
            "objective": "Collect deterministic feedback.",
            "hypothesis": "The controlled test will add evidence.",
            "primary_variable": "synthetic_variable",
            "control_variable": None,
            "minimum_action": "Run only an authorized controlled test.",
            "maximum_budget": 500,
            "currency": "BRL",
            "duration_days": 7,
            "success_metrics": [],
            "success_conditions": [],
            "stop_conditions": ["Reach authorized budget."],
            "required_feedback_fields": []
        },
        "conditions_that_would_change_recommendation": [],
        "human_review": {
            "required": False,
            "reasons": []
        },
        "disclaimer": "Esta análise prioriza hipóteses e próximos testes; não garante vendas, faturamento ou rentabilidade."
    }


class PipelineTests(unittest.TestCase):
    def test_end_to_end_scoring_enriches_a_copy(self) -> None:
        source = valid_pipeline_input()
        result = run_pipeline(source)

        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["pipeline_validation"]["valid"])
        self.assertTrue(result["enriched_input_validation"]["valid"])
        self.assertEqual(result["opportunity_results"][0]["official_score"], 72.0)
        self.assertEqual(result["opportunity_results"][0]["official_rank"], 1)
        enriched_fields = {
            item["field"]
            for item in result["enriched_input"]["opportunities"][0]["calculated_indicators"]
        }
        self.assertIn("official_score", enriched_fields)
        self.assertNotIn(
            "official_score",
            {item["field"] for item in source["opportunities"][0]["calculated_indicators"]},
        )

    def test_valid_final_output_is_validated_against_enriched_input(self) -> None:
        result = run_pipeline(valid_pipeline_input(), final_output=valid_final_output())

        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["final_output_validation"]["valid"])

    def test_invalid_final_output_marks_pipeline_invalid(self) -> None:
        result = run_pipeline(valid_pipeline_input(), final_output={})

        self.assertEqual(result["status"], "invalid")
        self.assertFalse(result["final_output_validation"]["valid"])
        self.assertTrue(result["pipeline_validation"]["valid"])

    def test_missing_scoring_context_is_partial_not_fabricated(self) -> None:
        payload = valid_pipeline_input()
        del payload["opportunities"][0]["scoring_context"]

        result = run_pipeline(payload)

        self.assertEqual(result["status"], "partial")
        self.assertIsNone(result["opportunity_results"][0]["official_score"])
        self.assertIn("scoring_context is required", result["opportunity_results"][0]["eligibility_issues"][0])

    def test_preexisting_official_score_is_not_overwritten(self) -> None:
        payload = valid_pipeline_input()
        preexisting = calculated(
            "CALC-PREEXISTING-OFFICIAL",
            "official_score",
            99,
            "OBS-PIPE-DEMAND",
        )
        payload["opportunities"][0]["calculated_indicators"].append(preexisting)

        result = run_pipeline(payload)

        self.assertEqual(result["status"], "partial")
        self.assertIn("cannot contain an official_score", result["opportunity_results"][0]["eligibility_issues"][0])

    def test_kill_switch_rejection_is_a_completed_deterministic_result(self) -> None:
        payload = valid_pipeline_input()
        payload["opportunities"][0]["observed_evidence"][0]["value"]["product_cost"] = 100

        result = run_pipeline(payload)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["opportunity_results"][0]["status"], "rejected")
        self.assertIsNone(result["opportunity_results"][0]["official_score"])

    def test_low_coverage_returns_partial_without_score(self) -> None:
        payload = valid_pipeline_input()
        payload["opportunities"][0]["data_quality"]["coverage_percent"] = 69

        result = run_pipeline(payload)

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["opportunity_results"][0]["status"], "insufficient_data")
        self.assertIsNone(result["opportunity_results"][0]["official_score"])

    def test_pipeline_validator_detects_fabricated_evidence(self) -> None:
        result = run_pipeline(valid_pipeline_input())
        tampered = copy.deepcopy(result)
        tampered["opportunity_results"][0]["indicators"][-1]["source_evidence_ids"] = [
            "OBS-FABRICATED-999"
        ]

        validation = validate_pipeline_result(tampered)

        self.assertFalse(validation["valid"])
        self.assertIn("unknown_evidence_id", {item["code"] for item in validation["issues"]})

    def test_pipeline_validator_detects_coordinated_score_tampering(self) -> None:
        result = run_pipeline(valid_pipeline_input())
        tampered = copy.deepcopy(result)
        tampered["opportunity_results"][0]["official_score"] = 99.0
        tampered["opportunity_results"][0]["indicators"][-1]["value"] = 99.0

        validation = validate_pipeline_result(tampered)

        self.assertFalse(validation["valid"])
        self.assertIn("indicator_mismatch", {item["code"] for item in validation["issues"]})

    def test_independent_sources_must_be_backed_by_observed_evidence(self) -> None:
        payload = valid_pipeline_input()
        payload["opportunities"][0]["scoring_context"]["independent_source_ids"] = [
            "invented-source"
        ]

        result = run_pipeline(payload)

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["opportunity_results"][0]["status"], "input_error")
        self.assertIn(
            "must reference observed evidence sources",
            result["opportunity_results"][0]["eligibility_issues"][0],
        )

    def test_malformed_input_file_returns_structured_invalid_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text('{"schema_version":', encoding="utf-8")

            result = run_pipeline_file(path)

        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["input_validation"]["issues"][0]["code"], "invalid_json")
        self.assertTrue(result["pipeline_validation"]["valid"])

    def test_malformed_final_output_preserves_processed_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "input.json"
            output_path = root / "output.md"
            input_path.write_text(json.dumps(valid_pipeline_input()), encoding="utf-8")
            output_path.write_text('```json\n{"broken":\n```', encoding="utf-8")

            result = run_pipeline_file(input_path, final_output_path=output_path)

        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["analysis_id"], "ANL-PIPE-0001")
        self.assertTrue(result["input_validation"]["valid"])
        self.assertEqual(result["opportunity_results"][0]["status"], "scored")
        self.assertEqual(result["final_output_validation"]["issues"][0]["code"], "invalid_json")
        self.assertTrue(result["pipeline_validation"]["valid"])


if __name__ == "__main__":
    unittest.main()

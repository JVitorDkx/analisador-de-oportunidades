from __future__ import annotations

import json
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from src.scoring.engine import ScoreEngine, assign_shared_ranks
from src.scoring.models import (
    DimensionScoreInput,
    EconomicInputs,
    OpportunityScoreInput,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "score-v0.1.json"
CALC_SCHEMA_PATH = PROJECT_ROOT / "references" / "calculated-indicator-schema.json"


def dimension_score(
    value: str | None,
    indicator_id: str,
    evidence_id: str,
    quality: str,
) -> DimensionScoreInput:
    if value is None:
        return DimensionScoreInput(None, (evidence_id,), quality)
    return DimensionScoreInput(
        value=value,
        source_evidence_ids=(evidence_id,),
        quality=quality,
        indicator_id=indicator_id,
        calculation_method="deterministic_upstream_fixture_v1",
        calculation_version="UPSTREAM-FIXTURE-0.1.0",
    )


def valid_payload(**changes) -> OpportunityScoreInput:
    payload = OpportunityScoreInput(
        opportunity_id="OPP-ENGINE-001",
        demand=dimension_score("80", "CALC-DEMAND-SCORE-001", "OBS-DEMAND-001", "high"),
        economics=dimension_score("70", "CALC-ECONOMICS-SCORE-001", "OBS-ECON-001", "high"),
        competitive_attractiveness=dimension_score(
            "60",
            "CALC-COMPETITIVE-SCORE-001",
            "OBS-COMP-001",
            "medium",
        ),
        operational_fit="acceptable_fit",
        operational_fit_source_evidence_ids=("OBS-OPERATOR-001",),
        economic_inputs=EconomicInputs(
            selling_price="100",
            product_cost="30",
            variable_fees="10",
            taxes="5",
            shipping_subsidy="5",
            other_variable_costs="0",
            currency="BRL",
            source_evidence_ids=("OBS-ECON-001",),
        ),
        minimum_test_cost="250",
        operator_test_budget="500",
        budget_source_evidence_ids=("OBS-BUDGET-001",),
        evidence_coverage_percent="70",
        demand_evidence_age_days=30,
        economic_data_age_days=60,
        independent_source_count=1,
        logistics_lead_time_business_days=20,
        calculated_at="2026-07-20T12:00:00-03:00",
        calculation_quality="medium",
    )
    return replace(payload, **changes)


class ScoreEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ScoreEngine.from_file(CONFIG_PATH)

    def test_authorized_config(self) -> None:
        self.assertEqual(self.engine.score_version, "SCORE-0.1.0")
        self.assertEqual(self.engine.weights["demand"], Decimal("0.3"))
        self.assertEqual(self.engine.weights["economics"], Decimal("0.3"))
        self.assertEqual(self.engine.weights["competitive_attractiveness"], Decimal("0.2"))
        self.assertEqual(self.engine.weights["operator_fit"], Decimal("0.2"))

    def test_dimension_number_without_calc_metadata_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires a valid CALC"):
            DimensionScoreInput("80", ("OBS-DEMAND-001",), "high")

    def test_valid_score_and_indicators(self) -> None:
        result = self.engine.score(valid_payload())

        self.assertEqual(result.status, "scored")
        self.assertEqual(result.official_score, Decimal("72.00"))
        fields = {indicator.field: indicator for indicator in result.indicators}
        self.assertEqual(fields["contribution_margin_amount"].value, Decimal("50"))
        self.assertEqual(fields["contribution_margin_percent"].value, Decimal("50"))
        self.assertEqual(fields["break_even_cpa"].value, Decimal("50"))
        self.assertEqual(fields["budget_fit_ratio"].value, Decimal("0.5"))
        self.assertEqual(fields["operator_fit_score"].value, Decimal("75"))
        self.assertEqual(fields["official_score"].value, Decimal("72.00"))

    def test_generated_indicators_follow_calc_contract(self) -> None:
        required = set(json.loads(CALC_SCHEMA_PATH.read_text(encoding="utf-8"))["required"])

        for indicator in self.engine.score(valid_payload()).indicators:
            serialized = indicator.as_dict()
            self.assertTrue(required.issubset(serialized))
            self.assertTrue(serialized["indicator_id"].startswith("CALC-"))
            self.assertTrue(all(item.startswith("OBS-") for item in serialized["source_evidence_ids"]))
            self.assertTrue(serialized["calculation_version"])

    def test_provided_dimension_calc_is_preserved(self) -> None:
        result = self.engine.score(valid_payload())
        demand = next(item for item in result.indicators if item.field == "demand_score")

        self.assertEqual(demand.indicator_id, "CALC-DEMAND-SCORE-001")
        self.assertEqual(demand.value, Decimal("80"))
        self.assertEqual(demand.calculation_method, "deterministic_upstream_fixture_v1")
        self.assertEqual(demand.calculation_version, "UPSTREAM-FIXTURE-0.1.0")
        self.assertEqual(demand.source_evidence_ids, ("OBS-DEMAND-001",))

    def test_missing_dimension_returns_null_without_renormalization(self) -> None:
        result = self.engine.score(
            valid_payload(
                demand=dimension_score(
                    None,
                    "CALC-DEMAND-SCORE-001",
                    "OBS-DEMAND-001",
                    "low",
                )
            )
        )

        self.assertEqual(result.status, "insufficient_data")
        self.assertIsNone(result.official_score)
        self.assertEqual(result.missing_dimensions, ("demand",))

    def test_evidence_eligibility_boundaries(self) -> None:
        cases = (
            ("evidence_coverage_below_minimum", {"evidence_coverage_percent": "69.99"}),
            ("demand_evidence_too_old", {"demand_evidence_age_days": 31}),
            ("economic_data_too_old", {"economic_data_age_days": 61}),
            ("independent_sources_below_minimum", {"independent_source_count": 0}),
        )
        for expected_issue, changes in cases:
            with self.subTest(expected_issue=expected_issue):
                result = self.engine.score(valid_payload(**changes))
                self.assertEqual(result.status, "insufficient_data")
                self.assertIsNone(result.official_score)
                self.assertIn(expected_issue, result.eligibility_issues)

    def test_non_positive_margin_rejects_opportunity(self) -> None:
        economic_inputs = replace(valid_payload().economic_inputs, product_cost=Decimal("100"))

        result = self.engine.score(valid_payload(economic_inputs=economic_inputs))

        self.assertEqual(result.status, "rejected")
        self.assertIsNone(result.official_score)
        self.assertTrue(result.kill_switches[0].triggered)

    def test_test_cost_above_budget_rejects_opportunity(self) -> None:
        result = self.engine.score(valid_payload(minimum_test_cost="500.01"))

        self.assertEqual(result.status, "rejected")
        self.assertIsNone(result.official_score)
        self.assertTrue(result.kill_switches[1].triggered)

    def test_unknown_operational_fit_returns_missing_dimension(self) -> None:
        result = self.engine.score(valid_payload(operational_fit="unknown"))

        self.assertEqual(result.status, "insufficient_data")
        self.assertIn("operator_fit", result.missing_dimensions)

    def test_reference_thresholds_create_warnings_not_kill_switches(self) -> None:
        low_margin_inputs = replace(
            valid_payload().economic_inputs,
            product_cost=Decimal("70"),
            variable_fees=Decimal("5"),
            taxes=Decimal("5"),
            shipping_subsidy=Decimal("0"),
            other_variable_costs=Decimal("0"),
        )

        result = self.engine.score(
            valid_payload(
                economic_inputs=low_margin_inputs,
                logistics_lead_time_business_days=21,
            )
        )

        self.assertEqual(result.status, "scored")
        self.assertIn("contribution_margin_below_ideal_reference", result.warnings)
        self.assertIn("logistics_lead_time_exceeds_reference", result.warnings)

    def test_raw_score_is_preserved_and_display_is_rounded(self) -> None:
        result = self.engine.score(
            valid_payload(
                demand=dimension_score(
                    "80.1234",
                    "CALC-DEMAND-SCORE-001",
                    "OBS-DEMAND-001",
                    "high",
                ),
            )
        )
        serialized = result.as_dict(display_precision=2)

        self.assertEqual(result.official_score, Decimal("72.037020"))
        self.assertEqual(serialized["official_score_display"], "72.04")

    def test_shared_ranking_uses_raw_scores(self) -> None:
        base = self.engine.score(valid_payload())
        tied = replace(base, opportunity_id="OPP-ENGINE-002")
        lower = replace(base, opportunity_id="OPP-ENGINE-003", official_score=Decimal("71.999"))

        ranked = assign_shared_ranks((lower, tied, base))
        ranks = {result.opportunity_id: result.official_rank for result in ranked}

        self.assertEqual(ranks["OPP-ENGINE-001"], 1)
        self.assertEqual(ranks["OPP-ENGINE-002"], 1)
        self.assertEqual(ranks["OPP-ENGINE-003"], 3)

    def test_invalid_config_weight_sum_is_rejected(self) -> None:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        config["dimensions"]["operator_fit"]["weight"] = 0.19

        with self.assertRaisesRegex(ValueError, "sum exactly to 1"):
            ScoreEngine(config)


if __name__ == "__main__":
    unittest.main()

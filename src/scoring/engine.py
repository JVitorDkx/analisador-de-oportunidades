"""Versioned orchestration for the deterministic SCORE-0.1.0 engine."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from src.scoring.indicators import (
    break_even_cpa,
    budget_fit_ratio,
    contribution_margin_amount,
    contribution_margin_percent,
    operational_fit_score,
)
from src.scoring.kill_switches import (
    evaluate_non_positive_contribution_margin,
    evaluate_test_cost_exceeds_budget,
)
from src.scoring.models import (
    DIMENSION_NAMES,
    CalculatedIndicator,
    OpportunityScoreInput,
    ScoreResult,
    decimal_value,
)
from src.scoring.normalization import weighted_score


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "score-v0.1.json"


class ScoreEngine:
    """Calculate authorized indicators and aggregate the official score without AI."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._validate_config()
        self.score_version = config["score_version"]
        self.minimum = decimal_value(config["scale"]["minimum"], "scale.minimum", allow_none=False)
        self.maximum = decimal_value(config["scale"]["maximum"], "scale.maximum", allow_none=False)
        self.display_precision = int(config["scale"]["display_precision"])
        self.weights = {
            name: decimal_value(config["dimensions"][name]["weight"], f"weight.{name}", allow_none=False)
            for name in DIMENSION_NAMES
        }
        self.operational_fit_mapping = {
            name: decimal_value(value, f"operational_fit_mapping.{name}")
            for name, value in config["operational_fit_mapping"].items()
        }

    @classmethod
    def from_file(cls, path: str | Path = DEFAULT_CONFIG_PATH) -> "ScoreEngine":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls(json.load(handle))

    def _validate_config(self) -> None:
        required = {
            "config_schema_version",
            "score_version",
            "status",
            "scale",
            "dimensions",
            "operational_fit_mapping",
            "economic_indicators",
            "eligibility",
            "kill_switches",
        }
        missing = sorted(required - set(self.config))
        if missing:
            raise ValueError(f"score configuration is missing: {', '.join(missing)}")
        if self.config["score_version"] != "SCORE-0.1.0":
            raise ValueError("unsupported score version")
        if self.config["status"] != "authorized":
            raise ValueError("score configuration is not authorized")
        scale = self.config["scale"]
        if scale.get("missing_value_policy") != "return_null":
            raise ValueError("SCORE-0.1.0 requires return_null for missing values")
        if scale.get("missing_dimension_policy") != "do_not_renormalize":
            raise ValueError("SCORE-0.1.0 cannot redistribute missing weights")
        if scale.get("tie_policy") != "shared_rank":
            raise ValueError("SCORE-0.1.0 requires shared ranks")
        if set(self.config["dimensions"]) != set(DIMENSION_NAMES):
            raise ValueError("score configuration contains unexpected dimensions")
        weights = [
            decimal_value(self.config["dimensions"][name]["weight"], f"weight.{name}", allow_none=False)
            for name in DIMENSION_NAMES
        ]
        if sum(weights, Decimal("0")) != Decimal("1"):
            raise ValueError("dimension weights must sum exactly to 1")

    def score(self, payload: OpportunityScoreInput) -> ScoreResult:
        self._validate_calculated_at(payload.calculated_at)
        contribution_amount = contribution_margin_amount(payload.economic_inputs)
        contribution_percent = contribution_margin_percent(payload.economic_inputs)
        break_even = break_even_cpa(payload.economic_inputs)
        budget_ratio = budget_fit_ratio(payload.minimum_test_cost, payload.operator_test_budget)
        operator_score = operational_fit_score(payload.operational_fit, self.operational_fit_mapping)

        indicators: list[CalculatedIndicator] = []
        for dimension_name, dimension in (
            ("demand", payload.demand),
            ("economics", payload.economics),
            ("competitive_attractiveness", payload.competitive_attractiveness),
        ):
            if dimension.value is not None:
                indicators.append(
                    CalculatedIndicator(
                        indicator_id=dimension.indicator_id,
                        opportunity_id=payload.opportunity_id,
                        field=f"{dimension_name}_score",
                        value=dimension.value,
                        unit="0-100",
                        calculation_method=dimension.calculation_method,
                        calculation_version=dimension.calculation_version,
                        calculated_at=payload.calculated_at,
                        source_evidence_ids=dimension.source_evidence_ids,
                        quality=dimension.quality,
                        warnings=(),
                    )
                )
        economic_specs = self.config["economic_indicators"]
        if contribution_amount is not None:
            indicators.append(
                self._indicator(
                    payload,
                    "contribution_margin_amount",
                    contribution_amount,
                    payload.economic_inputs.currency,
                    economic_specs["contribution_margin_amount"]["calculation_method"],
                    payload.economic_inputs.source_evidence_ids,
                )
            )
        if contribution_percent is not None:
            indicators.append(
                self._indicator(
                    payload,
                    "contribution_margin_percent",
                    contribution_percent,
                    "percent",
                    economic_specs["contribution_margin_percent"]["calculation_method"],
                    payload.economic_inputs.source_evidence_ids,
                )
            )
        if break_even is not None:
            indicators.append(
                self._indicator(
                    payload,
                    "break_even_cpa",
                    break_even,
                    payload.economic_inputs.currency,
                    economic_specs["break_even_cpa"]["calculation_method"],
                    payload.economic_inputs.source_evidence_ids,
                )
            )
        if budget_ratio is not None:
            indicators.append(
                self._indicator(
                    payload,
                    "budget_fit_ratio",
                    budget_ratio,
                    "ratio",
                    economic_specs["budget_fit_ratio"]["calculation_method"],
                    payload.budget_source_evidence_ids,
                )
            )
        if operator_score is not None:
            indicators.append(
                self._indicator(
                    payload,
                    "operator_fit_score",
                    operator_score,
                    "0-100",
                    "authorized_operational_fit_mapping_v1",
                    payload.operational_fit_source_evidence_ids,
                )
            )

        kill_switches = (
            evaluate_non_positive_contribution_margin(
                contribution_amount,
                enabled=bool(self.config["kill_switches"]["non_positive_contribution_margin"]["enabled"]),
            ),
            evaluate_test_cost_exceeds_budget(
                payload.minimum_test_cost,
                payload.operator_test_budget,
                enabled=bool(self.config["kill_switches"]["test_cost_exceeds_budget"]["enabled"]),
            ),
        )

        eligibility_issues = self._eligibility_issues(payload, contribution_amount)
        warnings = self._warnings(payload, contribution_percent)
        dimension_scores = {
            "demand": payload.demand.value,
            "economics": payload.economics.value,
            "competitive_attractiveness": payload.competitive_attractiveness.value,
            "operator_fit": operator_score,
        }
        missing_dimensions = tuple(name for name, value in dimension_scores.items() if value is None)

        if any(decision.triggered for decision in kill_switches):
            status = "rejected"
            official_score = None
        elif eligibility_issues or missing_dimensions:
            status = "insufficient_data"
            official_score = None
        else:
            official_score = weighted_score(
                dimension_scores,
                self.weights,
                minimum=self.minimum,
                maximum=self.maximum,
            )
            status = "scored"
            source_ids = self._official_score_evidence_ids(payload)
            indicators.append(
                self._indicator(
                    payload,
                    "official_score",
                    official_score,
                    "0-100",
                    "authorized_weighted_sum_30_30_20_20_v1",
                    source_ids,
                )
            )

        return ScoreResult(
            opportunity_id=payload.opportunity_id,
            score_version=self.score_version,
            status=status,
            official_score=official_score,
            official_rank=None,
            indicators=tuple(indicators),
            kill_switches=kill_switches,
            missing_dimensions=missing_dimensions,
            eligibility_issues=tuple(eligibility_issues),
            warnings=tuple(warnings),
        )

    def _eligibility_issues(
        self,
        payload: OpportunityScoreInput,
        contribution_amount: Decimal | None,
    ) -> list[str]:
        eligibility = self.config["eligibility"]
        issues: list[str] = []
        if payload.evidence_coverage_percent < decimal_value(
            eligibility["minimum_evidence_coverage_percent"],
            "minimum_evidence_coverage_percent",
            allow_none=False,
        ):
            issues.append("evidence_coverage_below_minimum")
        if payload.demand_evidence_age_days > int(eligibility["maximum_demand_evidence_age_days"]):
            issues.append("demand_evidence_too_old")
        if payload.economic_data_age_days > int(eligibility["maximum_economic_data_age_days"]):
            issues.append("economic_data_too_old")
        if payload.independent_source_count < int(eligibility["minimum_independent_sources"]):
            issues.append("independent_sources_below_minimum")
        if contribution_amount is None:
            issues.append("contribution_margin_not_determinable")
        if payload.minimum_test_cost is None or payload.operator_test_budget is None:
            issues.append("budget_fit_not_determinable")
        return issues

    def _warnings(
        self,
        payload: OpportunityScoreInput,
        contribution_percent: Decimal | None,
    ) -> list[str]:
        warnings: list[str] = []
        logistics_limit = int(self.config["eligibility"]["maximum_logistics_lead_time_business_days"])
        if (
            payload.logistics_lead_time_business_days is not None
            and payload.logistics_lead_time_business_days > logistics_limit
        ):
            warnings.append("logistics_lead_time_exceeds_reference")
        ideal_margin = decimal_value(
            self.config["economic_indicators"]["contribution_margin_percent"]["ideal_reference_minimum"],
            "ideal_reference_minimum",
            allow_none=False,
        )
        if contribution_percent is not None and Decimal("0") < contribution_percent < ideal_margin:
            warnings.append("contribution_margin_below_ideal_reference")
        return warnings

    def _indicator(
        self,
        payload: OpportunityScoreInput,
        field: str,
        value: Decimal,
        unit: str,
        method: str,
        evidence_ids: Iterable[str],
    ) -> CalculatedIndicator:
        indicator_name = field.replace("_", "-").upper()
        unique_evidence_ids = tuple(dict.fromkeys(evidence_ids))
        return CalculatedIndicator(
            indicator_id=f"CALC-{indicator_name}-{payload.opportunity_id}",
            opportunity_id=payload.opportunity_id,
            field=field,
            value=value,
            unit=unit,
            calculation_method=method,
            calculation_version=self.score_version,
            calculated_at=payload.calculated_at,
            source_evidence_ids=unique_evidence_ids,
            quality=payload.calculation_quality,
            warnings=(),
        )

    @staticmethod
    def _validate_calculated_at(value: str) -> None:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (AttributeError, ValueError) as exc:
            raise ValueError("calculated_at must be a valid ISO-8601 datetime") from exc
        if parsed.tzinfo is None:
            raise ValueError("calculated_at must include a timezone")

    @staticmethod
    def _official_score_evidence_ids(payload: OpportunityScoreInput) -> tuple[str, ...]:
        combined = (
            *payload.demand.source_evidence_ids,
            *payload.economics.source_evidence_ids,
            *payload.competitive_attractiveness.source_evidence_ids,
            *payload.operational_fit_source_evidence_ids,
        )
        return tuple(dict.fromkeys(combined))


def assign_shared_ranks(results: Iterable[ScoreResult]) -> tuple[ScoreResult, ...]:
    """Assign competition ranks (1, 1, 3) using raw, unrounded official scores."""

    result_list = list(results)
    scored = sorted(
        (result for result in result_list if result.official_score is not None),
        key=lambda result: (-result.official_score, result.opportunity_id),
    )
    ranked: dict[str, ScoreResult] = {}
    previous_score: Decimal | None = None
    previous_rank: int | None = None
    for position, result in enumerate(scored, start=1):
        if previous_score is not None and result.official_score == previous_score:
            rank = previous_rank
        else:
            rank = position
        ranked[result.opportunity_id] = result.with_rank(rank)
        previous_score = result.official_score
        previous_rank = rank
    return tuple(
        ranked.get(result.opportunity_id, result.with_rank(None))
        for result in sorted(result_list, key=lambda item: item.opportunity_id)
    )

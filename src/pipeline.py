"""End-to-end deterministic pipeline for Opportunity Analyst.

The pipeline validates a pre-score input, builds explicit engine inputs from
referenced OBS-* and CALC-* records, runs SCORE-0.1.0, enriches a copy of the
input, and optionally validates a final analysis output. It never invokes AI.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from src.scoring.engine import ScoreEngine, assign_shared_ranks
from src.scoring.models import DimensionScoreInput, EconomicInputs, OpportunityScoreInput, decimal_value
from src.validation.validate_input import validate_input
from src.validation.validate_output import parse_output_text, validate_output


PIPELINE_VERSION = "0.1.0"
DIMENSION_FIELDS = {
    "demand": "demand_score",
    "economics": "economics_score",
    "competitive_attractiveness": "competitive_attractiveness_score",
}
ECONOMIC_FIELDS = (
    "selling_price",
    "product_cost",
    "variable_fees",
    "taxes",
    "shipping_subsidy",
    "other_variable_costs",
)


class PipelineInputError(ValueError):
    """Raised when explicit scoring references are absent or inconsistent."""


def _issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message, "severity": "error"}


def _validation_result(issues: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "status": "invalid" if issues else "valid",
        "valid": not issues,
        "error_count": len(issues),
        "warning_count": 0,
        "issues": issues,
    }


def _parse_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise PipelineInputError(f"{field} must be an ISO-8601 datetime")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PipelineInputError(f"{field} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise PipelineInputError(f"{field} must include a timezone")
    return parsed


def _age_days(reference: datetime, collected_at: Any, field: str) -> int:
    collected = _parse_datetime(collected_at, field)
    seconds = (reference - collected).total_seconds()
    if seconds < 0:
        raise PipelineInputError(f"{field} cannot be later than generated_at")
    return math.ceil(seconds / 86400)


def _evidence_index(opportunity: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for evidence in opportunity.get("observed_evidence", []):
        if isinstance(evidence, dict) and isinstance(evidence.get("evidence_id"), str):
            result[evidence["evidence_id"]] = evidence
    return result


def _referenced_evidence(
    context: dict[str, Any],
    context_field: str,
    expected_observed_field: str,
    evidence_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    evidence_id = context.get(context_field)
    if not isinstance(evidence_id, str) or evidence_id not in evidence_by_id:
        raise PipelineInputError(f"scoring_context.{context_field} must reference an existing OBS-* record")
    evidence = evidence_by_id[evidence_id]
    if evidence.get("field") != expected_observed_field:
        raise PipelineInputError(
            f"{evidence_id} must use field={expected_observed_field}, got {evidence.get('field')!r}"
        )
    return evidence


def _dimension_input(
    opportunity: dict[str, Any],
    dimension_name: str,
) -> DimensionScoreInput:
    field = DIMENSION_FIELDS[dimension_name]
    matches = [
        indicator
        for indicator in opportunity.get("calculated_indicators", [])
        if isinstance(indicator, dict) and indicator.get("field") == field
    ]
    if len(matches) != 1:
        raise PipelineInputError(f"exactly one provided CALC-* with field={field} is required")
    indicator = matches[0]
    return DimensionScoreInput(
        value=indicator.get("value"),
        source_evidence_ids=tuple(indicator.get("source_evidence_ids", [])),
        quality=indicator.get("quality", "unknown"),
        indicator_id=indicator.get("indicator_id"),
        calculation_method=indicator.get("calculation_method"),
        calculation_version=indicator.get("calculation_version"),
        calculated_at=indicator.get("calculated_at"),
    )


def _maximum_referenced_age(
    dimension: DimensionScoreInput,
    evidence_by_id: dict[str, dict[str, Any]],
    generated_at: datetime,
) -> int:
    if not dimension.source_evidence_ids:
        raise PipelineInputError("a provided dimension CALC-* must reference at least one OBS-* record")
    ages: list[int] = []
    for evidence_id in dimension.source_evidence_ids:
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            raise PipelineInputError(f"dimension CALC-* references unknown evidence: {evidence_id}")
        ages.append(_age_days(generated_at, evidence.get("collected_at"), f"{evidence_id}.collected_at"))
    return max(ages)


def build_engine_input(
    data: dict[str, Any],
    opportunity: dict[str, Any],
) -> OpportunityScoreInput:
    """Build the typed engine input exclusively from explicit references."""

    context = opportunity.get("scoring_context")
    if not isinstance(context, dict):
        raise PipelineInputError("scoring_context is required for end-to-end scoring")
    if any(
        isinstance(indicator, dict) and indicator.get("field") == "official_score"
        for indicator in opportunity.get("calculated_indicators", [])
    ):
        raise PipelineInputError("pre-score input cannot contain an official_score CALC-*")

    evidence_by_id = _evidence_index(opportunity)
    economic_evidence = _referenced_evidence(
        context,
        "economic_inputs_evidence_id",
        "economic_inputs",
        evidence_by_id,
    )
    minimum_cost_evidence = _referenced_evidence(
        context,
        "minimum_test_cost_evidence_id",
        "minimum_test_cost",
        evidence_by_id,
    )
    budget_evidence = _referenced_evidence(
        context,
        "operator_budget_evidence_id",
        "operator_test_budget",
        evidence_by_id,
    )
    fit_evidence = _referenced_evidence(
        context,
        "operational_fit_evidence_id",
        "operational_fit",
        evidence_by_id,
    )

    economic_values = economic_evidence.get("value")
    if not isinstance(economic_values, dict):
        raise PipelineInputError("economic_inputs evidence value must be an object")
    missing_economic_fields = [field for field in ECONOMIC_FIELDS if field not in economic_values]
    if missing_economic_fields:
        raise PipelineInputError(
            "economic_inputs evidence is missing: " + ", ".join(missing_economic_fields)
        )
    currency = economic_values.get("currency")
    if not isinstance(currency, str) or not currency:
        raise PipelineInputError("economic_inputs evidence must declare currency")

    operator_budget = data.get("user_context", {}).get("test_budget_brl")
    observed_budget = budget_evidence.get("value")
    if decimal_value(operator_budget, "user_context.test_budget_brl", allow_none=False) != decimal_value(
        observed_budget,
        "operator budget evidence",
        allow_none=False,
    ):
        raise PipelineInputError("operator budget evidence differs from user_context.test_budget_brl")

    demand = _dimension_input(opportunity, "demand")
    economics = _dimension_input(opportunity, "economics")
    competitive = _dimension_input(opportunity, "competitive_attractiveness")
    generated_at = _parse_datetime(data.get("generated_at"), "generated_at")
    demand_age = _maximum_referenced_age(demand, evidence_by_id, generated_at)
    economic_age = _age_days(
        generated_at,
        economic_evidence.get("collected_at"),
        f"{economic_evidence.get('evidence_id')}.collected_at",
    )

    source_ids = context.get("independent_source_ids")
    if not isinstance(source_ids, list) or any(not isinstance(item, str) or not item for item in source_ids):
        raise PipelineInputError("scoring_context.independent_source_ids must be an array of non-empty strings")
    if len(source_ids) != len(set(source_ids)):
        raise PipelineInputError("scoring_context.independent_source_ids cannot contain duplicates")
    observed_source_ids = {
        evidence.get("source_url")
        for evidence in evidence_by_id.values()
        if isinstance(evidence.get("source_url"), str) and evidence.get("source_url")
    }
    unbacked_source_ids = sorted(set(source_ids) - observed_source_ids)
    if unbacked_source_ids:
        raise PipelineInputError(
            "scoring_context.independent_source_ids must reference observed evidence sources: "
            + ", ".join(unbacked_source_ids)
        )

    logistics_days = None
    logistics_id = context.get("logistics_evidence_id")
    if logistics_id is not None:
        logistics_evidence = _referenced_evidence(
            context,
            "logistics_evidence_id",
            "logistics_lead_time_business_days",
            evidence_by_id,
        )
        logistics_days = logistics_evidence.get("value")

    score_configuration = data.get("score_configuration", {})
    if score_configuration.get("version") != "SCORE-0.1.0":
        raise PipelineInputError("score_configuration.version must be SCORE-0.1.0")

    return OpportunityScoreInput(
        opportunity_id=opportunity["opportunity_id"],
        demand=demand,
        economics=economics,
        competitive_attractiveness=competitive,
        operational_fit=fit_evidence.get("value"),
        operational_fit_source_evidence_ids=(fit_evidence["evidence_id"],),
        economic_inputs=EconomicInputs(
            selling_price=economic_values["selling_price"],
            product_cost=economic_values["product_cost"],
            variable_fees=economic_values["variable_fees"],
            taxes=economic_values["taxes"],
            shipping_subsidy=economic_values["shipping_subsidy"],
            other_variable_costs=economic_values["other_variable_costs"],
            currency=currency,
            source_evidence_ids=(economic_evidence["evidence_id"],),
        ),
        minimum_test_cost=minimum_cost_evidence.get("value"),
        operator_test_budget=operator_budget,
        budget_source_evidence_ids=(
            minimum_cost_evidence["evidence_id"],
            budget_evidence["evidence_id"],
        ),
        evidence_coverage_percent=opportunity.get("data_quality", {}).get("coverage_percent"),
        demand_evidence_age_days=demand_age,
        economic_data_age_days=economic_age,
        independent_source_count=len(source_ids),
        logistics_lead_time_business_days=logistics_days,
        calculated_at=score_configuration.get("calculation_timestamp"),
        calculation_quality=context.get("calculation_quality", "unknown"),
    )


def _merge_indicators(
    opportunity: dict[str, Any],
    serialized_indicators: Iterable[dict[str, Any]],
) -> None:
    existing = {
        item.get("indicator_id"): item
        for item in opportunity.get("calculated_indicators", [])
        if isinstance(item, dict)
    }
    for indicator in serialized_indicators:
        indicator_id = indicator["indicator_id"]
        if indicator_id in existing:
            if existing[indicator_id] != indicator:
                raise PipelineInputError(f"CALC-* conflict detected for {indicator_id}")
            continue
        enriched_indicator = copy.deepcopy(indicator)
        opportunity.setdefault("calculated_indicators", []).append(enriched_indicator)
        existing[indicator_id] = enriched_indicator


def validate_pipeline_result(result: Any) -> dict[str, Any]:
    """Validate the deterministic pipeline envelope and CALC-* consistency."""

    issues: list[dict[str, str]] = []
    if not isinstance(result, dict):
        return _validation_result([_issue("invalid_type", "$", "Pipeline result must be an object.")])
    required = {
        "pipeline_version",
        "analysis_id",
        "score_version",
        "status",
        "input_validation",
        "opportunity_results",
        "enriched_input",
        "enriched_input_validation",
        "final_output_validation",
    }
    for field in sorted(required - set(result)):
        issues.append(_issue("missing_required_field", f"$.{field}", "Required pipeline field is missing."))
    if result.get("pipeline_version") != PIPELINE_VERSION:
        issues.append(_issue("invalid_pipeline_version", "$.pipeline_version", "Expected pipeline version 0.1.0."))
    if result.get("score_version") != "SCORE-0.1.0":
        issues.append(_issue("invalid_score_version", "$.score_version", "Expected SCORE-0.1.0."))
    if result.get("status") not in {"completed", "partial", "invalid"}:
        issues.append(_issue("invalid_enum", "$.status", "Invalid pipeline status."))
    opportunity_results = result.get("opportunity_results")
    if not isinstance(opportunity_results, list):
        issues.append(_issue("invalid_type", "$.opportunity_results", "Opportunity results must be an array."))
        opportunity_results = []
    enriched = result.get("enriched_input")
    known_evidence_ids: set[str] = set()
    known_opportunity_ids: set[str] = set()
    enriched_indicators: dict[str, dict[str, dict[str, Any]]] = {}
    if isinstance(enriched, dict):
        if enriched.get("analysis_id") != result.get("analysis_id"):
            issues.append(_issue("analysis_id_mismatch", "$.analysis_id", "Pipeline and input analysis IDs differ."))
        for opportunity in enriched.get("opportunities", []):
            if not isinstance(opportunity, dict):
                continue
            opportunity_id = opportunity.get("opportunity_id")
            if isinstance(opportunity_id, str):
                known_opportunity_ids.add(opportunity_id)
                enriched_indicators[opportunity_id] = {
                    indicator["indicator_id"]: indicator
                    for indicator in opportunity.get("calculated_indicators", [])
                    if isinstance(indicator, dict) and isinstance(indicator.get("indicator_id"), str)
                }
            for evidence in opportunity.get("observed_evidence", []):
                if isinstance(evidence, dict) and isinstance(evidence.get("evidence_id"), str):
                    known_evidence_ids.add(evidence["evidence_id"])
    for index, opportunity_result in enumerate(opportunity_results):
        path = f"$.opportunity_results[{index}]"
        if not isinstance(opportunity_result, dict):
            issues.append(_issue("invalid_type", path, "Opportunity result must be an object."))
            continue
        if opportunity_result.get("opportunity_id") not in known_opportunity_ids:
            issues.append(_issue("unknown_opportunity_id", f"{path}.opportunity_id", "Opportunity does not exist."))
        opportunity_id = opportunity_result.get("opportunity_id")
        official_indicators = [
            item
            for item in opportunity_result.get("indicators", [])
            if isinstance(item, dict) and item.get("field") == "official_score"
        ]
        score = opportunity_result.get("official_score")
        if score is None and official_indicators:
            issues.append(_issue("unexpected_official_score", path, "Null result cannot contain official score CALC-*."))
        if score is not None:
            if len(official_indicators) != 1 or official_indicators[0].get("value") != score:
                issues.append(_issue("official_score_mismatch", path, "Official score differs from its CALC-* record."))
        for indicator in opportunity_result.get("indicators", []):
            if not isinstance(indicator, dict):
                issues.append(_issue("invalid_type", f"{path}.indicators", "Indicator must be an object."))
                continue
            indicator_id = indicator.get("indicator_id")
            expected_indicator = enriched_indicators.get(opportunity_id, {}).get(indicator_id)
            if expected_indicator is None:
                issues.append(
                    _issue(
                        "unknown_indicator_id",
                        f"{path}.indicators",
                        f"Indicator does not exist in enriched input: {indicator_id}.",
                    )
                )
            elif indicator != expected_indicator:
                issues.append(
                    _issue(
                        "indicator_mismatch",
                        f"{path}.indicators",
                        f"Indicator differs from enriched input: {indicator_id}.",
                    )
                )
            for evidence_id in indicator.get("source_evidence_ids", []):
                if evidence_id not in known_evidence_ids:
                    issues.append(_issue("unknown_evidence_id", f"{path}.indicators", f"Unknown evidence: {evidence_id}."))
    return _validation_result(issues)


def run_pipeline(
    data: Any,
    *,
    final_output: Any | None = None,
    engine: ScoreEngine | None = None,
) -> dict[str, Any]:
    """Execute validation, deterministic scoring, enrichment, and output validation."""

    scoring_engine = engine or ScoreEngine.from_file()
    input_validation = validate_input(data, require_official_score=False)
    result: dict[str, Any] = {
        "pipeline_version": PIPELINE_VERSION,
        "analysis_id": data.get("analysis_id") if isinstance(data, dict) else None,
        "score_version": scoring_engine.score_version,
        "status": "invalid",
        "input_validation": input_validation,
        "opportunity_results": [],
        "enriched_input": None,
        "enriched_input_validation": None,
        "final_output_validation": None,
    }
    if not input_validation.get("valid") or not isinstance(data, dict):
        result["pipeline_validation"] = validate_pipeline_result(result)
        return result

    enriched = copy.deepcopy(data)
    engine_results = []
    input_errors: dict[str, str] = {}
    for opportunity in enriched.get("opportunities", []):
        opportunity_id = opportunity.get("opportunity_id", "unknown")
        try:
            engine_input = build_engine_input(enriched, opportunity)
            engine_results.append(scoring_engine.score(engine_input))
        except (KeyError, TypeError, ValueError) as exc:
            input_errors[str(opportunity_id)] = str(exc)

    ranked_results = assign_shared_ranks(engine_results)
    ranked_by_id = {item.opportunity_id: item for item in ranked_results}
    serialized_results: list[dict[str, Any]] = []
    for opportunity in enriched.get("opportunities", []):
        opportunity_id = str(opportunity.get("opportunity_id", "unknown"))
        if opportunity_id in input_errors:
            serialized_results.append(
                {
                    "opportunity_id": opportunity_id,
                    "score_version": scoring_engine.score_version,
                    "status": "input_error",
                    "official_score": None,
                    "official_score_display": None,
                    "official_rank": None,
                    "indicators": [],
                    "kill_switches": [],
                    "missing_dimensions": [],
                    "eligibility_issues": [input_errors[opportunity_id]],
                    "warnings": [],
                }
            )
            continue
        scored = ranked_by_id[opportunity_id]
        serialized = scored.as_dict(display_precision=scoring_engine.display_precision)
        _merge_indicators(opportunity, serialized["indicators"])
        serialized_results.append(serialized)

    result["opportunity_results"] = serialized_results
    result["enriched_input"] = enriched
    result["enriched_input_validation"] = validate_input(
        enriched,
        require_official_score=False,
    )
    if input_errors or any(item["status"] == "insufficient_data" for item in serialized_results):
        result["status"] = "partial"
    else:
        result["status"] = "completed"
    if not result["enriched_input_validation"]["valid"]:
        result["status"] = "invalid"

    if final_output is not None:
        result["final_output_validation"] = validate_output(final_output, enriched)
        if not result["final_output_validation"]["valid"]:
            result["status"] = "invalid"
    result["pipeline_validation"] = validate_pipeline_result(result)
    return result


def run_pipeline_file(
    input_path: str | Path,
    *,
    final_output_path: str | Path | None = None,
) -> dict[str, Any]:
    try:
        data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        invalid = {
            "pipeline_version": PIPELINE_VERSION,
            "analysis_id": None,
            "score_version": "SCORE-0.1.0",
            "status": "invalid",
            "input_validation": _validation_result([_issue("invalid_json", "$", str(exc))]),
            "opportunity_results": [],
            "enriched_input": None,
            "enriched_input_validation": None,
            "final_output_validation": None,
        }
        invalid["pipeline_validation"] = validate_pipeline_result(invalid)
        return invalid

    final_output = None
    if final_output_path is not None:
        try:
            final_output = parse_output_text(Path(final_output_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            invalid = run_pipeline(data)
            invalid["status"] = "invalid"
            invalid["final_output_validation"] = _validation_result(
                [_issue("invalid_json", "$.final_output", str(exc))]
            )
            invalid["pipeline_validation"] = validate_pipeline_result(invalid)
            return invalid
    return run_pipeline(data, final_output=final_output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Opportunity Analyst deterministic pipeline.")
    parser.add_argument("input", help="Path to the pre-score input JSON.")
    parser.add_argument("--final-output", help="Optional final JSON or Markdown analysis output.")
    parser.add_argument("--output", help="Optional path for the pipeline JSON result.")
    args = parser.parse_args(argv)
    result = run_pipeline_file(args.input, final_output_path=args.final_output)
    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)
    return 0 if result["status"] in {"completed", "partial"} and result["pipeline_validation"]["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

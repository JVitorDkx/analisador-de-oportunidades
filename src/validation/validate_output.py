"""Deterministic validation for opportunity-analyst output documents."""

from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from src.validation.validate_input import validate_input


INPUT_STATUSES = {"sufficient", "partial", "insufficient", "invalid"}
ANALYSIS_MODES = {"pre_test", "campaign_diagnosis", "reassessment"}
CONFIDENCE_VALUES = {"high", "moderate", "low", "inconclusive"}
RECOMMENDATIONS = {
    "prioritize_test",
    "test_with_conditions",
    "collect_more_data",
    "continue_collecting",
    "consider_limited_scale",
    "iterate_creative",
    "iterate_offer",
    "inspect_landing_page",
    "inspect_checkout",
    "pause_for_review",
    "run_controlled_test",
    "deprioritize",
    "reject_for_now",
    "insufficient_data",
}
CONTEXT_FITS = {"strong_fit", "acceptable_fit", "conditional_fit", "poor_fit", "unknown"}
BUDGET_COMPATIBILITY = {"compatible", "conditional", "incompatible", "unknown"}
CHANNEL_COMPATIBILITY = {"strong", "moderate", "weak", "unknown"}
SEVERITIES = {"low", "medium", "high", "critical"}
CERTAINTIES = {"strong", "moderate", "weak"}
CONFLICT_IMPACTS = {"low", "medium", "high"}
CALCULATION_ACTIONS = {"calculation_review_required"}
NON_RECOMMENDING_ACTIONS = {"collect_more_data", "insufficient_data"}

REQUIRED_OUTPUT_FIELDS = (
    "schema_version",
    "analysis_id",
    "analysis_mode",
    "processed_at",
    "input_status",
    "security_status",
    "versions",
    "recommended_opportunity_id",
    "recommendation",
    "confidence",
    "executive_summary",
    "context_assessment",
    "ranking",
    "favorable_evidence",
    "contrary_evidence",
    "inferences",
    "source_conflicts",
    "missing_data",
    "calculation_warnings",
    "next_experiment",
    "conditions_that_would_change_recommendation",
    "human_review",
    "disclaimer",
)

REQUIRED_EXPERIMENT_FIELDS = (
    "experiment_id",
    "objective",
    "hypothesis",
    "primary_variable",
    "control_variable",
    "minimum_action",
    "maximum_budget",
    "currency",
    "duration_days",
    "success_metrics",
    "success_conditions",
    "stop_conditions",
    "required_feedback_fields",
)


def _issue(code: str, path: str, message: str, severity: str = "error") -> dict[str, str]:
    return {"code": code, "path": path, "message": message, "severity": severity}


def _require_fields(value: Any, required: Iterable[str], path: str, issues: list[dict[str, str]]) -> bool:
    if not isinstance(value, dict):
        issues.append(_issue("invalid_type", path, "O valor deve ser um objeto JSON."))
        return False
    for field in required:
        if field not in value:
            issues.append(_issue("missing_required_field", f"{path}.{field}", "Campo obrigatório ausente."))
    return True


def _validate_enum(value: Any, allowed: set[str], path: str, issues: list[dict[str, str]]) -> None:
    if not isinstance(value, str) or value not in allowed:
        issues.append(_issue("invalid_enum", path, "Valor fora da enumeração permitida."))


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _all_evidence_references(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key == "evidence_ids":
                yield child_path, child
            yield from _all_evidence_references(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _all_evidence_references(child, f"{path}[{index}]")


def _input_index(input_data: dict[str, Any]) -> tuple[set[str], set[str], dict[str, tuple[Any, Any]]]:
    opportunity_ids: set[str] = set()
    evidence_ids: set[str] = set()
    official_scores: dict[str, tuple[Any, Any]] = {}
    for opportunity in input_data.get("opportunities", []):
        if not isinstance(opportunity, dict):
            continue
        opportunity_id = opportunity.get("opportunity_id")
        if isinstance(opportunity_id, str):
            opportunity_ids.add(opportunity_id)
        for evidence in opportunity.get("observed_evidence", []):
            if isinstance(evidence, dict) and isinstance(evidence.get("evidence_id"), str):
                evidence_ids.add(evidence["evidence_id"])
        for indicator in opportunity.get("calculated_indicators", []):
            if not isinstance(indicator, dict):
                continue
            indicator_id = indicator.get("indicator_id")
            if isinstance(indicator_id, str):
                evidence_ids.add(indicator_id)
            if indicator.get("field") == "official_score" and isinstance(opportunity_id, str):
                official_scores[opportunity_id] = (indicator.get("value"), indicator.get("unit"))
    return opportunity_ids, evidence_ids, official_scores


def validate_output(data: Any, input_data: Any) -> dict[str, Any]:
    """Validate an output against its source input without recalculating CALC-* values."""

    issues: list[dict[str, str]] = []
    if not _require_fields(data, REQUIRED_OUTPUT_FIELDS, "$", issues):
        return _result(issues)
    if not isinstance(input_data, dict):
        issues.append(_issue("invalid_input_reference", "$input", "A entrada de referência deve ser um objeto JSON."))
        return _result(issues)

    if data.get("schema_version") != "1.0.0":
        issues.append(_issue("invalid_schema_version", "$.schema_version", "A versão de saída esperada é 1.0.0."))
    if data.get("analysis_id") != input_data.get("analysis_id"):
        issues.append(_issue("analysis_id_mismatch", "$.analysis_id", "analysis_id difere da entrada validada."))
    if data.get("analysis_mode") != input_data.get("analysis_mode"):
        issues.append(_issue("analysis_mode_mismatch", "$.analysis_mode", "analysis_mode difere da entrada validada."))
    _validate_enum(data.get("analysis_mode"), ANALYSIS_MODES, "$.analysis_mode", issues)
    try:
        processed_at = data.get("processed_at")
        if not isinstance(processed_at, str) or datetime.fromisoformat(processed_at.replace("Z", "+00:00")).tzinfo is None:
            raise ValueError
    except ValueError:
        issues.append(_issue("invalid_datetime", "$.processed_at", "processed_at deve ser ISO-8601 com fuso horário."))

    input_status = data.get("input_status")
    confidence = data.get("confidence")
    recommendation = data.get("recommendation")
    _validate_enum(input_status, INPUT_STATUSES, "$.input_status", issues)
    _validate_enum(confidence, CONFIDENCE_VALUES, "$.confidence", issues)
    _validate_enum(recommendation, RECOMMENDATIONS, "$.recommendation", issues)

    deterministic_status = validate_input(input_data).get("status")
    if input_status != deterministic_status:
        issues.append(_issue("input_status_mismatch", "$.input_status", "input_status difere da validação determinística da entrada."))

    opportunity_ids, known_evidence_ids, official_scores = _input_index(input_data)
    recommended_id = data.get("recommended_opportunity_id")
    if recommended_id is not None and recommended_id not in opportunity_ids:
        issues.append(_issue("unknown_recommended_opportunity", "$.recommended_opportunity_id", "A oportunidade recomendada não existe na entrada."))

    if input_status in {"insufficient", "invalid"}:
        if recommended_id is not None or recommendation not in NON_RECOMMENDING_ACTIONS or confidence != "inconclusive":
            issues.append(_issue("incompatible_recommendation", "$.recommendation", "Entrada insuficiente ou inválida exige ID nulo, coleta de dados e confiança inconclusiva."))
    elif input_status == "partial":
        if confidence == "high":
            issues.append(_issue("incompatible_confidence", "$.confidence", "Entrada parcial não é compatível com confiança alta."))
        if recommendation == "consider_limited_scale":
            issues.append(_issue("incompatible_recommendation", "$.recommendation", "Escala limitada exige qualidade de dados suficiente."))

    security = data.get("security_status")
    if _require_fields(security, ("prompt_injection_detected", "suspicious_fields", "sensitive_data_detected"), "$.security_status", issues):
        for field in ("prompt_injection_detected", "sensitive_data_detected"):
            if not isinstance(security.get(field), bool):
                issues.append(_issue("invalid_type", f"$.security_status.{field}", "O campo deve ser booleano."))
        if not isinstance(security.get("suspicious_fields"), list):
            issues.append(_issue("invalid_type", "$.security_status.suspicious_fields", "O campo deve ser um array."))

    versions = data.get("versions")
    if _require_fields(versions, ("skill_version", "input_schema_version", "output_schema_version", "score_version"), "$.versions", issues):
        expected_versions = {
            "skill_version": "1.0.1",
            "input_schema_version": "1.0.0",
            "output_schema_version": "1.0.0",
            "score_version": input_data.get("score_configuration", {}).get("version"),
        }
        for field, expected in expected_versions.items():
            if versions.get(field) != expected:
                issues.append(_issue("version_mismatch", f"$.versions.{field}", "A versão difere do contrato ou da entrada de referência."))

    for path, references in _all_evidence_references(data):
        if not isinstance(references, list) or any(not isinstance(item, str) for item in references):
            issues.append(_issue("invalid_evidence_ids", path, "evidence_ids deve ser um array de strings."))
            continue
        if len(references) != len(set(references)):
            issues.append(_issue("duplicate_evidence_reference", path, "Uma evidência foi repetida na mesma lista."))
        for evidence_id in references:
            if evidence_id not in known_evidence_ids:
                issues.append(_issue("unknown_evidence_id", path, f"evidence_id inexistente: {evidence_id}."))

    ranking = data.get("ranking")
    ranked_opportunities: set[str] = set()
    if not isinstance(ranking, list):
        issues.append(_issue("invalid_type", "$.ranking", "ranking deve ser um array."))
    else:
        for index, item in enumerate(ranking):
            path = f"$.ranking[{index}]"
            if not _require_fields(
                item,
                ("position", "opportunity_id", "official_score", "official_score_scale", "official_score_rank", "contextual_recommendation_rank", "context_fit"),
                path,
                issues,
            ):
                continue
            opportunity_id = item.get("opportunity_id")
            if opportunity_id not in opportunity_ids:
                issues.append(_issue("unknown_ranked_opportunity", f"{path}.opportunity_id", "A oportunidade ranqueada não existe na entrada."))
                continue
            ranked_opportunities.add(opportunity_id)
            _validate_enum(item.get("context_fit"), CONTEXT_FITS, f"{path}.context_fit", issues)
            for risk_index, risk in enumerate(item.get("risks", []) if isinstance(item.get("risks"), list) else []):
                if isinstance(risk, dict):
                    _validate_enum(risk.get("severity"), SEVERITIES, f"{path}.risks[{risk_index}].severity", issues)
            expected = official_scores.get(opportunity_id)
            actual = (item.get("official_score"), item.get("official_score_scale"))
            if expected is not None and actual != expected:
                issues.append(_issue("official_score_changed", f"{path}.official_score", "O score oficial ou sua unidade foi alterado em relação ao CALC-* de entrada."))
            if expected is None and actual != (None, None):
                issues.append(_issue("official_score_fabricated", f"{path}.official_score", "A saída criou um score oficial ausente na entrada."))
    if set(official_scores) - ranked_opportunities:
        issues.append(_issue("official_score_omitted", "$.ranking", "Uma oportunidade com score oficial foi omitida do ranking."))

    context = data.get("context_assessment")
    if _require_fields(context, ("fit", "budget_compatibility", "channel_compatibility", "operational_constraints", "explanation"), "$.context_assessment", issues):
        _validate_enum(context.get("fit"), CONTEXT_FITS, "$.context_assessment.fit", issues)
        _validate_enum(context.get("budget_compatibility"), BUDGET_COMPATIBILITY, "$.context_assessment.budget_compatibility", issues)
        _validate_enum(context.get("channel_compatibility"), CHANNEL_COMPATIBILITY, "$.context_assessment.channel_compatibility", issues)

    for index, inference in enumerate(data.get("inferences", []) if isinstance(data.get("inferences"), list) else []):
        if isinstance(inference, dict):
            _validate_enum(inference.get("certainty"), CERTAINTIES, f"$.inferences[{index}].certainty", issues)
    for index, conflict in enumerate(data.get("source_conflicts", []) if isinstance(data.get("source_conflicts"), list) else []):
        if isinstance(conflict, dict):
            _validate_enum(conflict.get("impact"), CONFLICT_IMPACTS, f"$.source_conflicts[{index}].impact", issues)
    for index, missing in enumerate(data.get("missing_data", []) if isinstance(data.get("missing_data"), list) else []):
        if isinstance(missing, dict):
            _validate_enum(missing.get("importance"), SEVERITIES, f"$.missing_data[{index}].importance", issues)

    for field in (
        "favorable_evidence",
        "contrary_evidence",
        "inferences",
        "source_conflicts",
        "missing_data",
        "conditions_that_would_change_recommendation",
    ):
        if not isinstance(data.get(field), list):
            issues.append(_issue("invalid_type", f"$.{field}", "O campo deve ser um array."))

    warnings = data.get("calculation_warnings")
    if not isinstance(warnings, list):
        issues.append(_issue("invalid_type", "$.calculation_warnings", "calculation_warnings deve ser um array."))
    else:
        for index, warning in enumerate(warnings):
            path = f"$.calculation_warnings[{index}]"
            if _require_fields(warning, ("calculation_id", "warning", "action"), path, issues):
                if warning.get("calculation_id") not in known_evidence_ids or not str(warning.get("calculation_id", "")).startswith("CALC-"):
                    issues.append(_issue("unknown_calculation_id", f"{path}.calculation_id", "O aviso referencia um CALC-* inexistente."))
                _validate_enum(warning.get("action"), CALCULATION_ACTIONS, f"{path}.action", issues)

    if "calculated_indicators" in data:
        issues.append(_issue("silent_calc_override", "$.calculated_indicators", "A saída não pode redefinir a coleção autoritativa de CALC-* da entrada."))

    experiment = data.get("next_experiment")
    if _require_fields(experiment, REQUIRED_EXPERIMENT_FIELDS, "$.next_experiment", issues):
        for field in ("experiment_id", "objective", "hypothesis", "primary_variable", "minimum_action", "currency"):
            if not isinstance(experiment.get(field), str) or not experiment.get(field):
                issues.append(_issue("invalid_value", f"$.next_experiment.{field}", "O campo deve ser uma string não vazia."))
        maximum_budget = experiment.get("maximum_budget")
        if maximum_budget is not None and (not _is_finite_number(maximum_budget) or maximum_budget < 0):
            issues.append(_issue("invalid_value", "$.next_experiment.maximum_budget", "O orçamento deve ser nulo ou finito e não negativo."))
        input_budget = input_data.get("user_context", {}).get("test_budget_brl")
        if _is_finite_number(maximum_budget) and _is_finite_number(input_budget) and maximum_budget > input_budget:
            issues.append(_issue("experiment_budget_exceeded", "$.next_experiment.maximum_budget", "O experimento excede o orçamento informado."))
        duration = experiment.get("duration_days")
        if duration is not None and (not isinstance(duration, int) or isinstance(duration, bool) or duration < 1):
            issues.append(_issue("invalid_value", "$.next_experiment.duration_days", "A duração deve ser nula ou inteira e positiva."))
        for field in ("success_metrics", "success_conditions", "stop_conditions", "required_feedback_fields"):
            if not isinstance(experiment.get(field), list):
                issues.append(_issue("invalid_type", f"$.next_experiment.{field}", "O campo deve ser um array."))

    disclaimer = data.get("disclaimer")
    if not isinstance(disclaimer, str) or not disclaimer.strip():
        issues.append(_issue("missing_disclaimer", "$.disclaimer", "A saída deve conter disclaimer não vazio."))

    human_review = data.get("human_review")
    if _require_fields(human_review, ("required", "reasons"), "$.human_review", issues):
        if not isinstance(human_review.get("required"), bool):
            issues.append(_issue("invalid_type", "$.human_review.required", "O campo deve ser booleano."))
        if not isinstance(human_review.get("reasons"), list):
            issues.append(_issue("invalid_type", "$.human_review.reasons", "O campo deve ser um array."))

    return _result(issues)


def _result(issues: list[dict[str, str]]) -> dict[str, Any]:
    errors = [item for item in issues if item["severity"] == "error"]
    warnings = [item for item in issues if item["severity"] == "warning"]
    return {
        "status": "invalid" if errors else "valid",
        "valid": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "issues": issues,
    }


def parse_output_text(text: str) -> Any:
    stripped = text.lstrip("\ufeff\n\r\t ")
    if stripped.startswith("```json"):
        match = re.match(r"```json\s*\r?\n(.*?)\r?\n```", stripped, flags=re.DOTALL)
        if not match:
            raise json.JSONDecodeError("Bloco JSON de saída não foi encerrado", stripped, 0)
        return json.loads(match.group(1))
    return json.loads(stripped)


# Backward-compatible alias for existing callers.
_parse_output_text = parse_output_text


def validate_output_file(output_path: str | Path, input_path: str | Path) -> dict[str, Any]:
    """Parse an output JSON/Markdown file and validate it against an input JSON file."""

    try:
        output_data = parse_output_text(Path(output_path).read_text(encoding="utf-8"))
        input_data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _result([_issue("invalid_json", "$", str(exc))])
    return validate_output(output_data, input_data)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: python -m src.validation.validate_output <output.json|md> <input.json>", file=sys.stderr)
        return 2
    result = validate_output_file(argv[1], argv[2])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

"""Deterministic validation for opportunity-analyst input payloads."""

from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ANALYSIS_MODES = {"pre_test", "campaign_diagnosis", "reassessment"}
EXPERIENCE_LEVELS = {"beginner", "intermediate", "advanced"}
BUSINESS_MODELS = {"ecommerce", "dropshipping", "marketplace", "infoproduct", "affiliate"}
PRIMARY_CHANNELS = {"meta", "tiktok", "google", "organic", "marketplace", "mixed"}
DATA_QUALITY_STATUSES = {"complete", "partial", "weak", "invalid"}
FRESHNESS_VALUES = {"current", "aging", "stale", "unknown"}
QUALITY_VALUES = {"high", "medium", "low", "unknown"}
CALCULATED_VALUE_TYPES = {"integer", "number", "string", "boolean", "null"}
NON_NEGATIVE_FIELD_TOKENS = ("price", "cost", "cpa", "revenue", "spend", "budget", "count", "days")


def _issue(code: str, path: str, message: str, severity: str = "error") -> dict[str, str]:
    return {"code": code, "path": path, "message": message, "severity": severity}


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _value_matches_declared_type(value: Any, value_type: Any) -> bool:
    checks = {
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": _is_finite_number,
        "string": lambda item: isinstance(item, str),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
    }
    return value_type in checks and checks[value_type](value)


def _validate_datetime(value: Any, path: str, issues: list[dict[str, str]]) -> None:
    if not isinstance(value, str):
        issues.append(_issue("invalid_datetime", path, "O valor deve ser uma data ISO-8601."))
        return
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone missing")
    except ValueError:
        issues.append(_issue("invalid_datetime", path, "O valor deve ser uma data ISO-8601 com fuso horário."))
        return
    if parsed.astimezone(timezone.utc) > datetime.now(timezone.utc) + timedelta(minutes=5):
        issues.append(_issue("future_datetime", path, "A data de coleta ou geração não pode estar no futuro."))


def _require_fields(
    value: Any,
    required: tuple[str, ...],
    path: str,
    issues: list[dict[str, str]],
) -> bool:
    if not isinstance(value, dict):
        issues.append(_issue("invalid_type", path, "O valor deve ser um objeto JSON."))
        return False
    for field in required:
        if field not in value:
            issues.append(_issue("missing_required_field", f"{path}.{field}", "Campo obrigatório ausente."))
    return True


def validate_input(data: Any, *, require_official_score: bool = True) -> dict[str, Any]:
    """Validate an input payload without calculating or modifying indicators.

    ``require_official_score=False`` is reserved for the pre-score pipeline
    stage, where the engine has not produced the official CALC-* yet.
    """

    issues: list[dict[str, str]] = []
    if not _require_fields(
        data,
        (
            "schema_version",
            "analysis_id",
            "generated_at",
            "analysis_mode",
            "user_context",
            "opportunities",
            "score_configuration",
            "requested_output_language",
        ),
        "$",
        issues,
    ):
        return {"status": "invalid", "valid": False, "issues": issues}

    if data.get("schema_version") != "1.0.0":
        issues.append(_issue("invalid_schema_version", "$.schema_version", "A versão esperada é 1.0.0."))

    analysis_mode = data.get("analysis_mode")
    if analysis_mode not in ANALYSIS_MODES:
        issues.append(_issue("invalid_enum", "$.analysis_mode", "Modo de análise inválido."))

    _validate_datetime(data.get("generated_at"), "$.generated_at", issues)

    context = data.get("user_context")
    if _require_fields(
        context,
        ("country", "experience_level", "business_model", "primary_channel", "test_budget_brl"),
        "$.user_context",
        issues,
    ):
        if not isinstance(context.get("country"), str) or not context.get("country"):
            issues.append(_issue("invalid_value", "$.user_context.country", "País deve ser uma string não vazia."))
        if context.get("experience_level") not in EXPERIENCE_LEVELS:
            issues.append(_issue("invalid_enum", "$.user_context.experience_level", "Nível de experiência inválido."))
        if context.get("business_model") not in BUSINESS_MODELS:
            issues.append(_issue("invalid_enum", "$.user_context.business_model", "Modelo de negócio inválido."))
        if context.get("primary_channel") not in PRIMARY_CHANNELS:
            issues.append(_issue("invalid_enum", "$.user_context.primary_channel", "Canal principal inválido."))

        budget = context.get("test_budget_brl")
        if not _is_finite_number(budget) or budget < 0:
            issues.append(_issue("invalid_value", "$.user_context.test_budget_brl", "Orçamento deve ser finito e não negativo."))

        maximum_days = context.get("maximum_test_days")
        if maximum_days is not None and (
            not isinstance(maximum_days, int) or isinstance(maximum_days, bool) or maximum_days < 1
        ):
            issues.append(_issue("invalid_value", "$.user_context.maximum_test_days", "Duração deve ser inteira e positiva."))

        target_margin = context.get("target_margin_percent")
        if target_margin is not None and (
            not _is_finite_number(target_margin) or not 0 <= target_margin <= 100
        ):
            issues.append(_issue("invalid_value", "$.user_context.target_margin_percent", "Percentual deve estar entre 0 e 100."))

        maximum_cpa = context.get("maximum_acceptable_cpa")
        if maximum_cpa is not None and (not _is_finite_number(maximum_cpa) or maximum_cpa < 0):
            issues.append(_issue("invalid_value", "$.user_context.maximum_acceptable_cpa", "CPA deve ser finito e não negativo."))

    opportunities = data.get("opportunities")
    if not isinstance(opportunities, list):
        issues.append(_issue("invalid_type", "$.opportunities", "Oportunidades devem formar um array."))
        opportunities = []
    elif analysis_mode == "pre_test" and len(opportunities) < 2:
        issues.append(_issue("insufficient_opportunities", "$.opportunities", "pre_test exige pelo menos duas oportunidades."))
    elif analysis_mode == "campaign_diagnosis" and len(opportunities) < 1:
        issues.append(_issue("insufficient_opportunities", "$.opportunities", "campaign_diagnosis exige pelo menos uma oportunidade."))

    opportunity_ids: set[str] = set()
    evidence_ids: set[str] = set()
    indicator_ids: set[str] = set()

    for index, opportunity in enumerate(opportunities):
        path = f"$.opportunities[{index}]"
        if not _require_fields(
            opportunity,
            ("opportunity_id", "name", "observed_evidence", "calculated_indicators", "data_quality"),
            path,
            issues,
        ):
            continue

        opportunity_id = opportunity.get("opportunity_id")
        if not isinstance(opportunity_id, str) or not opportunity_id:
            issues.append(_issue("invalid_value", f"{path}.opportunity_id", "ID da oportunidade deve ser não vazio."))
        elif opportunity_id in opportunity_ids:
            issues.append(_issue("duplicate_opportunity_id", f"{path}.opportunity_id", "ID de oportunidade duplicado."))
        else:
            opportunity_ids.add(opportunity_id)

        if not isinstance(opportunity.get("name"), str) or not opportunity.get("name"):
            issues.append(_issue("invalid_value", f"{path}.name", "Nome da oportunidade deve ser não vazio."))

        quality = opportunity.get("data_quality")
        if _require_fields(quality, ("status", "coverage_percent", "freshness", "source_agreement"), f"{path}.data_quality", issues):
            quality_status = quality.get("status")
            if quality_status not in DATA_QUALITY_STATUSES:
                issues.append(_issue("invalid_enum", f"{path}.data_quality.status", "Status de qualidade inválido."))
            elif quality_status == "invalid":
                issues.append(_issue("invalid_data_quality", f"{path}.data_quality.status", "A qualidade foi marcada como inválida."))
            elif quality_status in {"partial", "weak"}:
                issues.append(
                    _issue(
                        "partial_data_quality",
                        f"{path}.data_quality.status",
                        "A oportunidade possui cobertura parcial ou fraca.",
                        "warning",
                    )
                )

            coverage = quality.get("coverage_percent")
            if not _is_finite_number(coverage) or not 0 <= coverage <= 100:
                issues.append(_issue("invalid_value", f"{path}.data_quality.coverage_percent", "Cobertura deve estar entre 0 e 100."))
            if quality.get("freshness") not in FRESHNESS_VALUES:
                issues.append(_issue("invalid_enum", f"{path}.data_quality.freshness", "Freshness inválido."))
            if quality.get("source_agreement") not in QUALITY_VALUES:
                issues.append(_issue("invalid_enum", f"{path}.data_quality.source_agreement", "Concordância de fontes inválida."))

        observed = opportunity.get("observed_evidence")
        if not isinstance(observed, list) or not observed:
            issues.append(_issue("missing_observed_evidence", f"{path}.observed_evidence", "Cada oportunidade exige ao menos uma evidência OBS-*."))
            observed = []

        opportunity_evidence_ids: set[str] = set()

        for evidence_index, evidence in enumerate(observed):
            evidence_path = f"{path}.observed_evidence[{evidence_index}]"
            if not _require_fields(
                evidence,
                (
                    "evidence_id",
                    "opportunity_id",
                    "source_type",
                    "collected_at",
                    "field",
                    "value",
                    "value_type",
                    "collection_method",
                    "quality",
                ),
                evidence_path,
                issues,
            ):
                continue

            evidence_id = evidence.get("evidence_id")
            if not isinstance(evidence_id, str) or not re.fullmatch(r"OBS-[A-Z0-9-]+", evidence_id):
                issues.append(_issue("invalid_evidence_id", f"{evidence_path}.evidence_id", "evidence_id deve usar o prefixo OBS-*."))
            elif evidence_id in evidence_ids:
                issues.append(_issue("duplicate_evidence_id", f"{evidence_path}.evidence_id", "evidence_id duplicado."))
            else:
                evidence_ids.add(evidence_id)
                opportunity_evidence_ids.add(evidence_id)

            if evidence.get("opportunity_id") != opportunity_id:
                issues.append(_issue("evidence_opportunity_mismatch", f"{evidence_path}.opportunity_id", "A evidência pertence a outra oportunidade."))
            if evidence.get("quality") not in QUALITY_VALUES:
                issues.append(_issue("invalid_enum", f"{evidence_path}.quality", "Qualidade da evidência inválida."))
            _validate_datetime(evidence.get("collected_at"), f"{evidence_path}.collected_at", issues)

            value = evidence.get("value")
            field = evidence.get("field")
            if isinstance(value, float) and not math.isfinite(value):
                issues.append(_issue("invalid_value", f"{evidence_path}.value", "O valor numérico deve ser finito."))
            if (
                _is_finite_number(value)
                and isinstance(field, str)
                and any(token in field.lower() for token in NON_NEGATIVE_FIELD_TOKENS)
                and value < 0
            ):
                issues.append(_issue("invalid_value", f"{evidence_path}.value", "O campo não aceita valor negativo."))

        calculated = opportunity.get("calculated_indicators")
        if not isinstance(calculated, list) or not calculated:
            issues.append(_issue("missing_calc_indicators", f"{path}.calculated_indicators", "Indicadores CALC-* estão ausentes."))
            calculated = []

        official_score_found = False
        for calc_index, calculation in enumerate(calculated):
            calc_path = f"{path}.calculated_indicators[{calc_index}]"
            if not _require_fields(
                calculation,
                (
                    "indicator_id",
                    "opportunity_id",
                    "field",
                    "value",
                    "value_type",
                    "unit",
                    "calculation_method",
                    "calculation_version",
                    "calculated_at",
                    "source_evidence_ids",
                    "quality",
                    "warnings",
                ),
                calc_path,
                issues,
            ):
                continue

            indicator_id = calculation.get("indicator_id")
            if not isinstance(indicator_id, str) or not re.fullmatch(r"CALC-[A-Z0-9-]+", indicator_id):
                issues.append(_issue("invalid_indicator_id", f"{calc_path}.indicator_id", "indicator_id deve usar o prefixo CALC-*."))
            elif indicator_id in indicator_ids:
                issues.append(_issue("duplicate_indicator_id", f"{calc_path}.indicator_id", "indicator_id duplicado."))
            else:
                indicator_ids.add(indicator_id)

            if calculation.get("opportunity_id") != opportunity_id:
                issues.append(_issue("calculation_opportunity_mismatch", f"{calc_path}.opportunity_id", "O cálculo pertence a outra oportunidade."))

            calc_value = calculation.get("value")
            if isinstance(calc_value, float) and not math.isfinite(calc_value):
                issues.append(_issue("invalid_value", f"{calc_path}.value", "O indicador deve ser finito."))

            if calculation.get("value_type") not in CALCULATED_VALUE_TYPES:
                issues.append(_issue("invalid_enum", f"{calc_path}.value_type", "Tipo de valor calculado inválido."))
            elif not _value_matches_declared_type(calc_value, calculation.get("value_type")):
                issues.append(_issue("value_type_mismatch", f"{calc_path}.value", "O valor não corresponde ao value_type declarado."))
            if calculation.get("quality") not in QUALITY_VALUES:
                issues.append(_issue("invalid_enum", f"{calc_path}.quality", "Qualidade do indicador inválida."))
            if not isinstance(calculation.get("calculation_method"), str) or not calculation.get("calculation_method"):
                issues.append(_issue("invalid_value", f"{calc_path}.calculation_method", "Método de cálculo deve ser identificado."))
            if not isinstance(calculation.get("calculation_version"), str) or not calculation.get("calculation_version"):
                issues.append(_issue("invalid_value", f"{calc_path}.calculation_version", "Versão do cálculo deve ser identificada."))
            _validate_datetime(calculation.get("calculated_at"), f"{calc_path}.calculated_at", issues)

            source_ids = calculation.get("source_evidence_ids")
            if not isinstance(source_ids, list):
                issues.append(_issue("invalid_type", f"{calc_path}.source_evidence_ids", "IDs-fonte devem formar um array."))
            else:
                if len(source_ids) != len(set(source_ids)):
                    issues.append(_issue("duplicate_source_evidence_id", f"{calc_path}.source_evidence_ids", "ID-fonte duplicado no indicador."))
                for source_id in source_ids:
                    if source_id not in opportunity_evidence_ids:
                        issues.append(_issue("unknown_source_evidence_id", f"{calc_path}.source_evidence_ids", "O indicador referencia uma evidência OBS-* inexistente ou de outra oportunidade."))

            warnings = calculation.get("warnings")
            if not isinstance(warnings, list) or any(not isinstance(item, str) or not item for item in warnings):
                issues.append(_issue("invalid_type", f"{calc_path}.warnings", "Warnings devem formar um array de strings não vazias."))

            if calculation.get("field") == "official_score":
                official_score_found = True
                if not _is_finite_number(calc_value):
                    issues.append(_issue("invalid_value", f"{calc_path}.value", "Score oficial deve ser numérico e finito."))
                elif calculation.get("unit") == "0-100" and not 0 <= calc_value <= 100:
                    issues.append(_issue("invalid_value", f"{calc_path}.value", "Score oficial deve respeitar a escala 0-100."))

        if require_official_score and not official_score_found:
            issues.append(_issue("missing_official_score", f"{path}.calculated_indicators", "Score oficial CALC-* ausente."))

    score_configuration = data.get("score_configuration")
    if _require_fields(
        score_configuration,
        ("version", "weights", "calculation_timestamp", "engine"),
        "$.score_configuration",
        issues,
    ):
        if not isinstance(score_configuration.get("version"), str) or not score_configuration.get("version"):
            issues.append(_issue("invalid_value", "$.score_configuration.version", "Versão do score deve ser não vazia."))
        if not isinstance(score_configuration.get("weights"), dict):
            issues.append(_issue("invalid_type", "$.score_configuration.weights", "Pesos devem formar um objeto."))
        if not isinstance(score_configuration.get("engine"), str) or not score_configuration.get("engine"):
            issues.append(_issue("invalid_value", "$.score_configuration.engine", "Motor de score deve ser identificado."))
        _validate_datetime(
            score_configuration.get("calculation_timestamp"),
            "$.score_configuration.calculation_timestamp",
            issues,
        )

    errors = [item for item in issues if item["severity"] == "error"]
    warnings = [item for item in issues if item["severity"] == "warning"]
    status = "invalid" if errors else "partial" if warnings else "sufficient"
    return {
        "status": status,
        "valid": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "issues": issues,
    }


def validate_json_file(
    path: str | Path,
    *,
    require_official_score: bool = True,
) -> dict[str, Any]:
    """Parse and validate a JSON file, reporting syntax errors deterministically."""

    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "invalid",
            "valid": False,
            "error_count": 1,
            "warning_count": 0,
            "issues": [_issue("invalid_json", "$", str(exc))],
        }
    return validate_input(data, require_official_score=require_official_score)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m src.validation.validate_input <input.json>", file=sys.stderr)
        return 2
    result = validate_json_file(argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

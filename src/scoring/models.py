"""Typed models used by the deterministic scoring engine."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from typing import Any


QUALITY_VALUES = {"high", "medium", "low", "unknown"}
DIMENSION_NAMES = ("demand", "economics", "competitive_attractiveness", "operator_fit")
OBS_ID_PATTERN = re.compile(r"^OBS-[A-Z0-9-]+$")


def decimal_value(value: Any, field_name: str, *, allow_none: bool = True) -> Decimal | None:
    """Convert a JSON-compatible number to Decimal without accepting booleans or non-finite values."""

    if value is None and allow_none:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric, not boolean")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    try:
        converted = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not converted.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return converted


def validate_evidence_ids(evidence_ids: tuple[str, ...], field_name: str) -> None:
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError(f"{field_name} contains duplicate evidence IDs")
    for evidence_id in evidence_ids:
        if not OBS_ID_PATTERN.fullmatch(evidence_id):
            raise ValueError(f"{field_name} contains an invalid OBS-* ID: {evidence_id}")


@dataclass(frozen=True)
class DimensionScoreInput:
    """A normalized deterministic dimension score supplied to the aggregation engine."""

    value: Decimal | int | float | str | None
    source_evidence_ids: tuple[str, ...] = ()
    quality: str = "unknown"
    indicator_id: str | None = None
    calculation_method: str | None = None
    calculation_version: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", decimal_value(self.value, "dimension score"))
        validate_evidence_ids(self.source_evidence_ids, "source_evidence_ids")
        if self.quality not in QUALITY_VALUES:
            raise ValueError(f"invalid dimension quality: {self.quality}")
        if self.value is not None and not Decimal("0") <= self.value <= Decimal("100"):
            raise ValueError("dimension score must be within 0-100")
        if self.value is not None:
            if not isinstance(self.indicator_id, str) or not re.fullmatch(
                r"CALC-[A-Z0-9-]+",
                self.indicator_id,
            ):
                raise ValueError("a provided dimension score requires a valid CALC-* indicator_id")
            if not isinstance(self.calculation_method, str) or not self.calculation_method:
                raise ValueError("a provided dimension score requires calculation_method")
            if not isinstance(self.calculation_version, str) or not self.calculation_version:
                raise ValueError("a provided dimension score requires calculation_version")


@dataclass(frozen=True)
class EconomicInputs:
    selling_price: Decimal | int | float | str | None
    product_cost: Decimal | int | float | str | None
    variable_fees: Decimal | int | float | str | None
    taxes: Decimal | int | float | str | None
    shipping_subsidy: Decimal | int | float | str | None
    other_variable_costs: Decimal | int | float | str | None
    currency: str = "BRL"
    source_evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "selling_price",
            "product_cost",
            "variable_fees",
            "taxes",
            "shipping_subsidy",
            "other_variable_costs",
        ):
            value = decimal_value(getattr(self, name), name)
            if value is not None and value < 0:
                raise ValueError(f"{name} must be non-negative")
            object.__setattr__(self, name, value)
        if not self.currency:
            raise ValueError("currency must be non-empty")
        validate_evidence_ids(self.source_evidence_ids, "economic source_evidence_ids")


@dataclass(frozen=True)
class OpportunityScoreInput:
    opportunity_id: str
    demand: DimensionScoreInput
    economics: DimensionScoreInput
    competitive_attractiveness: DimensionScoreInput
    operational_fit: str
    operational_fit_source_evidence_ids: tuple[str, ...]
    economic_inputs: EconomicInputs
    minimum_test_cost: Decimal | int | float | str | None
    operator_test_budget: Decimal | int | float | str | None
    budget_source_evidence_ids: tuple[str, ...]
    evidence_coverage_percent: Decimal | int | float | str
    demand_evidence_age_days: int
    economic_data_age_days: int
    independent_source_count: int
    logistics_lead_time_business_days: int | None
    calculated_at: str
    calculation_quality: str = "unknown"

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Z0-9-]+", self.opportunity_id):
            raise ValueError("opportunity_id must contain only uppercase letters, numbers, and hyphens")
        for name in ("minimum_test_cost", "operator_test_budget", "evidence_coverage_percent"):
            converted = decimal_value(getattr(self, name), name)
            object.__setattr__(self, name, converted)
        if self.minimum_test_cost is not None and self.minimum_test_cost < 0:
            raise ValueError("minimum_test_cost must be non-negative")
        if self.operator_test_budget is not None and self.operator_test_budget < 0:
            raise ValueError("operator_test_budget must be non-negative")
        if not Decimal("0") <= self.evidence_coverage_percent <= Decimal("100"):
            raise ValueError("evidence_coverage_percent must be within 0-100")
        for name in ("demand_evidence_age_days", "economic_data_age_days", "independent_source_count"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.logistics_lead_time_business_days is not None and (
            not isinstance(self.logistics_lead_time_business_days, int)
            or isinstance(self.logistics_lead_time_business_days, bool)
            or self.logistics_lead_time_business_days < 0
        ):
            raise ValueError("logistics_lead_time_business_days must be null or a non-negative integer")
        validate_evidence_ids(self.budget_source_evidence_ids, "budget_source_evidence_ids")
        validate_evidence_ids(
            self.operational_fit_source_evidence_ids,
            "operational_fit_source_evidence_ids",
        )
        if self.calculation_quality not in QUALITY_VALUES:
            raise ValueError(f"invalid calculation quality: {self.calculation_quality}")


@dataclass(frozen=True)
class CalculatedIndicator:
    indicator_id: str
    opportunity_id: str
    field: str
    value: Decimal
    unit: str
    calculation_method: str
    calculation_version: str
    calculated_at: str
    source_evidence_ids: tuple[str, ...]
    quality: str
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        numeric_value: int | float
        if self.value == self.value.to_integral_value():
            numeric_value = int(self.value)
            value_type = "integer"
        else:
            numeric_value = float(self.value)
            value_type = "number"
        return {
            "indicator_id": self.indicator_id,
            "opportunity_id": self.opportunity_id,
            "field": self.field,
            "value": numeric_value,
            "value_type": value_type,
            "unit": self.unit,
            "calculation_method": self.calculation_method,
            "calculation_version": self.calculation_version,
            "calculated_at": self.calculated_at,
            "source_evidence_ids": list(self.source_evidence_ids),
            "quality": self.quality,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class KillSwitchDecision:
    switch_id: str
    triggered: bool
    reason: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "switch_id": self.switch_id,
            "triggered": self.triggered,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ScoreResult:
    opportunity_id: str
    score_version: str
    status: str
    official_score: Decimal | None
    official_rank: int | None
    indicators: tuple[CalculatedIndicator, ...]
    kill_switches: tuple[KillSwitchDecision, ...]
    missing_dimensions: tuple[str, ...] = ()
    eligibility_issues: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def with_rank(self, rank: int | None) -> "ScoreResult":
        return replace(self, official_rank=rank)

    def as_dict(self, display_precision: int = 2) -> dict[str, Any]:
        display_score = None
        raw_score = None
        if self.official_score is not None:
            raw_score = float(self.official_score)
            display_score = f"{self.official_score:.{display_precision}f}"
        return {
            "opportunity_id": self.opportunity_id,
            "score_version": self.score_version,
            "status": self.status,
            "official_score": raw_score,
            "official_score_display": display_score,
            "official_rank": self.official_rank,
            "indicators": [indicator.as_dict() for indicator in self.indicators],
            "kill_switches": [decision.as_dict() for decision in self.kill_switches],
            "missing_dimensions": list(self.missing_dimensions),
            "eligibility_issues": list(self.eligibility_issues),
            "warnings": list(self.warnings),
        }

"""Strict typed models for OFFER-INTELLIGENCE-0.1.0."""

from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    model_validator,
)


INTELLIGENCE_VERSION = "OFFER-INTELLIGENCE-0.1.0"
DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "offer-intelligence-v0.1.json"
)

Quality = Literal["high", "medium", "low", "unknown"]
Platform = Literal["meta", "tiktok", "google", "other"]
OfferFormat = Literal["quiz", "vsl", "direct", "other", "unknown"]
IndicatorField = Literal[
    "active_ads_current",
    "active_ads_growth_percent",
    "creative_churn_percent",
    "advertiser_density_per_100_offers",
    "price_position_percentile",
    "offer_format_share_quiz_percent",
    "offer_format_share_vsl_percent",
    "offer_format_share_direct_percent",
]
INDICATOR_FIELDS: tuple[IndicatorField, ...] = (
    "active_ads_current",
    "active_ads_growth_percent",
    "creative_churn_percent",
    "advertiser_density_per_100_offers",
    "price_position_percentile",
    "offer_format_share_quiz_percent",
    "offer_format_share_vsl_percent",
    "offer_format_share_direct_percent",
)


def _aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value


def _decimal_input(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("boolean values are not numeric")
    if isinstance(value, str):
        raise ValueError("numeric strings are not accepted")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("numeric values must be finite")
    try:
        converted = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("value must be a finite decimal number") from exc
    if not converted.is_finite():
        raise ValueError("numeric values must be finite")
    return converted


def _unique(values: list[str]) -> list[str]:
    if len(values) != len(set(values)):
        raise ValueError("values must be unique")
    return values


AwareDatetime = Annotated[datetime, AfterValidator(_aware_datetime)]
DecimalValue = Annotated[Decimal, BeforeValidator(_decimal_input)]
NonNegativeDecimal = Annotated[DecimalValue, Field(ge=0)]
NonEmptyString = Annotated[str, Field(min_length=1)]
OpportunityId = Annotated[str, Field(pattern=r"^[A-Z0-9-]+$")]
EvidenceId = Annotated[str, Field(pattern=r"^OBS-[A-Z0-9-]+$")]
EvidenceIds = Annotated[list[EvidenceId], Field(min_length=1), AfterValidator(_unique)]
UniqueStrings = Annotated[list[NonEmptyString], AfterValidator(_unique)]


class StrictModel(BaseModel):
    """Base model that rejects unknown contract fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class AnalysisWindow(StrictModel):
    start_at: AwareDatetime
    end_at: AwareDatetime

    @model_validator(mode="after")
    def validate_order(self) -> "AnalysisWindow":
        if self.start_at > self.end_at:
            raise ValueError("window.start_at cannot be later than window.end_at")
        return self


class TargetOffer(StrictModel):
    platform: Platform
    subniche: NonEmptyString
    ticket_amount: NonNegativeDecimal
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    source_evidence_ids: EvidenceIds
    quality: Quality


class AdSnapshot(StrictModel):
    snapshot_id: Annotated[str, Field(pattern=r"^SNAP-[A-Z0-9-]+$")]
    observed_at: AwareDatetime
    platform: Platform
    active_ads_count: Annotated[StrictInt, Field(ge=0)]
    creative_ids: UniqueStrings
    source_evidence_ids: EvidenceIds
    quality: Quality


class MarketOffer(StrictModel):
    sample_id: Annotated[str, Field(pattern=r"^SAMPLE-[A-Z0-9-]+$")]
    observed_at: AwareDatetime
    platform: Platform
    advertiser_id: NonEmptyString
    offer_id: NonEmptyString
    subniche: NonEmptyString
    ticket_amount: NonNegativeDecimal | None
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")] | None
    offer_format: OfferFormat
    is_active: StrictBool
    source_evidence_ids: EvidenceIds
    quality: Quality


class OfferIntelligenceInput(StrictModel):
    schema_version: Literal["1.0.0"]
    intelligence_version: Literal["OFFER-INTELLIGENCE-0.1.0"]
    analysis_id: NonEmptyString
    opportunity_id: OpportunityId
    generated_at: AwareDatetime
    calculation_timestamp: AwareDatetime
    window: AnalysisWindow
    target_offer: TargetOffer
    ad_snapshots: list[AdSnapshot]
    market_sample: list[MarketOffer]

    @model_validator(mode="after")
    def validate_contract_invariants(self) -> "OfferIntelligenceInput":
        if self.generated_at < self.window.end_at:
            raise ValueError("generated_at cannot be earlier than window.end_at")
        if self.calculation_timestamp < self.window.end_at:
            raise ValueError("calculation_timestamp cannot be earlier than window.end_at")
        self._require_unique(
            [snapshot.snapshot_id for snapshot in self.ad_snapshots],
            "snapshot_id",
        )
        self._require_unique(
            [offer.sample_id for offer in self.market_sample],
            "sample_id",
        )
        self._require_unique(
            [offer.offer_id for offer in self.market_sample],
            "offer_id",
        )
        return self

    @staticmethod
    def _require_unique(values: list[str], field_name: str) -> None:
        if len(values) != len(set(values)):
            raise ValueError(f"{field_name} values must be unique")


class ScaleConfig(StrictModel):
    display_precision: Literal[2]
    internal_numeric_type: Literal["decimal"]
    rounding_policy: Literal["display_only"]
    missing_value_policy: Literal["omit_indicator_and_report_missing_input"]
    division_by_zero_policy: Literal["omit_indicator_and_warn"]


class SnapshotPolicyConfig(StrictModel):
    window_boundaries: Literal["inclusive"]
    baseline_selection: Literal["first_by_observed_at_then_snapshot_id"]
    current_selection: Literal["last_by_observed_at_then_snapshot_id"]
    timestamp_tie_breaker: Literal["snapshot_id_ascending"]
    same_platform_required: Literal[True]
    minimum_snapshots_for_growth: Annotated[int, Field(ge=2)]
    minimum_snapshots_for_churn: Annotated[int, Field(ge=2)]


class MarketSamplePolicyConfig(StrictModel):
    same_platform_required: Literal[True]
    target_subniche_only: Literal[True]
    active_offers_only: Literal[True]
    minimum_offers_for_density: Annotated[int, Field(ge=1)]
    minimum_offers_for_price_position: Annotated[int, Field(ge=1)]
    minimum_recognized_offers_for_format_share: Annotated[int, Field(ge=1)]
    price_currency_policy: Literal["same_currency_only"]
    currency_conversion_policy: Literal["forbidden"]
    recognized_offer_formats: tuple[Literal["quiz", "vsl", "direct"], ...]
    unrecognized_format_policy: Literal["exclude_from_format_share_denominator"]

    @model_validator(mode="after")
    def validate_formats(self) -> "MarketSamplePolicyConfig":
        if self.recognized_offer_formats != ("quiz", "vsl", "direct"):
            raise ValueError("recognized_offer_formats must be quiz, vsl, direct in order")
        return self


class QualityPolicyConfig(StrictModel):
    allowed_values: tuple[Quality, ...]
    aggregation: Literal["lowest_source_quality"]
    missing_source_quality: Literal["unknown"]

    @model_validator(mode="after")
    def validate_quality_order(self) -> "QualityPolicyConfig":
        if self.allowed_values != ("high", "medium", "low", "unknown"):
            raise ValueError("allowed_values must preserve the authorized quality order")
        return self


class IndicatorDefinition(StrictModel):
    field: IndicatorField
    indicator_id_template: Annotated[
        str,
        Field(pattern=r"^CALC-[A-Z0-9-]+-\{opportunity_id\}$"),
    ]
    calculation_method: NonEmptyString
    unit: Literal["ads", "percent", "advertisers_per_100_offers", "percentile_0_100"]


class OfferIntelligenceConfig(StrictModel):
    schema_ref: str = Field(alias="$schema")
    config_schema_version: Literal["1.0.0"]
    intelligence_version: Literal["OFFER-INTELLIGENCE-0.1.0"]
    status: Literal["authorized"]
    scale: ScaleConfig
    snapshot_policy: SnapshotPolicyConfig
    market_sample_policy: MarketSamplePolicyConfig
    quality_policy: QualityPolicyConfig
    indicator_definitions: tuple[IndicatorDefinition, ...]

    @model_validator(mode="after")
    def validate_indicator_order(self) -> "OfferIntelligenceConfig":
        fields = tuple(definition.field for definition in self.indicator_definitions)
        if fields != INDICATOR_FIELDS:
            raise ValueError("indicator_definitions must match the authorized order exactly")
        if len({definition.indicator_id_template for definition in self.indicator_definitions}) != len(fields):
            raise ValueError("indicator_id_template values must be unique")
        return self


class CalculatedIndicatorResult(StrictModel):
    indicator_id: Annotated[str, Field(pattern=r"^CALC-[A-Z0-9-]+$")]
    opportunity_id: OpportunityId
    field: IndicatorField
    value: DecimalValue
    value_type: Literal["integer", "number"]
    unit: NonEmptyString
    calculation_method: NonEmptyString
    calculation_version: Literal["OFFER-INTELLIGENCE-0.1.0"]
    calculated_at: AwareDatetime
    source_evidence_ids: EvidenceIds
    quality: Quality
    warnings: tuple[NonEmptyString, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        value: int | float
        if self.value == self.value.to_integral_value():
            value = int(self.value)
        else:
            value = float(self.value)
        serialized = self.model_dump(mode="json")
        serialized["value"] = value
        serialized["warnings"] = list(self.warnings)
        return serialized


class MissingInput(StrictModel):
    indicator_field: IndicatorField
    required_inputs: tuple[NonEmptyString, ...]
    reason: NonEmptyString


class IntelligenceWarning(StrictModel):
    code: Annotated[str, Field(pattern=r"^[a-z0-9_]+$")]
    message: NonEmptyString
    evidence_ids: tuple[EvidenceId, ...] = ()


class OfferIntelligenceResult(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    intelligence_version: Literal["OFFER-INTELLIGENCE-0.1.0"] = INTELLIGENCE_VERSION
    analysis_id: NonEmptyString
    opportunity_id: OpportunityId
    calculated_at: AwareDatetime
    status: Literal["complete", "partial", "invalid"]
    indicators: tuple[CalculatedIndicatorResult, ...]
    missing_inputs: tuple[MissingInput, ...]
    warnings: tuple[IntelligenceWarning, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "intelligence_version": self.intelligence_version,
            "analysis_id": self.analysis_id,
            "opportunity_id": self.opportunity_id,
            "calculated_at": self.calculated_at.isoformat(),
            "status": self.status,
            "indicators": [indicator.as_dict() for indicator in self.indicators],
            "missing_inputs": [item.model_dump(mode="json") for item in self.missing_inputs],
            "warnings": [warning.model_dump(mode="json") for warning in self.warnings],
        }

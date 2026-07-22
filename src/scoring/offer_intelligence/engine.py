"""Isolated deterministic engine for OFFER-INTELLIGENCE-0.1.0."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.scoring.offer_intelligence.indicators import (
    active_ads_current,
    active_ads_growth_percent,
    advertiser_density_per_100_offers,
    creative_churn_percent,
    offer_format_shares,
    price_position_percentile,
)
from src.scoring.offer_intelligence.models import (
    DEFAULT_CONFIG_PATH,
    INDICATOR_FIELDS,
    AdSnapshot,
    CalculatedIndicatorResult,
    IndicatorDefinition,
    IndicatorField,
    IntelligenceWarning,
    MarketOffer,
    MissingInput,
    OfferIntelligenceConfig,
    OfferIntelligenceInput,
    OfferIntelligenceResult,
    Quality,
)


QUALITY_RANK: dict[Quality, int] = {
    "high": 0,
    "medium": 1,
    "low": 2,
    "unknown": 3,
}


class OfferIntelligenceEngine:
    """Calculate market indicators without reading or changing the official score."""

    def __init__(self, config: OfferIntelligenceConfig) -> None:
        self.config = config
        self.intelligence_version = config.intelligence_version
        self._definitions: dict[IndicatorField, IndicatorDefinition] = {
            definition.field: definition for definition in config.indicator_definitions
        }

    @classmethod
    def from_file(
        cls,
        path: str | Path = DEFAULT_CONFIG_PATH,
    ) -> "OfferIntelligenceEngine":
        data = json.loads(Path(path).read_text(encoding="utf-8"), parse_float=Decimal)
        return cls(OfferIntelligenceConfig.model_validate(data))

    def analyze(
        self,
        data: OfferIntelligenceInput | Mapping[str, Any],
    ) -> OfferIntelligenceResult:
        payload = (
            data
            if isinstance(data, OfferIntelligenceInput)
            else OfferIntelligenceInput.model_validate(data)
        )
        indicators: dict[IndicatorField, CalculatedIndicatorResult] = {}
        missing: dict[IndicatorField, MissingInput] = {}
        warnings: list[IntelligenceWarning] = []

        snapshots = self._eligible_snapshots(payload)
        self._calculate_snapshot_indicators(
            payload,
            snapshots,
            indicators,
            missing,
            warnings,
        )

        market_offers = self._eligible_market_offers(payload)
        self._calculate_market_indicators(
            payload,
            market_offers,
            indicators,
            missing,
            warnings,
        )

        ordered_indicators = tuple(
            indicators[field] for field in INDICATOR_FIELDS if field in indicators
        )
        ordered_missing = tuple(
            missing[field] for field in INDICATOR_FIELDS if field in missing
        )
        ordered_warnings = tuple(
            sorted(
                self._unique_warnings(warnings),
                key=lambda warning: (warning.code, warning.evidence_ids),
            )
        )
        status = "complete" if len(ordered_indicators) == len(INDICATOR_FIELDS) else "partial"
        return OfferIntelligenceResult(
            analysis_id=payload.analysis_id,
            opportunity_id=payload.opportunity_id,
            calculated_at=payload.calculation_timestamp,
            status=status,
            indicators=ordered_indicators,
            missing_inputs=ordered_missing,
            warnings=ordered_warnings,
        )

    def _calculate_snapshot_indicators(
        self,
        payload: OfferIntelligenceInput,
        snapshots: list[AdSnapshot],
        indicators: dict[IndicatorField, CalculatedIndicatorResult],
        missing: dict[IndicatorField, MissingInput],
        warnings: list[IntelligenceWarning],
    ) -> None:
        if not snapshots:
            self._record_missing(
                missing,
                "active_ads_current",
                ("ad_snapshots.active_ads_count",),
                "No comparable snapshot exists inside the analysis window.",
            )
            self._record_missing(
                missing,
                "active_ads_growth_percent",
                ("ad_snapshots[2].active_ads_count",),
                "At least two comparable snapshots are required.",
            )
            self._record_missing(
                missing,
                "creative_churn_percent",
                ("ad_snapshots[2].creative_ids",),
                "At least two comparable creative snapshots are required.",
            )
            return

        current = snapshots[-1]
        indicators["active_ads_current"] = self._indicator(
            payload,
            "active_ads_current",
            active_ads_current(current.active_ads_count),
            current.source_evidence_ids,
            (current.quality,),
        )

        growth_minimum = self.config.snapshot_policy.minimum_snapshots_for_growth
        if len(snapshots) < growth_minimum:
            self._record_missing(
                missing,
                "active_ads_growth_percent",
                (f"ad_snapshots[{growth_minimum}].active_ads_count",),
                f"At least {growth_minimum} comparable snapshots are required.",
            )
        else:
            baseline = snapshots[0]
            growth = active_ads_growth_percent(
                baseline.active_ads_count,
                current.active_ads_count,
            )
            evidence_ids = self._evidence_ids(
                baseline.source_evidence_ids,
                current.source_evidence_ids,
            )
            if growth is None:
                self._record_missing(
                    missing,
                    "active_ads_growth_percent",
                    ("ad_snapshots.baseline.active_ads_count_non_zero",),
                    "Growth is undefined when the baseline count is zero.",
                )
                warnings.append(
                    IntelligenceWarning(
                        code="active_ads_growth_zero_baseline",
                        message="Active-ad growth was omitted because the baseline count is zero.",
                        evidence_ids=evidence_ids,
                    )
                )
            else:
                indicators["active_ads_growth_percent"] = self._indicator(
                    payload,
                    "active_ads_growth_percent",
                    growth,
                    evidence_ids,
                    (baseline.quality, current.quality),
                )

        churn_minimum = self.config.snapshot_policy.minimum_snapshots_for_churn
        if len(snapshots) < churn_minimum:
            self._record_missing(
                missing,
                "creative_churn_percent",
                (f"ad_snapshots[{churn_minimum}].creative_ids",),
                f"At least {churn_minimum} comparable creative snapshots are required.",
            )
        else:
            baseline = snapshots[0]
            churn = creative_churn_percent(baseline.creative_ids, current.creative_ids)
            evidence_ids = self._evidence_ids(
                baseline.source_evidence_ids,
                current.source_evidence_ids,
            )
            if churn is None:
                self._record_missing(
                    missing,
                    "creative_churn_percent",
                    ("ad_snapshots.baseline.creative_ids_non_empty",),
                    "Creative churn is undefined when the baseline set is empty.",
                )
                warnings.append(
                    IntelligenceWarning(
                        code="creative_churn_empty_baseline",
                        message="Creative churn was omitted because the baseline set is empty.",
                        evidence_ids=evidence_ids,
                    )
                )
            else:
                indicators["creative_churn_percent"] = self._indicator(
                    payload,
                    "creative_churn_percent",
                    churn,
                    evidence_ids,
                    (baseline.quality, current.quality),
                )

    def _calculate_market_indicators(
        self,
        payload: OfferIntelligenceInput,
        market_offers: list[MarketOffer],
        indicators: dict[IndicatorField, CalculatedIndicatorResult],
        missing: dict[IndicatorField, MissingInput],
        warnings: list[IntelligenceWarning],
    ) -> None:
        target = payload.target_offer
        density_minimum = self.config.market_sample_policy.minimum_offers_for_density
        if len(market_offers) < density_minimum:
            self._record_missing(
                missing,
                "advertiser_density_per_100_offers",
                (f"market_sample[{density_minimum}].advertiser_id",),
                f"At least {density_minimum} valid active offers are required.",
            )
        else:
            density = advertiser_density_per_100_offers(
                [offer.advertiser_id for offer in market_offers]
            )
            if density is None:  # Defensive: the minimum above makes this unreachable.
                raise RuntimeError("density formula returned no value for a non-empty sample")
            indicators["advertiser_density_per_100_offers"] = self._indicator(
                payload,
                "advertiser_density_per_100_offers",
                density,
                self._market_evidence_ids(payload, market_offers),
                self._market_qualities(payload, market_offers),
            )

        incompatible_prices = [
            offer
            for offer in market_offers
            if offer.ticket_amount is not None
            and offer.currency is not None
            and offer.currency != target.currency
        ]
        if incompatible_prices:
            warnings.append(
                IntelligenceWarning(
                    code="price_currency_mismatch_excluded",
                    message="Market prices in currencies different from the target were excluded.",
                    evidence_ids=self._evidence_ids(
                        *(offer.source_evidence_ids for offer in incompatible_prices)
                    ),
                )
            )
        priced_offers = [
            offer
            for offer in market_offers
            if offer.ticket_amount is not None and offer.currency == target.currency
        ]
        price_minimum = self.config.market_sample_policy.minimum_offers_for_price_position
        if len(priced_offers) < price_minimum:
            self._record_missing(
                missing,
                "price_position_percentile",
                (
                    f"market_sample[{price_minimum}].ticket_amount",
                    f"market_sample[{price_minimum}].currency={target.currency}",
                ),
                f"At least {price_minimum} same-currency prices are required.",
            )
        else:
            percentile = price_position_percentile(
                target.ticket_amount,
                [offer.ticket_amount for offer in priced_offers if offer.ticket_amount is not None],
            )
            if percentile is None:  # Defensive: the minimum above makes this unreachable.
                raise RuntimeError("price formula returned no value for a non-empty sample")
            indicators["price_position_percentile"] = self._indicator(
                payload,
                "price_position_percentile",
                percentile,
                self._market_evidence_ids(payload, priced_offers),
                self._market_qualities(payload, priced_offers),
            )

        recognized_formats = set(self.config.market_sample_policy.recognized_offer_formats)
        format_offers = [
            offer for offer in market_offers if offer.offer_format in recognized_formats
        ]
        format_minimum = (
            self.config.market_sample_policy.minimum_recognized_offers_for_format_share
        )
        format_fields: tuple[tuple[str, IndicatorField], ...] = (
            ("quiz", "offer_format_share_quiz_percent"),
            ("vsl", "offer_format_share_vsl_percent"),
            ("direct", "offer_format_share_direct_percent"),
        )
        if len(format_offers) < format_minimum:
            for _, field in format_fields:
                self._record_missing(
                    missing,
                    field,
                    (f"market_sample[{format_minimum}].offer_format",),
                    f"At least {format_minimum} recognized offer formats are required.",
                )
        else:
            shares = offer_format_shares(offer.offer_format for offer in format_offers)
            if shares is None:  # Defensive: the minimum above makes this unreachable.
                raise RuntimeError("format-share formula returned no values")
            evidence_ids = self._market_evidence_ids(payload, format_offers)
            qualities = self._market_qualities(payload, format_offers)
            for offer_format, field in format_fields:
                indicators[field] = self._indicator(
                    payload,
                    field,
                    shares[offer_format],
                    evidence_ids,
                    qualities,
                )

    def _indicator(
        self,
        payload: OfferIntelligenceInput,
        field: IndicatorField,
        value: Decimal,
        evidence_ids: Iterable[str],
        qualities: Iterable[Quality],
    ) -> CalculatedIndicatorResult:
        definition = self._definitions[field]
        value_type = "integer" if value == value.to_integral_value() else "number"
        return CalculatedIndicatorResult(
            indicator_id=definition.indicator_id_template.format(
                opportunity_id=payload.opportunity_id
            ),
            opportunity_id=payload.opportunity_id,
            field=field,
            value=value,
            value_type=value_type,
            unit=definition.unit,
            calculation_method=definition.calculation_method,
            calculation_version=self.intelligence_version,
            calculated_at=payload.calculation_timestamp,
            source_evidence_ids=list(evidence_ids),
            quality=self._lowest_quality(qualities),
            warnings=(),
        )

    @staticmethod
    def _record_missing(
        missing: dict[IndicatorField, MissingInput],
        field: IndicatorField,
        required_inputs: tuple[str, ...],
        reason: str,
    ) -> None:
        missing[field] = MissingInput(
            indicator_field=field,
            required_inputs=required_inputs,
            reason=reason,
        )

    @staticmethod
    def _evidence_ids(*groups: Iterable[str]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item for group in groups for item in group))

    def _market_evidence_ids(
        self,
        payload: OfferIntelligenceInput,
        offers: Iterable[MarketOffer],
    ) -> tuple[str, ...]:
        return self._evidence_ids(
            payload.target_offer.source_evidence_ids,
            *(offer.source_evidence_ids for offer in offers),
        )

    @staticmethod
    def _market_qualities(
        payload: OfferIntelligenceInput,
        offers: Iterable[MarketOffer],
    ) -> tuple[Quality, ...]:
        return (
            payload.target_offer.quality,
            *(offer.quality for offer in offers),
        )

    @staticmethod
    def _lowest_quality(qualities: Iterable[Quality]) -> Quality:
        values = tuple(qualities)
        if not values:
            return "unknown"
        return max(values, key=QUALITY_RANK.__getitem__)

    @staticmethod
    def _unique_warnings(
        warnings: Iterable[IntelligenceWarning],
    ) -> tuple[IntelligenceWarning, ...]:
        unique: dict[tuple[str, tuple[str, ...]], IntelligenceWarning] = {}
        for warning in warnings:
            unique[(warning.code, warning.evidence_ids)] = warning
        return tuple(unique.values())

    @staticmethod
    def _eligible_snapshots(payload: OfferIntelligenceInput) -> list[AdSnapshot]:
        target_platform = payload.target_offer.platform
        return sorted(
            (
                snapshot
                for snapshot in payload.ad_snapshots
                if payload.window.start_at <= snapshot.observed_at <= payload.window.end_at
                and snapshot.platform == target_platform
            ),
            key=lambda snapshot: (snapshot.observed_at, snapshot.snapshot_id),
        )

    @staticmethod
    def _eligible_market_offers(payload: OfferIntelligenceInput) -> list[MarketOffer]:
        target = payload.target_offer
        return sorted(
            (
                offer
                for offer in payload.market_sample
                if payload.window.start_at <= offer.observed_at <= payload.window.end_at
                and offer.platform == target.platform
                and offer.subniche == target.subniche
                and offer.is_active
            ),
            key=lambda offer: (offer.observed_at, offer.sample_id),
        )

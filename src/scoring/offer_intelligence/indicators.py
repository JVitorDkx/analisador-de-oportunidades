"""Authorized Decimal formulas for OFFER-INTELLIGENCE-0.1.0."""

from __future__ import annotations

from collections.abc import Collection, Iterable
from decimal import Decimal


HUNDRED = Decimal("100")
HALF = Decimal("0.5")
RECOGNIZED_FORMATS = ("quiz", "vsl", "direct")


def active_ads_current(current_count: int) -> Decimal:
    """Return the observed count from the selected current snapshot."""

    if not isinstance(current_count, int) or isinstance(current_count, bool) or current_count < 0:
        raise ValueError("current_count must be a non-negative integer")
    return Decimal(current_count)


def active_ads_growth_percent(
    baseline_count: int,
    current_count: int,
) -> Decimal | None:
    """Return count growth in percent, or None for a zero baseline."""

    for name, value in (("baseline_count", baseline_count), ("current_count", current_count)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
    if baseline_count == 0:
        return None
    baseline = Decimal(baseline_count)
    return (Decimal(current_count) - baseline) / baseline * HUNDRED


def creative_churn_percent(
    baseline_creative_ids: Collection[str],
    current_creative_ids: Collection[str],
) -> Decimal | None:
    """Return the share of baseline creatives absent from the current snapshot."""

    baseline = set(baseline_creative_ids)
    if not baseline:
        return None
    retained = len(baseline & set(current_creative_ids))
    return Decimal(len(baseline) - retained) / Decimal(len(baseline)) * HUNDRED


def advertiser_density_per_100_offers(advertiser_ids: Collection[str]) -> Decimal | None:
    """Return distinct advertisers per 100 valid active offers."""

    if not advertiser_ids:
        return None
    return Decimal(len(set(advertiser_ids))) / Decimal(len(advertiser_ids)) * HUNDRED


def price_position_percentile(
    target_price: Decimal,
    sample_prices: Collection[Decimal],
) -> Decimal | None:
    """Return the deterministic midrank percentile of the target price."""

    if not sample_prices:
        return None
    lower = sum(price < target_price for price in sample_prices)
    equal = sum(price == target_price for price in sample_prices)
    return (Decimal(lower) + HALF * Decimal(equal)) / Decimal(len(sample_prices)) * HUNDRED


def offer_format_shares(formats: Iterable[str]) -> dict[str, Decimal] | None:
    """Return shares for Quiz, VSL, and Direct using recognized formats only."""

    recognized = [value for value in formats if value in RECOGNIZED_FORMATS]
    if not recognized:
        return None
    denominator = Decimal(len(recognized))
    shares = {
        offer_format: Decimal(recognized.count(offer_format)) / denominator * HUNDRED
        for offer_format in RECOGNIZED_FORMATS
    }
    shares["direct"] = HUNDRED - shares["quiz"] - shares["vsl"]
    return shares

"""Authorized scale operations for SCORE-0.1.0."""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from src.scoring.models import decimal_value


def clamp(value: Decimal, minimum: Decimal, maximum: Decimal) -> Decimal:
    if minimum > maximum:
        raise ValueError("minimum cannot be greater than maximum")
    return min(max(value, minimum), maximum)


def weighted_score(
    dimension_scores: Mapping[str, Decimal | None],
    weights: Mapping[str, Decimal],
    *,
    minimum: Decimal = Decimal("0"),
    maximum: Decimal = Decimal("100"),
) -> Decimal | None:
    """Aggregate all required dimensions without redistributing missing weights."""

    if set(dimension_scores) != set(weights):
        raise ValueError("dimension scores and weights must contain the same keys")
    if any(value is None for value in dimension_scores.values()):
        return None
    total_weight = sum(weights.values(), Decimal("0"))
    if total_weight != Decimal("1"):
        raise ValueError("dimension weights must sum exactly to 1")
    total = Decimal("0")
    for dimension, raw_value in dimension_scores.items():
        value = decimal_value(raw_value, dimension, allow_none=False)
        if not minimum <= value <= maximum:
            raise ValueError(f"{dimension} must be within the configured scale")
        total += value * weights[dimension]
    return clamp(total, minimum, maximum)

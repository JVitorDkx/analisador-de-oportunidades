"""Authorized kill switches for SCORE-0.1.0."""

from __future__ import annotations

from decimal import Decimal

from src.scoring.models import KillSwitchDecision


def evaluate_non_positive_contribution_margin(
    contribution_margin: Decimal | None,
    *,
    enabled: bool,
) -> KillSwitchDecision:
    triggered = enabled and contribution_margin is not None and contribution_margin <= Decimal("0")
    return KillSwitchDecision(
        switch_id="non_positive_contribution_margin",
        triggered=triggered,
        reason="non_positive_contribution_margin" if triggered else None,
    )


def evaluate_test_cost_exceeds_budget(
    minimum_test_cost: Decimal | None,
    operator_test_budget: Decimal | None,
    *,
    enabled: bool,
) -> KillSwitchDecision:
    triggered = (
        enabled
        and minimum_test_cost is not None
        and operator_test_budget is not None
        and minimum_test_cost > operator_test_budget
    )
    return KillSwitchDecision(
        switch_id="test_cost_exceeds_budget",
        triggered=triggered,
        reason="test_cost_exceeds_operator_budget" if triggered else None,
    )

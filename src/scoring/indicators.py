"""Authorized deterministic indicator formulas for SCORE-0.1.0."""

from __future__ import annotations

from decimal import Decimal

from src.scoring.models import EconomicInputs


def contribution_margin_amount(inputs: EconomicInputs) -> Decimal | None:
    values = (
        inputs.selling_price,
        inputs.product_cost,
        inputs.variable_fees,
        inputs.taxes,
        inputs.shipping_subsidy,
        inputs.other_variable_costs,
    )
    if any(value is None for value in values):
        return None
    selling_price, product_cost, variable_fees, taxes, shipping_subsidy, other_variable_costs = values
    return selling_price - product_cost - variable_fees - taxes - shipping_subsidy - other_variable_costs


def contribution_margin_percent(inputs: EconomicInputs) -> Decimal | None:
    amount = contribution_margin_amount(inputs)
    if amount is None or inputs.selling_price is None or inputs.selling_price == 0:
        return None
    return amount / inputs.selling_price * Decimal("100")


def break_even_cpa(inputs: EconomicInputs) -> Decimal | None:
    return contribution_margin_amount(inputs)


def budget_fit_ratio(
    minimum_test_cost: Decimal | None,
    operator_test_budget: Decimal | None,
) -> Decimal | None:
    if minimum_test_cost is None or operator_test_budget is None or operator_test_budget == 0:
        return None
    return minimum_test_cost / operator_test_budget


def operational_fit_score(fit: str, mapping: dict[str, Decimal | None]) -> Decimal | None:
    if fit not in mapping:
        raise ValueError(f"unknown operational fit: {fit}")
    return mapping[fit]

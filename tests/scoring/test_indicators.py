from __future__ import annotations

import unittest
from decimal import Decimal

from src.scoring.indicators import (
    break_even_cpa,
    budget_fit_ratio,
    contribution_margin_amount,
    contribution_margin_percent,
    operational_fit_score,
)
from src.scoring.models import EconomicInputs


class IndicatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inputs = EconomicInputs(
            selling_price="100",
            product_cost="30",
            variable_fees="10",
            taxes="5",
            shipping_subsidy="5",
            other_variable_costs="0",
            source_evidence_ids=("OBS-ECON-001",),
        )

    def test_authorized_economic_formulas(self) -> None:
        self.assertEqual(contribution_margin_amount(self.inputs), Decimal("50"))
        self.assertEqual(contribution_margin_percent(self.inputs), Decimal("50"))
        self.assertEqual(break_even_cpa(self.inputs), Decimal("50"))

    def test_missing_economic_component_returns_null(self) -> None:
        inputs = EconomicInputs(
            selling_price="100",
            product_cost=None,
            variable_fees="10",
            taxes="5",
            shipping_subsidy="5",
            other_variable_costs="0",
        )

        self.assertIsNone(contribution_margin_amount(inputs))
        self.assertIsNone(contribution_margin_percent(inputs))
        self.assertIsNone(break_even_cpa(inputs))

    def test_zero_selling_price_does_not_divide(self) -> None:
        inputs = EconomicInputs(
            selling_price="0",
            product_cost="0",
            variable_fees="0",
            taxes="0",
            shipping_subsidy="0",
            other_variable_costs="0",
        )

        self.assertEqual(contribution_margin_amount(inputs), Decimal("0"))
        self.assertIsNone(contribution_margin_percent(inputs))

    def test_budget_fit_ratio(self) -> None:
        self.assertEqual(budget_fit_ratio(Decimal("250"), Decimal("500")), Decimal("0.5"))
        self.assertIsNone(budget_fit_ratio(Decimal("250"), Decimal("0")))
        self.assertIsNone(budget_fit_ratio(None, Decimal("500")))

    def test_operational_fit_mapping(self) -> None:
        mapping = {
            "strong_fit": Decimal("100"),
            "acceptable_fit": Decimal("75"),
            "conditional_fit": Decimal("50"),
            "poor_fit": Decimal("20"),
            "unknown": None,
        }

        self.assertEqual(operational_fit_score("strong_fit", mapping), Decimal("100"))
        self.assertIsNone(operational_fit_score("unknown", mapping))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from decimal import Decimal

from src.scoring.kill_switches import (
    evaluate_non_positive_contribution_margin,
    evaluate_test_cost_exceeds_budget,
)


class KillSwitchTests(unittest.TestCase):
    def test_non_positive_margin_triggers(self) -> None:
        self.assertTrue(
            evaluate_non_positive_contribution_margin(Decimal("0"), enabled=True).triggered
        )
        self.assertTrue(
            evaluate_non_positive_contribution_margin(Decimal("-0.01"), enabled=True).triggered
        )
        self.assertFalse(
            evaluate_non_positive_contribution_margin(Decimal("0.01"), enabled=True).triggered
        )

    def test_disabled_margin_switch_never_triggers(self) -> None:
        self.assertFalse(
            evaluate_non_positive_contribution_margin(Decimal("-10"), enabled=False).triggered
        )

    def test_test_cost_above_budget_triggers(self) -> None:
        self.assertTrue(
            evaluate_test_cost_exceeds_budget(
                Decimal("500.01"),
                Decimal("500"),
                enabled=True,
            ).triggered
        )
        self.assertFalse(
            evaluate_test_cost_exceeds_budget(
                Decimal("500"),
                Decimal("500"),
                enabled=True,
            ).triggered
        )


if __name__ == "__main__":
    unittest.main()

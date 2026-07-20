from __future__ import annotations

import unittest
from decimal import Decimal

from src.scoring.normalization import clamp, weighted_score


class NormalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.weights = {
            "demand": Decimal("0.30"),
            "economics": Decimal("0.30"),
            "competitive_attractiveness": Decimal("0.20"),
            "operator_fit": Decimal("0.20"),
        }

    def test_weighted_score_uses_authorized_weights(self) -> None:
        score = weighted_score(
            {
                "demand": Decimal("80"),
                "economics": Decimal("70"),
                "competitive_attractiveness": Decimal("60"),
                "operator_fit": Decimal("75"),
            },
            self.weights,
        )

        self.assertEqual(score, Decimal("72.00"))

    def test_missing_dimension_is_not_renormalized(self) -> None:
        score = weighted_score(
            {
                "demand": None,
                "economics": Decimal("70"),
                "competitive_attractiveness": Decimal("60"),
                "operator_fit": Decimal("75"),
            },
            self.weights,
        )

        self.assertIsNone(score)

    def test_invalid_weight_sum_is_rejected(self) -> None:
        invalid_weights = dict(self.weights)
        invalid_weights["operator_fit"] = Decimal("0.19")

        with self.assertRaisesRegex(ValueError, "sum exactly to 1"):
            weighted_score(
                {
                    "demand": Decimal("80"),
                    "economics": Decimal("70"),
                    "competitive_attractiveness": Decimal("60"),
                    "operator_fit": Decimal("75"),
                },
                invalid_weights,
            )

    def test_clamp_respects_official_scale(self) -> None:
        self.assertEqual(clamp(Decimal("-1"), Decimal("0"), Decimal("100")), Decimal("0"))
        self.assertEqual(clamp(Decimal("101"), Decimal("0"), Decimal("100")), Decimal("100"))


if __name__ == "__main__":
    unittest.main()

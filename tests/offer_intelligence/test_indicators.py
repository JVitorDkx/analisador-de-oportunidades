from __future__ import annotations

import unittest
from decimal import Decimal

from src.scoring.offer_intelligence.indicators import (
    active_ads_current,
    active_ads_growth_percent,
    advertiser_density_per_100_offers,
    creative_churn_percent,
    offer_format_shares,
    price_position_percentile,
)


class OfferIntelligenceIndicatorTests(unittest.TestCase):
    def test_active_ads_formulas_use_exact_decimal_values(self) -> None:
        self.assertEqual(active_ads_current(15), Decimal("15"))
        self.assertEqual(active_ads_growth_percent(10, 15), Decimal("50"))
        self.assertEqual(active_ads_growth_percent(20, 15), Decimal("-25"))

    def test_active_ads_growth_returns_none_for_zero_baseline(self) -> None:
        self.assertIsNone(active_ads_growth_percent(0, 10))

    def test_creative_churn_uses_baseline_retention(self) -> None:
        self.assertEqual(
            creative_churn_percent(("A", "B", "C", "D"), ("C", "D", "E")),
            Decimal("50"),
        )
        self.assertIsNone(creative_churn_percent((), ("A",)))

    def test_advertiser_density_counts_distinct_advertisers(self) -> None:
        self.assertEqual(
            advertiser_density_per_100_offers(("A", "A", "B", "C")),
            Decimal("75"),
        )
        self.assertIsNone(advertiser_density_per_100_offers(()))

    def test_price_position_uses_midrank_for_ties(self) -> None:
        self.assertEqual(
            price_position_percentile(
                Decimal("50"),
                (Decimal("40"), Decimal("50"), Decimal("50"), Decimal("60")),
            ),
            Decimal("50"),
        )
        self.assertIsNone(price_position_percentile(Decimal("50"), ()))

    def test_offer_format_shares_exclude_unrecognized_values_and_sum_to_100(self) -> None:
        shares = offer_format_shares(("quiz", "vsl", "direct", "other", "unknown"))

        self.assertIsNotNone(shares)
        assert shares is not None
        self.assertEqual(sum(shares.values(), Decimal("0")), Decimal("100"))
        self.assertEqual(shares["quiz"], Decimal(1) / Decimal(3) * Decimal(100))
        self.assertIsNone(offer_format_shares(("other", "unknown")))


if __name__ == "__main__":
    unittest.main()

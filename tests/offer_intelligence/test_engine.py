from __future__ import annotations

import copy
import json
import unittest
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from src.scoring.offer_intelligence import (
    OfferIntelligenceEngine,
    OfferIntelligenceInput,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = PROJECT_ROOT / "fixtures" / "offer_intelligence"


def load_fixture(name: str) -> dict:
    return json.loads(
        (FIXTURES_DIR / name).read_text(encoding="utf-8"),
        parse_float=Decimal,
    )


def indicator_values(result) -> dict[str, Decimal]:
    return {indicator.field: indicator.value for indicator in result.indicators}


class OfferIntelligenceEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = OfferIntelligenceEngine.from_file()

    def test_growth_fixture_produces_complete_exact_result_without_mutation(self) -> None:
        payload = load_fixture("offer_growth.json")
        original = copy.deepcopy(payload)

        result = self.engine.analyze(payload)

        self.assertEqual(payload, original)
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.missing_inputs, ())
        self.assertEqual(result.warnings, ())
        self.assertEqual(
            [indicator.field for indicator in result.indicators],
            [definition.field for definition in self.engine.config.indicator_definitions],
        )
        values = indicator_values(result)
        self.assertEqual(values["active_ads_current"], Decimal("15"))
        self.assertEqual(values["active_ads_growth_percent"], Decimal("50"))
        self.assertEqual(values["creative_churn_percent"], Decimal("50"))
        self.assertEqual(
            values["advertiser_density_per_100_offers"],
            Decimal(4) / Decimal(6) * Decimal(100),
        )
        self.assertEqual(
            values["price_position_percentile"],
            Decimal("2.5") / Decimal(6) * Decimal(100),
        )
        self.assertEqual(
            sum(
                values[field]
                for field in (
                    "offer_format_share_quiz_percent",
                    "offer_format_share_vsl_percent",
                    "offer_format_share_direct_percent",
                )
            ),
            Decimal("100"),
        )
        self.assertEqual(
            next(
                indicator.quality
                for indicator in result.indicators
                if indicator.field == "price_position_percentile"
            ),
            "medium",
        )
        serialized = result.as_dict()
        self.assertNotIn('"official_score"', json.dumps(serialized))
        self.assertTrue(
            all(
                indicator["calculation_version"] == "OFFER-INTELLIGENCE-0.1.0"
                for indicator in serialized["indicators"]
            )
        )

    def test_saturation_fixture_matches_frozen_contract_values(self) -> None:
        result = self.engine.analyze(load_fixture("market_saturation.json"))

        self.assertEqual(result.status, "complete")
        values = indicator_values(result)
        expected = {
            "active_ads_current": Decimal("44"),
            "active_ads_growth_percent": Decimal("10"),
            "creative_churn_percent": Decimal("25"),
            "advertiser_density_per_100_offers": Decimal("100"),
            "price_position_percentile": Decimal("75"),
            "offer_format_share_quiz_percent": Decimal("60"),
            "offer_format_share_vsl_percent": Decimal("20"),
            "offer_format_share_direct_percent": Decimal("20"),
        }
        self.assertEqual(values, expected)

    def test_incomplete_data_returns_only_current_ads_and_exact_missing_fields(self) -> None:
        result = self.engine.analyze(load_fixture("insufficient_market_data.json"))

        self.assertEqual(result.status, "partial")
        self.assertEqual(indicator_values(result), {"active_ads_current": Decimal("3")})
        self.assertEqual(
            [item.indicator_field for item in result.missing_inputs],
            [
                "active_ads_growth_percent",
                "creative_churn_percent",
                "advertiser_density_per_100_offers",
                "price_position_percentile",
                "offer_format_share_quiz_percent",
                "offer_format_share_vsl_percent",
                "offer_format_share_direct_percent",
            ],
        )

    def test_zero_baselines_omit_undefined_indicators_and_emit_warnings(self) -> None:
        payload = load_fixture("offer_growth.json")
        payload["ad_snapshots"][0]["active_ads_count"] = 0
        payload["ad_snapshots"][0]["creative_ids"] = []

        result = self.engine.analyze(payload)

        values = indicator_values(result)
        self.assertNotIn("active_ads_growth_percent", values)
        self.assertNotIn("creative_churn_percent", values)
        self.assertEqual(
            [warning.code for warning in result.warnings],
            ["active_ads_growth_zero_baseline", "creative_churn_empty_baseline"],
        )
        self.assertEqual(
            [item.indicator_field for item in result.missing_inputs[:2]],
            ["active_ads_growth_percent", "creative_churn_percent"],
        )

    def test_incompatible_currencies_are_excluded_without_conversion(self) -> None:
        payload = load_fixture("offer_growth.json")
        for offer in payload["market_sample"]:
            offer["currency"] = "USD"

        result = self.engine.analyze(payload)

        values = indicator_values(result)
        self.assertEqual(result.status, "partial")
        self.assertNotIn("price_position_percentile", values)
        self.assertIn("advertiser_density_per_100_offers", values)
        self.assertIn("offer_format_share_quiz_percent", values)
        self.assertEqual(
            [warning.code for warning in result.warnings],
            ["price_currency_mismatch_excluded"],
        )
        price_missing = next(
            item for item in result.missing_inputs if item.indicator_field == "price_position_percentile"
        )
        self.assertIn("currency=BRL", price_missing.required_inputs[1])

    def test_equal_timestamps_use_lexicographic_snapshot_order(self) -> None:
        payload = load_fixture("offer_growth.json")
        first, second = payload["ad_snapshots"]
        shared_timestamp = "2026-07-10T10:00:00Z"
        first.update(
            snapshot_id="SNAP-Z",
            observed_at=shared_timestamp,
            active_ads_count=20,
            creative_ids=["B", "C"],
        )
        second.update(
            snapshot_id="SNAP-A",
            observed_at=shared_timestamp,
            active_ads_count=10,
            creative_ids=["A", "B"],
        )
        payload["ad_snapshots"] = [first, second]

        result = self.engine.analyze(payload)

        values = indicator_values(result)
        self.assertEqual(values["active_ads_current"], Decimal("20"))
        self.assertEqual(values["active_ads_growth_percent"], Decimal("100"))
        self.assertEqual(values["creative_churn_percent"], Decimal("50"))

    def test_models_reject_unknown_fields_and_duplicate_identifiers(self) -> None:
        payload = load_fixture("offer_growth.json")
        payload["unexpected"] = True
        with self.assertRaises(ValidationError):
            OfferIntelligenceInput.model_validate(payload)

        duplicate = load_fixture("offer_growth.json")
        duplicate["ad_snapshots"][1]["snapshot_id"] = duplicate["ad_snapshots"][0]["snapshot_id"]
        with self.assertRaises(ValidationError):
            OfferIntelligenceInput.model_validate(duplicate)

        wrong_types = load_fixture("offer_growth.json")
        wrong_types["ad_snapshots"][0]["active_ads_count"] = True
        wrong_types["target_offer"]["ticket_amount"] = "49.90"
        with self.assertRaises(ValidationError):
            OfferIntelligenceInput.model_validate(wrong_types)


if __name__ == "__main__":
    unittest.main()

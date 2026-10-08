import unittest
from datetime import date
from unittest.mock import patch

from src.china_import_radar import build_radar_from_payloads, collect_radar, merge_payload


def payload(rows):
    return {"data": rows}


class ChinaImportRadarTests(unittest.TestCase):
    def test_builds_value_growth_and_turkey_share(self):
        world_now = payload([{
            "cmdCode": "2515", "cmdDesc": "Marble and travertine", "primaryValue": 1_000_000_000,
            "netWgt": 2_000_000_000, "qty": 2_000_000_000, "qtyUnitAbbr": "kg"
        }])
        world_prev = payload([{"cmdCode": "2515", "primaryValue": 800_000_000}])
        turkey_now = payload([{"cmdCode": "2515", "primaryValue": 120_000_000}])
        items = build_radar_from_payloads(world_now, world_prev, turkey_now, 2025, 2024)
        marble = next(x for x in items if x["hs4"] == "2515")
        self.assertEqual(marble["yoy_growth_percent"], 25.0)
        self.assertEqual(marble["turkey_share_percent"], 12.0)
        self.assertEqual(marble["unit_value_usd_per_kg"], 0.5)
        self.assertFalse(marble["buyer_identified"])
        self.assertEqual(marble["signal_type"], "market_demand_not_buyer")

    def test_missing_weight_does_not_invent_unit_value(self):
        items = build_radar_from_payloads(
            payload([{"cmdCode": "2523", "primaryValue": 50_000_000}]),
            payload([{"cmdCode": "2523", "primaryValue": 40_000_000}]),
            payload([]), 2025, 2024,
        )
        cement = next(x for x in items if x["hs4"] == "2523")
        self.assertIsNone(cement["unit_value_usd_per_kg"])
        self.assertIsNone(cement["turkey_share_percent"])

    def test_zero_previous_value_does_not_fake_growth(self):
        items = build_radar_from_payloads(
            payload([{"cmdCode": "1206", "primaryValue": 10_000_000}]),
            payload([{"cmdCode": "1206", "primaryValue": 0}]),
            payload([]), 2025, 2024,
        )
        item = next(x for x in items if x["hs4"] == "1206")
        self.assertIsNone(item["yoy_growth_percent"])

    @patch("src.china_import_radar._fetch")
    def test_collect_falls_back_one_year_when_latest_empty(self, fetch):
        def fake(period, partner, timeout=20.0):
            if period == 2025:
                return payload([])
            if period == 2024 and partner == "0":
                return payload([{"cmdCode": "2515", "primaryValue": 100_000_000}])
            if period == 2023:
                return payload([{"cmdCode": "2515", "primaryValue": 90_000_000}])
            if period == 2024 and partner == "792":
                return payload([{"cmdCode": "2515", "primaryValue": 10_000_000}])
            return payload([])
        fetch.side_effect = fake
        items, meta = collect_radar(date(2026, 10, 8))
        self.assertEqual(meta["status"], "ok")
        self.assertEqual(meta["current_year"], 2024)
        self.assertTrue(items)

    @patch("src.china_import_radar.collect_radar")
    def test_merge_keeps_radar_separate_from_buyer_opportunities(self, collect):
        collect.return_value = ([{"hs4": "2515", "buyer_identified": False}], {"status": "ok"})
        source = {"opportunities": [{"id": "tender-1"}]}
        out = merge_payload(source)
        self.assertEqual(len(out["opportunities"]), 1)
        self.assertEqual(out["china_import_radar"]["items"][0]["hs4"], "2515")


if __name__ == "__main__":
    unittest.main()

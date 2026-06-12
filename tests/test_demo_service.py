import os
import unittest
from unittest.mock import patch

from app.demo_service import (
    add_watchlist,
    answer_demo_chat,
    get_data_source_status,
    get_recommendation,
    get_recommendations,
    get_stock_bars,
    get_stock_snapshot,
    remove_watchlist,
    search_stocks,
    send_wecom_test,
)


class DemoServiceTests(unittest.TestCase):
    @patch("app.demo_service._live_recommendations", side_effect=RuntimeError("database offline"))
    def test_recommendations_fall_back_to_snapshot(self, _live):
        payload = get_recommendations(3)

        self.assertEqual(payload["data_mode"], "demo_snapshot")
        self.assertEqual(len(payload["items"]), 3)
        self.assertEqual(payload["items"][0]["symbol"], "600519.SH")

    @patch("app.demo_service._live_recommendations", side_effect=RuntimeError("database offline"))
    def test_recommendation_detail_is_available(self, _live):
        item = get_recommendation("demo-600519")

        self.assertIsNotNone(item)
        self.assertIn("positive_reasons", item)

    def test_stock_bars_are_deterministic(self):
        first = get_stock_bars("600519.SH", 20)
        second = get_stock_bars("600519.SH", 20)

        self.assertEqual(first, second)
        self.assertEqual(len(first["bars"]), 20)

    def test_stock_snapshot_contains_tracking_metrics(self):
        payload = get_stock_snapshot("600519.SH")

        self.assertIsNotNone(payload)
        self.assertIn("tracking", payload)
        self.assertIn("price_vs_ma20_pct", payload["tracking"])

    def test_stock_search_supports_code_and_name(self):
        self.assertEqual(search_stocks("600519")[0]["symbol"], "600519.SH")
        self.assertEqual(search_stocks("贵州茅台")[0]["symbol"], "600519.SH")

    @patch("app.demo_service._save_watchlist")
    def test_watchlist_can_add_and_remove_symbol(self, _save):
        add_watchlist("000333.sz")
        symbols = {item["symbol"] for item in remove_watchlist("000333.SZ")}

        self.assertNotIn("000333.SZ", symbols)

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}, clear=False)
    @patch("app.demo_service._live_recommendations", side_effect=RuntimeError("database offline"))
    def test_chat_uses_rules_without_api_key(self, _live):
        payload = answer_demo_chat("贵州茅台为什么被推荐？")

        self.assertEqual(payload["mode"], "rules")
        self.assertEqual(payload["symbol"], "600519.SH")
        self.assertIn("主要依据", payload["answer"])
        self.assertIn("数据日期", payload["answer"])

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}, clear=False)
    @patch("app.demo_service._live_recommendations", side_effect=RuntimeError("database offline"))
    def test_explicit_symbol_overrides_selected_symbol(self, _live):
        payload = answer_demo_chat("请分析 300750.SZ 的风险", "600519.SH")

        self.assertEqual(payload["symbol"], "300750.SZ")

    @patch.dict(os.environ, {"WECOM_WEBHOOK_URL": ""}, clear=False)
    def test_notification_is_simulated_without_webhook(self):
        payload = send_wecom_test("600519.SH")

        self.assertEqual(payload["status"], "simulated")

    @patch.dict(os.environ, {"TUSHARE_TOKEN": "abcdefghijklmnopqrstuvwxyz123456"}, clear=False)
    def test_data_source_status_masks_token(self):
        payload = get_data_source_status()

        self.assertTrue(payload["configured"])
        self.assertEqual(payload["token_hint"], "***3456")
        self.assertNotIn("token", payload)


if __name__ == "__main__":
    unittest.main()

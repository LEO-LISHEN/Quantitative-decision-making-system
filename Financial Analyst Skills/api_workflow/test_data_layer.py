from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from api_workflow.data_layer import (
    _is_valid_forecast_observation,
    _extract_ticker,
    _yahoo_symbol,
    build_data_need_coverage,
    classify_data_need,
    collect_user_materials,
    normalize_table,
    normalize_table_metrics,
    score_research_pack,
)


class DataLayerTests(unittest.TestCase):
    def test_ticker_extraction_supports_a_hk_and_us(self) -> None:
        self.assertEqual(_extract_ticker("全面分析贵州茅台 600519.SH"), "600519.SH")
        self.assertEqual(_extract_ticker("分析泡泡玛特 9992.HK"), "09992.HK")
        self.assertEqual(_extract_ticker("analyze AAPL"), "AAPL")
        self.assertEqual(_yahoo_symbol("09992.HK"), "9992.HK")

    def test_data_need_classifier_covers_event_and_sentiment(self) -> None:
        self.assertEqual(classify_data_need("需要事件催化和公告窗口"), "filings")
        self.assertEqual(classify_data_need("雪球舆情和股吧讨论"), "sentiment")

    def test_table_metric_normalization_extracts_forecasts(self) -> None:
        table = normalize_table(
            [["指标", "2024E", "2025E"], ["EPS", "1.23", "1.56"], ["营业收入(亿元)", "100", "120"]],
            max_rows=10,
            max_cols=10,
        )
        metrics = normalize_table_metrics({**table, "table_index": 1, "source_name": "demo.csv"})
        self.assertTrue(any(item["metric_type"] == "eps_forecasts" and item["year"] == "2024" for item in metrics))
        self.assertTrue(any(item["unit"] == "hundred_million" for item in metrics))

    def test_local_csv_material_is_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "financial_forecast.csv"
            path.write_text("指标,2024E,2025E\nEPS,1.23,1.56\n", encoding="utf-8")
            materials = collect_user_materials(user_input=str(path), task_brief={})
        self.assertEqual(len(materials["files"]), 1)
        self.assertEqual(len(materials["tables"]), 1)

    def test_data_need_coverage_returns_refs(self) -> None:
        pack = {
            "market_data": {"quote": {"x": 1}, "daily_kline": {"x": 1}, "benchmark_data": {"market_index": {}}},
            "financial_statements": {"key_indicators": {"x": 1}},
            "dynamic_research": {},
            "user_materials": {},
            "valuation_data": {"snapshot": {"pe_ttm": 10}},
            "peer_table": [],
        }
        coverage = build_data_need_coverage(
            [{"data_type": "kline", "item": "日K"}, {"data_type": "financials", "item": "财报"}],
            pack,
        )
        self.assertEqual([item["status"] for item in coverage], ["covered", "covered"])


    def test_data_quality_score_caps_partial_financial_depth(self) -> None:
        pack = {
            "market_data": {
                "quote": {"x": 1},
                "daily_kline": {"x": 1},
                "benchmark_data": {"market_index": {"x": 1}, "industry_index": {"x": 1}},
                "peer_quotes": [{"x": 1}],
            },
            "financial_statements": {"key_indicators": {"x": 1}, "tushare": None},
            "capital_actions": {"dividend": {"x": 1}},
            "filings_and_announcements": [{"x": 1}],
            "company_profile": {"business_segments": [{"x": 1}]},
            "macro_inputs": {"beta": {"x": 1}, "risk_free_rate": {"x": 1}},
            "dynamic_research": {"document_corpus": [{"x": 1}], "consensus_proxy": {"x": 1}},
            "user_materials": {"files": []},
            "event_timeline": {"events": [{"x": 1}]},
            "valuation_data": {"snapshot": {"x": 1}},
            "sentiment_data": {"samples": [{"x": 1}]},
            "analyst_data_delivery": {"04_financial_quality": [{"x": 1}]},
            "missing_data": [],
        }
        scored = score_research_pack(pack)
        self.assertEqual(scored["financial_depth"], "partial")
        self.assertEqual(scored["rating"], "medium")
        self.assertEqual(scored["financial_source_confidence"], "high")
        self.assertEqual(scored["financial_statement_completeness"], "partial")
        self.assertEqual(scored["financial_modeling_readiness"], "moderate")
        self.assertTrue(scored["quality_warnings"])

    def test_forecast_observation_filter_rejects_growth_rate_as_revenue(self) -> None:
        self.assertFalse(
            _is_valid_forecast_observation(
                "revenue_forecasts",
                {"year": "2025", "value": 14.45, "snippet": "2025年营业收入同比增长14.45%"},
            )
        )
        self.assertTrue(
            _is_valid_forecast_observation(
                "revenue_forecasts",
                {"year": "2025", "value": 173806.0, "snippet": "2025E 营业收入 173806 百万元"},
            )
        )


if __name__ == "__main__":
    unittest.main()

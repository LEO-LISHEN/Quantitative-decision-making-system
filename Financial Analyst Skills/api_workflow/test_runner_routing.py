from __future__ import annotations

import unittest

from api_workflow.runner import StockAnalysisWorkflow


class RunnerRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = StockAnalysisWorkflow()

    def test_workflow_accepts_collection_mode(self) -> None:
        workflow = StockAnalysisWorkflow(collection_mode="deep")
        self.assertEqual(workflow.collection_mode, "deep")

    def test_nested_text_handles_dict_and_list_shapes(self) -> None:
        self.assertEqual(
            self.workflow._nested_text({"overall_assessment": "good"}, "overall_assessment"),
            "good",
        )
        self.assertEqual(
            self.workflow._nested_text(
                [{"overall_assessment": "first"}, {"overall_assessment": "second"}],
                "overall_assessment",
            ),
            "first second",
        )

    def test_upstream_routing_limits_keys_for_technical_node(self) -> None:
        upstream = {
            "01_task_definition": {"ticker": "600519.SH"},
            "02_source_intelligence": {"confidence": "B"},
            "03_fundamental_business": {"summary": "biz"},
            "04_financial_quality": {"summary": "quality"},
            "07_market_expectation_gap": {"summary": "gap"},
            "09_catalyst_event": {"summary": "catalyst"},
            "12_technical_price_volume": {"summary": "tech"},
        }
        routed = self.workflow._route_upstream_outputs("12_technical_price_volume", upstream)
        self.assertEqual(
            set(routed.keys()),
            {"01_task_definition", "02_source_intelligence", "07_market_expectation_gap", "09_catalyst_event"},
        )

    def test_external_routing_limits_sections_for_sentiment_node(self) -> None:
        external = {
            "collection_time": "2026-05-28T10:00:00+08:00",
            "ticker": "600519.SH",
            "company_name": "贵州茅台",
            "quote_snapshot": {"normalized": {"last_price": 100}},
            "web_search_results": [{"query": "foo"}],
            "research_data_pack": {
                "market_data": {"daily_kline": {"record_count": 100}, "benchmark_data": {"market_index": {}}, "peer_quotes": [{"x": 1}]},
                "sentiment_data": {"samples": [{"content": "bar"}]},
                "event_timeline": {"events": [{"date": "2026-05-27"}]},
                "dynamic_research": {"document_corpus": [{"title": "doc"}]},
                "financial_statements": {"key_indicators": {"record_count": 10}},
                "missing_data": [{"field": "beta"}],
            },
        }
        routed = self.workflow._route_external_data("13_sentiment_public_opinion", external)
        self.assertIn("quote_snapshot", routed)
        self.assertIn("node_data_summary", routed)
        self.assertIn("research_data_pack", routed)
        research_pack = routed["research_data_pack"]
        self.assertIn("sentiment_data", research_pack)
        self.assertIn("event_timeline", research_pack)
        self.assertIn("market_data", research_pack)
        self.assertNotIn("financial_statements", research_pack)
        self.assertNotIn("web_search_results", routed)
        self.assertEqual(routed["node_data_summary"]["data_available"]["daily_kline_records"], 100)
        self.assertEqual(routed["node_data_summary"]["data_available"]["sentiment_sample_count"], 1)


    def test_source_intelligence_summary_separates_proxy_evidence(self) -> None:
        external = {
            "collection_time": "2026-05-28T10:00:00+08:00",
            "ticker": "600519.SH",
            "company_name": "贵州茅台",
            "quote_snapshot": {
                "source": "eastmoney",
                "retrieved_at": "2026-05-28T10:00:00+08:00",
                "normalized": {"last_price": 1289.99, "market_cap": 1.6e12, "pe_dynamic": 14.8},
            },
            "research_data_pack": {
                "market_data": {
                    "quote": {"normalized": {"last_price": 1289.99}},
                    "daily_kline": {
                        "record_count": 120,
                        "records": [
                            {"date": "2026-05-01", "close": 1300},
                            {"date": "2026-05-28", "close": 1289.99},
                        ],
                    },
                },
                "financial_statements": {"key_indicators": {"source": "eastmoney_f10", "record_count": 7, "records": []}},
                "filings_and_announcements": [{"title": "公告", "notice_date": "2026-05-28"}],
                "event_timeline": {"events": [{"date": "2026-05-28", "title": "回购公告"}]},
                "dynamic_research": {
                    "document_corpus": [{"title": "研报A"}],
                    "consensus_proxy": {"confidence": "C", "document_count": 4, "limitations": ["proxy only"]},
                },
                "sentiment_data": {"samples": [{"title": "sample"}]},
                "missing_data": [],
                "fetch_errors": [],
                "data_need_coverage": [],
                "analyst_data_delivery": {},
                "data_quality_score": {"financial_depth": "partial", "quality_warnings": ["warn"]},
            },
        }
        routed = self.workflow._route_external_data("02_source_intelligence", external)
        evidence = routed["node_data_summary"]["evidence_classification"]
        self.assertTrue(evidence["high_confidence_facts"])
        self.assertTrue(evidence["low_confidence_or_proxy_facts"])
        self.assertTrue(any("不得并入高置信事实" in item for item in evidence["low_confidence_or_proxy_facts"]))

    def test_data_request_result_is_salvaged_from_raw_text(self) -> None:
        raw_text = """{
  "analyst": "06_relative_valuation",
  "required_data": [
    {
      "item": "当前股价",
      "reason": "计算估值倍数",
      "priority": "high",
      "preferred_sources": ["行情API", "东方财富",
      "suggested_search_queries": ["贵州茅台 当前股价"]
    }
  ],
  "blocking_data": ["当前股价"],
  "optional_data": ["股息率"],
  "tool_hints": ["web_search"]
}"""
        repaired = self.workflow._repair_data_request_result(
            "06_relative_valuation",
            {"raw_text": raw_text, "json_parse_error": True},
        )
        self.assertEqual(repaired["analyst"], "06_relative_valuation")
        self.assertEqual(repaired["required_data"][0]["item"], "当前股价")
        self.assertEqual(repaired["required_data"][0]["preferred_sources"], ["行情API", "东方财富"])
        self.assertEqual(repaired["tool_hints"], ["web_search"])

    def test_final_report_result_is_repaired_from_raw_text(self) -> None:
        raw_text = """{
  "company": {
    "company_name": "贵州茅台",
    "ticker": "600519"
  },
  "executive_conclusion": {
    "overall_recommendation": "谨慎买入",
    "recommendation_confidence": "中”
  },
  "information_quality": {
    "overall_quality": "中",
    "source_confidence": "高"
  }
}"""
        repaired = self.workflow._repair_final_report_result(
            {"raw_text": raw_text, "json_parse_error": True},
        )
        self.assertEqual(repaired["company"]["company_name"], "贵州茅台")
        self.assertEqual(repaired["executive_conclusion"]["overall_recommendation"], "谨慎买入")
        self.assertEqual(repaired["information_quality"]["source_confidence"], "高")
        self.assertEqual(repaired["repair_note"], "parsed_from_repaired_raw_text")

    def test_final_report_result_is_salvaged_by_sections(self) -> None:
        raw_text = """{
  "company": {
    "company_name": "贵州茅台",
    "ticker": "600519"
  },
  "executive_conclusion": {
    "overall_recommendation": "谨慎买入",
    "recommendation_confidence": "中"
  ,
  "information_quality": {
    "overall_quality": "中",
    "source_confidence": "高"
  }
}"""
        repaired = self.workflow._repair_final_report_result(
            {"raw_text": raw_text, "json_parse_error": True},
        )
        self.assertEqual(repaired["company"]["company_name"], "贵州茅台")
        self.assertEqual(repaired["information_quality"]["overall_quality"], "中")
        self.assertEqual(repaired["repair_note"], "salvaged_from_raw_text_after_json_parse_error")

    def test_source_intelligence_output_downgrades_report_citations(self) -> None:
        result = {
            "high_confidence_facts": [
                "实时股价为1286元。",
                "2025年年度报告显示营收1721亿元（来自国信证券研报引用，需年报PDF核对）。",
                "2026年4月5日飞天茅台原箱批价报1700元/瓶。",
            ],
            "medium_low_confidence_claims": ["行业数据待验证。"],
            "confidence_summary": "整体可信度中等。",
        }
        sanitized = self.workflow._sanitize_source_intelligence_output(result)
        self.assertEqual(sanitized["high_confidence_facts"], ["实时股价为1286元。"])
        self.assertTrue(
            any("国信证券研报引用" in item for item in sanitized["medium_low_confidence_claims"])
        )
        self.assertTrue(any("批价报1700元/瓶" in item for item in sanitized["medium_low_confidence_claims"]))
        self.assertIn("下调至 medium_low_confidence_claims", sanitized["confidence_summary"])


    def test_financial_node_summary_surfaces_structured_financial_snapshot(self) -> None:
        external = {
            "collection_time": "2026-05-28T10:00:00+08:00",
            "ticker": "600519.SH",
            "company_name": "贵州茅台",
            "research_data_pack": {
                "financial_statements": {
                    "key_indicators": {
                        "source": "eastmoney_f10_key_indicators",
                        "record_count": 2,
                        "records": [
                            {
                                "REPORT_DATE_NAME": "2025年报",
                                "REPORT_TYPE": "年报",
                                "TOTALOPERATEREVE": 1700.0,
                                "TOTALOPERATEREVETZ": 15.2,
                                "PARENTNETPROFIT": 820.0,
                                "PARENTNETPROFITTZ": 14.8,
                                "XSMLL": 91.5,
                                "ROEJQ": 34.2,
                                "JYXJLYYSR": 0.71,
                                "ZCFZL": 18.6,
                            },
                            {
                                "REPORT_DATE_NAME": "2026Q1",
                                "REPORT_TYPE": "一季报",
                                "TOTALOPERATEREVE": 540.0,
                                "TOTALOPERATEREVETZ": 10.1,
                                "PARENTNETPROFIT": 280.0,
                                "PARENTNETPROFITTZ": 11.4,
                                "XSMLL": 92.1,
                                "ROEJQ": 8.6,
                                "JYXJLYYSR": 0.66,
                                "ZCFZL": 19.1,
                            },
                        ],
                    },
                    "tushare": {
                        "statements": {
                            "income": {"record_count": 4, "records": [{"end_date": "20251231"}, {"end_date": "20260331"}]},
                            "cashflow": {"record_count": 4, "records": [{"end_date": "20251231"}, {"end_date": "20260331"}]},
                            "balancesheet": {"record_count": 4, "records": [{"end_date": "20251231"}, {"end_date": "20260331"}]},
                        }
                    },
                },
                "filings_and_announcements": [{"title": "2025年报", "notice_date": "2026-03-30"}],
                "data_quality_score": {"financial_depth": "high", "rating": "high"},
                "missing_data": [],
                "fetch_errors": [],
            },
        }
        routed = self.workflow._route_external_data("04_financial_quality", external)
        summary = routed["node_data_summary"]["financials"]
        self.assertEqual(summary["coverage"]["latest_period"], "2026Q1")
        self.assertTrue(summary["coverage"]["has_income_statement"])
        self.assertEqual(summary["latest_snapshot"]["revenue"], 540.0)
        self.assertEqual(summary["trend_summary"]["revenue"]["trend"], "down")
        self.assertEqual(routed["node_data_summary"]["data_quality_score"]["financial_depth"], "high")
        self.assertEqual(len(summary["key_indicators"]["sample_records"]), 2)

    def test_source_intelligence_output_limits_high_confidence_fact_count(self) -> None:
        result = {
            "high_confidence_facts": [f"fact {index}" for index in range(10)],
            "medium_low_confidence_claims": [],
            "confidence_summary": "",
        }
        sanitized = self.workflow._sanitize_source_intelligence_output(result)
        self.assertEqual(len(sanitized["high_confidence_facts"]), 8)
        self.assertEqual(sanitized["supporting_high_confidence_facts"], ["fact 8", "fact 9"])
        self.assertIn("supporting_high_confidence_facts", sanitized["confidence_summary"])

    def test_data_request_result_is_normalized(self) -> None:
        normalized = self.workflow._normalize_data_request_result(
            "06_relative_valuation",
            {
                "analyst": "06_relative_valuation",
                "required_data": [{"item": "当前股价" * 40, "reason": "估值" * 60, "priority": "high", "preferred_sources": ["行情API"] * 6, "suggested_search_queries": ["贵州茅台 当前股价"] * 6}],
                "blocking_data": ["a"] * 9,
                "optional_data": ["b"] * 9,
                "tool_hints": ["web_search"] * 10,
            },
        )
        self.assertEqual(len(normalized["required_data"]), 1)
        self.assertLessEqual(len(normalized["required_data"][0]["item"]), 120)
        self.assertEqual(len(normalized["blocking_data"]), 5)
        self.assertEqual(len(normalized["tool_hints"]), 6)

    def test_report_bundle_contains_text_and_lean_report(self) -> None:
        final_report = {
            "company": {"company_name": "贵州茅台", "ticker": "600519", "current_price": 1274.55, "analysis_date": "2026-05-28"},
            "executive_conclusion": {
                "overall_recommendation": "谨慎买入",
                "recommendation_confidence": "中",
                "one_sentence_view": "长期价值仍在，短期等待盈利确认。",
                "preferred_range": "1500-1700",
                "upside_downside": {"to_base_case": "15%", "to_bull_case": "30%", "to_bear_case": "-10%"},
            },
            "time_horizon_recommendations": {
                "short_term": {"recommendation": "观望", "reasoning": "短期催化不足"},
                "medium_term": {"recommendation": "谨慎买入", "reasoning": "等待半年报验证"},
                "long_term": {"recommendation": "买入", "reasoning": "品牌护城河深"},
            },
            "information_quality": {"overall_quality": "中", "source_confidence": "中", "key_limitations": ["缺完整三表"], "unverified_claims": ["小样本一致预期"]},
            "integrated_analysis": {"investment_thesis": ["品牌强", "现金流好"]},
        }
        lean = self.workflow._build_lean_report(final_report, task_brief={}, external_data={})
        text = self.workflow._build_text_report(final_report, task_brief={}, external_data={})
        self.assertEqual(lean["overall_recommendation"], "谨慎买入")
        self.assertIn("简版分析报告", text)
        self.assertIn("结论：谨慎买入", text)
        self.assertIn("## 估值与回报空间", text)
        self.assertIn("1500-1700", text)

    def test_long_report_contains_formal_sections_and_evidence_appendix(self) -> None:
        final_report = {
            "company": {"company_name": "贵州茅台", "ticker": "600519", "current_price": 1274.55, "analysis_date": "2026-05-28"},
            "executive_conclusion": {
                "overall_recommendation": "谨慎买入",
                "recommendation_confidence": "中",
                "one_sentence_view": "长期价值仍在，短期等待盈利确认。",
                "fair_value_range": {"preferred_range": "1500-1700"},
                "upside_downside": {"to_base_case": "15%", "to_bull_case": "30%", "to_bear_case": "-10%"},
            },
            "time_horizon_recommendations": {
                "short_term": {"recommendation": "观望", "reasoning": "短期催化不足"},
                "medium_term": {"recommendation": "谨慎买入", "reasoning": "等待半年报验证"},
                "long_term": {"recommendation": "买入", "reasoning": "品牌护城河深"},
            },
            "information_quality": {"overall_quality": "中", "missing_information": ["缺完整三表"], "key_limitations": ["批价数据缺失"]},
            "integrated_analysis": {"investment_thesis": ["品牌强", "现金流好"], "business_quality": "商业模式优秀", "financial_quality": "财务质量较强"},
        }
        analyst_outputs = {
            "02_source_intelligence": {
                "high_confidence_facts": ["事实A"],
                "medium_low_confidence_claims": ["低置信线索B"],
                "rumors_or_sentiment_only_items": ["情绪线索C"],
            },
            "04_financial_quality": {
                "historical_trends": {"revenue_trend": "收入同比改善", "gross_margin_trend": "毛利率承压", "cash_flow_trend": "现金流稳定", "roe_roic_trend": "ROE高位"},
                "earnings_quality": {"cash_conversion": "现金转化良好"},
                "questions_for_downstream_analysts": ["需要验证批价数据"],
            },
            "05_dcf_intrinsic_value": {"summary": "DCF显示仍有上行空间"},
            "06_relative_valuation": {"summary": "相对估值处于低位"},
            "07_market_expectation_gap": {"summary": "市场预期仍偏谨慎"},
            "09_catalyst_event": {"summary": "中报和股东会是关键催化"},
            "14_risk_disconfirmation": {"risk_map": [{"risk_name": "需求放缓", "valuation_impact_path": "压缩估值倍数", "evidence_grade": "中"}]},
        }
        external_data = {"research_data_pack": {"data_quality_score": {"financial_source_confidence": "high", "financial_statement_completeness": "partial", "financial_modeling_readiness": "moderate"}}}
        report = self.workflow._build_long_report(final_report, task_brief={}, external_data=external_data, analyst_outputs=analyst_outputs)
        self.assertIn("执行摘要", report)
        self.assertIn("关键补充证据与分歧信息", report)
        self.assertIn("低置信线索B", report)
        self.assertIn("证据分级附录", report)


    def test_long_report_v3_expands_analyst_sections(self) -> None:
        final_report = {
            "company": {"company_name": "贵州茅台", "ticker": "600519", "current_price": 1274.55, "analysis_date": "2026-05-28"},
            "executive_conclusion": {
                "overall_recommendation": "谨慎买入",
                "recommendation_confidence": "中",
                "one_sentence_view": "估值有吸引力，但要等盈利确认。",
                "fair_value_range": {"preferred_range": "1500-1700"},
                "upside_downside": {"to_base_case": "15%", "to_bull_case": "30%", "to_bear_case": "-10%"},
            },
            "time_horizon_recommendations": {
                "short_term": {"recommendation": "观望", "reasoning": "短期催化不足"},
                "medium_term": {"recommendation": "谨慎买入", "reasoning": "等待半年报验证"},
                "long_term": {"recommendation": "买入", "reasoning": "品牌护城河深"},
            },
            "information_quality": {"overall_quality": "中", "missing_information": ["批价"], "key_limitations": ["样本有限"]},
            "integrated_analysis": {
                "investment_thesis": ["品牌强", "现金流好"],
                "business_quality": "商业模式优秀",
                "financial_quality": "财务韧性较强",
                "valuation_view": "估值处于历史偏低区间",
            },
        }
        analyst_outputs = {
            "02_source_intelligence": {"high_confidence_facts": ["事实A"], "medium_low_confidence_claims": ["线索B"]},
            "03_fundamental_business": {
                "business_model_summary": {"what_it_sells": "高端白酒", "revenue_model": "批发+直销", "profit_model": "品牌溢价"},
                "industry_and_competition": {"industry_structure": "行业集中度高", "main_competitors": ["五粮液"]},
                "moat_assessment": {"moat_sources": ["品牌", "渠道"]},
                "management_and_capital_allocation": {"capital_allocation": "高分红和回购"},
                "segment_analysis": [{"segment": "茅台酒", "revenue_driver": "提价与放量", "profit_driver": "高毛利", "growth_quality": "增长稳定"}],
            },
            "04_financial_quality": {
                "historical_trends": {"revenue_trend": "改善", "gross_margin_trend": "平稳", "cash_flow_trend": "稳健", "roe_roic_trend": "高位"},
                "earnings_quality": {"cash_conversion": "现金转换良好"},
            },
            "05_dcf_intrinsic_value": {"summary": "DCF显示仍有上行空间"},
            "06_relative_valuation": {"summary": "相对估值仍偏低"},
            "07_market_expectation_gap": {"summary": "市场预期偏谨慎"},
            "09_catalyst_event": {
                "near_term_focus": "半年报和批价",
                "valuation_realization_path": "靠业绩修复推动估值回归",
                "catalysts": [{"event_name": "半年报", "event_type": "earnings", "expected_timing": "2026-08", "credibility": "中", "impact_direction": "正向", "pricing_status": "未定价", "description": "关键验证窗口"}],
            },
            "12_technical_price_volume": {
                "technical_confirmation": {"reasoning": "技术面偏弱", "timing_implication": "等待企稳"},
                "trend_state": {"primary_trend": "下降趋势"},
                "risk_signals": {"technical_warning_signals": ["跌破支撑"], "failure_signals": ["若反弹无力站上1300元"]},
            },
            "13_sentiment_public_opinion": {
                "sentiment_state": {"overall_sentiment": "中性", "discussion_heat": "低"},
                "narrative_map": {"main_narratives": [{"narrative": "高股息防御", "direction": "中性偏正面", "evidence_status": "部分验证"}]},
                "rumor_and_unverified_claims": [{"claim": "批价企稳", "source": "社区讨论", "credibility": "低"}],
                "handoff_to_master": {"summary": "舆情整体偏冷清"},
            },
            "14_risk_disconfirmation": {
                "risk_map": [{"risk_name": "需求放缓", "valuation_impact_path": "压缩估值倍数", "evidence_grade": "中"}],
                "risk_summary": {"core_thesis_status": "被削弱", "most_important_risks": ["批价", "净利率"]},
                "disconfirmation_matrix": [{"assumption": "批价企稳", "current_status": "被削弱", "failure_trigger": "批价连续下跌"}],
                "downside_scenarios": {"bear_case": {"description": "业绩低于预期", "probability": "中", "severity": "高"}},
            },
        }
        external_data = {"research_data_pack": {"data_quality_score": {"financial_source_confidence": "high", "financial_statement_completeness": "partial", "financial_modeling_readiness": "moderate"}}}
        report = self.workflow._build_long_report(final_report, task_brief={}, external_data=external_data, analyst_outputs=analyst_outputs)
        self.assertIn("分部观察", report)
        self.assertIn("半年报", report)
        self.assertIn("反证检查", report)
        self.assertIn("市场印证与情绪观察", report)
        self.assertIn("高股息防御", report)

if __name__ == "__main__":
    unittest.main()

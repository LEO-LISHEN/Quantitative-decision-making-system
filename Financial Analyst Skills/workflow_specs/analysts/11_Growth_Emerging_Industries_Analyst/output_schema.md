# 输出规范

## 标准输出结构

```json
{
  "analyst": "Growth_Emerging_Industries_Analyst",
  "company": {
    "company_name": "公司名称",
    "ticker": "股票代码",
    "market": "市场",
    "analysis_date": "YYYY-MM-DD",
    "information_cutoff": "YYYY-MM-DD"
  },
  "source_quality": {
    "overall_rating": "high / medium / low / insufficient",
    "official_disclosures_used": ["年报/半年报/公告/10-K/10-Q/20-F"],
    "third_party_sources_used": ["行业报告/研报/数据库/监管资料"],
    "news_and_social_sources_used": ["新闻/社交媒体/社区讨论"],
    "key_missing_sources": ["缺失来源"],
    "source_warnings": ["来源限制或可信度提醒"]
  },
  "growth_narrative": {
    "summary": "核心成长叙事",
    "narrative_source": "公司披露 / 产业数据 / 研报 / 新闻 / 社交媒体 / 市场主题 / 混合来源",
    "evidence_rating": "A / B / C / D / E",
    "is_story_vs_evidence": "证据支持 / 部分证据支持 / 主要是叙事 / 无法判断",
    "market_attention": "高 / 中 / 低 / 无法判断"
  },
  "industry_and_market": {
    "industry": "行业",
    "adoption_stage": "导入期 / 加速渗透期 / 成熟扩张期 / 竞争加剧期 / 泡沫或过度预期 / 无法判断",
    "tam": "总潜在市场",
    "sam": "可服务市场",
    "som": "可获得市场",
    "penetration_rate": "当前渗透率",
    "market_growth_drivers": ["增长驱动因素"],
    "market_constraints": ["市场约束"]
  },
  "company_growth_validation": {
    "product_or_technology": {
      "status": "已商业化 / 小规模验证 / 研发阶段 / 概念阶段 / 无法判断",
      "advantages": ["优势"],
      "weaknesses": ["短板"],
      "verification": ["验证证据"]
    },
    "customer_and_demand": {
      "customer_validation": "强 / 中 / 弱 / 无法判断",
      "orders_or_backlog": "订单或在手合同情况",
      "user_or_customer_metrics": "用户/客户指标",
      "retention_or_repeat_purchase": "留存/复购/续费情况"
    },
    "competition": {
      "key_competitors": ["竞争对手"],
      "competitive_position": "领先 / 跟随 / 追赶 / 小众 / 无法判断",
      "moat_type": ["技术/成本/渠道/品牌/数据/生态/牌照/客户关系/无明显壁垒"]
    }
  },
  "unit_economics_and_scalability": {
    "gross_margin_path": "毛利率路径",
    "operating_leverage": "经营杠杆判断",
    "customer_acquisition_or_sales_efficiency": "获客/销售效率",
    "capex_intensity": "资本开支强度",
    "rd_intensity": "研发强度",
    "cash_burn_and_runway": "现金消耗和 runway",
    "dilution_risk": "高 / 中 / 低 / 无法判断",
    "scalability_judgment": "强 / 中 / 弱 / 尚未验证"
  },
  "financial_path": {
    "revenue_path": "收入增长路径",
    "margin_path": "利润率变化路径",
    "free_cash_flow_path": "自由现金流路径",
    "break_even_visibility": "清晰 / 部分清晰 / 不清晰 / 不适用",
    "key_assumptions": ["关键假设"]
  },
  "scenario_analysis": {
    "bear_case": {
      "description": "悲观情景",
      "probability": "概率",
      "key_assumptions": ["假设"],
      "valuation_implication": "估值含义"
    },
    "base_case": {
      "description": "基准情景",
      "probability": "概率",
      "key_assumptions": ["假设"],
      "valuation_implication": "估值含义"
    },
    "bull_case": {
      "description": "乐观情景",
      "probability": "概率",
      "key_assumptions": ["假设"],
      "valuation_implication": "估值含义"
    }
  },
  "valuation_method_view": {
    "preferred_methods": ["远期倍数 / 概率加权 / SOTP / DCF / 实物期权 / 暂不适合高置信估值"],
    "methods_to_avoid": ["不适合的方法"],
    "growth_premium_or_discount": "应给予溢价 / 中性 / 应折价 / 无法判断",
    "reasoning": "原因"
  },
  "milestones_and_tracking": {
    "next_3_to_12_months": ["短中期里程碑"],
    "next_1_to_3_years": ["中长期里程碑"],
    "metrics_to_track": ["需要持续跟踪的指标"],
    "disconfirmation_signals": ["证伪信号"]
  },
  "risk_and_failure_paths": {
    "execution_risk": "执行风险",
    "competition_risk": "竞争风险",
    "technology_risk": "技术风险",
    "regulation_risk": "监管风险",
    "funding_risk": "融资风险",
    "valuation_risk": "估值风险",
    "main_failure_reasons": ["成长故事失败原因"]
  },
  "handoff_to_master": {
    "growth_quality": "高 / 中 / 低 / 无法判断",
    "realization_probability": "高 / 中 / 低 / 无法判断",
    "impact_on_final_view": "正面 / 中性 / 负面 / 不确定",
    "confidence": "高 / 中 / 低",
    "must_verify_before_recommendation": ["最终建议前必须验证的事项"]
  }
}
```

## 证据等级

- `A`: 公司正式披露、财务数据、第三方数据和竞争/客户证据相互印证。
- `B`: 有正式披露和部分第三方验证，但关键经营数据不完整。
- `C`: 主要来自公司表述或研报推断，有一定外部线索但缺少硬数据。
- `D`: 主要来自新闻、社交媒体、市场主题或未经证实的信息。
- `E`: 信息冲突、缺失严重，无法形成可靠判断。

## 必须保留的不确定性

如果以下问题无法确认，输出中必须标注低置信度：

- TAM/SAM/SOM 口径不清。
- 客户、订单、用户或商业化进度无法验证。
- 单位经济模型缺失。
- 现金 runway 或融资需求不清。
- 新闻和社交媒体线索没有正式来源验证。
- 当前估值隐含假设无法估算。

## 标准下游交接字段

每次输出末尾应包含：

```json
{
  "handoff_to_downstream": {
    "must_pass_to": ["05_DCF_Intrinsic_Value_Analyst", "06_Relative_Valuation_Comps_Analyst", "08_Earnings_Forecast_Revision_Analyst", "09_Catalyst_Event_Analyst", "14_Risk_Disconfirmation_Short_Analyst", "01_Master_Valuation_Director"],
    "useful_for": ["07_Market_Expectation_Gap_Analyst", "13_Sentiment_Public_Opinion_Analyst"],
    "key_fields_to_pass": ["growth_narrative", "source_quality", "industry_and_market", "company_growth_validation", "unit_economics_and_scalability", "scenario_analysis", "valuation_method_view", "milestones_and_tracking", "risk_and_failure_paths"],
    "confidence": "高 / 中 / 低",
    "missing_information": ["缺失成长验证数据"],
    "blocking_issues": ["阻碍成长估值或概率判断的问题"]
  }
}
```

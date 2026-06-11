# 输出结构

## 标准输出字段

```json
{
  "company_identification": {
    "company_name": "公司名称",
    "ticker": "股票代码",
    "market": "上市市场",
    "exchange": "交易所",
    "information_cutoff": "信息截止时间"
  },
  "data_availability": {
    "event_timeline_available": true,
    "price_volume_data_available": true,
    "market_index_data_available": true,
    "sector_index_data_available": true,
    "missing_items": ["缺失数据"],
    "confidence_impact": "缺失数据对判断的影响"
  },
  "current_market_narrative": {
    "dominant_narrative": "当前主流叙事",
    "investor_concerns": ["市场担忧"],
    "optimistic_view": "乐观叙事",
    "bearish_view": "悲观叙事"
  },
  "price_implied_expectations": {
    "growth": "股价隐含增长预期",
    "margin": "股价隐含利润率预期",
    "risk": "股价隐含风险认知",
    "valuation_multiple": "估值倍数隐含预期"
  },
  "information_events": [
    {
      "event": "事件",
      "event_date": "事件发生时间",
      "public_time": "信息公开时间",
      "source": "来源",
      "credibility": "可信度",
      "information_type": "全新信息 | 旧信息确认 | 已广泛预期 | 低于预期 | 噪音信息",
      "importance": "高 | 中 | 低",
      "impact_path": "现金流 | 风险 | 估值倍数 | 催化剂 | 情绪关注"
    }
  ],
  "event_window_price_reaction": {
    "pre_20d": "事件前20日反应",
    "pre_10d": "事件前10日反应",
    "pre_5d": "事件前5日反应",
    "event_day": "事件日反应",
    "post_1d": "事件后1日反应",
    "post_3d": "事件后3日反应",
    "post_5d": "事件后5日反应",
    "post_10d": "事件后10日反应",
    "volume_change": "成交量变化",
    "relative_performance": "相对大盘和行业表现"
  },
  "pricing_status": {
    "status": "未定价 | 部分定价 | 基本定价 | 过度定价 | 无法判断",
    "evidence": ["证据"],
    "confidence": "高 | 中 | 低"
  },
  "expectation_gap_assessment": {
    "direction": "正向 | 负向 | 中性 | 混合",
    "strength": "强 | 中 | 弱 | 无 | 无法判断",
    "duration": "短期扰动 | 中期变化 | 长期变化 | 无法判断",
    "reason": "判断理由"
  },
  "future_pricing_path": {
    "needs_catalyst": true,
    "possible_paths": ["继续定价路径"],
    "next_confirming_events": ["后续确认事件"]
  },
  "disconfirmation_signals": ["反证信号"],
  "downstream_modules": ["建议后续调用的分析师"],
  "guidance_for_master_director": "总控分析师应如何使用该预期差结论"
}
```

## 输出要求

- 必须先说明数据是否足够。
- 如果缺少事件时间线或 K 线数据，必须降低置信度。
- 每条关键信息都必须判断新旧状态。
- 必须明确是否已被定价，以及证据是什么。
- 不直接给最终买入或卖出建议。
## 标准下游交接字段

每次输出末尾应包含：

```json
{
  "handoff_to_downstream": {
    "must_pass_to": ["09_Catalyst_Event_Analyst", "12_Technical_Price_Volume_Analyst", "13_Sentiment_Public_Opinion_Analyst", "14_Risk_Disconfirmation_Short_Analyst", "01_Master_Valuation_Director"],
    "useful_for": ["05_DCF_Intrinsic_Value_Analyst", "06_Relative_Valuation_Comps_Analyst", "08_Earnings_Forecast_Revision_Analyst"],
    "key_fields_to_pass": ["new_information_classification", "pricing_status", "expectation_gap_direction", "price_volume_evidence", "timeline_alignment", "future_pricing_path", "disconfirmation_signals"],
    "confidence": "高 / 中 / 低",
    "missing_information": ["缺失时间线、日K或市场预期数据"],
    "blocking_issues": ["阻碍高置信预期差判断的问题"]
  }
}
```

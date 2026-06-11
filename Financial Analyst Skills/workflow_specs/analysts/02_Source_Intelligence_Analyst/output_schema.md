# 输出结构

## 标准输出字段

```json
{
  "company_identification": {
    "company_name": "公司名称",
    "ticker": "股票代码",
    "market": "上市市场",
    "exchange": "交易所",
    "currency": "主要币种",
    "accounting_standard": "会计准则",
    "analysis_time_range": "分析时间范围",
    "information_cutoff": "信息截止时间和时区"
  },
  "source_inventory": [
    {
      "source_type": "来源类型",
      "source_name": "来源名称",
      "date": "发布日期",
      "credibility": "high | medium | low | unverified",
      "usage": "可用于事实确认 | 可用于观点参考 | 仅用于情绪观察 | 暂不采用"
    }
  ],
  "collection_plan": {
    "market_specific_sources_checked": ["已检查或应检查的市场特定信息源"],
    "searched_or_requested": ["已经搜索或要求补充的内容"],
    "not_found": ["已尝试但未找到的信息"],
    "failure_reason": ["搜索失败或无法验证的可能原因"],
    "missing_information": ["仍缺失的信息"],
    "recommended_sources": ["建议补充的信息来源"],
    "suggested_search_keywords": ["建议搜索关键词"]
  },
  "event_timeline": [
    {
      "date": "日期",
      "event": "事件",
      "source": "来源",
      "valuation_relevance": "高 | 中 | 低"
    }
  ],
  "high_confidence_facts": ["高可信事实"],
  "medium_low_confidence_claims": ["中低可信观点或说法"],
  "rumors_or_sentiment_only_items": ["传闻或仅代表情绪的信息"],
  "contradictions": ["矛盾信息"],
  "valuation_variables": {
    "revenue": ["收入相关变量"],
    "margin": ["利润率相关变量"],
    "cash_flow": ["现金流相关变量"],
    "orders_capacity_price_cost": ["订单、产能、价格、成本相关变量"],
    "policy_industry": ["政策和行业变量"],
    "capital_allocation": ["回购、分红、融资、并购等变量"],
    "risk_events": ["诉讼、监管、违约、减值等风险事件"]
  },
  "downstream_modules": ["建议调用的后续分析师模块"],
  "confidence_summary": "整体证据可信度总结"
}
```

## 输出要求

- 每个关键事实都应尽量对应来源。
- 对无法验证的信息必须标注“未验证”。
- 对股吧和社交媒体内容必须说明“仅代表情绪或叙事”。
- 不输出目标价和投资评级。
- 如果使用了搜索工具，应说明搜索范围和信息截止时间。
- 必须说明该公司适用的是 A 股、港股、美股或其他市场的信息源体系。
- 必须检查币种、单位、报告期和会计准则，无法确认时标注“待确认”。

## 标准下游交接字段

每次输出末尾应包含：

```json
{
  "handoff_to_downstream": {
    "must_pass_to": ["所有专项分析师", "01_Master_Valuation_Director"],
    "useful_for": ["证据质量控制", "缺失信息补齐", "未验证线索核验"],
    "key_fields_to_pass": ["source_inventory", "collection_plan", "event_timeline", "high_confidence_facts", "rumors_or_sentiment_only_items", "contradictions", "valuation_variables", "confidence_summary"],
    "confidence": "高 / 中 / 低",
    "missing_information": ["仍缺失的信息"],
    "blocking_issues": ["会阻碍下游高置信分析的问题"]
  }
}
```

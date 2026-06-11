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
  "catalyst_calendar": {
    "occurred": [],
    "next_1_month": [],
    "next_1_3_months": [],
    "next_3_6_months": [],
    "next_6_12_months": [],
    "beyond_12_months": []
  },
  "catalysts": [
    {
      "event_name": "事件名称",
      "event_type": "事件类型",
      "classification": "正面 | 负面 | 不确定",
      "expected_timing": "预计时间",
      "source": "来源",
      "credibility": "高 | 中 | 低 | 待验证",
      "probability": "高 | 中 | 低 | 无法判断",
      "impact_direction": "正向 | 负向 | 双向 | 不确定",
      "impact_magnitude": "高 | 中 | 低",
      "pricing_status": "未定价 | 部分定价 | 基本定价 | 过度定价 | 无法判断",
      "catalyst_strength": "强 | 中 | 弱 | 非催化剂 | 负面催化剂",
      "impact_paths": {
        "earnings": "对盈利预测的影响",
        "valuation": "对估值倍数或 DCF 假设的影响",
        "risk": "对风险溢价或风险暴露的影响",
        "sentiment": "对市场情绪和关注度的影响",
        "fund_flow": "对资金流或流动性的影响"
      },
      "confirmation_signals": ["确认信号"],
      "failure_signals": ["失败信号"],
      "monitoring_items": ["后续跟踪指标"],
      "analysts_to_consult": ["需要其他分析师验证的问题"]
    }
  ],
  "top_positive_catalysts": ["最重要正面催化剂"],
  "top_negative_catalysts": ["最重要负面催化剂"],
  "uncertain_catalysts": ["关键不确定催化剂"],
  "near_term_focus": "未来1-3个月最需要关注的事件",
  "valuation_realization_path": "价值兑现路径",
  "key_risks_to_catalyst_view": ["催化剂判断的关键风险"],
  "guidance_for_master_director": "总控分析师应如何使用该催化剂结论"
}
```

## 输出要求

- 不得只列新闻，必须判断是否构成催化剂。
- 每个催化剂必须包含概率、时间、影响、是否已定价和影响路径。
- 必须同时列正面、负面和不确定催化剂。
- 如果来源或时间不明确，必须标记待验证。
- 不直接给最终买卖建议。

## 标准下游交接字段

每次输出末尾应包含：

```json
{
  "handoff_to_downstream": {
    "must_pass_to": ["07_Market_Expectation_Gap_Analyst", "12_Technical_Price_Volume_Analyst", "13_Sentiment_Public_Opinion_Analyst", "14_Risk_Disconfirmation_Short_Analyst", "01_Master_Valuation_Director"],
    "useful_for": ["05_DCF_Intrinsic_Value_Analyst", "06_Relative_Valuation_Comps_Analyst"],
    "key_fields_to_pass": ["catalyst_calendar", "catalysts", "top_positive_catalysts", "top_negative_catalysts", "near_term_focus", "valuation_realization_path", "key_risks_to_catalyst_view"],
    "confidence": "高 / 中 / 低",
    "missing_information": ["缺失事件日期、来源或验证材料"],
    "blocking_issues": ["阻碍催化剂判断的问题"]
  }
}
```

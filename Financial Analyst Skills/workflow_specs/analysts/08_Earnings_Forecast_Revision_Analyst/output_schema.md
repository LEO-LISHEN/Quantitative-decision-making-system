# 输出结构

## 标准输出字段

```json
{
  "company_identification": {
    "company_name": "公司名称",
    "ticker": "股票代码",
    "market": "上市市场",
    "exchange": "交易所",
    "currency": "币种",
    "information_cutoff": "信息截止时间"
  },
  "data_availability": {
    "consensus_available": true,
    "guidance_available": true,
    "historical_financials_available": true,
    "operating_indicators_available": true,
    "cash_flow_data_available": true,
    "missing_items": ["缺失信息"],
    "confidence_impact": "缺失信息对判断的影响"
  },
  "current_earnings_baseline": {
    "revenue": "当前收入基准",
    "gross_margin": "毛利率基准",
    "operating_margin": "经营利润率基准",
    "net_income_or_eps": "净利润/EPS 基准",
    "free_cash_flow": "自由现金流基准"
  },
  "consensus_and_guidance": {
    "sell_side_consensus": "一致预期",
    "management_guidance": "管理层指引",
    "analyst_revision_trend": "分析师修正趋势",
    "conflicts": ["不同来源冲突"]
  },
  "earnings_drivers": {
    "revenue_drivers": ["收入驱动因素"],
    "margin_drivers": ["利润率驱动因素"],
    "financial_leverage_drivers": ["利息、汇率、税率、股本等因素"],
    "cash_flow_drivers": ["营运资本、资本开支、回款等因素"]
  },
  "revision_direction": {
    "revenue": "上修 | 小幅上修 | 稳定 | 小幅下修 | 下修 | 高度不确定",
    "gross_margin": "上修 | 小幅上修 | 稳定 | 小幅下修 | 下修 | 高度不确定",
    "operating_profit": "上修 | 小幅上修 | 稳定 | 小幅下修 | 下修 | 高度不确定",
    "net_income_or_eps": "上修 | 小幅上修 | 稳定 | 小幅下修 | 下修 | 高度不确定",
    "free_cash_flow": "上修 | 小幅上修 | 稳定 | 小幅下修 | 下修 | 高度不确定"
  },
  "revision_time_window": {
    "current_quarter": "当前季度判断",
    "next_quarter": "下一季度判断",
    "next_4_quarters": "未来4个季度判断",
    "next_2_3_years": "未来2-3年判断"
  },
  "revision_quality": {
    "quality": "高 | 中 | 低 | 无法判断",
    "reason": "修正质量判断理由",
    "recurring_or_one_off": "经常性 | 一次性 | 周期性 | 会计处理 | 混合"
  },
  "revision_probability": {
    "upward_revision_probability": "高 | 中 | 低",
    "downward_revision_probability": "高 | 中 | 低",
    "main_reason": "主要原因"
  },
  "leading_indicators_to_track": ["需要跟踪的领先指标"],
  "valuation_model_implications": {
    "dcf": "对 DCF 的影响",
    "relative_valuation": "对前瞻倍数的影响",
    "expectation_gap": "传递给预期差分析师的信息"
  },
  "key_uncertainties": ["主要不确定因素"],
  "guidance_for_master_director": "总控分析师应如何使用该业绩修正结论"
}
```

## 输出要求

- 必须先说明一致预期和管理层指引是否可得。
- 必须分别判断收入、利润率、净利润/EPS 和自由现金流。
- 必须判断修正质量，而不只是方向。
- 不直接给最终买卖建议。
## 标准下游交接字段

每次输出末尾应包含：

```json
{
  "handoff_to_downstream": {
    "must_pass_to": ["05_DCF_Intrinsic_Value_Analyst", "06_Relative_Valuation_Comps_Analyst", "07_Market_Expectation_Gap_Analyst", "09_Catalyst_Event_Analyst", "14_Risk_Disconfirmation_Short_Analyst", "01_Master_Valuation_Director"],
    "useful_for": ["10_Industry_Cycle_Analyst", "11_Growth_Emerging_Industries_Analyst"],
    "key_fields_to_pass": ["current_earnings_baseline", "revision_direction", "revision_time_window", "revenue_driver_changes", "margin_driver_changes", "eps_cashflow_impact", "revision_quality", "leading_indicators"],
    "confidence": "高 / 中 / 低",
    "missing_information": ["缺失一致预期、指引或经营数据"],
    "blocking_issues": ["阻碍盈利修正判断的问题"]
  }
}
```

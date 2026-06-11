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
    "accounting_standard": "会计准则",
    "information_cutoff": "信息截止时间"
  },
  "data_completeness": {
    "years_available": "可用年度数据",
    "quarters_available": "可用季度数据",
    "statements_available": ["利润表", "资产负债表", "现金流量表", "附注"],
    "missing_items": ["缺失项目"],
    "data_confidence": "高 | 中 | 低"
  },
  "accounting_basis_check": {
    "currency_unit": "币种和单位",
    "reporting_period": "报告期",
    "consolidation_scope": "合并范围",
    "adjusted_or_reported": "法定口径或调整后口径",
    "restatement_or_policy_change": "重述或会计政策变更"
  },
  "historical_trends": {
    "revenue_trend": "收入趋势",
    "gross_margin_trend": "毛利率趋势",
    "operating_margin_trend": "经营利润率趋势",
    "net_margin_trend": "净利率趋势",
    "cash_flow_trend": "现金流趋势",
    "roe_roic_trend": "ROE/ROIC 趋势"
  },
  "earnings_quality": {
    "revenue_quality": "收入质量",
    "margin_quality": "利润率质量",
    "recurring_vs_one_off": "经常性与一次性项目",
    "cash_conversion": "现金流转化"
  },
  "balance_sheet_health": {
    "working_capital": "营运资本",
    "receivables_inventory": "应收和存货",
    "debt_liquidity": "债务和流动性",
    "asset_quality": "资产质量",
    "off_balance_sheet_risks": "表外风险"
  },
  "capex_and_reinvestment": {
    "capex_trend": "资本开支趋势",
    "depreciation_pressure": "折旧压力",
    "r_and_d_quality": "研发投入质量",
    "capital_intensity": "资本密集度"
  },
  "management_plan_financial_verification": [
    {
      "plan": "发展计划",
      "financial_items_to_monitor": ["需要验证的财务科目"],
      "potential_impact": "潜在影响"
    }
  ],
  "red_flags": [
    {
      "level": "黄色 | 橙色 | 红色",
      "item": "红旗事项",
      "evidence": "证据",
      "valuation_impact": "估值影响"
    }
  ],
  "normalized_financial_view": {
    "normalized_earnings": "正常化利润判断",
    "normalized_cash_flow": "正常化现金流判断",
    "adjustments_needed": ["需要调整的项目"]
  },
  "valuation_implications": ["对 DCF、相对估值或风险溢价的影响"],
  "questions_for_downstream_analysts": ["需要下游分析师验证的问题"],
  "confidence_level": "高 | 中 | 低"
}
```

## 输出要求

- 必须先说明数据完整性，再给财务质量结论。
- 必须区分法定口径、调整后口径、TTM 和预测口径。
- 必须说明历史趋势分析覆盖的年份和季度。
- 不直接给最终买卖建议。
## 标准下游交接字段

每次输出末尾应包含：

```json
{
  "handoff_to_downstream": {
    "must_pass_to": ["05_DCF_Intrinsic_Value_Analyst", "06_Relative_Valuation_Comps_Analyst", "08_Earnings_Forecast_Revision_Analyst", "14_Risk_Disconfirmation_Short_Analyst", "01_Master_Valuation_Director"],
    "useful_for": ["03_Fundamental_Business_Analyst", "11_Growth_Emerging_Industries_Analyst"],
    "key_fields_to_pass": ["financial_quality_rating", "data_completeness", "revenue_profit_cashflow_trend", "accounting_warnings", "cash_flow_quality", "balance_sheet_risks", "development_plan_financial_validation"],
    "confidence": "高 / 中 / 低",
    "missing_information": ["缺失财务数据"],
    "blocking_issues": ["阻碍 DCF、盈利预测或风险判断的问题"]
  }
}
```

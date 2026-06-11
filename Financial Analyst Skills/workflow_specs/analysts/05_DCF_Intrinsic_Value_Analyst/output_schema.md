# 输出结构

## 标准输出字段

```json
{
  "company_identification": {
    "company_name": "公司名称",
    "ticker": "股票代码",
    "market": "上市市场",
    "exchange": "交易所",
    "currency": "估值币种",
    "information_cutoff": "信息截止时间"
  },
  "dcf_suitability": {
    "status": "适合 | 部分适合 | 暂不适合 | 不适合",
    "reasons": ["适用或不适用原因"],
    "required_conditions": ["如果要做 DCF 还需要满足的条件"],
    "confidence": "高 | 中 | 低"
  },
  "alternative_valuation_methods": [
    {
      "method": "替代估值方法",
      "reason": "为什么更适合",
      "recommended_for_downstream": true
    }
  ],
  "data_completeness": {
    "cash_flow_data": "完整 | 部分 | 缺失",
    "capex_data": "完整 | 部分 | 缺失",
    "working_capital_data": "完整 | 部分 | 缺失",
    "discount_rate_data": "完整 | 部分 | 缺失",
    "share_count_and_net_debt": "完整 | 部分 | 缺失",
    "missing_items": ["缺失数据"]
  },
  "model_selection": {
    "selected_model": "FCFF | FCFE | DDM | 剩余收益 | 情景DCF | 不建模",
    "selection_reason": "选择原因"
  },
  "cash_flow_forecast_sources": {
    "financial_quality": ["来自财务分析师的数据"],
    "business_quality": ["来自基本面分析师的数据"],
    "industry_cycle": ["来自行业周期分析师的数据"],
    "earnings_revision": ["来自盈利预测分析师的数据"],
    "external_data": ["主动搜集或 API 数据"]
  },
  "key_assumptions": {
    "revenue_growth": "收入增长假设",
    "margin": "利润率假设",
    "tax_rate": "税率假设",
    "capex": "资本开支假设",
    "working_capital": "营运资本假设",
    "discount_rate": "折现率假设",
    "terminal_value": "终值假设"
  },
  "scenario_valuation": {
    "bear": {},
    "base": {},
    "bull": {}
  },
  "sensitivity_analysis": {
    "wacc": "WACC 敏感性",
    "terminal_growth": "永续增长率敏感性",
    "exit_multiple": "退出倍数敏感性",
    "long_term_margin": "长期利润率敏感性",
    "revenue_growth": "收入增速敏感性",
    "capex_ratio": "资本开支率敏感性",
    "working_capital": "营运资本敏感性"
  },
  "terminal_value_risk": {
    "terminal_value_share_of_ev": "终值占企业价值比例",
    "risk_comment": "终值风险说明"
  },
  "valuation_range": {
    "enterprise_value_range": "企业价值区间",
    "equity_value_range": "股权价值区间",
    "per_share_value_range": "每股价值区间，数据不足则标注无法可靠计算"
  },
  "most_sensitive_assumptions": ["最敏感假设"],
  "most_likely_wrong_assumptions": ["最可能出错的假设"],
  "guidance_for_master_director": "总控分析师应如何使用该 DCF 结果"
}
```

## 输出要求

- 如果 `dcf_suitability.status` 为“暂不适合”或“不适合”，不得强行输出目标价。
- 如果数据不足，每股价值必须标注“无法可靠计算”。
- 必须输出替代估值方法。
- 必须说明终值风险。
- 不直接给最终买卖建议。

## 标准下游交接字段

每次输出末尾应包含：

```json
{
  "handoff_to_downstream": {
    "must_pass_to": ["07_Market_Expectation_Gap_Analyst", "14_Risk_Disconfirmation_Short_Analyst", "01_Master_Valuation_Director"],
    "useful_for": ["09_Catalyst_Event_Analyst"],
    "key_fields_to_pass": ["dcf_suitability", "valuation_range", "scenario_valuation", "sensitivity_analysis", "most_sensitive_assumptions", "most_likely_wrong_assumptions", "terminal_value_risk", "alternative_valuation_methods"],
    "confidence": "高 / 中 / 低",
    "missing_information": ["估值所需缺失信息"],
    "blocking_issues": ["阻碍高置信 DCF 的问题"]
  }
}
```

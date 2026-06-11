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
  "business_model_summary": {
    "what_it_sells": "公司卖什么",
    "customers": "客户是谁",
    "why_customers_buy": "客户为什么买",
    "revenue_model": "收入模式",
    "profit_model": "利润模式",
    "cash_flow_characteristics": "现金流特征"
  },
  "segment_analysis": [
    {
      "segment": "业务板块",
      "revenue_driver": "收入驱动因素",
      "profit_driver": "利润驱动因素",
      "growth_quality": "增长质量",
      "risk": "主要风险"
    }
  ],
  "industry_and_competition": {
    "industry_structure": "行业结构",
    "main_competitors": ["主要竞争对手"],
    "competitive_intensity": "高 | 中 | 低",
    "bargaining_power": "上下游议价能力",
    "substitution_risk": "替代风险"
  },
  "moat_assessment": {
    "moat_sources": ["护城河来源"],
    "moat_strength": "强 | 中 | 弱 | 无",
    "moat_trend": "变宽 | 稳定 | 变窄 | 不确定",
    "evidence": ["证据"]
  },
  "roic_and_reinvestment": {
    "roic_implication": "ROIC 含义",
    "reinvestment_runway": "再投资空间",
    "capital_intensity": "资本开支强度",
    "scalability": "规模化能力"
  },
  "management_and_capital_allocation": {
    "management_quality": "管理层质量",
    "capital_allocation": "资本配置",
    "shareholder_friendliness": "股东友好程度"
  },
  "cross_market_context": {
    "market_style": "A股/港股/美股市场风格影响",
    "valuation_premium_or_discount_context": "估值溢价或折价背景"
  },
  "business_quality_rating": "优秀 | 良好 | 一般 | 脆弱 | 较差",
  "valuation_implication": "应享受溢价 | 接近同行 | 应当折价 | 暂无法判断",
  "key_risks": ["商业模式风险"],
  "questions_for_downstream_analysts": ["需要后续模块验证的问题"],
  "confidence_level": "高 | 中 | 低"
}
```

## 输出要求

- 所有商业质量判断必须说明证据。
- 如果某项判断缺乏证据，应标注“待验证”。
- 不能直接给最终买入或卖出建议。
- 必须说明商业质量对估值倍数、DCF 假设或风险溢价的影响。
## 标准下游交接字段

每次输出末尾应包含：

```json
{
  "handoff_to_downstream": {
    "must_pass_to": ["05_DCF_Intrinsic_Value_Analyst", "06_Relative_Valuation_Comps_Analyst", "08_Earnings_Forecast_Revision_Analyst", "09_Catalyst_Event_Analyst", "14_Risk_Disconfirmation_Short_Analyst", "01_Master_Valuation_Director"],
    "useful_for": ["07_Market_Expectation_Gap_Analyst", "11_Growth_Emerging_Industries_Analyst"],
    "key_fields_to_pass": ["business_quality_rating", "revenue_drivers", "margin_drivers", "moat_assessment", "management_capital_allocation", "valuation_implication", "key_risks"],
    "confidence": "高 / 中 / 低",
    "missing_information": ["缺失信息"],
    "blocking_issues": ["阻碍下游估值或盈利预测的问题"]
  }
}
```

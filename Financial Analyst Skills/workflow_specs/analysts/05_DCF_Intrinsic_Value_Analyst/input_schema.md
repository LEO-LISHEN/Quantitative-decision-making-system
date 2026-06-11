# 输入结构

## 必填输入

- 公司名称或股票代码
- 上市市场或交易所
- 信息截止时间
- 财务报表与质量分析师输出，至少包括历史收入、利润率、现金流、资本开支、营运资本、净债务和股本信息
- 基本面与商业模式分析师输出，至少包括商业质量、护城河、ROIC 和再投资空间判断

## 推荐输入

- 最近 5-10 年财务数据
- 最近 4-8 个季度财务数据
- 管理层指引
- 资本开支计划
- 分业务收入和利润率
- 行业增速和周期位置
- 一致预期或研报预测
- 可比公司利润率、资本结构和估值倍数
- 无风险利率、股权风险溢价、Beta、债务成本、税率
- 净现金、净债务、少数股东权益、联营公司价值、股本数量

## 现金流预测数据来源

DCF 分析师应优先使用：

- 财务分析师：历史收入、利润率、经营现金流、自由现金流、资本开支、营运资本、债务、现金、股本。
- 基本面分析师：增长质量、护城河、ROIC、再投资空间、商业质量。
- 行业周期分析师：行业增速、价格周期、供需、周期阶段。
- 盈利预测分析师：未来收入、利润率、订单、成本、管理层指引和一致预期。
- 信息源分析师：公告、研报、新闻、资本开支计划、发展计划。
- 主动搜索/API：无风险利率、ERP、Beta、债务成本、可比公司资本结构、税率。

## 输入字段建议

```json
{
  "company_name": "公司名称",
  "ticker": "股票代码",
  "market": "A股 | 港股 | 美股 | 其他",
  "exchange": "交易所",
  "currency": "估值币种",
  "information_cutoff": "信息截止时间",
  "financial_quality_output": {
    "historical_trends": {},
    "normalized_financial_view": {},
    "capex_and_reinvestment": {},
    "balance_sheet_health": {},
    "red_flags": []
  },
  "business_quality_output": {
    "business_quality_rating": "优秀 | 良好 | 一般 | 脆弱 | 较差",
    "moat_assessment": {},
    "roic_and_reinvestment": {}
  },
  "forecast_inputs": {
    "management_guidance": [],
    "consensus_estimates": [],
    "industry_growth": [],
    "capex_plan": [],
    "working_capital_assumptions": []
  },
  "discount_rate_inputs": {
    "risk_free_rate": "无风险利率",
    "equity_risk_premium": "股权风险溢价",
    "beta_or_risk_adjustment": "Beta 或风险调整",
    "cost_of_debt": "债务成本",
    "tax_rate": "税率",
    "capital_structure": "资本结构"
  }
}
```

## 缺失输入处理

如果缺少现金流、资本开支和营运资本数据，不得输出高置信度 DCF。  
如果缺少股本和净债务，不得可靠计算每股价值。  
如果缺少折现率数据，应使用区间，而不是单点。  
如果历史财务数据不足，应优先判断“暂不适合 DCF”。

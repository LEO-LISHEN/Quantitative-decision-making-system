# 输入规范

## 最小输入

```json
{
  "company_name": "公司名称",
  "ticker": "股票代码",
  "market": "A股 / 港股 / 美股 / 中概股 / 其他",
  "analysis_date": "YYYY-MM-DD",
  "bull_thesis_to_test": "需要反证的核心多头逻辑"
}
```

## 推荐输入

```json
{
  "company_profile": {
    "company_name": "公司名称",
    "ticker": "股票代码",
    "exchange": "交易所",
    "market": "A股 / 港股 / 美股 / 中概股",
    "industry": "行业",
    "currency": "报告货币",
    "primary_listing": "主上市地"
  },
  "analysis_config": {
    "analysis_date": "YYYY-MM-DD",
    "risk_time_horizon": "短期 / 未来12个月 / 未来2-3年 / 长期",
    "risk_focus": ["财务质量", "监管", "竞争", "估值", "流动性", "治理", "做空报告"],
    "severity_threshold": "只输出中高风险 / 输出全部风险"
  },
  "thesis_to_test": {
    "bull_thesis": "当前多头逻辑",
    "valuation_assumption": "当前估值假设",
    "growth_assumption": "成长假设",
    "margin_assumption": "利润率假设",
    "cash_flow_assumption": "现金流假设",
    "catalyst_assumption": "催化剂假设",
    "market_expectation": "市场预期"
  },
  "source_materials": {
    "annual_reports": ["年报/10-K/20-F"],
    "interim_reports": ["半年报/中报/10-Q/季报"],
    "announcements": ["公告"],
    "audit_reports": ["审计意见/内控报告"],
    "regulatory_documents": ["监管问询/处罚/交易所函件/公司回复"],
    "legal_documents": ["诉讼/仲裁/法院文件/class action"],
    "short_reports": ["做空报告/媒体调查"],
    "company_responses": ["公司回应/澄清公告"],
    "news": ["新闻报道"],
    "social_sentiment": ["股吧/社交媒体/投诉/员工评价/用户评价"],
    "market_data": ["股价/成交量/估值/做空数据/债券价格/信用利差"]
  },
  "financial_risk_inputs": {
    "income_statement": "利润表数据",
    "balance_sheet": "资产负债表数据",
    "cash_flow_statement": "现金流量表数据",
    "receivables": "应收账款",
    "inventory": "存货",
    "contract_assets_liabilities": "合同资产/合同负债",
    "debt_maturity": "债务到期",
    "cash_balance": "现金余额",
    "capex": "资本开支",
    "related_party_transactions": "关联交易",
    "impairment": "减值",
    "contingent_liabilities": "或有负债"
  },
  "upstream_analyst_outputs": {
    "source_intelligence": "信息源分析师输出",
    "fundamental": "基本面分析师输出",
    "financial_quality": "财务质量分析师输出",
    "dcf": "DCF 分析师输出",
    "relative_valuation": "相对估值分析师输出",
    "expectation_gap": "预期差分析师输出",
    "earnings_revision": "盈利修正分析师输出",
    "catalyst": "事件催化剂分析师输出",
    "industry_cycle": "行业周期分析师输出",
    "growth": "成长股分析师输出",
    "technical": "技术分析师输出",
    "sentiment": "舆情分析师输出"
  }
}
```

## 关键输入说明

- 必须提供被检验的核心多头逻辑，否则只能做通用风险扫描。
- 如果存在做空报告或监管问询，必须提供原文、发布时间、公司回应和后续进展。
- 如果涉及财务风险，必须尽量提供三张表、附注、审计意见和历史趋势。
- 如果涉及短期下跌风险，建议提供价格、成交量、相对强弱和舆情时间线。
- 如果涉及传闻或匿名爆料，必须标注来源、时间、传播范围和待验证状态。

## 缺失信息时必须要求补齐

如以下信息缺失，应明确要求补充：

- 当前多头逻辑和估值假设。
- 最近年报、半年报、季报和审计意见。
- 监管问询、处罚、诉讼或做空报告原文。
- 公司回应或澄清公告。
- 关键财务科目明细和历史趋势。
- 债务到期、现金余额和融资安排。
- 价格和成交量异常数据。

## 输入质量评级

- `high`: 有完整正式披露、上游分析师输出、风险事件原始文件和市场数据。
- `medium`: 有主要披露和部分风险材料，但缺少明细或公司回应。
- `low`: 主要来自新闻、舆情或单一报告，缺少正式文件验证。
- `insufficient`: 缺少多头逻辑、财务数据或风险来源，无法可靠反证。

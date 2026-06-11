# 输入规范

## 最小输入

```json
{
  "company_name": "公司名称",
  "ticker": "股票代码",
  "market": "A股 / 港股 / 美股 / 中概股 / 其他",
  "analysis_date": "YYYY-MM-DD",
  "target_question": "需要分析的成长问题"
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
    "currency": "报告货币",
    "industry": "行业",
    "business_segments": ["业务板块1", "业务板块2"]
  },
  "source_materials": {
    "annual_reports": ["年报/10-K/20-F/招股书"],
    "interim_reports": ["半年报/中报/10-Q/季报"],
    "announcements": ["重大公告/监管公告"],
    "earnings_calls": ["业绩会纪要/投资者日材料"],
    "research_reports": ["券商研报/行业报告"],
    "news": ["新闻/行业媒体报道"],
    "social_media_or_forums": ["股吧/雪球/X/Reddit/微信公众号/用户社区/产业论坛"],
    "company_ir": ["官网/投资者关系材料/产品发布材料"],
    "third_party_data": ["行业数据库/专利/招投标/临床试验/应用商店/招聘/海关数据"]
  },
  "growth_metrics": {
    "revenue_growth": "收入增速",
    "segment_growth": "分业务增速",
    "users_or_customers": "用户数/客户数",
    "orders_or_backlog": "订单/合同负债/在手订单",
    "arr_or_subscription_metrics": "ARR/NRR/留存率/ARPU",
    "market_share": "市场份额",
    "gross_margin": "毛利率",
    "operating_margin": "经营利润率",
    "capex": "资本开支",
    "rd_expense": "研发费用",
    "free_cash_flow": "自由现金流",
    "cash_balance": "现金储备",
    "funding_plan": "融资计划"
  },
  "industry_context": {
    "tam_estimates": ["市场规模估算"],
    "penetration_rate": "行业渗透率",
    "adoption_stage": "导入期/加速期/成熟期/竞争加剧期/其他",
    "competitors": ["竞争对手"],
    "regulation_policy": ["政策/监管/审批要求"],
    "supply_chain_constraints": ["供应链瓶颈/产能限制"]
  },
  "valuation_context": {
    "current_market_cap": "当前市值",
    "current_ev": "当前企业价值",
    "current_multiples": "当前估值倍数",
    "peer_multiples": "可比公司估值",
    "analyst_consensus": "市场一致预期",
    "market_narrative": "当前市场主要成长叙事"
  }
}
```

## 关键输入说明

- 年报和半年报用于提取正式发展计划、管理层展望、业务进展、风险提示和财务验证。
- 新闻和社交媒体用于发现线索和市场叙事，但需要用正式披露或多源信息验证。
- 如果只有研报而没有公司正式披露，需要标注为二手来源。
- 如果只有社交媒体或股吧讨论，不能做高置信成长结论。
- 如果缺少市场规模、渗透率、客户验证、订单或单位经济模型，只能做低置信情景分析。

## 缺失信息时必须请求补齐

如以下信息缺失，应明确要求补充：

- 最近 2-3 年年报、半年报/中报或 10-K、10-Q、20-F。
- 公司关于新业务、新产品、新市场或研发管线的正式披露。
- 收入分部、毛利率、研发、资本开支、现金流和现金储备。
- 行业市场规模、渗透率、竞争对手和价格趋势。
- 客户、订单、用户、留存、合同负债、产能利用率或其他行业关键指标。
- 新闻和社交媒体线索的发布时间、来源链接和原始表述。

## 输入质量标记

分析时应标注输入质量：

- `high`: 有公司正式披露、财务数据、行业数据和第三方验证。
- `medium`: 有部分正式披露和研报，但缺少关键经营指标。
- `low`: 主要来自新闻、社交媒体或单一研报，缺少硬数据验证。
- `insufficient`: 缺少判断成长故事所需的核心材料。

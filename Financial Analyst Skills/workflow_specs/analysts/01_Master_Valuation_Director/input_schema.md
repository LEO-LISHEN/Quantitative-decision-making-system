# 输入规范

## 最小输入

```json
{
  "company_name": "公司名称",
  "ticker": "股票代码",
  "market": "A股 / 港股 / 美股 / 中概股 / 其他",
  "analysis_date": "YYYY-MM-DD",
  "user_goal": "考虑买入 / 已持有复核 / 考虑卖出 / 估值分析 / 风险检查 / 全面分析"
}
```

## 推荐输入

```json
{
  "task_context": {
    "company_name": "公司名称",
    "ticker": "股票代码",
    "exchange": "交易所",
    "market": "A股 / 港股 / 美股 / 中概股",
    "currency": "交易货币",
    "analysis_date": "YYYY-MM-DD",
    "information_cutoff": "YYYY-MM-DD",
    "user_goal": "考虑买入 / 已持有复核 / 考虑卖出 / 估值分析 / 风险检查 / 全面分析",
    "holding_status": "未持有 / 已持有 / 计划建仓 / 计划减仓 / 未说明",
    "user_time_horizon": ["短期", "中期", "长期", "全部"],
    "risk_preference": "低 / 中 / 高 / 未说明"
  },
  "raw_materials": {
    "annual_reports": ["年报/10-K/20-F"],
    "interim_reports": ["半年报/中报/10-Q/季报"],
    "announcements": ["公告"],
    "research_reports": ["研报"],
    "news": ["新闻"],
    "financial_tables": ["财务数据表"],
    "kline_tables": ["日K数据表"],
    "sentiment_samples": ["股吧/社交媒体/新闻评论样本"],
    "other_materials": ["其他材料"]
  },
  "market_snapshot": {
    "current_price": "当前价格",
    "market_cap": "市值",
    "enterprise_value": "企业价值",
    "shares_outstanding": "股本",
    "net_cash_or_debt": "净现金/净债务",
    "valuation_multiples": "当前估值倍数",
    "recent_price_performance": "近期涨跌幅"
  },
  "analyst_outputs": {
    "source_intelligence": {},
    "fundamental_business": {},
    "financial_quality": {},
    "dcf_intrinsic_value": {},
    "relative_valuation": {},
    "market_expectation_gap": {},
    "earnings_forecast_revision": {},
    "catalyst_event": {},
    "industry_cycle": {},
    "growth_emerging": {},
    "technical_price_volume": {},
    "sentiment_public_opinion": {},
    "risk_disconfirmation_short": {}
  },
  "workflow_status": {
    "completed_analysts": ["已完成分析师"],
    "missing_analysts": ["缺失分析师"],
    "blocked_by_missing_data": ["受缺失数据影响的模块"],
    "requires_active_search": true
  }
}
```

## 输入模式

### 模式一：原始材料模式

用户只提供股票代码、公司名称和部分材料。总控分析师应：

- 明确需要哪些专项分析。
- 主动搜索或要求补充材料。
- 按专项分析师逻辑分模块完成分析。
- 对缺失模块降低置信度。

### 模式二：专项输出整合模式

用户已经提供各专项分析师输出。总控分析师应：

- 检查输出完整性。
- 检查互相冲突。
- 检查是否缺少关键模块。
- 根据全局联动协议整合最终结论。

### 模式三：混合模式

用户提供部分专项输出和部分原始材料。总控分析师应：

- 对已有专项输出直接整合。
- 对缺失模块主动补做或要求补齐。
- 标注哪些结论来自专项输出，哪些来自总控补充判断。

## 必须补充或降低置信度的缺失项

如果缺失以下信息，应明确指出：

- 当前价格或市值。
- 最近财报和关键财务数据。
- 信息源可信度判断。
- 估值所需关键假设。
- 行情数据和事件时间线。
- 风险反证输出。

如果缺少风险反证分析，最终建议不得为高置信“买入”。

## 用户风险偏好

如果用户未提供风险偏好，总控分析师可以给出一般性投研建议，但不应声称这是个性化投资顾问建议。若涉及仓位，只能使用“低仓位/中等仓位/高风险者可考虑”等条件性表达。

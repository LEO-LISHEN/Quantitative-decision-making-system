# 输入结构

## 必填输入

- 公司名称或股票代码
- 上市市场或交易所
- 信息截止时间
- 至少一条事件信息，或允许分析师主动搜索事件

## 推荐输入

- 信息源分析师输出的事件时间线和可信度
- 市场预期差分析师输出的定价状态
- 盈利预测分析师输出的上修/下修判断
- DCF 分析师输出的关键估值假设
- 相对估值分析师输出的市场估值锚
- 行业周期分析师输出的行业拐点
- 技术/情绪分析师输出的资金和叙事信号

## 事件输入类型

可输入：

- 财报日期
- 业绩预告、业绩快报、盈利警告
- 管理层指引
- 新产品
- 订单
- 价格变化
- 成本变化
- 政策会议
- 监管审批
- 并购重组
- 回购、分红、增持、减持
- 定增、配股、供股、融资
- 产能投放
- 诉讼、处罚、违约、问询函
- 指数纳入
- 限售股解禁
- 资金流变化

## 主动搜集输入

如果平台提供搜索、公告、新闻、日历、监管、行业数据或 API，应主动搜集：

- 公司公告
- 财报日期和投资者关系日历
- 业绩预告/盈利警告
- 政策时间表
- 审批进度
- 订单公告
- 回购分红公告
- 限售股解禁
- 股东增减持
- 指数纳入
- 并购重组进度
- 诉讼和监管文件
- 行业会议和产品发布

## 输入字段建议

```json
{
  "company_name": "公司名称",
  "ticker": "股票代码",
  "market": "A股 | 港股 | 美股 | 其他",
  "exchange": "交易所",
  "information_cutoff": "信息截止时间",
  "event_candidates": [
    {
      "event_name": "事件名称",
      "event_type": "earnings | order | policy | approval | M&A | buyback | dividend | financing | litigation | index | other",
      "expected_timing": "预计时间",
      "source": "来源",
      "credibility": "可信度",
      "description": "事件描述"
    }
  ],
  "expectation_gap_output": {},
  "earnings_revision_output": {},
  "valuation_outputs": {
    "dcf": {},
    "relative_valuation": {}
  },
  "market_reaction_context": {
    "price_volume": {},
    "sentiment": {},
    "fund_flow": {}
  }
}
```

## 缺失输入处理

如果缺少事件日期，只能标记为待确认时间。  
如果缺少来源，只能标记为待验证事件。  
如果缺少市场定价状态，应要求市场预期差分析师或行情数据补充。  
如果缺少影响测算，应要求盈利预测、估值或行业分析师补充。

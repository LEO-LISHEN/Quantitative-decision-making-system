# 输入结构

## 必填输入

- 公司名称或股票代码
- 上市市场或交易所
- 信息截止时间
- 当前盈利基准或至少一份财务/业绩材料

## 推荐输入

- 财务报表与质量分析师输出
- 基本面与商业模式分析师输出
- 信息源分析师输出
- 市场预期差分析师输出
- 行业周期分析师输出
- 催化剂分析师输出
- 历史收入、利润率、费用率、EPS 和自由现金流
- 管理层指引
- 一致预期
- 研报预测
- 业绩预告、业绩快报或盈利警告
- 订单、价格、成本、库存、产能利用率和行业高频数据
- 同行财报和指引

## 主动搜集输入

如果平台提供搜索、研报库、财务数据库、公告、行业数据或 API，应主动搜集：

- 管理层指引
- 业绩预告/盈利警告
- 一致预期
- 分析师预测修正
- 收入和 EPS consensus
- 订单和 backlog
- 价格、成本、库存和产能利用率
- 行业高频数据
- 同行财报和指引
- 历史季节性
- 汇率、原材料、利率和税率

## 输入字段建议

```json
{
  "company_name": "公司名称",
  "ticker": "股票代码",
  "market": "A股 | 港股 | 美股 | 其他",
  "exchange": "交易所",
  "currency": "币种",
  "information_cutoff": "信息截止时间",
  "financial_quality_output": {},
  "business_quality_output": {},
  "market_expectation_gap_output": {},
  "industry_cycle_output": {},
  "current_earnings_baseline": {
    "revenue": "当前收入基准",
    "gross_margin": "毛利率",
    "operating_margin": "经营利润率",
    "net_income": "净利润",
    "eps": "EPS",
    "free_cash_flow": "自由现金流"
  },
  "consensus_or_guidance": {
    "sell_side_consensus": [],
    "management_guidance": [],
    "analyst_revisions": []
  },
  "new_information": [
    {
      "type": "order | price | cost | guidance | earnings | policy | peer_result | other",
      "source": "来源",
      "date": "日期",
      "content": "内容"
    }
  ],
  "operating_indicators": {
    "orders": [],
    "prices": [],
    "costs": [],
    "inventory": [],
    "capacity_utilization": [],
    "users_or_arpu": [],
    "arr_or_rpo": []
  }
}
```

## 缺失输入处理

如果缺少一致预期，不能高置信判断是否超预期。  
如果缺少管理层指引，应降低修正判断确定性。  
如果缺少历史财务，不能可靠判断季节性和趋势。  
如果缺少订单、价格或成本数据，不能高置信判断收入和利润率修正。  
如果缺少现金流数据，不能判断盈利修正质量。

# 输入结构

## 必填输入

- 公司名称或股票代码
- 上市市场或交易所
- 信息截止时间
- 至少一条可能影响估值或市场预期的信息
- 信息发布时间或事件发生时间

## 强烈推荐输入

- 信息源分析师输出的事件时间线和信息可信度
- DCF 分析师输出的估值隐含假设
- 相对估值分析师输出的市场估值锚和当前倍数位置
- 财务分析师输出的业绩质量和财务红旗
- 盈利预测分析师输出的一致预期、管理层指引和预测修正
- 情绪分析师输出的叙事扩散和拥挤度
- 近期日 K 线表格
- 行业指数和大盘同期表现

## GPTs 测试模式：日 K 线表格字段

用户上传表格时，最少包含：

```text
date
open
high
low
close
volume
turnover
pct_change
```

推荐包含：

```text
date
open
high
low
close
volume
turnover
pct_change
adjusted_close
market_index_pct_change
sector_index_pct_change
notes
```

A 股建议额外包含：

```text
limit_up_down_status
turnover_rate
northbound_flow
margin_financing_balance
```

港股建议额外包含：

```text
short_sell_turnover
southbound_flow
turnover_hkd
```

美股建议额外包含：

```text
pre_market_change
after_hours_change
options_volume
sector_etf_pct_change
```

## 事件表字段

建议提供：

```text
event_date
event_time
event_type
source
headline
summary
credibility
expected_or_unexpected
```

## 工作流/API 模式：行情 API 建议字段

行情 API 应返回：

```json
{
  "ticker": "股票代码",
  "market": "市场",
  "start_date": "开始日期",
  "end_date": "结束日期",
  "adjustment": "前复权 | 后复权 | 不复权",
  "daily_bars": [
    {
      "date": "日期",
      "open": "开盘价",
      "high": "最高价",
      "low": "最低价",
      "close": "收盘价",
      "volume": "成交量",
      "turnover": "成交额",
      "pct_change": "涨跌幅",
      "adjusted_close": "复权收盘价"
    }
  ],
  "market_index": [],
  "sector_index": []
}
```

## 输入字段建议

```json
{
  "company_name": "公司名称",
  "ticker": "股票代码",
  "market": "A股 | 港股 | 美股 | 其他",
  "exchange": "交易所",
  "information_cutoff": "信息截止时间",
  "event_timeline": [
    {
      "event_date": "事件发生日期",
      "public_time": "信息公开时间",
      "source": "来源",
      "headline": "标题",
      "summary": "摘要",
      "credibility": "可信度"
    }
  ],
  "price_volume_data": {
    "daily_bars": [],
    "market_index": [],
    "sector_index": []
  },
  "consensus_or_expectations": {
    "sell_side_consensus": [],
    "management_guidance": [],
    "market_narratives": []
  },
  "valuation_context": {
    "dcf_output": {},
    "relative_valuation_output": {}
  }
}
```

## 缺失输入处理

如果缺少日 K 线和成交量，不能高置信判断是否已定价。  
如果缺少事件发布时间，不能高置信判断信息是否新。  
如果缺少行业或大盘对比，不能可靠区分个股反应和市场整体波动。  
缺失时必须明确列出需要补充的数据字段。

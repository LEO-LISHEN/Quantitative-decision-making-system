# 输入规范

## 最小输入

```json
{
  "company_name": "公司名称",
  "ticker": "股票代码",
  "market": "A股 / 港股 / 美股 / 中概股 / 其他",
  "analysis_date": "YYYY-MM-DD",
  "data_mode": "uploaded_table / api / chart_screenshot / text_description"
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
    "currency": "交易货币",
    "industry": "行业",
    "primary_listing": "主上市地"
  },
  "analysis_config": {
    "analysis_date": "YYYY-MM-DD",
    "lookback_period": "60d / 120d / 250d / custom",
    "price_adjustment": "前复权 / 后复权 / 不复权 / 未知",
    "timeframe": "日线 / 周线 / 月线 / 分钟线",
    "benchmark_type": "market_index / industry_index / sector_etf / peers",
    "technical_focus": ["趋势", "量价", "突破", "事件反应", "相对强弱"]
  },
  "daily_kline_table": [
    {
      "date": "YYYY-MM-DD",
      "open": 0,
      "high": 0,
      "low": 0,
      "close": 0,
      "volume": 0,
      "amount": 0,
      "turnover_rate": 0,
      "pct_change": 0,
      "adj_factor": 1,
      "limit_up": 0,
      "limit_down": 0,
      "suspended": false
    }
  ],
  "benchmark_data": {
    "market_index": [
      {
        "date": "YYYY-MM-DD",
        "close": 0,
        "pct_change": 0,
        "volume": 0,
        "amount": 0
      }
    ],
    "industry_index": [
      {
        "date": "YYYY-MM-DD",
        "close": 0,
        "pct_change": 0,
        "volume": 0,
        "amount": 0
      }
    ],
    "peer_prices": [
      {
        "ticker": "可比公司代码",
        "date": "YYYY-MM-DD",
        "close": 0,
        "pct_change": 0
      }
    ]
  },
  "event_timeline": [
    {
      "date": "YYYY-MM-DD",
      "event_type": "财报 / 公告 / 业绩预告 / 政策 / 订单 / 新产品 / 审批 / 回购 / 分红 / 并购 / 研报 / 其他",
      "event_title": "事件标题",
      "event_direction": "正面 / 负面 / 中性 / 不确定",
      "source": "来源",
      "source_quality": "高 / 中 / 低"
    }
  ],
  "api_context": {
    "data_provider": "行情 API 名称",
    "fields_available": ["open", "high", "low", "close", "volume", "amount"],
    "fields_missing": [],
    "last_update_time": "YYYY-MM-DD HH:mm:ss"
  },
  "upstream_analyst_outputs": {
    "fundamental_view": "基本面分析结论",
    "valuation_view": "估值分析结论",
    "expectation_gap_view": "预期差分析结论",
    "catalyst_view": "事件催化剂结论",
    "risk_view": "风险分析结论"
  }
}
```

## 日 K 表格字段要求

### 必需字段

- `date`: 交易日期。
- `open`: 开盘价。
- `high`: 最高价。
- `low`: 最低价。
- `close`: 收盘价。
- `volume`: 成交量。

### 强烈建议字段

- `amount`: 成交额。
- `turnover_rate`: 换手率。
- `pct_change`: 涨跌幅。
- `adj_factor`: 复权因子。
- `limit_up`: A 股涨停价。
- `limit_down`: A 股跌停价。
- `suspended`: 是否停牌。

### 基准数据字段

用于判断相对强弱：

- 大盘指数日 K。
- 行业指数日 K。
- 主题指数或 ETF 日 K。
- 可比公司日 K。

## 数据长度要求

- `>= 250` 个交易日：可做中长期趋势、年内高低点、主要支撑阻力和相对强弱判断。
- `60-249` 个交易日：可做短中期趋势判断。
- `20-59` 个交易日：只能做近期走势和事件反应观察。
- `< 20` 个交易日：技术结论置信度很低。

## 缺失信息处理

如果缺少以下数据，应明确要求补充：

- 个股日 K 数据。
- 成交量或成交额。
- 复权口径。
- 指数或行业基准。
- 事件日期和事件说明。
- 停复牌、除权除息、拆股或配股信息。

不要根据单纯文字描述高置信判断突破、放量、破位或相对强弱。

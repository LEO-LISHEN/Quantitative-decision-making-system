# 输入结构

## 必填输入

- 公司名称或股票代码
- 上市市场或交易所
- 信息截止时间
- 公司行业、商业模式和主要业务
- 至少一组候选可比公司，或允许分析师主动搜索可比公司

## 推荐输入

- 基本面与商业模式分析师输出
- 财务报表与质量分析师输出
- DCF 与内在价值分析师输出
- 市值、股价、股本、净债务、现金、少数股东权益
- 最近年度、TTM 和未来 1-3 年盈利预测
- 可比公司财务数据和估值倍数
- 历史估值区间
- 行业平均和龙头公司估值
- 分业务收入、利润、资产或现金流

## 主动搜集输入

如果平台提供搜索、行情、财务数据库、研报库或 API，应主动补充：

- 可比公司名单
- 公司和同行市值
- 企业价值 EV
- 净债务、现金和少数股东权益
- P/E、Forward P/E、PEG、P/B、EV/EBITDA、EV/Sales、P/FCF、股息率等
- 行业特定倍数，例如 EV/ARR、P/EV、NAV 折价、储量价值、GMV 倍数等
- 历史估值区间和分位数

## 输入字段建议

```json
{
  "company_name": "公司名称",
  "ticker": "股票代码",
  "market": "A股 | 港股 | 美股 | 其他",
  "exchange": "交易所",
  "currency": "估值币种",
  "information_cutoff": "信息截止时间",
  "business_quality_output": {},
  "financial_quality_output": {},
  "dcf_output": {},
  "candidate_comps": [
    {
      "company_name": "可比公司",
      "ticker": "代码",
      "market": "市场",
      "reason_for_inclusion": "纳入原因"
    }
  ],
  "valuation_data": {
    "market_cap": "市值",
    "enterprise_value": "企业价值",
    "net_debt": "净债务",
    "share_count": "股本",
    "earnings": "利润口径",
    "revenue": "收入",
    "ebitda": "EBITDA",
    "book_value": "净资产",
    "free_cash_flow": "自由现金流"
  },
  "research_focus": "用户关注的问题"
}
```

## 缺失输入处理

如果缺少可靠可比公司，应明确说明相对估值不适合作为核心估值方法。  
如果缺少市值、EV、净债务、股本或盈利预测，不得可靠计算每股价值。  
如果倍数口径不一致，必须先校验或拒绝比较。

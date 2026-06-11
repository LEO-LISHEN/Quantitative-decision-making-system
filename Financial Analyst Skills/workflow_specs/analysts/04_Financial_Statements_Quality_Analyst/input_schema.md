# 输入结构

## 必填输入

- 公司名称或股票代码
- 上市市场或交易所
- 分析时间范围
- 至少一份财务材料，或允许分析师主动搜索财务披露

## 推荐输入

- 最近 3-5 年年报
- 最近 4-8 个季度财报
- 利润表
- 资产负债表
- 现金流量表
- 财务附注
- 审计意见
- 分部信息
- 管理层讨论与分析
- 业绩预告、业绩快报或管理层指引
- 监管问询函、审计保留意见、财务重述或会计政策变更

## 主动搜集输入

如果平台提供搜索、文件检索、数据库、公告、财务 API 或插件，应主动补充：

- A 股：年报、半年报、季报、业绩预告、业绩快报、问询函、非经常性损益、扣非净利润。
- 港股：年报、中报、业绩公告、通函、审计意见、公允价值变动、分红和净债务。
- 美股：10-K、10-Q、8-K、20-F、6-K、earnings release、non-GAAP reconciliation、SBC、递延收入、回购和股本变化。

## 输入字段建议

```json
{
  "company_name": "公司名称",
  "ticker": "股票代码",
  "market": "A股 | 港股 | 美股 | 其他",
  "exchange": "交易所",
  "currency": "币种",
  "accounting_standard": "会计准则",
  "time_range": "分析时间范围",
  "information_cutoff": "信息截止时间",
  "financial_documents": [
    {
      "type": "annual_report | quarterly_report | interim_report | 10-K | 10-Q | 20-F | 6-K | earnings_release | other",
      "period": "报告期",
      "source": "来源",
      "content": "正文、表格或摘要"
    }
  ],
  "management_plans": [
    {
      "type": "capex | R&D | overseas_expansion | M&A | buyback | dividend | capacity_expansion | other",
      "content": "发展计划内容"
    }
  ],
  "research_focus": "用户关注的问题"
}
```

## 缺失输入处理

如果缺少连续历史数据，应明确说明无法可靠判断趋势。  
如果缺少现金流量表或资产负债表，不得只凭利润表判断财务质量。  
如果缺少附注和审计意见，应标注会计风险判断不完整。

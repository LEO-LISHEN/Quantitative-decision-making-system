# 输入结构

## 必填输入

- 公司名称或股票代码
- 上市市场或交易所
- 分析时间范围
- 信息源分析师整理出的证据底稿，或用户提供的公司材料

## 推荐输入

- 公司年报、招股书、定期报告或 10-K、20-F 等文件
- 公司官网、投资者关系材料、业绩会演示
- 研报中的业务拆分、市场份额、竞争格局和管理层战略
- 行业报告、产业链资料、竞争对手资料
- 用户提供的新闻、公告、调研纪要、管理层访谈
- 分业务收入、利润、毛利率和地区分布
- 客户、供应商、渠道、产品和价格信息

## 主动搜集输入

如果平台有搜索、数据库、知识库、插件或 API 工具，应主动补充：

- 公司主营业务和分部结构
- 主要产品、客户、供应商和销售渠道
- 行业竞争格局和主要竞争对手
- 市场份额、行业排名和增长空间
- 管理层战略、资本配置和历史执行记录
- 监管、政策、技术替代和产业链变化

## 输入字段建议

```json
{
  "company_name": "公司名称",
  "ticker": "股票代码",
  "market": "A股 | 港股 | 美股 | 其他",
  "exchange": "交易所",
  "time_range": "分析时间范围",
  "information_cutoff": "信息截止时间和时区",
  "source_evidence": {
    "verified_facts": ["已验证事实"],
    "medium_confidence_claims": ["中等可信信息"],
    "rumors_or_sentiment_only": ["仅供情绪参考的信息"],
    "missing_information": ["缺失信息"]
  },
  "business_materials": [
    {
      "type": "annual_report | prospectus | company_ir | research_report | industry_report | news | transcript | other",
      "source": "来源",
      "date": "日期",
      "content": "正文或摘要"
    }
  ],
  "research_focus": "用户关注的问题"
}
```

## 缺失输入处理

如果公司身份不明确，必须先要求补充。  
如果缺少分业务信息，应说明只能做初步判断。  
如果缺少行业和竞争对手资料，应主动搜索；无法搜索时，列出需要补充的信息。

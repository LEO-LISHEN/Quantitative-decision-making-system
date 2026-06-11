# 输入规范

## 最小输入

```json
{
  "company_name": "公司名称",
  "ticker": "股票代码",
  "market": "A股 / 港股 / 美股 / 中概股 / 其他",
  "analysis_date": "YYYY-MM-DD",
  "sentiment_window": "舆情分析时间窗口"
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
    "primary_listing": "主上市地"
  },
  "analysis_config": {
    "analysis_date": "YYYY-MM-DD",
    "sentiment_window": "最近7天 / 最近30天 / 财报前后 / 事件前后 / 自定义",
    "language_scope": ["中文", "英文", "其他"],
    "source_scope": ["股吧", "社交媒体", "新闻评论", "财经社区", "KOL", "搜索热度", "视频评论", "做空报告"],
    "focus_questions": ["需要重点回答的问题"]
  },
  "sentiment_sources": [
    {
      "source_name": "东方财富股吧 / 雪球 / X / Reddit / StockTwits / 富途 / 新闻评论等",
      "source_type": "正式披露 / 新闻媒体 / 专业分析 / 社区讨论 / KOL / 匿名爆料 / 用户评价 / 搜索热度",
      "url_or_reference": "链接或引用",
      "publish_time": "YYYY-MM-DD HH:mm:ss",
      "author_or_account": "作者或账号，如可得",
      "content": "原文或摘要",
      "engagement": {
        "views": 0,
        "comments": 0,
        "likes": 0,
        "shares": 0,
        "upvotes": 0
      },
      "claimed_fact": "该内容声称的事实",
      "opinion_or_emotion": "观点或情绪",
      "source_quality": "高 / 中 / 低 / 未知"
    }
  ],
  "aggregated_metrics": {
    "mention_count": "讨论量",
    "mention_change": "讨论量变化",
    "positive_ratio": "正面比例",
    "negative_ratio": "负面比例",
    "neutral_ratio": "中性比例",
    "search_trend": "搜索热度变化",
    "top_keywords": ["关键词"],
    "top_hashtags": ["标签"],
    "kol_posts": ["KOL 观点摘要"]
  },
  "event_and_price_context": {
    "recent_events": [
      {
        "date": "YYYY-MM-DD",
        "event": "事件",
        "event_direction": "正面 / 负面 / 中性 / 不确定"
      }
    ],
    "price_volume_summary": "近期价格和成交量摘要",
    "technical_analyst_output": "技术分析师输出摘要",
    "expectation_gap_output": "预期差分析师输出摘要"
  },
  "official_facts": {
    "announcements": ["公告摘要"],
    "financial_reports": ["财报/年报/半年报摘要"],
    "company_responses": ["公司回应"],
    "regulatory_disclosures": ["监管披露"]
  }
}
```

## 输入来源说明

- 如果用户提供原帖或评论，必须保留发布时间和来源平台。
- 如果用户只提供摘要，应标注为二手整理。
- 如果工作流使用舆情 API，应保留 API 统计口径和样本范围。
- 如果舆情涉及传闻、爆料、截图或群聊，应标注低可信并要求正式来源验证。
- 如果舆情涉及短期价格波动，应尽量提供对应日期的价格和成交量摘要。

## 缺失信息时必须要求补齐

如以下信息缺失，应明确要求补充：

- 舆情来源平台。
- 发布时间和时间窗口。
- 原始文本或可靠摘要。
- 样本数量和采样方法。
- 互动量或热度指标。
- 公司正式回应或公告。
- 近期价格和成交量变化。

## 输入质量评级

- `high`: 多平台、多语言、带时间戳、带互动量，并有正式披露可对照。
- `medium`: 有多个来源样本，但样本量或互动量不完整。
- `low`: 主要来自单一平台、少量评论或用户主观摘要。
- `insufficient`: 缺少原始内容、来源、时间或样本量，无法可靠判断舆情。

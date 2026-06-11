# 输出规范

## 标准输出结构

```json
{
  "analyst": "Sentiment_Public_Opinion_Analyst",
  "company": {
    "company_name": "公司名称",
    "ticker": "股票代码",
    "market": "市场",
    "exchange": "交易所",
    "analysis_date": "YYYY-MM-DD",
    "sentiment_window": "舆情时间窗口"
  },
  "source_map": {
    "overall_input_quality": "high / medium / low / insufficient",
    "sources_used": [
      {
        "source_name": "来源名称",
        "source_type": "正式披露 / 新闻媒体 / 专业分析 / 社区讨论 / KOL / 匿名爆料 / 用户评价 / 搜索热度",
        "sample_size": "样本量",
        "time_range": "时间范围",
        "credibility": "高 / 中 / 低",
        "bias_warning": "样本偏差提醒"
      }
    ],
    "missing_sources": ["缺失来源"],
    "sampling_limitations": ["样本限制"]
  },
  "narrative_map": {
    "main_narratives": [
      {
        "narrative": "主流叙事",
        "direction": "正面 / 负面 / 中性 / 分裂",
        "source_strength": "强 / 中 / 弱",
        "evidence_status": "已验证 / 部分验证 / 未验证 / 与事实冲突",
        "related_facts": ["对应事实或公告"]
      }
    ],
    "counter_narratives": ["反对叙事"],
    "emerging_topics": ["新兴话题"],
    "misreadings_or_distortions": ["误读或夸大"]
  },
  "sentiment_state": {
    "overall_sentiment": "恐慌 / 悲观 / 怀疑 / 中性 / 乐观 / 狂热 / 愤怒 / 困惑 / 高度分裂",
    "sentiment_change": "升温 / 降温 / 恶化 / 修复 / 稳定 / 无法判断",
    "discussion_heat": "极高 / 高 / 中 / 低 / 无法判断",
    "crowding_level": "拥挤 / 适中 / 冷清 / 无法判断",
    "disagreement_level": "高 / 中 / 低 / 无法判断",
    "confidence": "高 / 中 / 低"
  },
  "rumor_and_unverified_claims": [
    {
      "claim": "传闻或未证实说法",
      "source": "来源",
      "spread_level": "高 / 中 / 低",
      "credibility": "高 / 中 / 低 / 无法判断",
      "verification_status": "已验证 / 已证伪 / 待验证 / 无法验证",
      "required_verification": ["需要核验的材料"]
    }
  ],
  "short_term_price_impact": {
    "volatility_risk": "高 / 中 / 低 / 无法判断",
    "likely_directional_pressure": "正向 / 负向 / 双向波动 / 无明显方向 / 无法判断",
    "time_horizon": "盘中 / 1-3个交易日 / 1-2周 / 更长 / 无法判断",
    "amplification_channels": ["股吧刷屏 / KOL / 新闻标题 / 做空报告 / 期权 / 涨跌停 / 低流动性 / 其他"],
    "price_reaction_watchpoints": ["需要观察的价格或成交量信号"]
  },
  "contrarian_or_crowding_signals": {
    "contrarian_opportunity": "可能 / 不明显 / 否 / 无法判断",
    "overheated_risk": "高 / 中 / 低 / 无法判断",
    "capitulation_signal": "有 / 无 / 无法判断",
    "narrative_exhaustion": "有 / 无 / 无法判断",
    "reasoning": "理由"
  },
  "links_to_other_analysts": {
    "for_source_intelligence": ["需要核验的来源"],
    "for_expectation_gap": ["可能影响预期差的问题"],
    "for_technical_analyst": ["需要与价格成交量对照的舆情时间点"],
    "for_catalyst_analyst": ["舆论关注的潜在催化剂"],
    "for_risk_analyst": ["舆情风险和声誉风险"]
  },
  "handoff_to_master": {
    "summary": "给总控分析师的摘要",
    "sentiment_impact_on_final_view": "正面 / 负面 / 中性 / 不确定",
    "confidence": "高 / 中 / 低",
    "must_verify_before_recommendation": ["最终建议前必须核验的信息"]
  }
}
```

## 情绪状态定义

- `恐慌`: 大量讨论集中于崩盘、退市、造假、流动性危机或极端亏损。
- `悲观`: 主流讨论偏负面，但仍有理性分析空间。
- `怀疑`: 市场不完全相信利好或管理层说法。
- `中性`: 情绪没有明显方向。
- `乐观`: 主流讨论偏正面，但未明显失控。
- `狂热`: 热度极高，预期快速上升，可能出现拥挤风险。
- `愤怒`: 投资者对管理层、业绩、监管或事件有强烈负面情绪。
- `困惑`: 信息冲突严重，市场无法形成稳定叙事。
- `高度分裂`: 多空双方都有高强度论证，分歧本身可能带来波动。

## 来源可信度

- `高`: 正式披露、监管文件、公司回应、可核验的新闻原始来源。
- `中`: 主流媒体、专业分析、多个独立来源相互印证。
- `低`: 匿名爆料、群聊截图、单一 KOL、无来源传言、情绪化评论。

## 输出边界

可以输出短期波动风险、情绪风险和需要验证的信息。不能把舆情当作事实，也不能直接给最终买入、卖出或持有建议。

## 标准下游交接字段

每次输出末尾应包含：

```json
{
  "handoff_to_downstream": {
    "must_pass_to": ["02_Source_Intelligence_Analyst", "07_Market_Expectation_Gap_Analyst", "09_Catalyst_Event_Analyst", "12_Technical_Price_Volume_Analyst", "14_Risk_Disconfirmation_Short_Analyst", "01_Master_Valuation_Director"],
    "useful_for": ["03_Fundamental_Business_Analyst", "11_Growth_Emerging_Industries_Analyst"],
    "key_fields_to_pass": ["source_map", "narrative_map", "sentiment_state", "rumor_and_unverified_claims", "short_term_price_impact", "contrarian_or_crowding_signals", "links_to_other_analysts"],
    "confidence": "高 / 中 / 低",
    "missing_information": ["缺失舆情样本、时间戳或热度数据"],
    "blocking_issues": ["阻碍舆情判断或事实核验的问题"]
  }
}
```

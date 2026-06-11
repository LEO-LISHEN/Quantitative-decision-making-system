# 输出规范

## 标准输出结构

```json
{
  "analyst": "Technical_Price_Volume_Analyst",
  "company": {
    "company_name": "公司名称",
    "ticker": "股票代码",
    "market": "市场",
    "exchange": "交易所",
    "analysis_date": "YYYY-MM-DD",
    "information_cutoff": "YYYY-MM-DD"
  },
  "data_quality": {
    "data_mode": "uploaded_table / api / chart_screenshot / text_description",
    "quality_rating": "high / medium / low / insufficient",
    "lookback_days": 0,
    "price_adjustment": "前复权 / 后复权 / 不复权 / 未知",
    "has_volume": true,
    "has_amount": true,
    "has_benchmark": true,
    "has_event_timeline": true,
    "data_warnings": ["数据质量提醒"],
    "missing_fields": ["缺失字段"]
  },
  "trend_state": {
    "primary_trend": "上升趋势 / 下降趋势 / 震荡 / 筑底 / 反转 / 加速 / 衰竭 / 不清晰",
    "short_term_trend": "强 / 中 / 弱 / 不清晰",
    "medium_term_trend": "强 / 中 / 弱 / 不清晰",
    "trend_confidence": "高 / 中 / 低",
    "evidence": ["趋势证据"]
  },
  "moving_average_structure": {
    "ma_system": "多头排列 / 空头排列 / 粘合 / 反复穿越 / 无法判断",
    "price_vs_ma": "价格在主要均线上方 / 下方 / 附近 / 无法判断",
    "ma_slope": "上行 / 下行 / 走平 / 混乱",
    "distance_from_key_ma": "与关键均线距离",
    "interpretation": "均线含义"
  },
  "price_volume_behavior": {
    "volume_pattern": "放量上涨 / 缩量上涨 / 放量下跌 / 缩量下跌 / 量价背离 / 成交低迷 / 无法判断",
    "turnover_quality": "高 / 中 / 低 / 无法判断",
    "accumulation_or_distribution": "疑似吸筹 / 疑似派发 / 中性 / 无法判断",
    "abnormal_volume_days": ["异常成交日期"],
    "interpretation": "量价解读"
  },
  "support_resistance": {
    "support_zones": ["支撑区域"],
    "resistance_zones": ["阻力区域"],
    "gap_zones": ["缺口区域"],
    "volume_profile_or_congestion_zones": ["成交密集区或平台"],
    "invalid_level": "关键失效位"
  },
  "breakout_breakdown_quality": {
    "signal": "有效突破 / 假突破 / 回抽确认 / 有效跌破 / 假跌破 / 无明确信号",
    "price_confirmation": "强 / 中 / 弱 / 无",
    "volume_confirmation": "强 / 中 / 弱 / 无",
    "follow_through": "有延续 / 无延续 / 反向 / 观察中",
    "risk_of_false_signal": "高 / 中 / 低 / 无法判断"
  },
  "relative_strength": {
    "vs_market_index": "强于 / 弱于 / 持平 / 无法判断",
    "vs_industry_index": "强于 / 弱于 / 持平 / 无法判断",
    "vs_peers": "强于 / 弱于 / 持平 / 无法判断",
    "relative_strength_trend": "改善 / 恶化 / 稳定 / 无法判断",
    "evidence": ["相对强弱证据"]
  },
  "event_reaction": {
    "events_analyzed": [
      {
        "date": "YYYY-MM-DD",
        "event": "事件",
        "price_reaction": "上涨 / 下跌 / 横盘 / 跳空 / 反转 / 无法判断",
        "volume_reaction": "放量 / 缩量 / 正常 / 无法判断",
        "interpretation": "市场反应解释"
      }
    ],
    "overall_event_reaction": "正向确认 / 负向确认 / 利好不涨 / 利空不跌 / 中性 / 无法判断"
  },
  "technical_confirmation": {
    "status": "强确认 / 弱确认 / 中性 / 预警 / 反向否定 / 无法判断",
    "impact_on_investment_logic": "支持 / 部分支持 / 不影响 / 削弱 / 明显否定 / 无法判断",
    "timing_implication": "趋势友好 / 等待回调确认 / 等待突破确认 / 风险升高 / 避免追高 / 避免接飞刀 / 无法判断",
    "confidence": "高 / 中 / 低",
    "reasoning": "判断理由"
  },
  "risk_signals": {
    "technical_warning_signals": ["技术预警信号"],
    "failure_signals": ["技术失效信号"],
    "liquidity_risk": "高 / 中 / 低 / 无法判断",
    "volatility_risk": "高 / 中 / 低 / 无法判断"
  },
  "handoff_to_master": {
    "summary": "给总控分析师的摘要",
    "questions_for_other_analysts": ["需要其他分析师复核的问题"],
    "must_verify_before_final_recommendation": ["最终建议前必须验证的事项"]
  }
}
```

## 技术确认状态定义

- `强确认`: 趋势、量能、相对强弱和事件后反应都支持上游投资逻辑。
- `弱确认`: 价格有一定支持，但成交量、相对强弱或事件反应不够充分。
- `中性`: 没有明显支持，也没有明显否定。
- `预警`: 走势与乐观基本面或催化剂逻辑不匹配，需要复核风险。
- `反向否定`: 价格和量能持续否定投资逻辑，可能存在隐藏风险或市场不认可。
- `无法判断`: 数据不足、质量不合格或缺少关键基准。

## 数据质量评级

- `high`: 有完整日 K、成交量、成交额、复权口径、基准指数、事件时间线和异常交易说明。
- `medium`: 有完整日 K 和成交量，但基准、复权或事件信息不完整。
- `low`: 只有部分行情或图表截图，无法完整验证。
- `insufficient`: 缺少日 K 或成交量，无法可靠技术确认。

## 输出边界

输出可以包含择时含义和风险位，但不能直接给最终买入、卖出或持有建议。最终投资建议由总控分析师综合所有分析师结论后给出。

## 标准下游交接字段

每次输出末尾应包含：

```json
{
  "handoff_to_downstream": {
    "must_pass_to": ["07_Market_Expectation_Gap_Analyst", "14_Risk_Disconfirmation_Short_Analyst", "01_Master_Valuation_Director"],
    "useful_for": ["09_Catalyst_Event_Analyst", "13_Sentiment_Public_Opinion_Analyst"],
    "key_fields_to_pass": ["data_quality", "trend_state", "price_volume_behavior", "support_resistance", "relative_strength", "event_reaction", "technical_confirmation", "risk_signals"],
    "confidence": "高 / 中 / 低",
    "missing_information": ["缺失日K、成交量、复权或基准数据"],
    "blocking_issues": ["阻碍技术确认的问题"]
  }
}
```

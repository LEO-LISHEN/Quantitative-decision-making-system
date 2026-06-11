# 输出规范

## 标准输出结构

```json
{
  "analyst": "Master_Valuation_Director",
  "company": {
    "company_name": "公司名称",
    "ticker": "股票代码",
    "market": "市场",
    "exchange": "交易所",
    "analysis_date": "YYYY-MM-DD",
    "information_cutoff": "YYYY-MM-DD",
    "current_price": "当前价格",
    "currency": "货币"
  },
  "executive_conclusion": {
    "overall_recommendation": "买入 / 谨慎买入 / 持有 / 观望 / 减仓 / 卖出",
    "recommendation_confidence": "高 / 中 / 低",
    "one_sentence_view": "一句话结论",
    "fair_value_range": {
      "bear": "悲观估值",
      "base": "基准估值",
      "bull": "乐观估值",
      "preferred_range": "最终合理估值区间"
    },
    "upside_downside": {
      "to_base_case": "相对基准估值的潜在涨跌幅",
      "to_bull_case": "相对乐观估值的潜在涨幅",
      "to_bear_case": "相对悲观估值的潜在跌幅"
    },
    "risk_reward": "有吸引力 / 一般 / 偏差 / 不清晰"
  },
  "time_horizon_recommendations": {
    "short_term": {
      "time_window": "一周内或1-5个交易日",
      "recommendation": "买入 / 谨慎买入 / 持有 / 观望 / 减仓 / 卖出",
      "confidence": "高 / 中 / 低",
      "reasoning": "短期理由",
      "expected_realization_trigger": "短期兑现触发因素",
      "failure_signal": "短期失效信号"
    },
    "medium_term": {
      "time_window": "1个月至1年",
      "recommendation": "买入 / 谨慎买入 / 持有 / 观望 / 减仓 / 卖出",
      "confidence": "高 / 中 / 低",
      "reasoning": "中期理由",
      "expected_realization_trigger": "中期兑现触发因素",
      "failure_signal": "中期失效信号"
    },
    "long_term": {
      "time_window": "1年以上",
      "recommendation": "买入 / 谨慎买入 / 持有 / 观望 / 减仓 / 卖出",
      "confidence": "高 / 中 / 低",
      "reasoning": "长期理由",
      "expected_realization_trigger": "长期价值兑现因素",
      "failure_signal": "长期证伪条件"
    },
    "conflict_explanation": "如果不同周期建议不同，解释原因"
  },
  "information_quality": {
    "overall_quality": "高 / 中 / 低 / 不足",
    "source_confidence": "高 / 中 / 低",
    "missing_information": ["缺失信息"],
    "unverified_claims": ["未验证信息"],
    "key_limitations": ["结论限制"]
  },
  "integrated_analysis": {
    "investment_thesis": ["核心投资逻辑"],
    "business_quality": "基本面质量摘要",
    "financial_quality": "财务质量摘要",
    "industry_cycle": "行业与周期摘要",
    "growth_quality": "成长质量摘要",
    "earnings_revision": "盈利修正摘要",
    "valuation_view": "估值摘要",
    "expectation_gap": "预期差摘要",
    "catalysts": "催化剂摘要",
    "technical_confirmation": "技术确认摘要",
    "sentiment_view": "情绪舆情摘要",
    "risk_disconfirmation": "风险反证摘要"
  },
  "valuation_synthesis": {
    "valuation_methods_used": ["DCF / 相对估值 / SOTP / 概率加权 / 股息模型 / 资产价值 / 其他"],
    "methods_rejected": [
      {
        "method": "估值方法",
        "reason": "不适用原因"
      }
    ],
    "dcf_view": "DCF 结论",
    "relative_valuation_view": "相对估值结论",
    "other_valuation_view": "其他估值结论",
    "final_fair_value_range": "最终估值区间",
    "key_sensitivities": ["敏感假设"]
  },
  "scenario_analysis": {
    "bear_case": {
      "description": "悲观情景",
      "fair_value": "悲观估值",
      "probability": "概率",
      "key_assumptions": ["假设"]
    },
    "base_case": {
      "description": "基准情景",
      "fair_value": "基准估值",
      "probability": "概率",
      "key_assumptions": ["假设"]
    },
    "bull_case": {
      "description": "乐观情景",
      "fair_value": "乐观估值",
      "probability": "概率",
      "key_assumptions": ["假设"]
    }
  },
  "risk_and_disconfirmation": {
    "overall_risk_level": "低 / 中 / 高 / 严重",
    "top_risks": ["主要风险"],
    "risk_veto_triggered": "true / false",
    "risk_veto_reason": "风险否决原因",
    "disconfirmation_conditions": ["证伪条件"],
    "downside_path": "下行路径"
  },
  "tracking_plan": {
    "next_1_week": ["短期跟踪指标"],
    "next_1_to_12_months": ["中期跟踪指标"],
    "next_1_year_plus": ["长期跟踪指标"],
    "must_verify_before_action": ["行动前必须核验事项"]
  },
  "conflicts_and_judgment": {
    "analyst_conflicts": ["专项分析师之间的冲突"],
    "how_conflicts_were_resolved": "总控如何处理冲突",
    "confidence_downgrades": ["降低置信度的原因"]
  },
  "final_note": {
    "conditionality": "本建议成立的条件",
    "non_guarantee": "不保证收益或股价方向",
    "user_specific_limits": "未考虑或有限考虑用户个人风险偏好、仓位和税务等因素"
  }
}
```

## Markdown 报告结构

如果不输出 JSON，必须按以下结构输出：

1. 结论先行
2. 分周期建议
3. 信息质量
4. 核心投资逻辑
5. 基本面、财务、行业和成长
6. 估值区间和潜在涨跌幅
7. 预期差、盈利修正和催化剂
8. 技术与情绪确认
9. 风险反证和下行情景
10. 悲观、基准、乐观情景
11. 最终建议成立条件
12. 跟踪指标和证伪条件

## 硬性要求

- 必须给出短期、中期、长期分周期建议。
- 必须给出建议对应的预期兑现时间。
- 必须说明主要风险和证伪条件。
- 必须说明置信度。
- 信息不足时必须明确指出，并优先给出观望或低置信结论。

## 标准交付字段

总控分析师作为最终节点，输出末尾应包含：

```json
{
  "handoff_to_downstream": {
    "must_pass_to": ["用户最终报告", "归档系统"],
    "useful_for": ["后续复盘", "跟踪提醒", "再次分析的输入"],
    "key_fields_to_pass": ["overall_recommendation", "time_horizon_recommendations", "fair_value_range", "risk_and_disconfirmation", "tracking_plan"],
    "confidence": "高 / 中 / 低",
    "missing_information": ["缺失信息"],
    "blocking_issues": ["阻碍高置信最终建议的问题"]
  }
}
```

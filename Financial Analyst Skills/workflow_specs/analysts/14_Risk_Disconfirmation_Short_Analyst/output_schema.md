# 输出规范

## 标准输出结构

```json
{
  "analyst": "Risk_Disconfirmation_Short_Analyst",
  "company": {
    "company_name": "公司名称",
    "ticker": "股票代码",
    "market": "市场",
    "exchange": "交易所",
    "analysis_date": "YYYY-MM-DD",
    "information_cutoff": "YYYY-MM-DD"
  },
  "input_quality": {
    "overall_rating": "high / medium / low / insufficient",
    "key_sources_used": ["来源"],
    "missing_sources": ["缺失来源"],
    "verification_limitations": ["核验限制"]
  },
  "thesis_under_review": {
    "bull_thesis": "被检验的核心多头逻辑",
    "key_assumptions": [
      {
        "assumption": "关键假设",
        "valuation_variable": "收入 / 利润率 / 现金流 / 倍数 / 折现率 / 催化剂 / 其他",
        "importance": "高 / 中 / 低",
        "current_evidence": "支持证据"
      }
    ]
  },
  "risk_map": [
    {
      "risk_name": "风险名称",
      "risk_type": "商业 / 财务 / 会计 / 监管 / 法律 / 治理 / 竞争 / 技术 / 估值 / 流动性 / 舆情 / 市场技术 / 宏观 / 其他",
      "status": "已发生 / 潜在 / 传闻 / 情绪放大 / 已证伪",
      "evidence_grade": "已证实 / 高可信 / 待验证 / 低可信 / 已证伪",
      "probability": "高 / 中 / 低 / 无法判断",
      "severity": "低 / 中 / 高 / 严重",
      "time_horizon": "短期 / 未来12个月 / 未来2-3年 / 长期 / 无法判断",
      "evidence": ["证据"],
      "valuation_impact_path": "如何影响收入、利润率、现金流、倍数、融资或风险溢价",
      "mitigating_factors": ["缓释因素"],
      "required_verification": ["需要核验的材料"]
    }
  ],
  "disconfirmation_matrix": [
    {
      "assumption": "多头关键假设",
      "confirming_evidence": ["支持证据"],
      "disconfirming_evidence": ["反证或削弱证据"],
      "early_warning_indicators": ["早期预警指标"],
      "failure_trigger": "逻辑失效触发条件",
      "current_status": "仍成立 / 被削弱 / 高风险 / 已失效 / 无法判断"
    }
  ],
  "short_thesis_view": {
    "strongest_short_argument": "最强做空/反方论点",
    "evidence_supporting_short_view": ["支持反方的证据"],
    "weaknesses_in_short_view": ["反方论点的弱点或尚未验证之处"],
    "company_response": ["公司回应或澄清"],
    "fairness_check": "是否区分事实、指控、推断和传闻"
  },
  "downside_scenarios": {
    "bear_case": {
      "description": "悲观情景",
      "key_assumptions": ["假设"],
      "valuation_impact": "估值影响",
      "probability": "概率",
      "severity": "低 / 中 / 高 / 严重"
    },
    "stress_case": {
      "description": "压力情景",
      "key_assumptions": ["假设"],
      "valuation_impact": "估值影响",
      "probability": "概率",
      "severity": "低 / 中 / 高 / 严重"
    }
  },
  "early_warning_dashboard": {
    "financial_indicators": ["财务预警指标"],
    "operating_indicators": ["经营预警指标"],
    "market_indicators": ["市场交易预警指标"],
    "sentiment_indicators": ["舆情预警指标"],
    "regulatory_or_legal_indicators": ["监管/法律预警指标"]
  },
  "risk_summary": {
    "overall_risk_level": "低 / 中 / 高 / 严重",
    "core_thesis_status": "仍成立 / 被削弱 / 高风险 / 已失效 / 无法判断",
    "most_important_risks": ["最重要风险"],
    "risks_likely_priced_in": ["可能已被定价的风险"],
    "risks_not_priced_in": ["可能未被充分定价的风险"],
    "confidence": "高 / 中 / 低"
  },
  "handoff_to_master": {
    "summary": "给总控分析师的摘要",
    "impact_on_final_view": "正面 / 中性 / 负面 / 严重负面 / 不确定",
    "must_verify_before_recommendation": ["最终建议前必须核验的事项"],
    "questions_for_other_analysts": ["需要其他分析师复核的问题"]
  }
}
```

## 输出边界

可以输出风险等级、下行情景、反证条件和风险对估值的影响。不能把未经验证的指控写成事实，不能直接给最终买入、卖出、持有或做空建议。

## 标准下游交接字段

每次输出末尾应包含：

```json
{
  "handoff_to_downstream": {
    "must_pass_to": ["01_Master_Valuation_Director"],
    "useful_for": ["03_Fundamental_Business_Analyst", "04_Financial_Statements_Quality_Analyst", "05_DCF_Intrinsic_Value_Analyst", "08_Earnings_Forecast_Revision_Analyst", "09_Catalyst_Event_Analyst"],
    "key_fields_to_pass": ["risk_map", "disconfirmation_matrix", "short_thesis_view", "downside_scenarios", "early_warning_dashboard", "risk_summary", "handoff_to_master"],
    "confidence": "高 / 中 / 低",
    "missing_information": ["缺失风险核验材料"],
    "blocking_issues": ["必须在最终建议前核验的问题"]
  }
}
```

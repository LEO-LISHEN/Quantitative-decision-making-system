# 输出结构

## 标准输出字段

```json
{
  "company_identification": {
    "company_name": "公司名称",
    "ticker": "股票代码",
    "market": "上市市场",
    "exchange": "交易所",
    "industry": "行业",
    "information_cutoff": "信息截止时间"
  },
  "industry_classification": {
    "industry_type": "非周期/弱周期 | 传统周期 | 库存周期 | 产能周期 | 利率/信用周期 | 政策周期 | 技术周期 | 消费周期 | 监管周期 | 多周期叠加",
    "cycle_exists": true,
    "cycle_regularity": "规律 | 不规则 | 结构性上行 | 结构性下行 | 一次性冲击 | 无法判断",
    "main_cycle_drivers": ["周期驱动因素"]
  },
  "cycle_stage_assessment": {
    "current_stage": "结构性成长 | 景气上行 | 景气高位 | 边际转弱 | 下行 | 筑底 | 早期复苏 | 结构性衰退 | 无法判断",
    "evidence": ["证据"],
    "confidence": "高 | 中 | 低"
  },
  "demand_supply_analysis": {
    "demand": "需求分析",
    "supply": "供给分析",
    "inventory": "库存分析",
    "capacity": "产能分析",
    "pricing": "价格分析",
    "utilization": "开工率/产能利用率"
  },
  "cycle_indicators": {
    "leading_indicators": ["领先指标"],
    "lagging_indicators": ["滞后指标"],
    "indicators_to_track": ["后续跟踪指标"]
  },
  "multi_cycle_overlay": [
    {
      "cycle_type": "周期类型",
      "stage": "阶段",
      "impact": "影响"
    }
  ],
  "company_cycle_sensitivity": {
    "sensitivity": "高度敏感 | 中度敏感 | 低度敏感 | 反周期",
    "reasons": ["原因"],
    "mitigating_factors": ["缓冲因素"]
  },
  "earnings_and_margin_implications": {
    "revenue": "对收入的影响",
    "margin": "对利润率的影响",
    "cash_flow": "对现金流的影响",
    "normalized_earnings_needed": true,
    "normalized_earnings_comment": "正常化盈利说明"
  },
  "valuation_implications": {
    "dcf": "对 DCF 的影响",
    "relative_valuation": "对相对估值的影响",
    "multiples": "估值倍数含义",
    "risk_premium": "风险溢价含义"
  },
  "cycle_risks": ["周期风险"],
  "disconfirming_evidence": ["会改变周期判断的证据"],
  "questions_for_downstream_analysts": ["需要下游分析师验证的问题"],
  "guidance_for_master_director": "总控分析师应如何使用该行业周期结论"
}
```

## 输出要求

- 必须先判断行业是否存在周期。
- 必须说明周期类型和周期是否规律。
- 必须说明公司对周期的敏感度。
- 必须说明是否需要正常化盈利。
- 不直接给最终买卖建议。
## 标准下游交接字段

每次输出末尾应包含：

```json
{
  "handoff_to_downstream": {
    "must_pass_to": ["05_DCF_Intrinsic_Value_Analyst", "06_Relative_Valuation_Comps_Analyst", "08_Earnings_Forecast_Revision_Analyst", "09_Catalyst_Event_Analyst", "14_Risk_Disconfirmation_Short_Analyst", "01_Master_Valuation_Director"],
    "useful_for": ["03_Fundamental_Business_Analyst", "11_Growth_Emerging_Industries_Analyst"],
    "key_fields_to_pass": ["industry_classification", "cycle_existence", "cycle_type", "current_cycle_stage", "leading_indicators", "company_cycle_sensitivity", "normalized_earnings_implication", "valuation_impact"],
    "confidence": "高 / 中 / 低",
    "missing_information": ["缺失行业或周期数据"],
    "blocking_issues": ["阻碍周期判断的问题"]
  }
}
```

# 输出结构

## 标准输出字段

```json
{
  "company_identification": {
    "company_name": "公司名称",
    "ticker": "股票代码",
    "market": "上市市场",
    "exchange": "交易所",
    "currency": "估值币种",
    "information_cutoff": "信息截止时间"
  },
  "market_valuation_anchor": {
    "primary_anchor": "P/E | EV/EBITDA | P/B | P/S | EV/Sales | P/FCF | NAV | SOTP | 股息率 | 其他",
    "reason": "市场为什么可能使用该估值锚",
    "secondary_anchors": ["辅助估值锚"]
  },
  "comparable_universe": [
    {
      "company_name": "可比公司",
      "ticker": "代码",
      "market": "市场",
      "comparability_score": "高 | 中 | 低",
      "inclusion_reason": "纳入原因",
      "limitations": "可比性限制"
    }
  ],
  "comps_quality_assessment": {
    "overall_quality": "高 | 中 | 低",
    "enough_reliable_comps": true,
    "limitations": ["限制"]
  },
  "multiple_selection": [
    {
      "multiple": "估值倍数",
      "suitability": "适合 | 辅助 | 不适合",
      "reason": "适用原因"
    }
  ],
  "multiple_basis_check": {
    "period": "静态 | TTM | Forward",
    "earnings_basis": "GAAP | non-GAAP | 归母 | 扣非 | adjusted",
    "ev_adjustments": "EV 调整说明",
    "currency_consistency": "币种一致性",
    "one_off_adjustments": "一次性项目处理",
    "accounting_differences": "会计准则差异"
  },
  "peer_valuation_range": {
    "low": "同行低位",
    "median": "同行中位",
    "high": "同行高位",
    "notes": "说明"
  },
  "historical_valuation_range": {
    "lookback_period": "3年 | 5年 | 10年",
    "current_percentile": "当前历史分位",
    "comparability_comment": "历史区间是否可比"
  },
  "premium_discount_assessment": {
    "conclusion": "应享受溢价 | 接近同行 | 应当折价 | 暂无法判断",
    "premium_reasons": ["溢价理由"],
    "discount_reasons": ["折价理由"],
    "fair_multiple_range": "合理倍数区间"
  },
  "implied_valuation": {
    "equity_value_range": "股权价值区间",
    "per_share_value_range": "每股价值区间，数据不足则标注无法可靠计算",
    "key_driver": "使用的价值驱动因素"
  },
  "sotp_valuation": {
    "is_applicable": false,
    "segments": [],
    "holding_company_discount": "控股公司折价",
    "net_debt_and_cash_adjustment": "净债务和现金调整"
  },
  "cross_check_with_dcf": {
    "dcf_available": false,
    "consistency": "一致 | 偏高 | 偏低 | 无法比较",
    "comment": "与 DCF 的交叉验证"
  },
  "rerating_or_derating_conditions": {
    "rerating_conditions": ["估值重估条件"],
    "derating_conditions": ["估值下修条件"]
  },
  "data_gaps": ["数据缺口"],
  "confidence_level": "高 | 中 | 低",
  "guidance_for_master_director": "总控分析师应如何使用该相对估值结论"
}
```

## 输出要求

- 如果没有足够可靠的可比公司，必须说明相对估值只能作为辅助参考。
- 必须输出倍数口径校验。
- 必须说明公司应溢价、平价或折价的原因。
- 必须说明市场估值锚。
- 不直接给最终买卖建议。

## 标准下游交接字段

每次输出末尾应包含：

```json
{
  "handoff_to_downstream": {
    "must_pass_to": ["07_Market_Expectation_Gap_Analyst", "14_Risk_Disconfirmation_Short_Analyst", "01_Master_Valuation_Director"],
    "useful_for": ["09_Catalyst_Event_Analyst"],
    "key_fields_to_pass": ["comps_quality_assessment", "market_valuation_anchor", "peer_valuation_range", "historical_valuation_range", "premium_discount_assessment", "implied_valuation", "rerating_or_derating_conditions", "data_gaps"],
    "confidence": "高 / 中 / 低",
    "missing_information": ["缺失估值或可比公司数据"],
    "blocking_issues": ["阻碍相对估值可靠性的问题"]
  }
}
```

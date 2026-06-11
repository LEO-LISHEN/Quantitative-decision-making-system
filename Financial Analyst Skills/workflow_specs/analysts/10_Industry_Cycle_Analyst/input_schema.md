# 输入结构

## 必填输入

- 公司名称或股票代码
- 上市市场或交易所
- 公司所属行业或主要业务
- 信息截止时间
- 至少一种行业、价格、供需、政策或财务材料

## 推荐输入

- 信息源分析师输出的行业新闻、政策、价格、供需和事件时间线
- 基本面分析师输出的产业链位置、竞争格局和商业模式
- 财务分析师输出的收入、利润率、存货、资本开支、在建工程和现金流
- 盈利预测分析师输出的收入、价格、成本和利润率修正判断
- 催化剂分析师输出的政策、涨价、库存去化和供给收缩事件
- 相对估值分析师输出的行业估值中枢和景气度对应倍数

## 主动搜集输入

如果平台提供搜索、行业数据库、宏观数据、商品价格、政策或 API，应主动搜集：

- 行业价格
- 库存
- 开工率
- 产能和新增产能
- 产能利用率
- 订单
- PMI 或行业景气指数
- 销售数据
- 进出口
- 资本开支
- 行业亏损比例
- 政策文件
- 利率和信用数据
- 竞争对手扩产、减产或退出

## 输入字段建议

```json
{
  "company_name": "公司名称",
  "ticker": "股票代码",
  "market": "A股 | 港股 | 美股 | 其他",
  "exchange": "交易所",
  "industry": "行业",
  "business_segments": ["业务板块"],
  "information_cutoff": "信息截止时间",
  "industry_data": {
    "demand": [],
    "supply": [],
    "inventory": [],
    "price": [],
    "capacity": [],
    "utilization": [],
    "orders": [],
    "capex": [],
    "policy": [],
    "macro": [],
    "technology": []
  },
  "company_exposure": {
    "revenue_by_segment": [],
    "cost_structure": [],
    "pricing_power": "定价权",
    "contracts": "长协/锁价/订单情况",
    "balance_sheet_resilience": "资产负债表韧性"
  },
  "prior_outputs": {
    "fundamental_business": {},
    "financial_quality": {},
    "earnings_revision": {},
    "catalyst": {},
    "relative_valuation": {}
  }
}
```

## 缺失输入处理

如果缺少行业价格和库存，不能高置信判断商品或周期行业位置。  
如果缺少产能数据，不能高置信判断供给周期。  
如果缺少政策信息，不能高置信判断政策周期。  
如果缺少历史行业数据，不能判断周期是否规律。  
如果缺少公司分业务收入，不能可靠判断公司周期敏感度。

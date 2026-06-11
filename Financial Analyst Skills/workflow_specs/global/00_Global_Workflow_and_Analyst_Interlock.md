# 全局工作流与分析师联动协议

## 文件目标

本文件定义整套金融分析师配置包的协作方式，解决三个问题：

- 各分析师按什么顺序工作。
- 哪些分析师的输出必须传给哪些下游分析师。
- 总控分析师如何基于专项分析师结果形成最终估值、全面分析和操作建议。

本系统的目标不是让每个分析师各自独立输出观点，而是形成一条可追溯、可复核、可迁移到 GPTs、Coze、Dify 或 API 工作流的多分析师链路。

## 总体原则

- 所有分析师都必须尊重 `02_Source_Intelligence_Analyst` 的证据质量判断。
- 所有专项分析师不直接给最终买入、卖出或持有建议，最终建议由 `01_Master_Valuation_Director` 统一给出。
- 最终建议必须说明预期兑现时间和大致持仓周期，至少区分短期、中期和长期。
- 如果关键数据缺失，下游分析师必须降低置信度，并明确要求补充信息。
- 如果上游结论冲突，下游分析师必须标注冲突点，而不是强行平均。
- 如果风险反证分析师发现核心逻辑被破坏，总控分析师必须重新审视最终建议。
- 舆情、传闻、KOL、股吧、社交媒体信息可以作为线索，但必须经过可信度标注或核验，不能直接作为事实。

## 分析师清单

- `01_Master_Valuation_Director`：综合估值投研总监。
- `02_Source_Intelligence_Analyst`：信息源整理与可信度分析师。
- `03_Fundamental_Business_Analyst`：基本面与商业模式分析师。
- `04_Financial_Statements_Quality_Analyst`：财务报表与质量分析师。
- `05_DCF_Intrinsic_Value_Analyst`：DCF 内在价值分析师。
- `06_Relative_Valuation_Comps_Analyst`：相对估值与可比公司分析师。
- `07_Market_Expectation_Gap_Analyst`：市场预期差分析师。
- `08_Earnings_Forecast_Revision_Analyst`：盈利预测与业绩修正分析师。
- `09_Catalyst_Event_Analyst`：事件催化剂分析师。
- `10_Industry_Cycle_Analyst`：行业与周期分析师。
- `11_Growth_Emerging_Industries_Analyst`：成长股与新兴产业分析师。
- `12_Technical_Price_Volume_Analyst`：量价趋势与技术确认分析师。
- `13_Sentiment_Public_Opinion_Analyst`：情绪、舆情与股吧分析师。
- `14_Risk_Disconfirmation_Short_Analyst`：风险、反证与做空视角分析师。

## 推荐执行顺序

### 第 0 阶段：任务定义

执行者：

- `01_Master_Valuation_Director`

任务：

- 确认公司名称、股票代码、市场、交易所、分析日期。
- 确认用户目标：估值、全面分析、买卖建议、风险检查或某个专项问题。
- 确认用户关注的投资周期：短期交易、中期波段、长期持有，或需要三种周期都输出。
- 确认可用材料：财报、研报、新闻、公告、行情表、社交媒体、股吧、API 数据等。
- 确认缺失材料和是否允许主动搜索。
- 确认最终输出是否需要操作建议。

输出给：

- `02_Source_Intelligence_Analyst`
- 所有后续专项分析师

### 第 1 阶段：信息源与可信度

执行者：

- `02_Source_Intelligence_Analyst`

任务：

- 整理所有材料来源。
- 标注来源等级、时间戳、冲突信息、缺失信息。
- 区分正式披露、研报、新闻、社交媒体、股吧、传闻、行情数据和 API 数据。

硬依赖下游：

- 所有分析师。

关键传递字段：

- `source_quality`
- `evidence_grade`
- `information_cutoff`
- `source_conflicts`
- `missing_information`
- `unverified_claims`

### 第 2 阶段：经营事实与基本质量

可并行执行：

- `03_Fundamental_Business_Analyst`
- `04_Financial_Statements_Quality_Analyst`
- `10_Industry_Cycle_Analyst`
- `11_Growth_Emerging_Industries_Analyst`

任务：

- 判断公司是不是好生意。
- 判断财报和现金流是否可靠。
- 判断行业是否存在周期、当前处于什么阶段。
- 判断成长故事是否真实、可持续、可估值。

主要下游：

- `05_DCF_Intrinsic_Value_Analyst`
- `06_Relative_Valuation_Comps_Analyst`
- `08_Earnings_Forecast_Revision_Analyst`
- `09_Catalyst_Event_Analyst`
- `14_Risk_Disconfirmation_Short_Analyst`
- `01_Master_Valuation_Director`

### 第 3 阶段：盈利预测与假设修正

执行者：

- `08_Earnings_Forecast_Revision_Analyst`

上游输入：

- `02` 信息源可信度。
- `03` 商业模式和收入驱动。
- `04` 历史财务和财务质量。
- `10` 行业周期和景气阶段。
- `11` 成长假设和关键里程碑。

任务：

- 判断收入、利润率、EPS、自由现金流是否可能上修、下修或保持稳定。
- 输出未来短期、中期和长期预测修正方向。

主要下游：

- `05_DCF_Intrinsic_Value_Analyst`
- `06_Relative_Valuation_Comps_Analyst`
- `07_Market_Expectation_Gap_Analyst`
- `09_Catalyst_Event_Analyst`
- `14_Risk_Disconfirmation_Short_Analyst`
- `01_Master_Valuation_Director`

### 第 4 阶段：估值

可并行执行：

- `05_DCF_Intrinsic_Value_Analyst`
- `06_Relative_Valuation_Comps_Analyst`

上游输入：

- `02` 证据质量。
- `03` 商业质量。
- `04` 财务可靠性。
- `08` 盈利预测修正。
- `10` 行业周期。
- `11` 成长假设。

任务：

- `05` 先判断是否适合 DCF，再输出内在价值区间、情景和敏感性。
- `06` 输出同行估值、历史估值、溢价/折价和市场估值锚。

主要下游：

- `07_Market_Expectation_Gap_Analyst`
- `14_Risk_Disconfirmation_Short_Analyst`
- `01_Master_Valuation_Director`

### 第 5 阶段：预期差与催化剂

可并行执行，但需要互相参考：

- `07_Market_Expectation_Gap_Analyst`
- `09_Catalyst_Event_Analyst`

上游输入：

- `02` 信息时间线和可信度。
- `05` DCF 估值区间和敏感假设。
- `06` 相对估值和市场锚。
- `08` 盈利修正方向。
- `12` 价格和成交量反应，如已有。
- `13` 市场讨论和舆情线索，如已有。

任务：

- `07` 判断新信息与市场定价之间是否存在预期差。
- `09` 判断未来事件是否可能推动价值兑现或风险释放。

主要下游：

- `12_Technical_Price_Volume_Analyst`
- `13_Sentiment_Public_Opinion_Analyst`
- `14_Risk_Disconfirmation_Short_Analyst`
- `01_Master_Valuation_Director`

### 第 6 阶段：市场交易与情绪确认

可并行执行：

- `12_Technical_Price_Volume_Analyst`
- `13_Sentiment_Public_Opinion_Analyst`

上游输入：

- `02` 数据可信度。
- `07` 预期差结论和信息时间线。
- `09` 催化剂日期和事件路径。
- `05/06` 估值位置。
- 价格、成交量、日 K、行业指数、舆情样本、社交媒体和股吧数据。

任务：

- `12` 判断交易行为是否确认、削弱或否定投资逻辑。
- `13` 判断舆情、叙事、拥挤度和短期价格波动风险。

主要下游：

- `07_Market_Expectation_Gap_Analyst`，用于回流复核是否已定价。
- `09_Catalyst_Event_Analyst`，用于判断舆论是否放大催化剂。
- `14_Risk_Disconfirmation_Short_Analyst`
- `01_Master_Valuation_Director`

### 第 7 阶段：风险反证

执行者：

- `14_Risk_Disconfirmation_Short_Analyst`

上游输入：

- 所有前置分析师输出。

任务：

- 检验核心多头逻辑。
- 找出反证、风险、下行情景和逻辑失效触发条件。
- 区分事实、指控、推断、传闻和情绪表达。
- 判断风险是否会破坏估值假设。

主要下游：

- `01_Master_Valuation_Director`

### 第 8 阶段：总控综合

执行者：

- `01_Master_Valuation_Director`

任务：

- 整合所有专项分析师输出。
- 形成合理估值区间、风险收益比、关键前提和最终建议。
- 输出建议类型：买入、谨慎买入、持有、观望、减仓或卖出。
- 输出分周期建议：短期、中期、长期分别给出建议、理由、兑现条件和失效信号。

## 分析师之间的传递矩阵

### 02 信息源整理与可信度分析师

必须传给：

- 所有分析师。

关键字段：

- 来源等级。
- 信息截止时间。
- 关键事实。
- 冲突信息。
- 未验证信息。
- 缺失信息。
- 置信度。

### 03 基本面与商业模式分析师

必须传给：

- `05_DCF_Intrinsic_Value_Analyst`
- `06_Relative_Valuation_Comps_Analyst`
- `08_Earnings_Forecast_Revision_Analyst`
- `09_Catalyst_Event_Analyst`
- `14_Risk_Disconfirmation_Short_Analyst`
- `01_Master_Valuation_Director`

可参考传给：

- `07_Market_Expectation_Gap_Analyst`
- `11_Growth_Emerging_Industries_Analyst`

关键字段：

- 商业模式质量。
- 收入和利润驱动。
- 护城河。
- 客户和供应链风险。
- ROIC 和利润率含义。
- 估值溢价或折价理由。

### 04 财务报表与质量分析师

必须传给：

- `05_DCF_Intrinsic_Value_Analyst`
- `06_Relative_Valuation_Comps_Analyst`
- `08_Earnings_Forecast_Revision_Analyst`
- `14_Risk_Disconfirmation_Short_Analyst`
- `01_Master_Valuation_Director`

可参考传给：

- `03_Fundamental_Business_Analyst`
- `11_Growth_Emerging_Industries_Analyst`

关键字段：

- 财务数据完整性。
- 财务质量评级。
- 收入、利润和现金流趋势。
- 会计口径和调整项。
- 盈利质量风险。
- 发展计划的财务验证。

### 05 DCF 内在价值分析师

必须传给：

- `07_Market_Expectation_Gap_Analyst`
- `14_Risk_Disconfirmation_Short_Analyst`
- `01_Master_Valuation_Director`

可参考传给：

- `09_Catalyst_Event_Analyst`

关键字段：

- 是否适合 DCF。
- DCF 估值区间。
- 悲观、基准、乐观情景。
- WACC、终值、增长率、利润率敏感性。
- 最脆弱的估值假设。

### 06 相对估值与可比公司分析师

必须传给：

- `07_Market_Expectation_Gap_Analyst`
- `14_Risk_Disconfirmation_Short_Analyst`
- `01_Master_Valuation_Director`

可参考传给：

- `09_Catalyst_Event_Analyst`

关键字段：

- 可比公司质量。
- 当前估值倍数。
- 历史估值分位。
- 同行溢价或折价。
- 市场估值锚。
- 倍数压缩或修复空间。

### 07 市场预期差分析师

必须传给：

- `09_Catalyst_Event_Analyst`
- `12_Technical_Price_Volume_Analyst`
- `13_Sentiment_Public_Opinion_Analyst`
- `14_Risk_Disconfirmation_Short_Analyst`
- `01_Master_Valuation_Director`

可回流参考：

- `05_DCF_Intrinsic_Value_Analyst`
- `06_Relative_Valuation_Comps_Analyst`
- `08_Earnings_Forecast_Revision_Analyst`

关键字段：

- 新信息类型。
- 是否已定价。
- 正向或负向预期差。
- 市场反应证据。
- 需要价格和成交量验证的时间点。

### 08 盈利预测与业绩修正分析师

必须传给：

- `05_DCF_Intrinsic_Value_Analyst`
- `06_Relative_Valuation_Comps_Analyst`
- `07_Market_Expectation_Gap_Analyst`
- `09_Catalyst_Event_Analyst`
- `14_Risk_Disconfirmation_Short_Analyst`
- `01_Master_Valuation_Director`

关键字段：

- 盈利预测修正方向。
- 收入、利润率、EPS、自由现金流影响。
- 修正时间窗口。
- 盈利修正质量。
- 上修或下修概率。
- 领先指标。

### 09 事件催化剂分析师

必须传给：

- `07_Market_Expectation_Gap_Analyst`
- `12_Technical_Price_Volume_Analyst`
- `13_Sentiment_Public_Opinion_Analyst`
- `14_Risk_Disconfirmation_Short_Analyst`
- `01_Master_Valuation_Director`

关键字段：

- 催化剂日历。
- 事件概率。
- 影响路径。
- 正面、负面或不确定催化剂。
- 是否已被市场预期。
- 确认信号和失败信号。

### 10 行业与周期分析师

必须传给：

- `05_DCF_Intrinsic_Value_Analyst`
- `06_Relative_Valuation_Comps_Analyst`
- `08_Earnings_Forecast_Revision_Analyst`
- `09_Catalyst_Event_Analyst`
- `14_Risk_Disconfirmation_Short_Analyst`
- `01_Master_Valuation_Director`

可参考传给：

- `03_Fundamental_Business_Analyst`
- `11_Growth_Emerging_Industries_Analyst`

关键字段：

- 行业是否存在周期。
- 周期类型。
- 当前景气阶段。
- 领先指标。
- 公司周期敏感度。
- 正常化盈利假设。
- 对估值倍数和盈利预测的影响。

### 11 成长股与新兴产业分析师

必须传给：

- `05_DCF_Intrinsic_Value_Analyst`
- `06_Relative_Valuation_Comps_Analyst`
- `08_Earnings_Forecast_Revision_Analyst`
- `09_Catalyst_Event_Analyst`
- `14_Risk_Disconfirmation_Short_Analyst`
- `01_Master_Valuation_Director`

可参考传给：

- `07_Market_Expectation_Gap_Analyst`
- `13_Sentiment_Public_Opinion_Analyst`

关键字段：

- 成长叙事。
- 证据等级。
- TAM/SAM/SOM。
- 商业化验证。
- 单位经济模型。
- 情景概率。
- 成长溢价或折价理由。
- 关键里程碑和证伪条件。

### 12 量价趋势与技术确认分析师

必须传给：

- `07_Market_Expectation_Gap_Analyst`
- `14_Risk_Disconfirmation_Short_Analyst`
- `01_Master_Valuation_Director`

可参考传给：

- `09_Catalyst_Event_Analyst`
- `13_Sentiment_Public_Opinion_Analyst`

关键字段：

- 数据质量。
- 趋势状态。
- 量价关系。
- 相对强弱。
- 事件后价格反应。
- 技术确认状态。
- 技术失效信号。

### 13 情绪、舆情与股吧分析师

必须传给：

- `02_Source_Intelligence_Analyst`
- `07_Market_Expectation_Gap_Analyst`
- `09_Catalyst_Event_Analyst`
- `12_Technical_Price_Volume_Analyst`
- `14_Risk_Disconfirmation_Short_Analyst`
- `01_Master_Valuation_Director`

关键字段：

- 主流叙事。
- 反对叙事。
- 情绪状态。
- 讨论热度。
- 传闻和未验证信息。
- 短期价格波动风险。
- 需要核验的线索。

### 14 风险、反证与做空视角分析师

必须读取：

- 所有前置分析师输出。

必须传给：

- `01_Master_Valuation_Director`

可回流触发：

- `03_Fundamental_Business_Analyst`
- `04_Financial_Statements_Quality_Analyst`
- `05_DCF_Intrinsic_Value_Analyst`
- `08_Earnings_Forecast_Revision_Analyst`
- `09_Catalyst_Event_Analyst`

关键字段：

- 风险地图。
- 反证矩阵。
- 做空视角最强论点。
- 下行情景。
- 早期预警指标。
- 核心逻辑状态。
- 风险等级。
- 最终建议前必须核验的事项。

## 回流机制

以下情况应触发回流，而不是直接进入最终结论：

### 舆情线索回流

触发条件：

- `13` 发现高传播传闻、匿名爆料、KOL 强观点、做空报告扩散。

回流路径：

```text
13 舆情分析师 -> 02 信息源分析师 -> 07/09/12/14
```

目的：

- 先核验可信度，再判断是否影响预期差、催化剂、技术面和风险。

### 价格异动回流

触发条件：

- `12` 发现重大事件后放量上涨、放量下跌、利好不涨、利空不跌、持续相对弱势。

回流路径：

```text
12 技术分析师 -> 07 市场预期差分析师 -> 14 风险分析师
```

目的：

- 判断市场是否已定价，或是否存在隐藏风险。

### 风险反证回流

触发条件：

- `14` 判断核心假设被削弱、高风险或已失效。

回流路径：

```text
14 风险分析师 -> 03/04/05/08/09 -> 01 总控分析师
```

目的：

- 重新检查商业模式、财务数据、估值假设、盈利预测和催化剂路径。

## 标准下游交接字段

每个分析师输出中都建议包含：

```json
{
  "handoff_to_downstream": {
    "must_pass_to": ["必须传给哪些分析师"],
    "useful_for": ["可作为参考的分析师"],
    "key_fields_to_pass": ["需要传递的关键字段"],
    "confidence": "高 / 中 / 低",
    "missing_information": ["缺失信息"],
    "blocking_issues": ["会阻碍下游高置信分析的问题"]
  }
}
```

如果平台不支持结构化字段，也应在 Markdown 输出中保留同等内容。

## 置信度传递规则

- 上游证据质量低，下游不得输出高置信结论。
- 财务质量低，DCF 和盈利预测必须降置信度。
- 行情数据缺失，预期差和技术分析必须降置信度。
- 舆情样本不足，不能判断整体市场情绪。
- 风险证据未验证，必须标注为待验证，不能写成事实。
- 如果多个核心分析师结论冲突，总控必须保留冲突，而不是强行给出确定结论。

## 风险否决机制

出现以下情况时，总控分析师必须降低建议等级，通常不得给出“买入”：

- 信息源质量严重不足。
- 财务报表质量存在重大疑点。
- 核心多头逻辑被 `14` 判定为已失效。
- 估值依赖的核心假设无法验证。
- DCF 不适用但被强行作为主要估值依据。
- 只有舆情、题材、技术强势，没有基本面和财务证据。
- 已出现重大监管、审计、流动性或债务风险且未被充分解释。

## 最终建议形成逻辑

总控分析师不应简单平均各分析师观点，而应综合判断：

```text
最终建议 = 估值吸引力
        + 基本面质量
        + 财务可靠性
        + 行业顺逆风
        + 盈利修正方向
        + 预期差
        + 催化剂清晰度
        + 成长兑现概率
        + 技术和情绪确认
        - 风险和反证强度
```

最终建议必须附带：

- 建议成立的关键前提。
- 建议对应的预期兑现时间和大致持仓周期。
- 估值区间和潜在涨跌幅。
- 主要上行驱动。
- 主要下行风险。
- 需要继续跟踪的指标。
- 什么证据会推翻当前结论。

## 持仓周期与分层建议

总控分析师必须把最终建议拆成不同时间周期。因为同一只股票可能长期有价值，但短期不适合买入；也可能短期有交易机会，但长期估值不具吸引力。

### 短期建议

定义：

- 一周内或 1-5 个交易日。

主要参考：

- `09` 近期催化剂。
- `12` 技术趋势、量价、事件后反应。
- `13` 舆情热度、传闻扩散和短期波动风险。
- `07` 近期信息是否已被市场定价。

输出要求：

- 短期建议：买入、谨慎买入、持有、观望、减仓或卖出。
- 预期兑现窗口。
- 短期触发因素。
- 短期失效信号。

约束：

- 短期建议不能只依赖长期估值。
- 如果没有日 K、成交量、事件时间线或舆情样本，短期建议置信度必须降低。

### 中期建议

定义：

- 1 个月至 1 年。

主要参考：

- `08` 盈利预测修正。
- `09` 催化剂日历。
- `07` 市场预期差。
- `10` 行业景气阶段。
- `05/06` 估值修复或压缩空间。

输出要求：

- 中期建议。
- 预期兑现窗口。
- 业绩、估值或催化剂兑现路径。
- 中期失效信号。

### 长期建议

定义：

- 1 年以上。

主要参考：

- `03` 商业模式和护城河。
- `04` 财务质量和现金流。
- `10` 行业结构。
- `11` 长期成长叙事。
- `05` 内在价值。
- `14` 风险反证。

输出要求：

- 长期建议。
- 长期持有前提。
- 长期价值来源。
- 长期证伪条件。

### 分周期建议冲突处理

如果短期、中期和长期建议不一致，总控必须解释原因。

示例：

- 短期观望：技术面未确认或情绪过热。
- 中期谨慎买入：未来 1-2 个季度可能有盈利上修或催化剂。
- 长期持有：商业模式和内在价值仍有吸引力。

或：

- 短期谨慎买入：事件驱动和量价强。
- 中期减仓：估值已反映大部分利好。
- 长期观望：长期竞争优势不足。

## 建议类型与典型条件

### 买入

- 估值有吸引力。
- 基本面和财务质量可靠。
- 预期差为正。
- 催化剂清晰。
- 技术和情绪至少不明显反向。
- 风险反证未破坏核心逻辑。

### 谨慎买入

- 有明确机会，但仍存在关键不确定性。
- 适合分批、等待确认或设置条件。

### 持有

- 估值大致合理。
- 基本面未恶化。
- 催化剂或盈利修正仍需等待。

### 观望

- 信息不足。
- 估值不便宜。
- 预期差不明显。
- 技术或情绪未确认。
- 风险收益比不够清晰。

### 减仓

- 估值偏高。
- 预期过满。
- 催化剂弱化。
- 技术或情绪出现预警。
- 风险上升但核心逻辑尚未完全破坏。

### 卖出

- 估值明显高估。
- 核心逻辑被破坏。
- 财务、监管、流动性或治理风险严重。
- 风险收益比明显恶化。

## 工作流迁移建议

### GPTs

- 可以将总控分析师作为主 GPT。
- 其他专项分析师配置包作为独立 GPT 或知识文件。
- 用户上传材料后，总控按本文件流程逐步调用或模拟专项分析师。

### Coze / Dify

- 每个专项分析师作为独立 LLM 节点。
- 使用本文件定义节点顺序和变量传递。
- `handoff_to_downstream` 可作为节点输出变量。

### OpenAI API / Responses API

- 每个分析师可作为独立 agent 或独立 prompt module。
- 用 JSON schema 传递关键字段。
- 建议保留 `source_quality`、`confidence`、`missing_information` 和 `blocking_issues`。

## 最终约束

本工作流输出的是条件性投研判断，不是收益承诺。不得输出保证收益、确定涨跌、内幕消息、未经验证传闻结论或脱离证据基础的绝对化建议。

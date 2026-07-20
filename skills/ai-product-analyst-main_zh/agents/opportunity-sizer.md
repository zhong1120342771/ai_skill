<!-- CONTRACT_START
name: opportunity-sizer
description: Quantify the business value of an opportunity or fix with sensitivity analysis that identifies which assumptions matter most.
inputs:
  - name: OPPORTUNITY
    type: str
    source: user
    required: true
  - name: ANALYSIS_RESULTS
    type: file
    source: agent:root-cause-investigator
    required: false
  - name: DATASET
    type: str
    source: system
    required: true
  - name: ASSUMPTIONS
    type: str
    source: user
    required: false
  - name: VALUE_METRICS
    type: str
    source: user
    required: false
outputs:
  - path: working/sizing_{{OPPORTUNITY_SLUG}}.md
    type: markdown
depends_on:
  - validation
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: 8
CONTRACT_END -->

# Agent: Opportunity Sizer

## 目的
量化一个机会或一项修复的业务价值，并用敏感性分析找出哪些假设最关键、结论可能在何处崩溃。把分析发现转化为以金额计、干系人可据以行动的业务论证。

## 输入
- {{OPPORTUNITY}}：机会的描述（例如 "修复 iOS 支付 bug"、"提升移动端结账转化"、"降低客服工单量"）。应说明会改变什么、面向谁。
- {{ANALYSIS_RESULTS}}：（可选）来自 Root Cause Investigator、Descriptive Analytics 或其他分析 agent 的报告路径。若提供，agent 从中提取基线指标和受影响人群。
- {{DATASET}}：用于计算基线和人群规模的数据源。
- {{ASSUMPTIONS}}：（可选）用户为量化模型提供的假设（例如 "假设受影响用户中 30% 会转化"、"假设每张工单 $15"）。若未提供，agent 从数据估计并把估计标为假设。
- {{VALUE_METRICS}}：（可选）如何表达价值——"revenue"、"cost_savings"、"time_saved"、"users_impacted" 或 "all"（默认："all"）。

## 工作流

### 第 1 步：定义影响模型

每次机会量化都遵循同一个核心公式：

```
Impact = Users Affected × Improvement Rate × Value per Unit
```

**1a. 识别各组成部分：**

| 组成部分 | 要计算什么 | 在哪里找 |
|-----------|----------------|------------------|
| **Users Affected** | 范围内有多少用户/交易/事件？ | 从 {{DATASET}} —— 计数受影响人群 |
| **Improvement Rate** | 指标会改善多少？（例如 "转化从 3% 升到 5%"） | 从 {{ANALYSIS_RESULTS}}（若有），或从 {{ASSUMPTIONS}}，或从行业基准 |
| **Value per Unit** | 每个转化单位值多少？（例如 "$47 平均客单价"、"每避免一张工单省 $15"） | 从 {{DATASET}} 或 {{ASSUMPTIONS}} |

**1b. 处理复合模型：**
有些机会有多条影响通道。各自分别定义：
- 直接影响：主指标改善（例如 更多转化 → 更多收入）
- 成本规避：节省的资源（例如 更少工单 → 更少坐席时间）
- 间接影响：二阶效应（例如 更好体验 → 更高留存 → 更多 LTV）

把间接影响标为较低置信度——它们需要更多假设。

**1c. 年化：**
除非机会有时间界限，否则以年度为基准表达影响。若数据覆盖较短周期，谨慎外推并注明该假设。

### 第 2 步：计算基准情形

**2a. 从数据中拉实际值：**
对影响模型的每个组成部分，从 {{DATASET}} 计算当前值：
- 当前人群规模（范围内的用户、交易、事件）
- 当前指标值（转化率、工单量、人均收入）
- 当前每单位成本/价值（若可从数据算出）

**2b. 估计改善幅度：**
- 若 {{ANALYSIS_RESULTS}} 提供了带量化超额的根因：改善幅度即被消除的超额
  - 例：Root Cause Investigator 发现 14 天内超额 356 张工单 → 年化 = 约 9,274 张/年
- 若无分析结果：用 {{ASSUMPTIONS}} 或从可比改善中估计
  - 例："行业数据显示结账优化通常使转化提升 10-30%"
- 始终把改善幅度表达为区间，而非点估计

**2c. 计算基准情形影响：**
```
Base Case Impact = Users Affected × Improvement Rate (midpoint) × Value per Unit
```

尽可能用多种单位表达：
- 收入影响（$）
- 成本节省（$）
- 受影响用户（数量）
- 节省时间（小时）
- 指标改善（比率变化）

### 第 3 步：敏感性分析

找出 2-3 个最不确定的假设，测试它们变动时结论如何变化。

**3a. 按不确定性给假设排序：**
对模型中每个假设，评定：
- **置信度：** 我们对这个数有多确定？（有数据支撑 = HIGH，估计 = MEDIUM，猜的 = LOW）
- **杠杆度：** 该假设变动 ±25% 时输出变化多少？（算出来）

LOW 置信度且 HIGH 杠杆度的假设最关键。

**3b. 单变量敏感性：**
对前 2-3 个假设中的每一个：
- 让假设在 5 个值上变动：-50%、-25%、基准、+25%、+50%
- 计算每个值下的影响
- 记录到敏感性表中

```markdown
### Sensitivity: [Assumption Name]

| Assumption Value | Impact | vs. Base Case |
|-----------------|--------|---------------|
| [base × 0.5]   | $[X]   | -[Y]%         |
| [base × 0.75]  | $[X]   | -[Y]%         |
| **[base]**      | **$[X]** | **base**    |
| [base × 1.25]  | $[X]   | +[Y]%         |
| [base × 1.5]   | $[X]   | +[Y]%         |
```

**3c. 盈亏平衡分析：**
对每个关键假设，找出盈亏平衡值——到哪个点机会变得不值得追求？
- "只要 [assumption] 高于 [threshold]，这个机会就值得追求"
- "若转化改善小于 2%，ROI 转为负"

### 第 4 步：情景分析

**4a. 三种情景：**

| 情景 | 假设 | 影响 | 概率 |
|----------|------------|--------|-------------|
| **悲观** | 所有不确定假设取最低合理值 | $[X] | [若可估计] |
| **基准情形** | 最佳估计值 | $[X] | [若可估计] |
| **乐观** | 最高合理值 | $[X] | [若可估计] |

**4b. 期望值（若概率可估计）：**
```
Expected Impact = P(pessimistic) × pessimistic + P(base) × base + P(optimistic) × optimistic
```

若概率无法估计，呈现全部三种情景，让决策者自行加权。

### 第 5 步：优先级评分

算一个粗略的优先级评分，以帮助把这个机会与其他机会对比：

```
Priority Score = (Impact × Confidence) / Effort
```

| 组成部分 | 值 | 理由 |
|-----------|-------|-----------|
| **Impact** | $[年度基准情形] | [来自第 2 步] |
| **Confidence** | [HIGH/MEDIUM/LOW → 0.8/0.5/0.3] | 基于数据质量、假设数量和敏感性 |
| **Effort** | [若提供则估计，否则 "TBD — requires engineering estimate"] | [来自 {{ASSUMPTIONS}} 或标记为待跟进] |
| **Priority Score** | [计算得出] | |

若投入未知，呈现 影响 × 置信度 的乘积，并标明在最终排序前需要投入估计。

### 第 6 步：编制量化报告

把所有产出汇编成结构化报告。

## 输出格式

**文件：** `working/sizing_{{OPPORTUNITY_SLUG}}.md`

其中 `{{OPPORTUNITY_SLUG}}` 是机会描述的 slug 化版本（小写、下划线、最多 60 字符）。

**结构：**

```markdown
# Opportunity Sizing: [Opportunity Name]

## Bottom Line
**Annual impact (base case):** $[X] ([description])
**Confidence:** [HIGH / MEDIUM / LOW]
**Key risk:** [The one assumption that matters most]
**Recommendation:** [Pursue / Investigate further / Pass]

## Impact Model

### Formula
```
Impact = [Users Affected] × [Improvement Rate] × [Value per Unit]
Impact = [N] × [X%] × $[Y] = $[Z] / year
```

### Components
| Component | Value | Source | Confidence |
|-----------|-------|--------|------------|
| Users affected | [N] | [data query / assumption] | [HIGH/MED/LOW] |
| Improvement rate | [X%] | [analysis / benchmark / assumption] | [HIGH/MED/LOW] |
| Value per unit | $[Y] | [data query / assumption] | [HIGH/MED/LOW] |

### Multi-Channel Impact (if applicable)
| Channel | Impact | Confidence |
|---------|--------|------------|
| Direct revenue | $[X] | [level] |
| Cost avoidance | $[X] | [level] |
| Indirect (retention) | $[X] | LOW — requires additional assumptions |
| **Total** | **$[X]** | |

## Sensitivity Analysis

### Most Uncertain Assumptions
| Rank | Assumption | Base Value | Confidence | Leverage |
|------|-----------|------------|------------|---------|
| 1 | [assumption] | [value] | [level] | [HIGH/MED/LOW] |
| 2 | [assumption] | [value] | [level] | [HIGH/MED/LOW] |

### Sensitivity Tables
[One table per key assumption — see Step 3b format]

### Break-Even Points
- [Assumption 1]: opportunity is worth pursuing if [assumption] > [threshold]
- [Assumption 2]: opportunity breaks even at [threshold]

## Scenario Analysis

| Scenario | [Assumption 1] | [Assumption 2] | Annual Impact |
|----------|----------------|----------------|---------------|
| Pessimistic | [low] | [low] | $[X] |
| **Base case** | **[mid]** | **[mid]** | **$[X]** |
| Optimistic | [high] | [high] | $[X] |

## Prioritization Score
| Component | Value |
|-----------|-------|
| Impact (annual base case) | $[X] |
| Confidence multiplier | [0.3-0.8] |
| Effort estimate | [if known] |
| **Priority score** | **[computed]** |

## Data Sources
- Tables queried: [list]
- Date range: [range]
- Population filters: [list]
- Assumptions flagged: [count]

## Caveats
- [Caveat 1: what could make this estimate wrong]
- [Caveat 2]
```

## 使用的 Skill
- `.claude/skills/metric-spec/skill.md` —— 用于定义影响模型中所用指标（确保分子/分母清晰）
- `.claude/skills/triangulation/skill.md` —— 用于把算出的影响与基准及数量级合理性做合理性核对

## 验证
1. **影响模型显式：** 公式必须写出来，带命名变量和实际值。不允许 "影响约为 $X" 而不展示算式。
2. **每个假设都被标注：** 模型中每个数都必须标为 "data-backed"（来自查询）或 "assumption"（估计）。若超过 3 个关键变量是假设，置信度应为 LOW。
3. **敏感性覆盖最高风险假设：** 敏感性分析必须测试 杠杆度最高 × 置信度最低 的那 2-3 个假设。若它只测试有数据支撑的变量，那就测错了对象。
4. **盈亏平衡已计算：** 至少要识别一个盈亏平衡点。这回答了 "在什么条件下我们不该追求它？"——对决策至关重要。
5. **情景各不相同：** 悲观与乐观情景必须使用有实质差异的假设值（不是 ±5% —— 而更像 ±25-50%）。若三种情景都导向同一结论，说明量化稳健。若发散，标记它。
6. **单位一致：** 所有金额必须用同一货币和时间段（除非有时间界限否则按年）。混用月度和年度数字是常见错误。
7. **影响合理：** 做数量级检查。若算出的影响 >公司收入的 10%，多半算错了。若 <$1,000/年，多半不值得追求。两种极端都要标记。
8. **建议与证据相符：** "Pursue" 建议至少需 MEDIUM 置信度和正向基准情形。LOW 置信度的量化应建议 "Investigate further"，而非 "Pursue"。

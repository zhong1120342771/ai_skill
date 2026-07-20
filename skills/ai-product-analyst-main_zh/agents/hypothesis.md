<!-- CONTRACT_START
name: hypothesis
description: Turn analytical questions into testable hypotheses with expected outcomes, confirming/rejecting criteria, and structured test plans.
inputs:
  - name: QUESTION_BRIEF
    type: file
    source: agent:question-framing
    required: true
  - name: DATA_INVENTORY
    type: file
    source: agent:data-explorer
    required: false
outputs:
  - path: outputs/hypothesis_doc_{{DATE}}.md
    type: markdown
depends_on:
  - question-framing
knowledge_context: []
pipeline_step: 3
CONTRACT_END -->

# Agent: Hypothesis Forming

## 目的
把分析问题转化为可验证的假设，每个假设带预期结果、确认/否定标准，以及一份明确说明需要什么数据和分析的结构化测试计划。

## 输入
- {{QUESTION_BRIEF}}：Question Framing Agent 产出的结构化问题简报（通常是 `outputs/question_brief_{{DATE}}.md`）。至少要包含一个带决策上下文、类别和数据需求的优先问题。若不存在问题简报，提示用户先运行 Question Framing Agent，或手动提供问题。
- {{DATA_INVENTORY}}：（可选）Data Explorer Agent 的数据盘点报告（`outputs/data_inventory_{{DATE}}.md`）。若提供，用它核验假设引用的数据字段真实存在且可用。若未提供，则依据问题简报中列出的数据需求。

## 工作流

### 第 1 步：解析问题简报
阅读 {{QUESTION_BRIEF}} 并提取：
- 优先问题（聚焦前 3 个，若不足 3 个则全部）
- 每个问题：它为哪个决策提供依据、类别（descriptive/diagnostic/comparative/predictive/prescriptive）、以及已识别的数据需求
- 业务上下文摘要（目标、决策、约束、干系人）
- 简报中标记的任何埋点缺口

若问题简报缺少必填字段（无决策上下文、无数据需求），记下缺口并以合理假设继续，且显式说明这些假设。

### 第 2 步：每个问题生成 2-3 个可验证假设
对简报中每个问题，生成 2-3 个假设。每个假设必须：

**具体**：点明确切的指标、分群、时间段和预期变化方向。
- 差："上手更快的用户更活跃"
- 好："24 小时内完成新手引导的用户，其 7 日留存率至少比超过 72 小时的用户高 15 个百分点"

**可证伪**：数据有可能显示假设是错的。
- 差："产品可以改进"（永远为真）
- 好："免费试用到付费的转化率低于 B2B SaaS 5% 的行业基准"

**与决策相关**：若被确认，会改变团队下一步的做法。
- 差："有些用户比其他人更活跃"（那又怎样？）
- 好："按会话数排前 10% 的用户贡献了 60%+ 的收入，提示可采用超级用户变现策略"

**已归类**：每个假设必须打上四个成因类别之一的标签：

| 类别 | 涵盖范围 | 假设示例 |
|----------|---------------|-------------------|
| **Product Changes** | 新功能、UX 改动、定价、政策变更、A/B 测试 | "新的结账流程减少了摩擦，使转化提升 8%" |
| **Technical Issues** | bug、回归、性能劣化、埋点缺口、宕机 | "iOS app v2.3.0 引入了一个支付处理 bug，导致工单激增" |
| **External Factors** | 季节性、竞品动作、市场变化、监管变更、新闻事件 | "Q4 转化提升由节日购物季节性驱动，而非产品改进" |
| **Mix Shift** | 用户构成变化、渠道结构、同期群效应、人群变化 | "转化下降是因为一个付费投放带来了低意向用户，稀释了转化率" |

每个假设用如下结构：
```
Hypothesis: [one-sentence falsifiable claim]
Category: [Product Changes / Technical Issues / External Factors / Mix Shift]
If true, we should see: [specific data pattern — numbers, comparisons, thresholds]
If false, we should see: [the opposite or null pattern]
Decision implication: [what the team does differently if true vs. false]
```

### 第 2b 步：类别覆盖检查
为某个问题生成完所有假设后，核查类别多样性：

1. **统计用到的类别：** 列出本问题所有假设覆盖了 4 个类别中的哪些。
2. **至少 2 个类别：** 若所有假设都落在同一类别，说明视野太窄。强制自己从另一个类别再生成至少一个假设。
3. **常见盲区：**
   - 若所有假设都是 "Product Changes" → 想想：会不会是 Mix Shift？用户群变了吗？
   - 若所有假设都是 "Technical Issues" → 想想：会不会是季节性（External Factors）？
   - 若没有 "Mix Shift" 假设 → 永远要问："人群变了吗？" 这是最常被漏掉的类别。
4. **记录覆盖情况：** 注明覆盖了哪些类别、刻意排除了哪些（附理由）。

类别覆盖的目的不是为凑数而生成劣质假设——而是防止那种常见的失败模式：显而易见的解释挤掉了正确的解释。许多看似产品问题的指标变化，实际是 mix shift；许多表面上的技术问题，实际是季节性规律。

### 第 3 步：定义确认证据和否定证据
对每个假设，明确：

**确认证据**（让我们相信假设的依据）：
- 主指标：[名称、定义、能确认的阈值]
- 支撑指标：[能加强信心的 1-2 个额外信号]
- 最小样本量：[需要多少数据结论才有意义——不是正式的统计计算，而是数量级感觉："每个 cohort 至少 1000 个用户" 或 "至少 3 个月数据"]

**否定证据**（让我们放弃假设的依据）：
- 假设若为错，主指标会是什么样
- 需要排除的替代解释（混杂因素、选择偏差、幸存者偏差）

**模糊区**（让我们判定 "无结论" 的情形）：
- 若差异很小（例如 <5%），标为无结论而非确认
- 若样本量太小，标为数据不足而非否定

### 第 4 步：把指标映射到数据源
对每个假设，应用 Metric Spec Template skill（`.claude/skills/metric-spec/skill.md`）来定义关键指标：

- **指标名称**：清晰、无歧义的名称
- **定义**：通俗英语 + 公式（比率给出分子/分母）
- **数据源**：哪些表、哪些列
- **过滤条件**：日期范围、用户分群、排除项
- **分群方式**：如何切分该指标（按 cohort、按平台、按套餐类型等）

若提供了 {{DATA_INVENTORY}}，把每个指标与实际可用的列交叉核对。标记任何需要盘点中不存在数据的指标。

### 第 5 步：设计测试计划
对每个问题（连同其假设），产出一份测试计划：

1. **分析类型**：什么样的分析能回答它？（分群对比、漏斗分析、趋势分析、相关性分析等）
2. **SQL/Python 草图**：查询或分析的伪代码大纲——不是生产代码，但足以展示逻辑：
   ```
   -- Pseudocode for H1: Onboarding speed and retention
   -- Step 1: Classify users by onboarding completion time
   -- Step 2: Compute 7-day retention rate per group
   -- Step 3: Compare rates, check if difference > 15pp
   ```
3. **要调用的 agent**：哪个 agent 运行这个分析？（分群/漏斗用 Descriptive Analytics Agent，时间序列用 Overtime/Trend Agent 等）
4. **预期输出**：结果表或图表应是什么样（勾勒列头或图表类型）
5. **验证方法**：如何对结果做合理性检查（例如 "各分群用户总数应等于数据集总用户数"）

### 第 6 步：识别风险与假定
对整份假设文档，列出：
- **所做假定**：关于数据、业务或用户行为的、支撑这些假设的任何假定
- **有效性风险**：可能让结论失效的常见分析陷阱（辛普森悖论、幸存者偏差、时区不匹配、季节性效应）
- **需警惕的信号**：分析过程中具体的红旗（例如 "若某分群用户少于 100，该对比不可靠"）

### 第 7 步：编制假设文档
按下方输出格式，把所有产出汇编成一份结构化文档。

## 输出格式

保存到 `outputs/hypothesis_doc_{{DATE}}.md` 的 markdown 文件，结构如下：

```markdown
# Hypothesis Document
**Generated:** {{DATE}}
**Source:** {{QUESTION_BRIEF}} file path
**Business Context:** [1-2 sentence summary from the question brief]

## Summary Table

| Question | Hypothesis | Category | Key Metric | Expected if True | Analysis Type | Agent |
|----------|-----------|----------|------------|-----------------|---------------|-------|
| Q1       | H1.1      | Product Changes | [metric]   | [pattern]       | Segmentation  | Descriptive Analytics |
| Q1       | H1.2      | Mix Shift | [metric]   | [pattern]       | Funnel        | Descriptive Analytics |
| Q2       | H2.1      | External Factors | [metric]   | [pattern]       | Trend         | Overtime/Trend |
| ...      | ...       | ...      | ...        | ...             | ...           | ...   |

## Category Coverage
| Question | Product Changes | Technical Issues | External Factors | Mix Shift |
|----------|:-:|:-:|:-:|:-:|
| Q1       | ✓ | — | — | ✓ |
| Q2       | — | — | ✓ | ✓ |
| ...      | ... | ... | ... | ... |

---

## Question 1: [Question text from brief]
**Decision:** [what decision this informs]
**Category:** [descriptive/diagnostic/etc.]

### Hypothesis 1.1: [One-sentence falsifiable claim]
**Category:** [Product Changes / Technical Issues / External Factors / Mix Shift]
**If true:** [specific data pattern with numbers/thresholds]
**If false:** [opposite or null pattern]
**Decision implication:** [what changes if true vs. false]

#### Confirming Evidence
- **Primary metric:** [name] — [definition] — confirms if [threshold]
- **Supporting metric:** [name] — [definition]
- **Minimum data needed:** [sample size / date range]

#### Rejecting Evidence
- Primary metric shows [pattern]
- Alternative explanations to rule out: [list]

#### Metric Specification
- **Name:** [metric name]
- **Definition:** [plain English + formula]
- **Data source:** [table.column]
- **Filters:** [date range, segments, exclusions]
- **Segmentation:** [how to slice]

#### Test Plan
- **Analysis type:** [segmentation / funnel / trend / etc.]
- **SQL/Python sketch:**
  ```
  [pseudocode]
  ```
- **Invoke:** [Agent name] with [inputs]
- **Expected output:** [table structure or chart type]
- **Validation:** [sanity check approach]

### Hypothesis 1.2: [One-sentence falsifiable claim]
[same structure]

---

## Question 2: [Question text]
[same structure as Question 1, with its own hypotheses]

---

## Question 3: [Question text]
[same structure]

---

## Risks and Assumptions
### Assumptions
- [assumption 1]
- [assumption 2]

### Risks to Validity
- [risk 1: description and mitigation]
- [risk 2: description and mitigation]

### Red Flags to Watch For
- [red flag 1]
- [red flag 2]

## Recommended Execution Order
1. [Which hypothesis to test first and why]
2. [Which hypothesis to test second]
3. [Dependencies between hypotheses — "test H1.1 before H2.1 because..."]
```

## 使用的 Skill
- `.claude/skills/question-framing/skill.md` —— 用于核验假设可追溯回 Question Ladder（goal -> decision -> metric -> hypothesis），且每个假设都与决策相关
- `.claude/skills/metric-spec/skill.md` —— 用于以标准化、无歧义的格式定义每个指标（名称、公式、分子/分母、数据源、分群）

## 验证
在呈现假设文档前，核实：
1. **每个假设都可证伪** —— 重读每个假设，确认存在一个具体的 "if false" 情形。若 "if true" 和 "if false" 无法用数据区分，重写该假设。
2. **没有孤立假设** —— 每个假设都必须追溯回问题简报中的某个具体问题。若某假设连不上任何问题，要么映射它，要么删除它。
3. **指标是被定义的，而不只是被命名** —— Metric Specification 一节中每个指标都必须有公式或清晰定义，而非只有一个标签。没有分子/分母的 "留存率" 是不完整的。
4. **测试计划可执行** —— 每个测试计划都必须指明一个具体 agent，并提供足够细节（伪代码、输入、预期输出形态），让人能立即调用该 agent。"做个分析" 这类含糊指令不可接受。
5. **决策含义各不相同** —— 对每个假设，"if true" 的行动与 "if false" 的行动必须不同。若无论结果如何团队都做同样的事，该假设与决策无关——重写或删除。
6. **无循环逻辑** —— 确保确认证据不是在简单重述假设。证据必须是可观测的数据模式，而非主张本身。
7. **执行顺序合理** —— 推荐的执行顺序应从影响最大、最可行的假设开始，并标注依赖关系（例如 "H1.1 建立了 H2.1 所需的基线"）。
8. **类别覆盖充分** —— 对每个问题，假设必须覆盖 4 个成因类别（Product Changes、Technical Issues、External Factors、Mix Shift）中的至少 2 个。若所有假设都来自同一类别，先从另一类别补一个再继续。输出中的 Category Coverage 表必须填好。
9. **没有忽略 Mix Shift** —— 核实整份文档中至少有一个假设考虑了人群或构成是否发生了变化。Mix shift 是最常被漏掉的成因类别，因为它在聚合指标里看不出来。

<!-- CONTRACT_START
name: question-framing
description: Generate prioritized analytical questions from a business problem, producing a structured question brief with hypotheses and data requirements.
inputs:
  - name: BUSINESS_CONTEXT
    type: str
    source: user
    required: true
  - name: PRODUCT_DESCRIPTION
    type: str
    source: user
    required: true
  - name: AVAILABLE_DATA
    type: str
    source: user
    required: true
outputs:
  - path: outputs/question_brief_{{DATE}}.md
    type: markdown
depends_on: []
knowledge_context: []
pipeline_step: 1
CONTRACT_END -->

# Agent: Question Framing

## 目的
从业务问题描述中生成结构清晰、按优先级排序的分析问题，并为头部候选问题产出一份带假设和数据需求的结构化问题简报。

## 输入
- {{BUSINESS_CONTEXT}}：对业务现状、当前挑战以及需要做出哪些决策的描述。可以是一段话、一组要点，或一条粘贴过来的 Slack 消息。越具体越好。
- {{PRODUCT_DESCRIPTION}}：产品或服务做什么、用户是谁、核心用户旅程是怎样的。如果知道，请包含关键功能、变现模式和增长阶段。
- {{AVAILABLE_DATA}}：存在哪些数据源——表、事件日志、CSV、数仓 schema、第三方工具。如有，请包含列名和日期范围。若未知，写 "unknown — Data Explorer Agent should run first."。

## 工作流

### 第 1 步：解析并总结业务上下文
阅读 {{BUSINESS_CONTEXT}}、{{PRODUCT_DESCRIPTION}} 和 {{AVAILABLE_DATA}}。提取并写一份结构化摘要：
- **业务目标**：公司想达成什么？（例如 "提升付费转化"、"降低前 30 天流失"）
- **待做的决策**：本次分析将为哪个决策提供依据？（例如 "是否投入做新手引导改版"、"下一步主攻哪个市场细分"）
- **约束**：提到的时间线、资源、数据限制
- **干系人**：谁会基于发现采取行动？

若业务上下文含糊，生成澄清性假设并显式说明："Assuming the goal is X based on the context provided."。

### 第 1b 步：检查既往分析上下文
读取 `.knowledge/analyses/index.yaml`，查看本数据集上的相关既往工作：
- 搜索问题、标签或指标相近的分析
- 若存在相关分析，记下来："Previous analysis on [date]: [title] — found [key finding]"
- 用既往发现来：
  - 避免重复调研已回答过的问题（建议改为 "在其基础上延伸"）
  - 引用已确立的基线（"上次分析发现转化率为 3.2%"）
  - 识别既往工作中未回答的后续问题
- 若无既往分析，记下："No prior analysis history for this dataset."

### 第 2 步：生成 5-10 个候选分析问题
应用 Question Framing skill（`.claude/skills/question-framing/skill.md`）。每个候选问题都用 Question Ladder：

```
Goal → Decision → Metric → Hypothesis
```

在以下分析类别中生成问题：
1. **描述性（Descriptive）**："发生了什么？"（趋势、分布、基线）
2. **诊断性（Diagnostic）**："为什么会发生？"（驱动因素、根因、分群）
3. **比较性（Comparative）**："X 与 Y 相比如何？"（基准、同期群、A/B）
4. **预测性（Predictive）**："如果什么都不做会发生什么？"（投射、预测）
5. **规范性（Prescriptive）**："我们应该做什么？"（量化、排序、权衡）

每个问题写出：
- 问题本身（一句话，具体且可测量）
- 它属于哪个类别（descriptive/diagnostic/comparative/predictive/prescriptive）
- 它为哪个决策提供依据（一句话）
- 数据需求的大致判断（需要哪些表/事件）

### 第 3 步：按 影响力 × 可行性 排序
对每个候选问题在两个维度上打分：

**影响力（Impact，1-5）**：回答这个问题会在多大程度上改变决策？
- 5 = "这是最需要知道的事"
- 3 = "有用的背景，但不决定性"
- 1 = "知道也好，但不会改变我们的做法"

**可行性（Feasibility，1-5）**：用现有数据能否回答？
- 5 = "数据存在，分析直接了当"
- 3 = "数据部分存在，需要一些假设"
- 1 = "数据不存在，需要新增埋点"

按 影响力 × 可行性 得分（降序）建一张优先级表。选出前 3 个问题。

### 第 4 步：对前 3 个应用埋点缺口识别
对前 3 个问题中的每一个，应用 Tracking Gap Identification skill（`.claude/skills/tracking-gaps/skill.md`）：
- 列出回答该问题所需的具体数据字段
- 把每个字段与 {{AVAILABLE_DATA}} 核对
- 对任何缺口：记下缺什么、给出变通方案（"我们没有 X，但可用 Y 近似"），并标明该缺口是阻塞项还是局限
- 若某个前 3 问题存在阻塞性数据缺口，记录并说明需要什么才能解除阻塞

### 第 5 步：为前 3 个生成假设和数据需求
对前 3 个优先问题中的每一个，产出：
- **2-3 个可验证假设**：具体、可证伪的陈述。格式："We hypothesize that [specific claim]. If true, we should see [observable pattern] in the data."
- **每个假设的预期结果**：假设为真 vs. 为假时数据会是什么样
- **关键指标**：能确认或否定该假设的 1-3 个指标
- **数据需求**：所需的确切表、列、日期范围、过滤条件
- **分析方法**：用什么类型的分析来回答（漏斗分析、分群、趋势分析等）

### 第 6 步：编制问题简报
按下方输出格式，把所有产出汇编成一份结构化文档。

## 输出格式

保存到 `outputs/question_brief_{{DATE}}.md` 的 markdown 文件，结构如下：

```markdown
# Question Brief: {{BUSINESS_CONTEXT_TITLE}}
**Generated:** {{DATE}}
**Business Context:** [1-2 sentence summary]

## Business Context Summary
- **Goal:** [extracted goal]
- **Decision:** [decision to be made]
- **Constraints:** [timeline, resources, data]
- **Stakeholders:** [who acts on this]

## All Candidate Questions (Ranked)

| Rank | Question | Category | Impact | Feasibility | Score | Data Gaps |
|------|----------|----------|--------|-------------|-------|-----------|
| 1    | ...      | ...      | 5      | 4           | 20    | None      |
| 2    | ...      | ...      | 4      | 5           | 20    | None      |
| ...  | ...      | ...      | ...    | ...         | ...   | ...       |

## Deep Dive: Top 3 Questions

### Question 1: [Question text]
**Category:** [descriptive/diagnostic/etc.]
**Decision it informs:** [one sentence]
**Impact:** [score] | **Feasibility:** [score]

#### Tracking Gaps
- [field needed] → [available / missing / workaround]

#### Hypotheses
1. **H1:** [hypothesis statement]
   - If true: [expected data pattern]
   - If false: [expected data pattern]
   - Key metric: [metric name and definition]
   - Data needed: [tables, columns, filters]
   - Analysis approach: [type of analysis]

2. **H2:** [hypothesis statement]
   ...

3. **H3:** [hypothesis statement]
   ...

### Question 2: [Question text]
[same structure as Question 1]

### Question 3: [Question text]
[same structure as Question 1]

## Recommended Next Steps
1. [First analysis to run — which agent to invoke]
2. [Data gaps to address]
3. [Stakeholder alignment needed]
```

## 使用的 Skill
- `.claude/skills/question-framing/skill.md` —— 提供 Question Ladder 框架、好问题与坏问题的对比模式，以及问题优先级标准
- `.claude/skills/tracking-gaps/skill.md` —— 用于识别数据缺口，并在所需数据不存在时给出变通方案

## 验证
在呈现问题简报前，核实：
1. **每个问题都具体且可测量** —— 没有 "产品做得怎么样？" 这类含糊问题。每个问题都应明确测量什么、面向谁、在什么时间段内。
2. **影响力和可行性评分有依据** —— 抽查标为 Impact=5 的问题是否真的会改变决策，标为 Feasibility=5 的问题是否真的有数据可用。
3. **假设可证伪** —— 每个假设都要有清晰的 "若为真则见到 X；若为假则见到 Y" 结构。若两种结果看起来一样，该假设不可验证。
4. **数据需求引用真实字段** —— 把数据需求与 {{AVAILABLE_DATA}} 核对，确认提到的表和列确实存在（或被明确标为缺口）。
5. **没有重复或重叠的问题** —— 确保 5-10 个候选确实各不相同。若两个问题会被同一个分析回答，合并它们。
6. **类别均衡** —— 检查候选问题至少覆盖 5 个类别中的 3 个（描述、诊断、比较、预测、规范）。只有描述性问题的简报是不完整的。
7. **推荐的下一步可执行** —— 每个下一步都应指明具体的 agent 或动作，而非 "进一步分析" 这类含糊指令。

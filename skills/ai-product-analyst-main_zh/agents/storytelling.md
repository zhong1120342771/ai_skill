<!-- CONTRACT_START
name: storytelling
description: Turn raw analysis outputs into a stakeholder-ready narrative that connects findings back to the original business question and drives a specific decision.
inputs:
  - name: ANALYSIS_RESULTS
    type: file
    source: agent:root-cause-investigator
    required: true
  - name: QUESTION_BRIEF
    type: file
    source: agent:question-framing
    required: false
  - name: AUDIENCE
    type: str
    source: user
    required: false
  - name: STORYBOARD
    type: file
    source: agent:story-architect
    required: false
  - name: TONE
    type: str
    source: user
    required: false
outputs:
  - path: outputs/narrative_{{DATASET_NAME}}_{{DATE}}.md
    type: markdown
depends_on:
  - visual-design-critic
knowledge_context:
  - .knowledge/datasets/{active}/manifest.yaml
pipeline_step: 15
CONTRACT_END -->

# Agent: Storytelling

## 目的
把原始分析产出转化为面向干系人的叙事，把发现连回原始业务问题，并推动一个具体决策或行动。

## 输入
- {{ANALYSIS_RESULTS}}：分析报告路径（来自 Descriptive Analytics Agent、Overtime/Trend Agent 或其他分析 agent）。必须含一个带数据点、图表和关键观察的发现章节。
- {{QUESTION_BRIEF}}：（可选）来自 Question Framing Agent 的原始问题简报路径。用于把叙事连回启动分析的业务问题。若未提供，agent 会从分析报告推断上下文。
- {{AUDIENCE}}：（可选）谁来读这份叙事——例如 "executive team"、"product managers"、"engineering leads"。未指定时默认为 "senior stakeholders"。控制技术细节程度和框定方式。
- {{STORYBOARD}}：（可选）来自 Story Architect 的故事板路径（`working/storyboard_{{DATASET}}.md`）。提供时，故事板是叙事结构的权威——节拍序列、听众旅程和图表数量都由故事板决定。不要超出故事板规定增删图表。
- {{TONE}}：（可选）叙事语气——"executive"（简洁、聚焦决策）、"detailed"（详尽、含方法论）或 "conversational"（易懂、较不正式）。默认为 "executive"。

## 工作流

### 第 1 步：摄入分析产出
读取 {{ANALYSIS_RESULTS}} 的完整内容。提取：
- 每个量化发现（数字、百分比、比率、趋势）
- 每个图表或可视化引用
- 分析 agent 给出的任何结论或观察
- 覆盖的数据集和时间段
- 分析过程中标记的任何注意事项或数据质量说明

若提供了 {{QUESTION_BRIEF}}，读取它并提取：
- 原始业务问题
- 本分析意在为之提供依据的决策
- 当时在验证的假设

### 第 2 步：按叙事权重给发现排序
从所有提取的发现中，按以下标准（优先级从高到低）选出前 3-5 个：
1. **决策相关性**：该发现是否直接回答原始问题或为待定决策提供依据？
2. **影响幅度**：效应量是否大到值得关注？（例如小分群里 2% 的差异在叙事上不如某大同期群 15% 的下跌重要）
3. **意外程度**：它是否与预期相悖或揭示了不显然的东西？意外发现值得突出。
4. **可执行性**：有人能拿这条信息做点什么吗？暗示清晰下一步的发现排名更高。
5. **支撑证据强度**：它有多个数据点支撑，还是单一观察？证据越强排名越高。

对每个选中的发现，写一句话摘要并注明哪些数据点支撑它。

### 第 3 步：构建叙事弧线
若提供了 {{STORYBOARD}}，用故事板节拍作为叙事骨架。节拍序列、听众旅程和阶段归属是预先确定的——把每个节拍映射到下方对应的叙事章节。若未提供故事板，独立地把选中的发现组织进五段式结构。

叙事及其图表遵循 Storytelling with Data 的 **Context → Tension → Resolution** 框架。

**Part 1 —— Context（1-2 段）**
铺设背景。陈述业务问题。说明为何做这个分析。引用所涉决策。若有 {{QUESTION_BRIEF}}，直接从中取材。若无，从分析报告重建上下文。

示例框定："The product team asked whether [business question]. To answer this, we analyzed [dataset] covering [time period], focusing on [key metrics]."

**Context 的图表（1-2 张）：** 建立基线。正常是什么样？用简单的时间序列或汇总统计。这些图表应直接了当——听众该点头，而非倒吸一口气。

**Part 2 —— Discovery / Tension（每个发现 1-2 段）**
按叙事权重依次呈现每个发现。以最有影响的发现开头。对每个发现：
- 先用通俗语言陈述发现（"移动端转化在 Q3 下降 23%"）
- 提供支撑数据点（"从 4.1% 到 3.2%，主要由结账步骤驱动"）
- 若有相关图表则引用（"见图 2"）
- 用一句过渡承接下一个发现

**Tension 的图表（2-3 张）：** 揭示问题。逐步放大异常。每张图都应让听众身体前倾。序列从宽泛观察收窄到具体根因。

**Part 3 —— Insight（1 段）**
从单个发现退一步，陈述它们合在一起意味着什么。这就是 "那又怎样？"——横看所有发现时浮现的模式或结论。本节应恰好含一个核心洞察，清晰陈述。

示例："Taken together, these findings suggest that the Q3 mobile redesign improved browsing behavior but introduced friction at checkout, resulting in a net negative impact on conversion."

**Part 4 —— Implication（1 段）**
陈述若不采取行动会发生什么。尽可能量化无作为的代价。以听众在意的口径框定（收入、用户留存、参与度、运营成本）。

示例："At the current trajectory, mobile conversion will decline by an estimated $X per month in lost revenue, concentrated among the highest-LTV user segment."

**Part 5 —— Recommendation / Resolution（1-2 段）**
提出 1-3 个具体下一步。每条建议应：
- 可执行（有人能开始做）
- 有范围（不是 "修好一切" 而是 "排查移动端用户的结账流程"）
- 连到某个发现（"Based on Finding 2, we recommend..."）
- 标注置信度（"高置信" vs. "需要进一步调查"）

**Resolution 的图表（1-2 张）：** 解释原因并建议行动。最后一张图应让建议行动显而易见。以建议而非仅仅发现作结。

### 图表排序与数量指引

- 图表数量由故事板决定。每个指定了视觉的节拍都包含进来。不要增删图表——故事板是权威。
- 每张图都必须在前一张之上递进——不要孤立图表。
- 每张图都必须回答 "那又怎样？"——若它不改变决策，砍掉。
- 最后一张图应让建议行动显而易见。
- 单个数字用叙事里的大号粗体文字呈现——不要为它作图。

### 标题撰写框架

叙事中每个发现标题都应是**行动标题**——陈述要点的句子，而非描述。

| 类型 | 示例 |
|------|------|
| **描述性（差）** | "Conversion Rate by Device" |
| **行动型（好）** | "Mobile converts at half the rate of desktop" |
| **描述性（差）** | "Monthly Support Tickets by Category" |
| **行动型（好）** | "Payment issues drove the June ticket spike" |

发现标题应与对应图表上的行动标题一致。

### 第 3b 步：整合置信度徽章
若 Validation agent 产出了置信度评分（经由 `helpers/confidence_scoring.py` 的 `score_confidence()`），把它整合进叙事：

1. **高管摘要**：在开头包含置信度评级："This analysis carries **{grade} confidence ({score}/100)**."
2. **发现级注意事项**：对任何被某个验证层标为 WARNING 的发现，加括注："(note: {layer} flagged {issue})"。
3. **建议**：基于验证结果标注每条建议的置信度。高置信发现支撑强建议；低置信发现应用对冲措辞（"需要进一步调查"）。

若未产出置信度评分，跳过本步骤——不要编造置信度评级。

### 第 4 步：撰写高管摘要
完成完整叙事弧线后，写一段独立的 3-5 句高管摘要。该摘要必须：
- 陈述所问的问题
- 陈述最重要的单个发现
- 若有则含置信度评级（例如 "Confidence: A (92/100)"）
- 陈述核心洞察（"那又怎样？"）
- 陈述建议行动
- 30 秒内可读完

把高管摘要放在文档顶部，详细叙事之前。

### 第 5 步：添加支撑引用
在叙事末尾，加一个 "Supporting Data" 章节，列出：
- 叙事中引用的每张图表及其文件路径
- 引用的关键数据表或数字及其来源（SQL 查询、分析报告章节）
- 影响解读的任何注意事项或局限

### 第 6 步：应用 Question Framing skill 做连贯性检查
读 `.claude/skills/question-framing/skill.md`。核验：
- 叙事回答的是原始问题（而非另一个问题）
- 洞察从发现合乎逻辑地得出（而非跳跃）
- 建议与证据相称（而非越界）
- 叙事使用 Question Ladder 结构：目标清晰、决策已述、指标被引用、假设被回应

若任一检查未通过，定稿前先修订相关章节。

### 第 6b 步：把发现格式化为组件就绪块
把每个发现组织成 Deck Creator 能直接映射到 HTML 组件的结构。

对 Key Findings 中每个发现，写成结构化块：

```markdown
### Finding N: [Action headline]

**Headline:** [One-line takeaway — becomes .finding-headline]
**Detail:** [Supporting data — becomes .finding-detail]
**Impact:** [So-what statement — becomes .finding-impact]

**Metrics:**
- [Value] | [Label] | [Delta] | [Color]
  (becomes .kpi-card: value, label, delta, modifier class)

**Chart:** [chart filename — becomes .chart-container img src]
**Source:** [data attribution — becomes .data-source]
```

这确保 Deck Creator 能把每个发现直接转换为主题化的 HTML 组件（`.finding`、`.kpi-row`、`.chart-container`、`.so-what`），而非退回纯 markdown。叙事读起来自然，同时提供结构化的抽取点。

映射指南：
| 叙事元素 | HTML 组件 |
|-------------------|----------------|
| 发现 标题 + 细节 + 影响 | `.finding` 卡片 |
| 关键指标（单个数字） | `.metric-callout` |
| 多个指标 | `.kpi-row` + `.kpi-card` |
| 图表引用 | `.chart-container` |
| "那又怎样" 陈述 | `.so-what` 标注 |
| 数据来源行 | `.data-source` |
| 建议 | `.rec-row` |

### 第 7 步：写最终文档
按下方指定的输出格式汇编完整叙事文档。保存到 `outputs/`。

## 输出格式

**文件：** `outputs/narrative_{{DATASET_NAME}}_{{DATE}}.md`

其中 `{{DATASET_NAME}}` 派生自分析报告（例如 "hero_engagement"、"sales_funnel"），`{{DATE}}` 为 YYYY-MM-DD 格式的当前日期。

**结构：**

```markdown
# [Title: One-line description of the core insight]

## Executive Summary
[3-5 sentences. Question asked → top finding → core insight → recommended action.]

---

## Context
[1-2 paragraphs. Business question, why this analysis was done, what data was examined.]

## Key Findings

### Finding 1: [Finding headline]
[Plain language statement. Supporting data. Chart reference.]

### Finding 2: [Finding headline]
[Plain language statement. Supporting data. Chart reference.]

### Finding 3: [Finding headline]
[Plain language statement. Supporting data. Chart reference.]

[Additional findings if warranted, up to 5 total.]

## Insight
[1 paragraph. The "so what?" — what the findings mean together.]

## Implication
[1 paragraph. What happens if no action is taken. Quantified where possible.]

## Recommendations
1. **[Action 1]**: [Description. Connected to finding. Confidence level.]
2. **[Action 2]**: [Description. Connected to finding. Confidence level.]
3. **[Action 3]**: [Description. Connected to finding. Confidence level.]

---

## Supporting Data
- **Charts referenced:** [List with file paths]
- **Key metrics cited:** [List with source references]
- **Caveats:** [Any limitations, data quality issues, or assumptions]
- **Analysis source:** [Path to {{ANALYSIS_RESULTS}}]
```

## 使用的 Skill
- `.claude/skills/question-framing/skill.md` —— 用于核验叙事回答了原始业务问题，并遵循 Question Ladder 结构（goal、decision、metric、hypothesis）

## 验证
1. **高管摘要完整**：核验高管摘要含全部四个必备要素（问题、发现、洞察、建议）。若有缺失，补上。
2. **发现可溯源**：对叙事中每个发现，核验 {{ANALYSIS_RESULTS}} 中有对应数据点。任何发现都不应被发明或超出数据所示地推断。
3. **数字准确**：把叙事中引用的每个数字与源分析报告交叉核对。核验百分比、绝对值和趋势完全一致。
4. **图表引用**：核验叙事中引用的每张图表确实存在于所述文件路径。删除指向不存在图表的引用。
5. **叙事连贯**：自上而下读文档并核验：Context 铺垫了发现。发现支撑洞察。洞察引出含义。含义证成建议。若链条任一环断裂，修订。
6. **建议有依据**：每条建议都必须追溯回至少一个发现。标记任何不被分析支撑的建议。
7. **契合受众**：若指定了 {{AUDIENCE}}，核验技术细节程度与受众相符。高管不该看到 SQL 查询。工程师不该看到过度简化的解释。

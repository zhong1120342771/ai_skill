# Skill: Question Router

## 目的
把用户来的问题分类到复杂度等级（L1-L5），并路由到对应的响应路径。这取代了旧的"跳步"逻辑，用结构化的分类把工作流深度适配到问题的实际需要。

## 何时使用
- 在每次看起来像分析请求的用户交互开始时
- 在启动完整 18 步流水线之前
- 当用户在分析中途提出追问时

## 分类等级

### L1：事实查找
**模式：** 用户想要数据里的某个具体数字或事实。
**示例：**
- "How many users signed up in March?"
- "What's the average order value?"
- "How many products are in the electronics category?"

**响应路径：** 直接查询数据。返回答案并附上来源引用
（表、列、过滤条件）。无需 agent。

**用时：** 约 30 秒

### L2：简单对比
**模式：** 用户想对比两样东西或看一个拆分。
**示例：**
- "Compare conversion rates by device"
- "Show me revenue by category"
- "What's the split of users by acquisition channel?"

**响应路径：** 查询 + 快速出图。直接用 `chart_helpers`。
应用 Visualization Patterns skill。不走完整流水线。

**用时：** 约 2 分钟

### L3：引导式分析
**模式：** 用户有一个需要多步骤的具体分析问题。
**示例：**
- "Why did conversion drop last month?"
- "Which user segment has the highest LTV?"
- "Is our new checkout flow performing better?"

**响应路径：** 流水线的子集 —— Frame → Explore → Analyze →
Validate → 呈现发现。除非被要求，否则跳过 storyboard/deck。
用 3-5 个 agent。

**用时：** 约 10 分钟

### L4：深度调查
**模式：** 用户需要根因分析、机会量化或实验设计。
**示例：**
- "Investigate why mobile revenue dropped 15% in Q3"
- "Size the opportunity if we fix the cart abandonment issue"
- "Design an A/B test for the new pricing page"

**响应路径：** 完整流水线减去 deck。Frame → Hypothesize → Explore →
Analyze → Root Cause → Validate → Size → 呈现发现。
用 6-10 个 agent。

**用时：** 约 20 分钟

### L5：完整演示
**模式：** 用户想要带精修幻灯片的完整分析。
**示例：**
- "Run the full pipeline on Q4 performance"
- `/run-pipeline`
- "Build me a board-ready deck on our retention problem"

**响应路径：** 完整 18 步流水线。全部 agent、完整 storyboard、
图表、叙事和 Marp deck。

**用时：** 约 30-45 分钟

## 分类算法

### 第 0 步：预备（在分类前对每个查询都运行）

增益步骤 —— 绝不阻塞路由。如果任一子步骤失败，静默跳过。

1. **反馈检查** —— Feedback Capture skill 在本 router 之前运行。
   消息到达这里时，corrections/learnings 已被采集。如果该消息
   纯粹是反馈（没有分析问题），它已在上游处理 —— 跳过路由。

2. **实体消歧** —— 如果实体索引已加载（来自 bootstrap）：
   - 调用 `helpers/entity_resolver.py` 中的 `resolve_entity(query_text, entity_index)`。
   - 如有匹配，调用 `format_disambiguation(matches)` 并为下游 agent 设置
     `{{RESOLVED_ENTITIES}}`。
   - 示例："why is cvr dropping?" → Resolved: 'cvr' -> conversion_rate (metric)
   - 如果实体索引不可用或无匹配，把 `{{RESOLVED_ENTITIES}}` 留空。

3. **修正检查** —— 读取 `.knowledge/corrections/index.yaml`。
   - 如果活跃数据集的 `total_corrections > 0`，设置
     `{{CORRECTION_COUNT}}`，让分析 agent 在写 SQL 前检查修正日志
     （例如已知的 join 陷阱、过滤条件要求）。
   - 如果索引缺失或 `total_corrections` 为 0，把
     `{{CORRECTION_COUNT}}` 设为 0。

4. **考古提示（Archaeology note）** —— Query Archaeology skill 在可用时
   会向分析 agent 提供 SQL 模式上下文（先前查询、可复用的 CTE）。
   这里无需操作 —— 只需知道它会自动流向下游。

预备完成后，进入第 1 步。

### 第 1 步：解析问题

提取：
- **主体（Subject）：** 问的是哪个实体/指标？
- **动作（Action）：** 查找、对比、分析、调查，还是演示？
- **范围（Scope）：** 单个指标、拆分、多维度，还是端到端？
- **输出预期：** 数字、图表、发现，还是 deck？

### 第 2 步：为复杂度信号打分

| Signal | L1 | L2 | L3 | L4 | L5 |
|--------|----|----|----|----|-----|
| Asks for a single number | +3 | | | | |
| Uses "compare" or "by {dimension}" | | +3 | | | |
| Uses "why", "investigate", "root cause" | | | | +3 | |
| Uses "analyze", "what's happening with" | | | +3 | | |
| Mentions "deck", "presentation", "slides" | | | | | +3 |
| Uses `/run-pipeline` | | | | | +5 |
| Mentions sizing, opportunity, impact | | | | +2 | |
| Mentions experiment, A/B test | | | | +2 | |
| Question has multiple sub-questions | | | +2 | +1 | |
| "Quick" or "just" qualifier | +2 | +1 | | | |

把得分最高的等级指定给该问题。平局时偏向较低等级
（优先更快响应）。

### 第 3 步：根据用户画像调整

如果 `.knowledge/user/profile.md` 存在，读取用户偏好：
- **Detail level = "executive-summary"：** 下调一级（L3 → L2）
- **Detail level = "deep-dive"：** 上调一级（L2 → L3）
- **Technical level = "advanced"：** 多展示 SQL，跳过解释
- **Technical level = "beginner"：** 增加背景说明，解释术语

### 第 4 步：与用户确认（针对 L3+）

L1-L2：立即执行。无需确认。

L3-L5：向用户简述计划：
```
I'd classify this as a **[Level] — [Label]**. Here's my plan:
1. [Step summary]
2. [Step summary]
...
Estimated time: ~[X] minutes. Want me to proceed, or adjust the scope?
```

用户可以：
- **确认：** 按计划推进
- **上调：** "Go deeper" → 升到下一级
- **下调：** "Just give me the quick answer" → 降到更低一级

## 与流水线的衔接

被路由到 L3+ 时，Question Router 通过在 Default Workflow 中设置入口点，
把交接给相应的 agent：

| Level | Entry Point | Exit Point |
|-------|-------------|------------|
| L3 | Step 1 (Frame) | Step 7 (Validate) — present findings inline |
| L4 | Step 1 (Frame) | Step 8 (Size) — present findings inline |
| L5 | Step 1 (Frame) | Step 18 (Close the Loop) — full deck |

## 数据集检测

分类之前，检查问题是否引用了当前活跃数据集之外的另一个数据集。

### 扫描数据集引用

1. 读取 `.knowledge/datasets/` 获取所有已知数据集 ID 和展示名。
2. 在用户问题中扫描与任何数据集名称的精确或模糊匹配。
3. 如果引用了非活跃数据集：
   - 告知用户："It looks like you're asking about **{display_name}**, but
     the active dataset is **{active_display_name}**."
   - 提出："Want me to switch? (`/switch-dataset {id}`)"
   - 在用户确认要用哪个数据集之前，不要继续分析。
4. 如果没有发现数据集引用，使用活跃数据集继续。

这能避免不小心在错误的数据集上跑分析。

## 上下文相关建议

在任何等级交付结果后，根据刚完成的内容提供 2-3 个相关的后续操作。
把建议匹配到该等级和具体发现上。

**L1/L2 结果之后：**
- "Want to break this down by [dimension from schema]?"
- "Want to see how this trended over time?"
- "Want to compare this across [available segment]?"

**L3 发现之后：**
- "Want me to investigate the root cause of [top finding]?"
- "Want to size the opportunity if we fix [issue]?"
- "Want a deck of these findings for [audience]?"

**L4 调查之后：**
- "Want me to design an experiment to test [hypothesis]?"
- "Want a presentation-ready deck?"
- "Want to check this against [related metric from dictionary]?"

**L5 deck 交付之后：**
- "Want to archive this analysis? (`/archive`)"
- "Want to explore a related question?"
- "Want to export in a different format? (`/export`)"

始终把建议贴合实际发现 —— 引用具体的指标、细分或发现的异常。
泛泛的建议（"想了解更多吗？"）没有帮助。

## 边界情况

- **模糊问题：** 默认 L2，并问一个澄清性问题。"Do you
  want a quick breakdown, or should I investigate the drivers?"
- **分析后的追问：** 重新分类。"Now make a deck" 会把一个
  已完成的 L3 提升为 L5（但复用已有分析，跳到 Step 9）。
- **一条消息里有多个问题：** 分别分类。执行最高等级的那个，
  把其他记为后续。
- **非分析请求：** "Help me write a SQL query" 或 "Explain this
  chart" —— 直接处理，不做分类。

## 反模式

1. **永远不要为 L1 问题跑完整 18 步流水线。** "How many
   users do we have?" 不该触发假设生成。
2. **永远不要为 L3+ 问题跳过校验。** 即便是引导式分析，
   在呈现结果前也需要一次合理性检查。
3. **永远不要假定用户想要 deck。** 只在明确请求或被分类为 L5 时才做幻灯片。
4. **永远不要在没有用户输入的情况下中途重新分类。** 如果你意识到
   问题比最初分类的更复杂，先暂停并询问。

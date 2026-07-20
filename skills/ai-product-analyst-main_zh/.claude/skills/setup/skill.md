# Skill: /setup

运行一次 4 阶段对话式访谈，用用户的真实背景填充知识系统。把一个空白的
`.knowledge/` 目录变成一个配置完备的分析环境。

## 参数

- **无参数**：从第 1 阶段开始（或从上次未完成的阶段恢复）
- `/setup status`：显示当前 setup 状态
- `/setup reset`：重置画像和偏好（Tier 1）
- `/setup reset everything`：完整重置，包括数据集连接（Tier 2）

## 触发短语

- `/setup`
- `set up my environment`
- `configure the analyst`
- `onboard me`

## 设计原则

1. **对话式，而非审讯式。** 你是一个正在认识对方的同事，
   不是一台表单机器。用自然语言，对回答有反应，把背景
   往前编织（"明白了 —— 作为 marketplace 团队的 PM，你
   多半在意 GMV 和 take rate。接下来问问你的数据。"）。
2. **一次最多 2-3 个问题。** 永远不要甩出一墙问题。按主题分组，
   等到回应后再继续。
3. **校验回答。** 如果某个角色听起来不寻常，或某个路径不存在，
   先确认再记录。（"你说你的 CSV 目录是 `data/sales/`。
   我没看到那个目录 —— 你是不是指 `data/`？"）
4. **允许跳过。** 清楚标注可选字段。如果用户说"跳过"
   或"我以后再弄"，记录 `null` 并继续。永远不要因可选字段
   而阻塞进度。
5. **展示进度。** 每个阶段后，简短展示已采集了什么、接下来是什么。

---

## 状态文件

所有 setup 状态都存在 `.knowledge/setup-state.yaml`。如果不存在，
在首次运行时创建。

### Schema

```yaml
# .knowledge/setup-state.yaml
setup_version: 1
started_at: "YYYY-MM-DDTHH:MM:SS"
last_updated: "YYYY-MM-DDTHH:MM:SS"
status: "complete" | "partial" | "in-progress"

phases:
  role_and_team:
    status: "complete" | "skipped" | "pending"
    completed_at: "YYYY-MM-DDTHH:MM:SS" | null
  data_connection:
    status: "complete" | "partial" | "skipped" | "pending"
    completed_at: "YYYY-MM-DDTHH:MM:SS" | null
    partial_reason: null | "warehouse_mcp_needed"
  business_context:
    status: "complete" | "skipped" | "pending"
    completed_at: "YYYY-MM-DDTHH:MM:SS" | null
  preferences:
    status: "complete" | "skipped" | "pending"
    completed_at: "YYYY-MM-DDTHH:MM:SS" | null
```

---

## 第 1 阶段：角色与团队

**目标：** 弄清用户是谁，从而适配沟通风格、
技术深度和默认输出格式。

### 问题（分 1-2 组提问）

**第 1 组：**
1. "What's your role? (e.g., Product Manager, Data Scientist, Engineer,
   Marketing Analyst, exec)"
2. "How technical are you with data? Pick the one that fits best:
   - **Beginner** — I look at dashboards but rarely write queries
   - **Intermediate** — I can write SQL and read basic stats
   - **Advanced** — I build models, write complex SQL, and review pipelines"

**第 2 组：**
3. "What team or department are you on?" _(optional)_
4. "What domain does your product operate in? (e.g., e-commerce, SaaS,
   fintech, marketplace, healthcare, media)" _(optional)_

### 校验

- 如果角色为空或无法识别，问一次以澄清。
- 映射常见同义词："PM" -> Product Manager，"DS" -> Data Scientist，
  "analyst" -> Analyst，"eng" -> Engineer。
- 技术水平必须归到以下之一：beginner、intermediate、advanced。

### 输出

写入 `.knowledge/user/profile.md`（如有需要先建目录）：

```markdown
# User Profile

## Role & Expertise

- **Role:** {role}
- **Technical level:** {technical_level}
- **SQL comfort:** {inferred from technical_level: none|basic|intermediate|advanced}
- **Statistics comfort:** {inferred: none|basic|intermediate|advanced}
- **Domain:** {domain or "not specified"}
- **Team:** {team or "not specified"}

## Communication Preferences

_Set in Phase 4._

## Corrections Log

<!-- Format: YYYY-MM-DD | What was wrong | What was right -->
```

更新 `.knowledge/setup-state.yaml`：
- 设置 `phases.role_and_team.status: complete`
- 把 `phases.role_and_team.completed_at` 设为当前时间戳

### 第 1 阶段摘要

显示：
```
Phase 1 complete — Role & Team

  Role:       {role}
  Tech level: {technical_level}
  Domain:     {domain}
  Team:       {team}

Next up: Phase 2 — Data Connection
```

---

## 第 2 阶段：数据连接

**目标：** 把用户的数据接上，让分析能跑起来。

### 问题

**第 1 组：**
1. "Let's connect your data. What do you have?
   - **CSV files** in a local directory
   - **DuckDB** database file
   - **Cloud warehouse** (MotherDuck, Postgres, BigQuery, Snowflake)
   - **Nothing yet** — I want to use a sample dataset"

### 分支逻辑

**如果是 CSV：**
- 问："What's the path to your CSV directory? (relative to this repo root)"
- 核实目录存在，并列出找到的 .csv 文件。
- 若目录不存在，建议替代项（检查 `data/`、`data/examples/`）。
- 确认后，内部调用 Connect Data skill（`/connect-data type=csv`）
  来创建 dataset brain 并对 schema 做剖析。

**如果是 DuckDB：**
- 问："What's the path to your .duckdb file?"
- 核实其存在。
- 确认后，调用 `/connect-data type=duckdb` 建立连接。

**如果是云数仓：**
- 说明："Cloud warehouses connect via MCP (Model Context Protocol). This
  requires configuring `.claude/mcp.json` with your credentials."
- 转到 `/connect-data` 做完整设置。
- 把本阶段标记为 `partial`，`partial_reason: warehouse_mcp_needed`。
- **不要阻塞第 3 阶段。** 继续访谈 —— 数据连接可以
  单独完成。

**如果是尚无 / 示例数据集：**
- 检查 `data/examples/` 中可用的示例数据集。
- 列出它们并附简短说明。
- 如果用户选了一个，复制/链接它并调用 `/connect-data type=csv`。
- 如果用户想跳过：把阶段标记为 `skipped`，并说明 `/connect-data`
  以后仍可用。

### 分叉决策

第 2 阶段之后：
- 如果 `data_connection.status == "complete"`：数据可用。继续到
  第 3 阶段。
- 如果 `data_connection.status == "partial"`（需要数仓 MCP）：仍然继续
  到第 3 阶段。用户可以单独完成数据连接。
- 如果 `data_connection.status == "skipped"`：继续到第 3 阶段。

### 输出

数据集产物由 `/connect-data` skill 创建（manifest.yaml、
schema.md、active.yaml）。第 2 阶段只追踪访谈状态。

更新 `.knowledge/setup-state.yaml`：
- 相应设置 `phases.data_connection.status`
- 设置 `phases.data_connection.completed_at`，若 partial/skipped 则留 null
- 如适用，设置 `phases.data_connection.partial_reason`

### 第 2 阶段摘要

显示：
```
Phase 2 complete — Data Connection

  Source:     {type} ({path or "pending MCP setup"})
  Tables:     {N} tables found  (or "N/A — skipped")
  Status:     {connected | partial — warehouse setup needed | skipped}

Next up: Phase 3 — Business Context
```

---

## 第 3 阶段：业务背景

**目标：** 理解业务，让分析产出相关的洞察，而不只是
数字。

### 问题（分 2-3 组提问）

**第 1 组：**
1. "What does your company/product do? Just a sentence or two is fine."
2. "What are the 2-3 metrics your team cares about most? (e.g., conversion
   rate, MRR, DAU, retention, NPS)"

**第 2 组：**
3. "What business question or problem are you trying to answer right now?
   This helps me prioritize what to explore first." _(optional)_
4. "Are there any current OKRs or goals I should know about?"
   _(optional)_

**第 3 组（如域情况需要）：**
5. "Any key segments I should know about? (e.g., free vs paid users,
   regions, platforms)" _(optional)_
6. "Is there seasonality or known patterns in your data? (e.g., holiday
   spikes, end-of-quarter effects)" _(optional)_

### 校验

- 指标：规范化常见名称（"CVR" -> "conversion rate"，"rev" ->
  "revenue"）。如果某个指标含义不明，请对方简要定义。
- 业务问题：若有提供，用 Question Router skill 对其分类
  （L1-L5）并记录等级。这会为首次分析埋下种子。

### 输出

写入 `.knowledge/user/business-context.md`：

```markdown
# Business Context

## Company & Product

{company_description}

## Key Metrics

| Metric | Definition | Notes |
|--------|-----------|-------|
| {metric_1} | {definition or "TBD"} | {any notes} |
| {metric_2} | {definition or "TBD"} | |

## Current Focus

- **Primary question:** {business_question or "Not specified"}
- **OKRs/Goals:** {okrs or "Not specified"}

## Segments & Patterns

- **Key segments:** {segments or "Not specified"}
- **Seasonality:** {seasonality or "Not specified"}
```

如果用户提供了指标且已连接数据集，用每个指标的存根条目
（名称 + 空定义）为 `.knowledge/datasets/{active}/metrics/index.yaml`
埋下种子。这些以后可以用 `/metrics` 补全。

更新 `.knowledge/setup-state.yaml`：
- 设置 `phases.business_context.status: complete`
- 设置 `phases.business_context.completed_at`

### 第 3 阶段摘要

显示：
```
Phase 3 complete — Business Context

  Product:    {one-line summary}
  Key metrics: {metric_1}, {metric_2}, {metric_3}
  Focus:      {business_question or "General exploration"}

Next up: Phase 4 — Preferences
```

---

## 第 4 阶段：偏好

**目标：** 配置输出风格和沟通偏好，让结果
符合用户实际想要的样子。

### 问题（分 1-2 组提问）

**第 1 组：**
1. "How much detail do you usually want in results?
   - **Executive summary** — just the key findings and recommendations
   - **Standard** — findings with supporting evidence and charts
   - **Deep dive** — full methodology, validation details, and data tables"
2. "Do you prefer lots of charts, or mostly text with a few visuals?
   - **Minimal** — text-first, charts only when essential
   - **Standard** — a chart for each key finding
   - **Chart-heavy** — visualize everything possible"

**第 2 组：**
3. "How do you usually share results? (helps me format exports)
   - Slide deck
   - Email summary
   - Slack message
   - Written brief
   - Jupyter notebook
   - Multiple of the above" _(optional)_
4. "Anything else I should know about how you like to work? (e.g., 'always
   show me the SQL', 'I hate pie charts', 'keep it under 5 slides')"
   _(optional)_

### 校验

- Detail level 必须归到：executive-summary、standard、deep-dive。
- Chart preference 必须归到：minimal、standard、chart-heavy。
- 导出渠道是自由文本，但规范化到 `/export` 的格式列表。

### 输出

更新 `.knowledge/user/profile.md` —— 填好 Communication Preferences
章节：

```markdown
## Communication Preferences

- **Detail level:** {detail_level}
- **Chart preference:** {chart_preference}
- **Narrative style:** {inferred: bullet-points for exec-summary, prose for deep-dive, mixed for standard}
- **Preferred exports:** {export_channels}
- **Custom notes:** {anything_else or "None"}
```

更新 `.knowledge/setup-state.yaml`：
- 设置 `phases.preferences.status: complete`
- 设置 `phases.preferences.completed_at`
- 设置 `status: complete`（若 data_connection 为 partial 则设 `partial`）
- 设置 `last_updated`

---

## Setup 完成摘要

第 4 阶段之后，显示最终摘要：

```
=== SETUP COMPLETE ===

  Role:         {role} ({technical_level})
  Domain:       {domain}
  Data:         {dataset_name} — {N} tables ({source_type})
  Key metrics:  {metric_1}, {metric_2}, {metric_3}
  Detail level: {detail_level}
  Charts:       {chart_preference}

  Status: {"Ready for analysis" | "Partial — data connection pending"}

Get started:
  - Ask a question: "What's our {metric_1} trend?"
  - Explore data:   /data
  - Full pipeline:  /run-pipeline
  - Dev context:    /setup-dev-context (optional — for development workflow preferences)
```

如果 setup 状态为 `partial`，还要显示：
```
  To finish data setup: /connect-data
```

---

## 子命令：/setup status

通过读取 `.knowledge/setup-state.yaml` 显示当前 setup 状态。

### 输出格式

```
Setup Status
============

  Phase 1 — Role & Team:       {status}  {completed_at or ""}
  Phase 2 — Data Connection:   {status}  {completed_at or ""}
  Phase 3 — Business Context:  {status}  {completed_at or ""}
  Phase 4 — Preferences:       {status}  {completed_at or ""}

  Overall: {status}
  Started: {started_at}
  Updated: {last_updated}
```

如果不存在 setup-state.yaml：
```
Setup has not been started yet. Run /setup to begin.
```

---

## 子命令：/setup reset

两层重置系统，以防止意外的数据丢失。

### Tier 1：`/setup reset`

清空画像和偏好（第 1 + 第 4 阶段数据）。**不**触碰
数据连接或业务背景。

**它做什么：**
1. 删除 `.knowledge/user/profile.md`
2. 在 setup-state.yaml 中把 `phases.role_and_team` 和 `phases.preferences`
   重置为 `pending`
3. 设置 `status: partial`
4. 设置 `last_updated`

**需要确认：** 问一次："This will reset your role profile and
output preferences. Your data connections and business context are safe.
Continue? (yes/no)"

### Tier 2：`/setup reset everything`

清空整个 setup —— 画像、偏好、业务背景，以及
数据集连接。这是一项破坏性操作。

**它做什么：**
1. 删除 `.knowledge/user/profile.md`
2. 删除 `.knowledge/user/business-context.md`
3. 删除所有 `.knowledge/datasets/*/` 目录
4. 把 `.knowledge/active.yaml` 重置为 `active_dataset: null`
5. 把 `.knowledge/setup-state.yaml` 重置为全 pending 状态
6. 清除 setup 添加的 `data_sources.yaml` 条目

**需要确认：** 用户必须键入完整短语
`reset everything` 才能确认。

提示：
```
This will erase your entire setup:
  - User profile and preferences
  - Business context
  - All dataset connections and schema documentation

This cannot be undone.

To confirm, type: reset everything
```

如果用户键入了 `reset everything` 以外的任何内容，取消该
操作："Reset cancelled. Your setup is unchanged."

---

## 第 5 阶段说明：开发上下文

第 5 阶段（开发上下文）是可选加入项，独立于核心 setup
流程。它涵盖开发工作流偏好，如 IDE、语言、
框架约定和代码风格偏好。

在第 4 阶段结束时，提一下它的存在：
```
Optional: Run /setup-dev-context to configure development workflow
preferences (IDE, languages, code style). This is independent of
your analytics setup.
```

本 skill **不**实现第 5 阶段。`/setup-dev-context` skill
单独处理它。

---

## 恢复逻辑

当调用 `/setup` 且 `.knowledge/setup-state.yaml` 已存在时：

1. 读取状态文件。
2. 找到第一个状态为 `pending` 的阶段。
3. 如果所有阶段都 `complete`，显示：
   ```
   Setup is already complete. Use /setup status to review,
   or /setup reset to start over.
   ```
4. 如果部分阶段已完成，简短问候并恢复：
   ```
   Welcome back. Phases 1-2 are done. Picking up at Phase 3 —
   Business Context.
   ```
5. 如果某阶段为 `partial`，提出完成它或跳过：
   ```
   Phase 2 (Data Connection) is partially complete — your warehouse
   needs MCP configuration. Want to finish that now, or continue
   to Phase 3?
   ```

---

## 反模式

1. **永远不要一次性甩出所有问题。** 始终分 2-3 个一组并等待
   回应。
2. **永远不要因可选字段而阻塞。** 如果用户说"跳过"或"以后"，
   接受它并继续。
3. **永远不要静默覆盖已有的画像数据。** 如果开始第 1 阶段时
   profile.md 已存在，要警告："You already have a profile.
   Running setup will overwrite it. Continue?"
4. **永远不要把凭证存进 setup-state.yaml。** 数据连接
   凭证走 `/connect-data`，且仅存在 manifest.yaml
   或环境变量中。
5. **永远不要跳过状态文件更新。** 每个阶段完成都必须在
   进入下一阶段前写入 setup-state.yaml。
6. **永远不要在没先问第 1 阶段的情况下跑第 3 阶段及以后**（恢复时除外）。
   第 1 阶段的角色背景塑造了后续
   阶段如何提问。
7. **永远不要混用重置层级。** `/setup reset` 始终是 Tier 1。
   Tier 2 需要明确的 `reset everything` 短语。

---

## 边界情况

| Scenario | Handling |
|----------|----------|
| User runs `/setup` but profile.md already exists | Warn and ask to confirm overwrite before proceeding |
| CSV path does not exist | Suggest alternatives, check `data/` and `data/examples/` |
| User provides warehouse type but no MCP | Mark Phase 2 as partial, continue interview |
| User skips all optional fields | That is fine. Record nulls and proceed. |
| User wants to jump to a specific phase | Allow it: "/setup phase 3" resumes from Phase 3 |
| Session ends mid-interview | State is saved per-phase. Next `/setup` resumes. |
| `/setup` called inside a pipeline | Warn: "Setup changes may affect the running pipeline. Finish the pipeline first, or continue at your own risk." |
| User gives contradictory answers | Ask once for clarification. Record what they confirm. |

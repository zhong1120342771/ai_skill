# AI Analyst v2

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Claude Code Required](https://img.shields.io/badge/requires-Claude%20Code-blueviolet.svg)](https://claude.ai/code)
[![Tests](https://img.shields.io/badge/tests-606%20passing-brightgreen.svg)](#)

一个构建在 Claude Code 上的 AI 产品分析师。你提出一个业务问题，它运行一条由 18 个 agent 组成的流水线，对问题进行框定、探索你的数据、找到根因、构建叙事，并交给你一份经过校验、带演讲备注的幻灯片。是几分钟，而非几周。

**18** 个专用 agent | **39** 个自动应用的 skill | **20** 个 slash 命令 | 基于 DAG 的并行执行 | PDF + HTML 导出

---

## 开始之前

这是给分析师用的工具，不是用来替代分析师的。它能完成人类分析师约 80% 的工作，也就是最耗时的那 80%。但前提是你得是专家。

**你就是评估标准。** 拿你了如指掌的数据来跑它。拿你本周本来就要做的报告来跑它。当它选错列或误读某个指标时，你会立刻发现，因为那个查询你早就写过。你纠正它，它保存这次纠正，下次就不再犯同样的错。这就是整个闭环。看、懂、纠、继续。

别把它交给无法校验输出的人。别拿你从没见过的数据来跑。它产出的分析在送到任何利益相关者面前之前，都需要你的判断。如果你跳过校验，你会得到听起来很有把握、却可能是错的数字。如果你做了校验，你会比以往任何时候都快。

**构建它的副产品就是工作本身。** 你不是抽出工作时间去搭一个 AI 工具，你是在用它做你真正的工作。第一份分析会稍慢一些，因为你在连接数据、教它你的背景。到第三份时，你已经比手工更快。到下周，你做的分析从 5 份变成 15 份。

**它不是开箱即用的。** 它是起点，不是成品。Opus 4.6 已具备相应的模型能力，但你需要教它你的数据、你的指标、你的业务背景。它错了就纠正它。把它养成适合你具体场景的样子，或者拆开重建成你想要的样子。这些 agent、skill 和流水线都是你能阅读和修改的 markdown 文件，没有任何隐藏。

**自带你的数据。** 不捆绑任何数据集。用 `/connect-data` 连接你的 CSV、DuckDB、Postgres、BigQuery 或 Snowflake，然后开始分析。

---

## V2 新增内容

V2 是对智能层的彻底重建。V1 的流水线和 agent 仍以同样方式运作 —— 使用体验上你不会察觉差别。变的是底下的一切。

| 领域 | V1 | V2 |
|------|----|----|
| **数据** | 捆绑的 NovaMart 电商数据集 | 自带 —— CSV、DuckDB、Postgres、BigQuery、Snowflake |
| **上手** | 手动配置，读文档 | `/setup` 访谈了解你的角色、数据和业务背景 |
| **记忆** | 跨会话无状态 | 知识系统持久保存纠错、经验、查询模式、业务术语表 |
| **自学习** | 无 | 采集反馈、记录纠错、检索经证实的 SQL 模式 —— 绝不重复同一错误 |
| **主题** | 硬编码图表样式 | 基于 YAML 的主题系统，含品牌色、符合 WCAG 的配色 |
| **业务背景** | 无 | 组织知识库 —— 术语表、指标、产品、团队。支持 Notion 导入。 |
| **流水线** | 单次运行，失败重启 | 运行跟踪（`/runs`）、可靠恢复、用于 Slack/邮件输出的 comms drafter |
| **测试** | 极少 | 606 个测试，使用合成 fixture，不依赖外部数据 |
| **数据集耦合** | NovaMart 表名硬编码在 agent 中 | 完全与数据集解耦 —— agent 从激活的 manifest 和 schema 解析 |

---

## 不知道能做什么？直接问。

Claude 了解整个系统 —— 每一个 agent、skill、命令和数据集。如果卡住了，就问它：

```
What can I do with this data?
What should I run to refresh the deck?
How do I connect my own CSV files?
Which agents handle root cause analysis?
Re-run just the chart maker and deck creator.
```

Claude 会告诉你确切的命令。你不需要记住本 README 里的任何东西。把它当作参考 —— Claude 才是向导。

---

## 快速开始

**1. 安装 Claude Code**（需要 [Claude Pro 订阅](https://claude.ai/pro)）

```bash
npm install -g @anthropic-ai/claude-code
```

**2. 克隆并安装**

```bash
git clone https://github.com/ai-analyst-lab/ai-analyst.git
cd ai-analyst
pip install -e ".[dev]"
```

**3. 启动 Claude Code**

```bash
claude
```

**4. 接入你的数据，开始**

```
/connect-data
```

或跳过向导，把数据放在某个目录里直接提问：

```
/run-pipeline data_path=data/my_csvs/ question="Why is conversion dropping?"
```

完整安装细节见：[docs/setup-guide.md](docs/setup-guide.md)

---

## 你能做的五件事

### 1. 问一个快速问题

```
What's our conversion rate by device?
```

Claude 查询数据并返回一个带图表的答案。简单问题在 2 分钟内得到回答，无需运行完整流水线。

### 2. 跑一次完整分析

```
/run-pipeline data_path=data/your_dataset/ question="What's driving the decline in conversion?"
```

流水线跨 4 个阶段运行 18 个 agent：框定问题、分析数据、构建故事、制作幻灯片。你会得到经校验的分析、品牌化图表、一段叙事，以及带演讲备注的幻灯片。导出为 PDF 和 HTML。

### 3. 探索一个数据集

```
/explore
```

不必投入完整分析的交互式数据浏览。预览表、检查分布、发现模式、形成假设。用 `/data users` 查看某张表的 schema。

### 4. 接入你自己的数据

```
/connect-data
```

引导式向导，带你接入 CSV 文件、本地 DuckDB、Postgres、BigQuery 或 Snowflake。自动剖析你的数据、生成 schema 文档，并跨会话记住你的数据集背景。

### 5. 做一张图表

```
Make a funnel chart of the checkout flow, highlighting the biggest drop-off step.
```

Claude 按 Storytelling with Data 方法论生成图表：暖米白背景、去杂坐标轴、行动标题、用直接标签取代图例。

---

## 工作原理：流水线

当你运行 `/run-pipeline` 时，Claude 编排 18 个 agent，跨 4 个阶段：

```
1. FRAME              2. ANALYZE                          3. STORY                 4. DECK
+-----------------+   +-----------------------------+   +--------------------+   +------------------+
| Question        |   | Data Explorer               |   | Story Architect    |   | Storytelling     |
|   Framing       |   |   > Source Tie-Out           |   |   > Coherence      |   |   > Deck Creator |
|   > Hypothesis  |   |   > Descriptive Analytics    |   |     Reviewer       |   |   > Slide Review |
|     Generation  |   |   > Root Cause Investigator  |   |   > Chart Maker    |   |   > Close the    |
|                 |-->|   > Validation               |-->|   > Design Critic  |-->|     Loop         |
+-----------------+   |   > Opportunity Sizer        |   +--------------------+   +------------------+
                      +-----------------------------+
```

**阶段 1 — 框定：** 把你的业务问题结构化为带可检验假设的分析性问题。检查点：分析开始前先复核框定。

**阶段 2 — 分析：** 探索数据、核验加载完整性、运行分群/漏斗/驱动因素分析、下钻到根因、校验发现、测算机会。检查点：自动化质量门。

**阶段 3 — 故事：** 设计故事板（背景-张力-化解弧线）、带碰撞检测地生成图表，并对照 16 点检查清单复核视觉质量。

**阶段 4 — 幻灯片：** 撰写面向利益相关者的叙事、用 HTML 组件构建品牌化 Marp 幻灯片、复核幻灯片设计，并确保每条建议都有后续计划。导出为 PDF 和 HTML。

你不必每次都跑完整套。五种执行计划让你只跑需要的部分：

| 计划 | 何时使用 | 运行什么 |
|------|----------|-----------|
| `full_presentation` | 从完整分析到幻灯片 | 全部 18 个 agent |
| `deep_dive` | 不要演示的分析 | 仅阶段 1-2 |
| `quick_chart` | 只要一张图 | Chart Maker + Design Critic |
| `refresh_deck` | 重做演示层 | 阶段 3-4（复用分析） |
| `validate_only` | 检查既有成果 | Validation + Source Tie-Out |

```
/run-pipeline data_path=data/your_dataset/ question="..." plan=deep_dive
```

如果流水线被中断，从上次停下的地方恢复：

```
/resume-pipeline
```

预览将会运行什么而不实际执行：

```
/run-pipeline data_path=data/your_dataset/ question="..." dry-run=true
```

---

## 工作原理：DAG 引擎

流水线不是逐个运行 agent。它自动解析依赖，并行运行相互独立的 agent：

```
Tier 0 (parallel)    Question Framing -----> Hypothesis
                     Data Explorer --------> Source Tie-Out
                                                  |
Tier 2 (parallel)              Descriptive Analytics  /  Overtime Trend  /  Cohort Analysis
                                        |
Tier 3 (sequential)           Root Cause --> Validation --> Opportunity Sizer
                                                                |
Tier 4 (sequential)           Story Architect --> Coherence Review
                                                       |
Tier 5 (parallel fan-out)     Chart Maker (per beat) --> Design Critic
                                                              |
Tier 6 (sequential)           Storytelling --> Deck Creator --> Slide Review --> Close the Loop
```

- **并行执行：** 同一 tier 内的 agent 并发运行（最多同时 3 个）。Tier 0 同时启动 Question Framing 和 Data Explorer。
- **自动依赖解析：** 引擎读取 `agents/registry.yaml`，用拓扑排序计算执行 tier。
- **熔断器：** 若同一 tier 内有 3 个 agent 失败，流水线停止并给出诊断报告。
- **超时：** 每个 agent 有 5 分钟。超时重试一次。关键 agent（source tie-out、validation）会停止流水线；非关键 agent（design critic）则优雅降级。
- **检查点：** 阶段之间的质量门。两个是自动的（分析核验、最终幻灯片 lint），两个面向用户（框定复核、故事板复核）。说 "just do it" 可跳过面向用户的那两个。

---

## 全部命令

| 命令 | 作用 | 示例 |
|---------|-------------|---------|
| `/run-pipeline` | 从完整分析到幻灯片 | `/run-pipeline data_path=data/your_dataset/ question="Why is conversion dropping?"` |
| `/resume-pipeline` | 恢复被中断的流水线 | `/resume-pipeline` |
| `/explore` | 交互式数据探索 | `/explore events` |
| `/data` | 展示激活数据集的 schema | `/data users` |
| `/datasets` | 列出所有已连接数据集 | `/datasets` |
| `/switch-dataset` | 切换激活数据集 | `/switch-dataset my_dataset` |
| `/connect-data` | 添加新数据源 | `/connect-data` |
| `/setup` | 交互式上手访谈 | `/setup` |
| `/metrics` | 浏览指标词典 | `/metrics conversion_rate` |
| `/history` | 查看历史分析 | `/history` |
| `/patterns` | 查看反复出现的模式 | `/patterns --global` |
| `/export` | 以多种格式导出结果 | `/export slides` 或 `/export email` 或 `/export slack` |
| `/forecast` | 生成时序预测 | `/forecast` |
| `/runs` | 列出、查看、对比流水线运行 | `/runs` |
| `/business` | 浏览组织知识 | `/business glossary` |
| `/log-correction` | 记录数据或方法纠错 | `/log-correction` |
| `/architect` | 多角色规划方法论 | `/architect` |
| `/notion-ingest` | 从 Notion 导入业务背景 | `/notion-ingest` |
| `/compare-datasets` | 跨数据集对比指标 | `/compare-datasets` |
| `/setup-dev-context` | 为开发团队添加代码库背景 | `/setup-dev-context` |

或者直接用大白话问。"Show me conversion by device" 和任何命令一样好用。

---

## 图表与可视化

每张图表都遵循 Storytelling with Data 方法论：

```
Your Data --> chart_helpers.py --> Base Chart (150 DPI)
                                      |
                              Collision Check
                              (3 fix strategies)
                                      |
                              Marp Deck (HTML components)
                                      |
                              marp_linter.py (8 check categories)
                                      |
                              marp_export.py --> PDF + HTML
```

**自动发生的事：**

- `swd_style()` 应用暖米白背景（#F7F6F2），去除图表杂乱（网格线、边框、冗余图例），设定一致的排版
- 每张图都获得一个行动标题（要点陈述，而非标签）和一个副标题（数据来源、时间范围）
- 尽可能用直接标签替代图例
- 碰撞检测检查文字重叠，带 3 种自动修复策略：偏移标签、缩小字号或丢弃最不重要的标签。存在未化解碰撞的图表会停止流水线。
- 幻灯片使用品牌化 HTML 组件：KPI 卡、发现卡、建议行、so-what 提示、前后对比面板、时间线等
- 一道 lint 门在导出前校验每份幻灯片：检查 frontmatter 完整性、HTML 组件使用（至少 3 种类型）、有效的幻灯片 class、幻灯片数量和节奏
- 基于 YAML 的主题，支持品牌色覆写和符合 WCAG 的配色（见 [docs/theming.md](docs/theming.md)）

---

## 你的数据

本仓库出厂干净 —— 不捆绑任何数据集。接入你自己的数据，系统会围绕它构建背景。

### 接入你自己的数据

运行 `/connect-data` 进行引导式安装，或 `/setup` 进行完整上手访谈。支持的数据源：

- **CSV 文件** —— 放进一个目录，把 Claude 指向它
- **DuckDB** —— 本地或 MotherDuck
- **Postgres** —— 任何 Postgres 兼容数据库
- **BigQuery** —— 用服务账号的 Google BigQuery
- **Snowflake** —— 用用户名/密码或密钥对的 Snowflake

系统自动剖析你的数据、生成 schema 文档、记录数据怪癖，并在 `.knowledge/datasets/` 中跨会话记住背景。

### 示例数据集

`data/examples/` 中提供了带 README 指南的精选公开数据集。

### 回退链

如果你的主连接失败，系统会自动回退：

1. 主连接（如通过 MCP 的 MotherDuck）
2. 本地 DuckDB（来自 `manifest.local_data.duckdb`）
3. 通过 pandas 的 CSV 文件（来自 `manifest.local_data.path`）

系统总会告诉你当前使用的是哪个数据源。

---

## 刚刚发生了什么？（输出指南）

运行流水线后，你会看到：

```
outputs/
  question_brief_YYYY-MM-DD.md          # 你的问题，结构化
  hypothesis_doc_YYYY-MM-DD.md          # 可检验的假设
  data_inventory_YYYY-MM-DD.md          # 存在哪些数据
  analysis_report_YYYY-MM-DD.md         # 含发现的完整分析
  validation_<dataset>_YYYY-MM-DD.md    # 对发现的独立校验
  narrative_<dataset>_YYYY-MM-DD.md     # 可直接面向利益相关者的故事
  deck_<dataset>_YYYY-MM-DD.marp.md    # 幻灯片（Marp 源文件）
  deck_<dataset>_YYYY-MM-DD.pdf        # PDF 导出
  deck_<dataset>_YYYY-MM-DD.html       # HTML 导出（自包含）
  close_the_loop_YYYY-MM-DD.md         # 建议的后续计划
  charts/                               # 所有生成的图表

working/                                # 中间文件（可安全删除）
  pipeline_state.json                   # 流水线进度（供 /resume-pipeline 使用）
  pipeline_metrics.json                 # 执行计时与并行效率
  storyboard_<dataset>.md              # 故事节拍 + 视觉映射
  design_review_<dataset>.md           # 图表质量复核（16 点清单）
  investigation_<dataset>.md           # 根因下钻日志
  sizing_*.md                           # 含敏感性分析的机会测算
```

`outputs/` 包含你的交付物。`working/` 包含支撑可恢复性和调试的中间产物。

---

## 定制

| 想要... | 这样做 |
|-----------|---------|
| 改变 Claude 的思考方式 | 编辑 `CLAUDE.md`（AI 的人设、规则、工作流） |
| 添加新 skill | 创建 `.claude/skills/my-skill/skill.md`，在 `CLAUDE.md` 中引用它 |
| 添加新 agent | 以 `agents/CONTRACT_TEMPLATE.md` 为起点创建 `agents/my-agent.md` |
| 改变幻灯片主题 | 在 `themes/brands/` 中创建 YAML 主题（见 [docs/theming.md](docs/theming.md)） |
| 添加幻灯片组件 | 编辑 `templates/marp_components.md`（片段库） |
| 修改流水线 | 编辑 `.claude/skills/run-pipeline/skill.md`（规则、检查点、执行） |
| 加入 agent DAG | 编辑 `agents/registry.yaml`（依赖、执行顺序） |

---

<details>
<summary><strong>全部 18 个 Agent</strong>（点击展开）</summary>

Agent 是 `agents/` 目录中的 markdown 提示词模板。每个定义一个多步骤工作流，含运行时填入的 `{{VARIABLES}}`。要调用某个 agent，让 Claude 运行它，或用 `/run-pipeline` 编排全部。

### 框定

| Agent | 作用 | 流水线步骤 |
|-------|-------------|---------------|
| question-framing | 把业务问题转化为带假设和数据需求的结构化分析性问题 | 1 |
| hypothesis | 跨成因类别生成可检验假设：产品变更、技术问题、外部因素、结构变化 | 3 |

### 数据发现

| Agent | 作用 | 流水线步骤 |
|-------|-------------|---------------|
| data-explorer | 剖析数据集：schema、分布、质量、缺口、支持的分析 | 4 |
| source-tieout | 通过对比 pandas 与 DuckDB 的行数、空值和求和，核验数据加载正确。不一致则停止。 | 4.5 |

### 分析

| Agent | 作用 | 流水线步骤 |
|-------|-------------|---------------|
| descriptive-analytics | 分群、漏斗分析和驱动因素分析，识别发生了什么以及为什么 | 5 |
| overtime-trend | 时序分析：趋势、异常、季节性、带标注的时间线图 | 5 |
| cohort-analysis | 留存曲线、队列对比、同期群分析、队列 LTV | 5 |
| root-cause-investigator | 逐层下钻各维度，找到具体、可行动的根因 | 6 |
| validation | 四层核验：结构、逻辑、业务规则和辛普森悖论检查 | 7 |
| opportunity-sizer | 用敏感性分析量化业务影响，显示哪些假设最关键 | 8 |

### 讲故事

| Agent | 作用 | 流水线步骤 |
|-------|-------------|---------------|
| story-architect | 设计带背景-张力-化解弧线的故事板，把节拍映射到视觉格式和 HTML 组件 | 9 |
| narrative-coherence-reviewer | 在任何制图之前，复核故事板的故事缺口、节拍流畅度和递进深度 | 10 |
| chart-maker | 生成带碰撞检测和行动标题的 SWD 风格图表 | 12 |
| visual-design-critic | 对照 16 点 SWD 清单外加 5 项陷阱检查和 6 项进阶技法检查复核图表。同时复核幻灯片级别的设计。 | 13/17 |

### 演示

| Agent | 作用 | 流水线步骤 |
|-------|-------------|---------------|
| storytelling | 把发现转化为可面向利益相关者的叙事，含执行摘要、发现、洞察和建议 | 15 |
| deck-creator | 用 HTML 组件、演讲备注和正确主题样式构建品牌化 Marp 幻灯片 | 16 |
| comms-drafter | 生成面向利益相关者的沟通：Slack 摘要、邮件简报、高管摘要 | 19 |

### 独立

| Agent | 作用 | 流水线步骤 |
|-------|-------------|---------------|
| experiment-designer | 设计 A/B 测试，含功效估计、护栏选择和决策规则 | （按需） |

</details>

---

<details>
<summary><strong>全部 39 个 Skill</strong>（点击展开）</summary>

Skill 是 `.claude/skills/` 中的指令文件，当触发条件匹配时 Claude 会自动遵循，你无需手动调用。当你要一张图表时，Visualization Patterns skill 会激活。当你开始分析时，Data Quality Check skill 会运行。

### 始终激活

这些 skill 塑造每一次交互：

| Skill | 作用 |
|-------|-------------|
| analysis-design-spec | 确保每次分析都从计划开始：问题、决策、所需数据、成功标准 |
| close-the-loop | 每条建议都获得决策负责人、成功指标、后续日期和回退计划 |
| data-quality-check | 在分析开始前校验数据完整性和一致性 |
| data-profiling | 深度剖析 schema、分布、时间模式和异常 |
| feedback-capture | 把用户纠错和方法指导采集到经验系统 |
| first-run-welcome | 根据可用数据为新用户提供自适应上手 |
| guardrails | 为每个成功指标配一个护栏指标；对正向发现检查权衡 |
| knowledge-bootstrap | 会话开始时加载激活数据集背景、schema、怪癖和用户画像 |
| metric-spec | 用于无歧义定义指标的标准模板 |
| question-framing | 用 Question Ladder 框架结构化模糊的业务问题 |
| question-router | 把问题分类为 L1-L5 并路由到正确的响应路径 |
| semantic-validation | 四层校验栈外加置信度评分 |
| stakeholder-communication | 让发现适配受众：同一洞察，不同表述 |
| tracking-gaps | 识别所需数据不存在的情形，并产出埋点需求 |
| triangulation | 在呈现前对照多个来源交叉验证发现 |
| visualization-patterns | 确保每张图表遵循 SWD 设计标准 |
| archaeology | 写新查询前，从查询考古中检索经证实的 SQL 模式 |

### 按需（Slash 命令）

这些在你使用命令时激活：

| Skill | 命令 | 作用 |
|-------|---------|-------------|
| run-pipeline | `/run-pipeline` | 带 DAG 执行、检查点和导出的端到端分析 |
| resume-pipeline | `/resume-pipeline` | 从上一个完成的 agent 恢复被中断的工作 |
| explore | `/explore` | 快速交互式数据探索 |
| export | `/export` | 导出为幻灯片、邮件、Slack 消息或数据 |
| connect-data | `/connect-data` | 添加新数据集的引导式向导 |
| switch-dataset | `/switch-dataset` | 切换激活数据集 |
| datasets | `/datasets` | 列出所有已连接数据集及状态 |
| data-inspect | `/data` | 展示激活 schema，可选下钻到某张表 |
| metrics | `/metrics` | 浏览和管理指标词典条目 |
| history | `/history` | 从归档中查看历史分析 |
| patterns | `/patterns` | 查看跨分析反复出现的模式 |
| forecast | `/forecast` | 生成时序预测 |
| compare-datasets | `/compare-datasets` | 跨两个数据集对比指标 |
| setup | `/setup` | 针对画像、数据和业务背景的交互式上手访谈 |
| setup-dev-context | `/setup-dev-context` | 为开发团队添加代码库背景 |
| runs | `/runs` | 列出、查看、对比和清理流水线运行 |
| business | `/business` | 浏览组织知识（术语表、指标、产品、团队） |
| log-correction | `/log-correction` | 用于方法修正的刻意纠错记录 |
| architect | `/architect` | 为新项目服务的多角色规划方法论 |
| notion-ingest | `/notion-ingest` | 爬取 Notion 工作区以抽取业务背景 |

### 演示与知识

| Skill | 作用 |
|-------|-------------|
| presentation-themes | 幻灯片的主题标准：布局、排版、配色 |
| archive-analysis | 把已完成的分析保存到知识系统以备日后调用 |

</details>

---

<details>
<summary><strong>全部辅助模块</strong>（点击展开）</summary>

`helpers/` 中的 Python 模块，由 agent 在执行时调用：

### 图表与可视化

| 模块 | 作用 |
|--------|-------------|
| `chart_helpers.py` | 核心 SWD 制图：`swd_style()`、`highlight_bar()`、`highlight_line()`、`action_title()`、`annotate_point()`、`save_chart()`、`stacked_bar()`、`retention_heatmap()`、`sensitivity_table()`、`funnel_waterfall()`、`big_number_layout()`、`check_label_collisions()` |
| `chart_palette.py` | 符合 WCAG 的配色，支持品牌色覆写 |
| `chart_style_guide.md` | 完整 SWD 参考：配色、去杂清单、图表决策树、反模式 |
| `analytics_chart_style.mplstyle` | Matplotlib 样式文件：米白背景、无上/右边框、无衬线、150 DPI |
| `marp_linter.py` | 校验 Marp 幻灯片：frontmatter、HTML 组件、幻灯片 class、节奏、标题碰撞 |
| `marp_export.py` | 通过 Marp CLI 把 Marp 幻灯片导出为 PDF 和 HTML，并解析主题 |
| `theme_loader.py` | 基于 YAML 的主题系统，支持品牌色加载和继承 |

### 数据与 SQL

| 模块 | 作用 |
|--------|-------------|
| `data_helpers.py` | 数据源抽象：`detect_active_source()`、`check_connection()`、`read_table()`、`list_tables()` |
| `sql_helpers.py` | SQL 合理性检查：join 基数、百分比求和、日期边界、重复、时间覆盖 |
| `sql_dialect.py` | 面向 Postgres、BigQuery、Snowflake、DuckDB 的 SQL 方言路由 |
| `connection_manager.py` | 多仓库连接的统一接口 |
| `tieout_helpers.py` | 数据源对账：带容差的双路径对比（pandas vs DuckDB） |
| `schema_profiler.py` | 自动 schema 发现与文档化 |

### 分析与统计

| 模块 | 作用 |
|--------|-------------|
| `analytics_helpers.py` | 用于分群、分解和驱动因素分析的工具 |
| `stats_helpers.py` | 统计检验：比例、均值、Mann-Whitney、卡方、bootstrap CI、效应量 |
| `forecast_helpers.py` | 带趋势和季节性检测的时序预测 |
| `deep_profiler.py` | 进阶数据质量：分布、相关性、完整性、异常 |

### 校验

| 模块 | 作用 |
|--------|-------------|
| `structural_validator.py` | 第 1 层：schema、主键、完整性检查 |
| `logical_validator.py` | 第 2 层：聚合一致性、趋势逻辑 |
| `business_rules.py` | 第 3 层：对照领域规则的合理性检查 |
| `business_validation.py` | 对照组织知识的业务规则校验 |
| `simpsons_paradox.py` | 第 4 层：辛普森悖论扫描 |
| `confidence_scoring.py` | 把四层综合为 A-F 置信度评级 |

### 知识与背景

| 模块 | 作用 |
|--------|-------------|
| `context_loader.py` | 会话开始时加载激活数据集背景、schema、怪癖 |
| `archaeology_helpers.py` | 查询考古：检索并匹配经证实的 SQL 模式 |
| `business_context.py` | 组织知识：术语表、指标、产品、团队 |
| `entity_resolver.py` | 跨数据集消歧实体引用 |
| `metric_validator.py` | 对照 schema 校验指标定义 |
| `schema_migration.py` | 处理知识文件的 schema 版本迁移 |
| `miss_rate_logger.py` | 跟踪知识系统未命中率以供改进 |

### 系统

| 模块 | 作用 |
|--------|-------------|
| `error_helpers.py` | 带建议的友好错误提示 |
| `file_helpers.py` | 原子文件写入、内容哈希、安全 YAML I/O |
| `health_check.py` | 数据连通性和依赖的系统健康诊断 |
| `lineage_tracker.py` | 跟踪数据从来源经变换到发现的血缘 |
| `pipeline_state.py` | 用于运行跟踪和恢复的流水线状态管理 |

</details>

---

## 系统要求

- **Python 3.10+**
- **Node.js 18+**（用于 Claude Code）
- **Claude Code** 以及 [Claude Pro 订阅](https://claude.ai/pro)（$20/月）
- **互联网连接**（用于 Claude API 和可选的 MotherDuck）

---

## 获取帮助

- **安装指南：** [docs/setup-guide.md](docs/setup-guide.md)
- **主题：** [docs/theming.md](docs/theming.md)
- **问题或缺陷：** 开一个 [GitHub Issue](https://github.com/ai-analyst-lab/ai-analyst/issues)

---

## 许可证

[MIT](LICENSE) —— 随你怎么用。

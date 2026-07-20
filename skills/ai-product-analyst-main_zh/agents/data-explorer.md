<!-- CONTRACT_START
name: data-explorer
description: Discover what data exists in a source, profile its quality and completeness, identify tracking gaps, and recommend supported analyses.
inputs:
  - name: DATA_SOURCE
    type: str
    source: user
    required: true
  - name: ANALYSIS_GOALS
    type: str
    source: user
    required: false
outputs:
  - path: outputs/data_inventory_{{DATE}}.md
    type: markdown
  - path: working/data_inventory_raw.md
    type: markdown
depends_on: []
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: 4
CONTRACT_END -->

# Agent: Data Explorer

## 目的
发现给定数据源里有哪些数据，画像其质量与完整性，识别埋点缺口，并推荐该数据能支撑哪些分析问题。

## 输入
- {{DATA_SOURCE}}：要探查的数据源。可以是：
  - 指向 CSV、Parquet 或 JSON 文件的路径（例如 `data/{dataset}/events.csv`）
  - 含多个数据文件的目录（例如 `data/{dataset}/`）
  - MotherDuck/DuckDB 连接串（例如 `md:{database}`）
  - 经由 ConnectionManager 的外部数仓（Postgres、BigQuery、Snowflake）
  - SQLite 数据库文件路径（例如 `data/analytics.db`）
  - 带连接说明的数据源文字描述

  对于外部数仓，用 `helpers/connection_manager.py` 的 `ConnectionManager` 和 `helpers/sql_dialect.py` 的 `get_dialect()` 生成数仓特定的 SQL。用 `helpers/schema_profiler.py` 的 `profile_external_warehouse()` 做 schema 发现。
- {{ANALYSIS_GOALS}}：（可选）团队想分析什么——一份问题简报、一份假设文档，或对分析目标的纯文本描述。若提供，agent 会针对这些目标定制其推荐。若未提供，agent 产出一份通用盘点。

## 工作流

### 第 0 步：检查已有 Schema

连接前，先检查当前数据集是否已存在结构化 schema：

1. 检查 `data/schemas/{active}.yaml` —— 若有，用 `helpers/data_helpers.py` 的 `schema_to_markdown()` 加载它，得到预建的 schema 概览。这能避免对种子数据集重复画像。
2. 检查 `.knowledge/datasets/{active}/schema.md` —— 若有，读取它以获取已知表和列的上下文。
3. 检查 `.knowledge/datasets/{active}/last_profile.md` —— 若存在较近的画像，用它在第 2 步跳过基础画像。

若以上任一存在，以其为起点，并把第 2 步聚焦于核验和缺口检测，而非完整画像。若都不存在，进行完整发现。

### 第 1 步：连接并枚举
连接到 {{DATA_SOURCE}}，枚举所有可用数据对象：

**对文件型数据源（CSV、Parquet、JSON）：**
- 列出所有文件、其大小和行数
- 从每个文件读取列名和数据类型
- 采样前 10 行以理解数据形态
- 识别分隔符、编码及任何解析问题

**对数据库型数据源（MotherDuck、DuckDB、SQLite）：**
- 列出所有 schema、表和视图
- 每张表：列名、数据类型、行数
- 在可见时识别主键、外键和索引
- 如适用，列出任何存储过程或函数

**对含多个文件的目录：**
- 枚举所有文件及其格式
- 把相关文件分组（例如 events_2024_01.csv、events_2024_02.csv 是按月分区）
- 注明文件间任何不一致（列数不同、命名变化）

把结果写到 `working/data_inventory_raw.md` 作为中间产出。

### 第 2 步：对每张表/文件画像
对发现的每张表或文件，计算：

**形态与覆盖：**
- 总行数
- 总列数
- 日期范围（任意时间戳/日期列的最小和最大值）
- 关键标识列的去重计数（user_id、session_id、event_type 等）

**列级画像（对每列）：**
- 数据类型（string、integer、float、boolean、timestamp 等）
- 空值计数和空值率（百分比）
- 去重值计数
- 数值列：min、max、mean、median、标准差
- 类别列：出现频率最高的前 10 个值及其计数
- 时间戳列：最小日期、最大日期、日期覆盖中的任何缺口

**视数据源类型，用 Python（pandas）或 SQL 执行此画像。** 写出真实代码、运行它、捕获结果。不要估计或猜测——计算真实值。

### 第 3 步：评估数据质量
应用 Data Quality Check skill（`.claude/skills/data-quality-check/skill.md`）。对每张表/文件，检查：

**完整性：**
- 把空值率 >5% 的列标为 WARNING，>20% 标为 BLOCKER
- 把缺天/缺周的日期范围标为 WARNING
- 把行数异常偏低的表标为 WARNING

**一致性：**
- 检查重复行（完全重复和关键列上的近似重复）
- 核验跨表参照完整性（例如 events 中所有 user_id 都存在于 users）
- 检查数据类型不匹配（数值列里有字符串、日期格式不一致）
- 检查不可能的值（负计数、未来日期、百分比 >100%）

**分布合理性：**
- 标记任何 >50% 的值是同一个值的列（低基数警告）
- 标记带极端异常值（偏离均值 >3 个标准差）的数值列
- 标记数据量随时间的任何突变（潜在的埋点断裂）

为每个发现评定严重度：
- **BLOCKER**：若不解决分析就会出错（例如关键列 80% 空值）
- **WARNING**：结果应谨慎解读（例如分群列 10% 空值）
- **INFO**：值得一提但不影响分析（例如 0.1% 重复）

### 第 4 步：识别埋点缺口
应用 Tracking Gap Identification skill（`.claude/skills/tracking-gaps/skill.md`）：

**若提供了 {{ANALYSIS_GOALS}}：**
- 从分析目标（问题、假设或纯文本）中提取数据需求
- 对每个所需数据点，检查它是否存在于盘点中
- 把每个分类为：AVAILABLE（存在且质量好）、PARTIAL（存在但有质量问题）、MISSING（数据中没有）、DERIVABLE（不直接存在但可由现有字段算出）
- 对 MISSING 字段：给出变通方案或替代方法
- 对 DERIVABLE 字段：说明如何计算（例如 "会话时长可由会话内首尾事件的时间戳算出"）

**若未提供 {{ANALYSIS_GOALS}}：**
- 基于现有字段，识别这份数据**能**支撑哪些常见分析问题
- 注明明显缺口："该数据集有用户事件但无用户属性——无法按用户属性分群"
- 建议增加哪些数据能让数据集更有分析价值

### 第 5 步：生成推荐分析
基于数据盘点和质量评估，推荐具体分析：

**对每条推荐，明确：**
- **分析描述**：一句话描述要调研什么
- **为何此数据支撑它**：哪些表/列让它可行
- **建议方法**：漏斗分析、分群、趋势分析等
- **要用的 agent**：哪个 agent 会执行它（Descriptive Analytics Agent、Overtime/Trend Agent 等）
- **注意事项**：会影响此分析的任何数据质量问题

生成 3-5 条推荐，按数据支撑强度排序（最可行的在前）。

**若提供了 {{ANALYSIS_GOALS}}**，额外把每个目标映射到可用数据，并标明它是完全支撑、部分支撑还是不支撑。

### 第 5b 步：记录血缘
记录该 agent 的数据流以便追溯：

```python
from helpers.lineage_tracker import track

track(
    step=4,  # pipeline_step from CONTRACT
    agent="data-explorer",
    inputs=[str(DATA_SOURCE)],  # source files/tables explored
    outputs=["outputs/data_inventory_{{DATE}}.md"],
    metadata={"tables_profiled": len(tables), "total_rows": total_rows}
)
```

### 第 6 步：编制数据盘点报告
按下方输出格式，把所有产出汇编成一份结构化文档。从 `working/` 中删除中间文件。

## 输出格式

保存到 `outputs/data_inventory_{{DATE}}.md` 的 markdown 文件，结构如下：

```markdown
# Data Inventory Report: {{DATA_SOURCE_NAME}}
**Generated:** {{DATE}}
**Source:** {{DATA_SOURCE}}
**Total tables/files:** [count]
**Date range:** [earliest date] to [latest date]
**Total rows across all tables:** [count]

## Executive Summary
[3-5 sentences: what data exists, its overall quality, and what it can support.
 Highlight any blockers. State the single most important finding about this data.]

## Table/File Inventory

### [Table/File 1 Name]
- **Rows:** [count]
- **Columns:** [count]
- **Date range:** [min] to [max]
- **Description:** [inferred description of what this table contains]

| Column | Type | Nulls | Null % | Distinct | Notes |
|--------|------|-------|--------|----------|-------|
| user_id | string | 0 | 0% | 45,231 | Primary identifier |
| event_type | string | 0 | 0% | 23 | Top: page_view (40%), click (25%) |
| timestamp | datetime | 12 | 0.01% | — | Range: 2024-01-01 to 2024-12-31 |
| revenue | float | 1,205 | 8.5% | — | Min: 0, Max: 9,999, Mean: 42.50 |
| ... | ... | ... | ... | ... | ... |

### [Table/File 2 Name]
[same structure]

## Data Quality Assessment

### Blockers
| Issue | Table | Column | Detail | Impact |
|-------|-------|--------|--------|--------|
| High null rate | events | user_segment | 35% nulls | Cannot segment 35% of users |

### Warnings
| Issue | Table | Column | Detail | Impact |
|-------|-------|--------|--------|--------|
| [issue] | [table] | [column] | [detail] | [impact] |

### Info
| Issue | Table | Column | Detail |
|-------|-------|--------|--------|
| [issue] | [table] | [column] | [detail] |

## Tracking Gap Analysis
[Only present if {{ANALYSIS_GOALS}} was provided]

| Required Data Point | Status | Source | Notes |
|--------------------|--------|--------|-------|
| [data point from goals] | AVAILABLE | events.column_name | Clean, ready to use |
| [data point from goals] | PARTIAL | users.segment | 35% nulls — use with caution |
| [data point from goals] | DERIVABLE | Compute from events.timestamp | session_duration = max(ts) - min(ts) per session |
| [data point from goals] | MISSING | — | Would need user survey data; workaround: use behavioral proxy |

## Recommended Analyses

### 1. [Analysis title]
- **Description:** [one sentence]
- **Data support:** [which tables/columns]
- **Approach:** [analysis type]
- **Agent:** [which agent to invoke]
- **Caveats:** [quality issues to watch]

### 2. [Analysis title]
[same structure]

### 3. [Analysis title]
[same structure]

## Entity Relationship Map
[If multiple tables exist, describe how they connect:]
- `users.user_id` → `events.user_id` (one-to-many)
- `events.product_id` → `products.product_id` (many-to-one)
- [Note any orphaned records: "1,203 events reference user_ids not in the users table"]

## Next Steps
1. [Address blockers — specific action items]
2. [Recommended first analysis to run]
3. [Data enrichment opportunities]
```

## 使用的 Skill
- `.claude/skills/data-quality-check/skill.md` —— 用于第 3 步的完整性、一致性和分布检查，含严重度评定标准（BLOCKER/WARNING/INFO）
- `.claude/skills/tracking-gaps/skill.md` —— 用于第 4 步的缺口分析，含 AVAILABLE/PARTIAL/MISSING/DERIVABLE 分类和变通方案建议

## 验证
在呈现数据盘点报告前，核实：
1. **行数是真实的，不是估计的** —— 对每张表/文件重跑一次 `COUNT(*)` 或 `len(df)`，确认报告中数字一致。不要从文件大小估行数。
2. **空值百分比算术正确** —— 至少对 3 列核验 空值数 / 总行数 = 报告的空值百分比。舍入误差可接受；数量级错误不可接受。
3. **日期范围合理** —— 检查报告的最小、最大日期合理（不在未来、不早于产品诞生）。标记任何 min/max 看起来不对的日期列。
4. **所有表/文件都已交代** —— 数一数第 1 步发现的表/文件数，确认报告里出现相同数量。漏掉一张表是严重错误。
5. **质量严重度评定一致** —— 重读每个 BLOCKER，确认它符合标准（>20% 空值或会导致分析出错）。确保没有任何 WARNING 其实应为 BLOCKER。
6. **实体关系已核验** —— 若报告声称表 A 在某键上连接表 B，通过检查该连接键在两表中都存在来核验，并报告孤儿率。
7. **推荐引用真实数据** —— 每条推荐分析都必须引用盘点中具体的表和列。引用不存在数据的推荐无效。

<!-- CONTRACT_START
name: source-tieout
description: Verify data loading integrity by comparing pandas direct-read vs DuckDB SQL on foundational metrics. HALT on mismatch.
inputs:
  - name: DATA_SOURCE
    type: file
    source: system
    required: true
  - name: DUCKDB_PATH
    type: str
    source: system
    required: true
  - name: DATASET_NAME
    type: str
    source: system
    required: true
  - name: TABLE_MAPPING
    type: str
    source: user
    required: false
outputs:
  - path: working/tieout_{{DATASET_NAME}}_{{DATE}}.md
    type: markdown
  - path: working/tieout_mapping.md
    type: markdown
depends_on:
  - data-explorer
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: 4.5
CONTRACT_END -->

# Agent: Source Tie-Out

## 目的
通过两种独立方式读取源文件（pandas 直读 vs DuckDB SQL）并对比基础指标，来校验数据加载完整性。它能抓出会同时污染分析及其验证的数据加载错误——分隔符错误、丢行、日期误解析、编码问题。它充当流水线闸门：FAIL 会在分析开始前中止流水线。

## 输入
- {{DATA_SOURCE}}：源数据文件的路径——CSV、Excel、Parquet 或 JSON。可以是单个文件或一个文件目录。
- {{DUCKDB_PATH}}：DuckDB 数据库文件的路径（例如 `working/hawaii.duckdb`）。若使用 MotherDuck，提供连接串。
- {{DATASET_NAME}}：用于输出文件命名的短名称（例如 "hawaii"、"my_dataset"）。
- {{TABLE_MAPPING}}：（可选）源文件到 DuckDB 表名的显式映射，形如 `file.csv:table_name` 对。若未提供，agent 会通过把文件名与表名匹配来自动发现映射。

## 工作流

### 第 0 步：Schema 预扫描

在发现源到表的映射之前，先跑一次自动 schema 画像，以了解数据集的完整结构，并确定哪些表、列和关系需要校验。

```python
from helpers.data_helpers import get_connection_for_profiling
from helpers.schema_profiler import profile_source, profile_external_warehouse, discover_relationships

# Get connection (auto-detects DuckDB vs CSV from active dataset)
conn_info = get_connection_for_profiling()

# For external warehouses (Postgres, BigQuery, Snowflake), use ConnectionManager:
if conn_info.get("type") in ("postgres", "bigquery", "snowflake"):
    schema = profile_external_warehouse(conn_info)
else:
    # DuckDB or CSV path
    schema = profile_source(conn_info)

# Use SQL dialect for warehouse-specific queries in tie-out:
from helpers.sql_dialect import get_dialect
dialect = get_dialect(conn_info.get("type", "duckdb"))

# Discover FK relationships between tables via name matching + value overlap
relationships = discover_relationships(schema)
```

用 schema 画像来**自动选取校验目标**：

1. **要校验的表：** `schema["tables"]` 中所有 `row_count > 0` 的表。跳过空表（记为 SKIPPED）。
2. **要对比的列：** 对每张表，优先：
   - 所有 `nullable: True` 且 `null_pct > 0` 的列（核验各路径间空值计数一致）
   - 所有数值列（核验求和一致）
   - 画像器检测到的所有日期列（核验日期范围一致）
   - `n_unique` 最高的列作为候选主键（核验去重计数）
3. **要校验的关系：** 对 `discover_relationships()` 返回的、`confidence >= 0.5` 的每个关系：
   - 在第 4 步加一项参照完整性检查——核验 `from_table.from_column` 中的 FK 值存在于 `to_table.to_column`
   - 用 `cardinality` 字段设定预期（many-to-one 应有 子表行数 <= 父表去重值数）
   - 把 `confidence < 0.5` 的关系记为 INFO 项，但不校验它们

把 schema 预扫描结果写到校验映射文件（`working/tieout_mapping.md`）顶部：

```markdown
## Schema Pre-Scan

**Tables found:** {count}
**Relationships discovered:** {count} (confidence >= 0.5)

### Relationship Map
| From Table | From Column | To Table | To Column | Confidence | Cardinality |
|------------|-------------|----------|-----------|------------|-------------|
| orders     | customer_id | customers | id       | 0.85       | many-to-one |
| ...        | ...         | ...      | ...       | ...        | ...         |

### Tie-Out Column Selection
| Table | Columns Selected | Reason |
|-------|-----------------|--------|
| orders | revenue, quantity, order_date, customer_id | numeric sums, date range, FK integrity |
| ...    | ...             | ...    |
```

这一预扫描取代手动选列——画像器的输出决定第 2-4 步跑哪些检查。若提供了 `{{TABLE_MAPPING}}`，用它把 schema 结果过滤为仅映射到的表。若未提供，用完整 schema 来指导第 1 步的自动发现。

### 第 1 步：发现源到表的映射
把每个源文件映射到其对应的 DuckDB 表。

**若提供了 {{TABLE_MAPPING}}：**
- 解析显式映射，核验每个文件存在、每个表在 DuckDB 中存在。

**若未提供 {{TABLE_MAPPING}}：**
- 列出 {{DATA_SOURCE}} 中所有数据文件（或将其视为单个文件）。
- 列出 {{DUCKDB_PATH}} 处 DuckDB 数据库中的所有表。
- 按名匹配：去掉文件名的扩展名及常见前后缀，再找最匹配的表名。
- 若某个源文件无法匹配到表，记为 SKIPPED 并附原因。

把映射写到 `working/tieout_mapping.md` 作为中间产出：

```markdown
| Source File | DuckDB Table | Match Method |
|-------------|-------------|--------------|
| 2025-total.xlsx | tourism_2025 | name match |
| arrivals.csv | arrivals | exact match |
```

### 第 2 步：用 Pandas 读取源文件
对每个映射的源文件：

1. 从 `helpers/tieout_helpers.py` 导入 `read_source_direct` 和 `profile_dataframe`。
2. 调用 `read_source_direct(file_path)`，只用 pandas 读取文件——这条代码路径里不用 DuckDB。
3. 调用 `profile_dataframe(df, label="source")` 计算：行数、列名、空值计数、数值求和、去重计数、日期范围。
4. 存下画像以备对比。

若某文件读取失败（编码错误、文件损坏、不支持的格式），立即记为 FAIL 并继续下一个文件。

### 第 3 步：用 DuckDB 查询相同的指标
对每个映射的 DuckDB 表，用 SQL 计算**相同的指标**——一条完全不同的代码路径：

```python
import duckdb

con = duckdb.connect("{{DUCKDB_PATH}}")

# Row count
con.sql("SELECT COUNT(*) FROM table_name")

# Column names
con.sql("DESCRIBE table_name")

# Null counts per column
con.sql("SELECT COUNT(*) - COUNT(col) AS nulls FROM table_name")

# Numeric sums
con.sql("SELECT SUM(numeric_col) FROM table_name")

# Distinct counts
con.sql("SELECT COUNT(DISTINCT col) FROM table_name")

# Date ranges
con.sql("SELECT MIN(date_col), MAX(date_col) FROM table_name")
```

把这些组装成一个画像 dict，结构与 `profile_dataframe()` 的输出相同，使用 `label="duckdb"`。

### 第 4 步：对比画像
对每个 源-表 对：

1. 从 `helpers/tieout_helpers.py` 导入 `compare_profiles`、`format_tieout_table` 和 `overall_status`。
2. 调用 `compare_profiles(source_profile, duckdb_profile)`。
3. 它会跑两档检查：
   - **Tier 1 —— 结构完整性：** 行数（精确匹配）、列名（精确匹配）、每列空值计数（精确匹配）。
   - **Tier 2 —— 聚合完整性：** 数值求和（误差 0.01% 以内）、去重计数（精确匹配）、日期范围（精确匹配）。
4. 用 `format_tieout_table(results)` 记录完整对比表。
5. 用 `overall_status(results)` 取汇总状态。

### 第 5 步：声明级抽查（可选）
若分析已产出发现（即这是后期校验），用两条路径重算前 5-10 个量化声明：

1. 对每个声明，针对源文件写一段 pandas 计算。
2. 针对 DuckDB 写一段等价 SQL 查询。
3. 在 0.1% 容差内对比结果。

本步骤为可选，仅在分析后做复校时适用。作为分析前闸门运行时跳过它。

### 第 6 步：闸门决策
把所有表级状态汇总为一个流水线级决策：

| 条件 | 决策 | 行动 |
|-----------|----------|--------|
| 所有表 PASS | **PROCEED** | 继续进入分析阶段 |
| 有表 WARN、无 FAIL | **PROCEED WITH CAUTION** | 继续，但在分析中记录警告 |
| 有任何表 FAIL | **HALT** | 停止流水线。报告哪些检查失败及原因。在数据加载问题解决前不要进入分析。 |

## 输出格式

**文件：** `working/tieout_{{DATASET_NAME}}_{{DATE}}.md`

其中 `{{DATE}}` 为 YYYY-MM-DD 格式的当前日期。

```markdown
# Source Tie-Out Report: {{DATASET_NAME}}

## Gate Decision: [PROCEED | PROCEED WITH CAUTION | HALT]

**Generated:** {{DATE}}
**Source:** {{DATA_SOURCE}}
**DuckDB:** {{DUCKDB_PATH}}
**Tables checked:** [count]

---

## Summary

[2-3 sentences: how many tables checked, overall result, any issues found.]

---

## Table: [table_name]

**Source file:** [path]
**DuckDB table:** [name]
**Status:** [PASS | WARN | FAIL]

### Comparison

| Check | Metric | Source | DuckDB | Status | Detail |
|-------|--------|--------|--------|--------|--------|
| Row count | rows | 1,234 | 1,234 | PASS | Match |
| Column names | columns | 12 | 12 | PASS | All columns match |
| Null count | revenue | 0 | 0 | PASS | Match |
| Numeric sum | revenue | 456,789.00 | 456,789.00 | PASS | Exact match |
| ... | ... | ... | ... | ... | ... |

[Repeat for each table]

---

## Claim-Level Spot Checks
[Only present if Step 5 was executed]

| Claim | Pandas Result | SQL Result | Status | Detail |
|-------|--------------|------------|--------|--------|
| Total revenue = $X | [value] | [value] | PASS | Match |

---

## Files Skipped
[List any source files that could not be matched to a DuckDB table, with reasons]

## Recommendations
[If HALT: specific actions to fix the data loading issue]
[If PROCEED WITH CAUTION: which warnings to document in the analysis]
```

## 使用的 Skill
- `helpers/tieout_helpers.py` —— `read_source_direct()`、`profile_dataframe()`、`compare_profiles()`、`format_tieout_table()`、`overall_status()`

## 验证
1. **代码路径相互独立**：核验 pandas 读取（第 2 步）与 DuckDB 查询（第 3 步）使用完全不同的代码——无共享函数，第 2 步无 DuckDB，第 3 步无 pandas。整个意义就在于双路径核验。
2. **所有映射的表都被检查**：数一数映射（第 1 步）中的表数，再数报告中的表小节数。两者必须一致（减去任何 SKIPPED 文件）。
3. **闸门决策一致**：重读各表状态，核验总体闸门决策遵循第 6 步规则。单个 FAIL 必须产生 HALT。
4. **容差正确**：行数和去重计数用精确匹配（容差 0）。数值求和用 0.01% 容差。声明级用 0.1%。核验没有任何检查使用比规定更宽松的容差。

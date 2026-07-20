# Skill: Data Profiling

## 用途
深度剖析当前激活的数据集，理解 schema 结构、取值分布、时间模式、相关性、完整性缺口和异常。产出一份完整的剖析报告，作为分析规划和数据质量评估的基础。

## 何时使用
- 连接新数据集后（bootstrap 之后、分析之前）
- 在任何数据集上做首次分析之前
- 用户显式调用时
- 当现有剖析已陈旧时（检查 manifest.yaml 中的 `last_profiled`）

## 操作步骤

### 第 1 步：连接并剖析 schema

```python
from helpers.data_helpers import get_connection_for_profiling
from helpers.schema_profiler import profile_source

# Get connection (auto-detects DuckDB vs CSV from active dataset)
conn_info = get_connection_for_profiling()

# Run full schema profile — introspects all tables: column names, types,
# nullability, row counts, sample values, basic statistics, date detection
schema = profile_source(conn_info)
```

记录输出。`schema` 包含完整的表清单及字段级元数据。用它来识别：
- 存在哪些表及其行数
- 哪些字段是日期字段（用于第 2 步的时间分析）
- 哪些字段是数值字段（用于分布和相关性分析）
- 哪些字段有空值（用于第 2 步的完整性深入）

### 第 2 步：逐表运行深度剖析

对 schema 中的每张表，加载数据并运行深度剖析函数。优先处理行数最多、日期/数值字段最多的表。

```python
from helpers.data_helpers import read_table
from helpers.deep_profiler import (
    profile_distributions,
    profile_temporal_patterns,
    profile_completeness,
)

for table_info in schema["tables"]:
    table_name = table_info["name"]
    df = read_table(table_name)

    # Distribution analysis on all numeric columns
    distributions = profile_distributions(df)

    # Completeness assessment — null rates, zeros, empty strings, constant cols
    completeness = profile_completeness(df)

    # Temporal pattern analysis (only if the table has date columns)
    temporal = None
    if table_info.get("date_columns"):
        primary_date = table_info["date_columns"][0]
        temporal = profile_temporal_patterns(df, primary_date, freq="D")
```

**重要：** 对于大表（>50K 行），`profile_source()` 已经会抽样。但 `read_table()` 会加载完整 CSV。如果某张表超过 100K 行，先抽样再做深度剖析：

```python
if len(df) > 100_000:
    df = df.sample(n=100_000, random_state=42)
```

### 第 3 步：在关键表上做相关性与异常分析

在含关键业务指标（收入、计数、比率）的表上做相关性和异常检测。通过查找名称形如 `revenue`、`amount`、`total`、`count`、`rate`、`price`、`quantity` 的字段来识别这些表。

```python
from helpers.deep_profiler import profile_correlations, profile_anomalies

# Correlations — find relationships between numeric columns
correlations = profile_correlations(df, threshold=0.5)

# Anomaly detection — requires a date column and pre-aggregated data
# Aggregate to daily granularity first if the table has event-level rows
if table_info.get("date_columns"):
    primary_date = table_info["date_columns"][0]
    # Only run on tables with a clear date + metric pattern
    metric_cols = [c for c in df.select_dtypes(include="number").columns
                   if c not in ("id", table_name.rstrip("s") + "_id")]
    if metric_cols:
        # Aggregate to daily for anomaly detection
        daily = df.groupby(pd.to_datetime(df[primary_date]).dt.date)[metric_cols].sum().reset_index()
        daily.rename(columns={daily.columns[0]: primary_date}, inplace=True)
        anomalies = profile_anomalies(daily, date_col=primary_date,
                                       metric_cols=metric_cols, window=14)
```

### 第 4 步：生成剖析报告

把完整剖析报告写到 `.knowledge/datasets/{active}/last_profile.md`。schema 部分用 `schema_to_markdown()`，然后追加深度剖析结果。

```python
from helpers.data_helpers import schema_to_markdown, detect_active_source

source = detect_active_source()
active_dataset = source["source"]

# Build the schema markdown section
schema_md = schema_to_markdown(schema)
```

汇编完整报告并写入：
```
.knowledge/datasets/{active_dataset}/last_profile.md
```

## 输出格式

```markdown
# Data Profile: {dataset_name}
**Profiled at:** {ISO timestamp}
**Source:** {connection type} ({path or schema prefix})
**Tables:** {count}  |  **Total rows:** {sum}

---

## Summary of Findings

| Severity | Count | Details |
|----------|-------|---------|
| BLOCKER  | X     | {brief list} |
| WARNING  | X     | {brief list} |
| INFO     | X     | {brief list} |

---

## Schema Overview

{output of schema_to_markdown()}

---

## Distribution Analysis

### {table_name}

| Column | Shape | Skewness | Outliers (IQR) | Recommended Transform |
|--------|-------|----------|----------------|----------------------|
| {col}  | {shape} | {skew} | {n_outliers}  | {transform or "none"} |

---

## Temporal Patterns

### {table_name} ({date_column})

- **Date range:** {min} to {max}
- **Coverage:** {actual}/{expected} periods ({pct}%)
- **Gaps:** {count} gaps found {list if any}
- **Trend:** {trend direction}
- **Seasonality:** {detected or not}
- **Day-of-week pattern:** {summary}

---

## Completeness

### {table_name}

| Column | Status | Null % | Zeros | Empty Strings | Constant? |
|--------|--------|--------|-------|---------------|-----------|
| {col}  | {status} | {pct} | {count} | {count}    | {yes/no}  |

---

## Correlations

### {table_name}

| Column A | Column B | Correlation | Strength | Direction |
|----------|----------|-------------|----------|-----------|
| {col_a}  | {col_b}  | {r}         | {strength} | {direction} |

---

## Anomalies

### {table_name}

{anomaly summary}

| Metric | Spikes | Drops | Details |
|--------|--------|-------|---------|
| {metric} | {count} | {count} | {top anomalies with dates} |

---

## Recommendations

- **BLOCKER items:** {must fix before analysis}
- **WARNING items:** {note as caveats}
- **Suggested analysis focus:** {tables/columns with most signal}
```

### 严重度分级

在所有小节中一致地应用这些规则：

| Severity | Condition |
|----------|-----------|
| **BLOCKER** | 关键指标字段空值 >50%；整段日期范围缺失（覆盖度 <50%）；本应有方差的常数字段；极强相关（r>0.95）暗示重复字段 |
| **WARNING** | 5-50% 空值；指标字段呈重尾或双峰分布；日期覆盖度 50-90%；检测到中等异常；偏度 >3 暗示数据质量问题 |
| **INFO** | <5% 空值；正态或轻微偏斜分布；日期覆盖完整；无异常；预期内的相关（如数量与收入） |

## 边界情况

1. **任何表都没有日期字段：** 完全跳过时间分析和异常检测。在报告中注明："No temporal columns detected -- temporal analysis skipped."
2. **单列表或查找表：** 只做完整性。跳过分布、相关性和异常。在报告中标记为 "lookup table"。
3. **所有字段都非数值：** 跳过分布和相关性分析。聚焦完整性和类别基数。
4. **非常宽的表（>50 列）：** 对所有字段做完整性剖析，但分布分析仅限按方差排前 20 的数值字段。注明跳过了哪些字段。
5. **空表（0 行）：** 记为 BLOCKER。不尝试剖析 —— 把该表报告为空并跳过。
6. **DuckDB 连接失败：** 通过 `read_table()` 回退到 CSV。schema 剖析器内部已处理，但深度剖析也应走 CSV 路径。

## 反模式

1. **绝不因 "数据看起来很干净" 就跳过剖析。** 意外藏在汇总统计看不到的分布和时间模式里。
2. **绝不在原始事件行上跑异常检测。** 始终先聚合到日或周粒度。在原始行上跑会把每一行都标成相对滚动统计的 "异常"。
3. **绝不脱离 schema 上下文做剖析。** 始终先跑 `profile_source()`（第 1 步），这样在深度剖析前你已经知道哪些字段是日期、哪些是数值、基数大概多少。
4. **绝不一视同仁地对待所有 WARNING 项。** 细分字段里 10% 的空值，比自由文本备注字段里 10% 的空值影响更大。按字段在分析中的角色来情境化严重度。
5. **绝不跳过报告写入。** 即使剖析顺利完成，也始终写 `last_profile.md`，让未来的会话无需重新剖析就能引用。

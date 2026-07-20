# Skill: Data Quality Check

## 用途
在任何分析开始前验证数据的完整性、一致性和覆盖度，给问题打上严重度评级，让分析师清楚什么会阻断分析、什么只需作为注意事项记录。

## 何时使用
在每次新分析开始时、连接新数据源时，或结果看起来可疑时应用本 skill。在从数据得出结论之前先跑质量检查。

## 操作步骤

### 检查顺序

按顺序运行这些检查。遇到阻断项立即停下并报告。

#### 1. 完整性检查

```sql
-- Null rate per column
SELECT
    column_name,
    COUNT(*) AS total_rows,
    COUNT(*) - COUNT(column_name) AS null_count,
    ROUND(100.0 * (COUNT(*) - COUNT(column_name)) / COUNT(*), 1) AS null_pct
FROM table_name
GROUP BY column_name;

-- Missing date ranges (for time-series data)
WITH date_spine AS (
    SELECT generate_series(MIN(date_col), MAX(date_col), INTERVAL '1 day') AS expected_date
    FROM table_name
)
SELECT expected_date
FROM date_spine
LEFT JOIN table_name ON date_col = expected_date
WHERE table_name.date_col IS NULL;

-- Unexpected zeros in numeric columns
SELECT column_name, COUNT(*) AS zero_count
FROM table_name
WHERE numeric_column = 0
GROUP BY column_name;
```

**严重度规则：**
- **BLOCKER**：主键有空值、关键分析字段空值 >50%、整段日期范围缺失
- **WARNING**：分析字段空值 5-50%、零散的缺失日期、收入/计数字段中的意外零值
- **INFO**：非关键字段空值 <5%、工作日数据中的周末缺口

#### 2. 一致性检查

```sql
-- Duplicate detection
SELECT id_column, COUNT(*) AS dupes
FROM table_name
GROUP BY id_column
HAVING COUNT(*) > 1;

-- Referential integrity
SELECT child.fk_column, COUNT(*)
FROM child_table child
LEFT JOIN parent_table parent ON child.fk_column = parent.pk_column
WHERE parent.pk_column IS NULL
GROUP BY child.fk_column;

-- Date format consistency
SELECT DISTINCT LENGTH(date_column), LEFT(date_column, 4)
FROM table_name
WHERE date_column IS NOT NULL;
```

**严重度规则：**
- **BLOCKER**：主键重复、影响 >10% 行的引用完整性断裂
- **WARNING**：日期格式混杂、类别字段大小写不一致、孤儿记录 <10%
- **INFO**：轻微大小写不一致、尾部空白

#### 3. 覆盖度检查

用 `check_temporal_coverage()` 做时间序列缺口检测，用
`check_value_domain()` 做类别完整性检查：

```python
from helpers.sql_helpers import check_temporal_coverage, check_value_domain

# Temporal coverage — detect missing days/weeks/months
coverage = check_temporal_coverage(df, "order_date", freq="D")
if coverage["status"] == "FAIL":
    print(f"BLOCKER: {coverage['message']}")

# Value domain — verify expected categories exist
domain = check_value_domain(df["device_type"], ["desktop", "mobile", "tablet"])
if domain["status"] == "FAIL":
    print(f"WARNING: {domain['message']}")
```

段覆盖度的 SQL 检查：

```sql
-- Expected segments present
SELECT segment_column, COUNT(*) AS row_count,
       MIN(date_col) AS earliest, MAX(date_col) AS latest
FROM table_name
GROUP BY segment_column
ORDER BY row_count DESC;

-- Missing cohorts
SELECT date_trunc('month', created_at) AS cohort_month, COUNT(DISTINCT user_id)
FROM users
GROUP BY 1
ORDER BY 1;
```

**严重度规则：**
- **BLOCKER**：关键段完全缺失、时间覆盖度 <80%
- **WARNING**：部分段的行数 <预期的 10%、覆盖度 80-95%、出现意外类别值
- **INFO**：段大小轻微不均、覆盖度 >95%

#### 4. 统计合理性检查

用辅助函数做系统化的异常值和空值集中度检查：

```python
from helpers.tieout_helpers import check_null_concentration, check_outliers

# Null concentration — flags columns with high null rates
null_results = check_null_concentration(df)
for r in null_results:
    if r["status"] == "FAIL":
        print(f"BLOCKER: {r['column']} — {r['detail']}")
    elif r["status"] == "WARN":
        print(f"WARNING: {r['column']} — {r['detail']}")

# Outlier detection — IQR method (default) or z-score
for col in numeric_columns:
    iqr_result = check_outliers(df[col], method="iqr")
    zscore_result = check_outliers(df[col], method="zscore")
    # Use IQR as primary, z-score as cross-check
    if iqr_result["status"] in ("WARN", "FAIL"):
        print(f"WARNING: {col} — {iqr_result['detail']}")
```

针对特定领域的合理性检查（不可能的值、可疑的分布）：

```python
def sanity_check(df, column):
    """Run statistical sanity checks on a numeric column."""
    stats = {
        "mean": df[column].mean(),
        "median": df[column].median(),
        "std": df[column].std(),
        "min": df[column].min(),
        "max": df[column].max(),
        "p1": df[column].quantile(0.01),
        "p99": df[column].quantile(0.99),
        "skew": df[column].skew(),
    }

    issues = []
    if column in ["conversion_rate", "percentage"] and (stats["max"] > 1 or stats["min"] < 0):
        issues.append(("BLOCKER", f"{column} has values outside [0,1] range"))
    if abs(stats["skew"]) > 3:
        issues.append(("WARNING", f"{column} is highly skewed (skew={stats['skew']:.1f})"))

    return stats, issues
```

**严重度规则：**
- **BLOCKER**：不可能的值（负收入、转化率 >100%、未来日期）、空值 >95%
- **WARNING**：极端异常值（>3 IQR）、空值 >50%、高度偏斜的分布
- **INFO**：中等异常值、轻微偏斜、空值 <5%

#### 5. 时间序列异常扫描

对数据集中每个按日期索引的指标字段：

```python
import pandas as pd
import numpy as np

def anomaly_scan(df, date_col, metric_col, window=14, threshold=2.0):
    """Detect time-series anomalies using rolling mean +/- std bands.

    IMPORTANT: Aggregate to daily/weekly granularity FIRST.
    Do NOT run on raw event rows.

    Args:
        df: DataFrame with date and metric columns (pre-aggregated).
        date_col: Name of the date column.
        metric_col: Name of the metric column.
        window: Rolling window size in periods. Default: 14.
        threshold: Number of standard deviations for anomaly band. Default: 2.0.

    Returns:
        Dict with 'anomalies' (list of dicts) and 'summary' (str).
    """
    ts = df.sort_values(date_col).copy()
    ts["rolling_mean"] = ts[metric_col].rolling(window, min_periods=3).mean()
    ts["rolling_std"] = ts[metric_col].rolling(window, min_periods=3).std()
    ts["upper"] = ts["rolling_mean"] + threshold * ts["rolling_std"]
    ts["lower"] = ts["rolling_mean"] - threshold * ts["rolling_std"]

    anomalies = []
    for _, row in ts.iterrows():
        if pd.notna(row["upper"]) and row[metric_col] > row["upper"]:
            pct = ((row[metric_col] - row["rolling_mean"]) / row["rolling_mean"]) * 100
            anomalies.append({
                "date": row[date_col], "value": row[metric_col],
                "direction": "spike", "pct_above_normal": round(pct, 1)
            })
        elif pd.notna(row["lower"]) and row[metric_col] < row["lower"]:
            pct = ((row["rolling_mean"] - row[metric_col]) / row["rolling_mean"]) * 100
            anomalies.append({
                "date": row[date_col], "value": row[metric_col],
                "direction": "drop", "pct_below_normal": round(pct, 1)
            })
    return {"anomalies": anomalies, "summary": f"{len(anomalies)} anomalies in {metric_col}"}
```

**执行顺序：** 在 Data Explorer 步骤的基础数据剖析之后运行，而非之前。需要已聚合的数据。

**严重度规则：**
- **WARNING**：检测到任何异常 —— 作为调查起点呈现
- **INFO**：未发现异常 —— 注明该指标看起来稳定

**输出格式：**
```
Notable patterns detected:
  - [metric] spiked [X]% above normal on [date range]
  - [metric] dropped [X]% below normal on [date range]
```

这些是观察，不是结论 —— 作为调查起点呈现。

#### 6. 数据新鲜度检查

对每张带日期/时间戳字段的表：

```python
import pandas as pd
from datetime import datetime, timedelta

def freshness_check(df, date_col, current_date=None):
    """Check data freshness and infer data cadence.

    Args:
        df: DataFrame with a date column.
        date_col: Name of the date/timestamp column.
        current_date: Override for current date (for testing). Default: today.

    Returns:
        Dict with 'max_date', 'days_ago', 'cadence', 'status'.
    """
    current_date = current_date or datetime.now().date()
    dates = pd.to_datetime(df[date_col]).dt.date
    max_date = dates.max()
    days_ago = (current_date - max_date).days

    # Infer cadence from median gap between consecutive distinct dates
    distinct_dates = sorted(dates.dropna().unique())
    if len(distinct_dates) >= 2:
        gaps = [(distinct_dates[i+1] - distinct_dates[i]).days
                for i in range(len(distinct_dates) - 1)]
        median_gap = sorted(gaps)[len(gaps) // 2]

        if median_gap <= 1.5:
            cadence = "daily"
            stale_threshold = 2
        elif median_gap <= 8:
            cadence = "weekly"
            stale_threshold = 10
        else:
            cadence = "static/historical"
            stale_threshold = None
    else:
        cadence = "unknown"
        stale_threshold = None

    # Determine status
    if days_ago > 90:
        cadence = "static/historical"
        status = "OK"
        note = f"Historical dataset, date range ends {max_date}"
    elif stale_threshold and days_ago > stale_threshold:
        status = "WARNING"
        note = f"Data is {days_ago} days old (expected {cadence} refresh)"
    else:
        status = "OK"
        note = f"Data is {days_ago} days old"

    return {
        "max_date": str(max_date), "days_ago": days_ago,
        "cadence": cadence, "status": status, "note": note
    }
```

**输出格式：**
```
Data freshness:
  - events: most recent = [date] ([N] days ago) [OK/WARNING]
  - orders: most recent = [date] ([N] days ago) [OK/WARNING]
  - users: most recent = [date] ([N] days ago) [OK/WARNING]
```

**严重度规则：**
- **WARNING**：相对推断出的更新节奏，数据已陈旧
- **INFO**：数据新鲜，或数据集为静态/历史性

### 输出格式

```markdown
# Data Quality Report: [Dataset Name]
## Date: [YYYY-MM-DD]
## Analyst: AI Product Analyst

### Summary
| Severity | Count | Details |
|----------|-------|---------|
| BLOCKER  | X     | [Must fix before analysis] |
| WARNING  | X     | [Note as caveat in analysis] |
| INFO     | X     | [For awareness only] |

### BLOCKERS
[List each blocker with: what's wrong, which column/table, how many rows affected, suggested fix]

### WARNINGS
[List each warning with: what's wrong, potential impact on analysis, recommended handling]

### INFO
[List each info item briefly]

### Data Profile
| Table | Rows | Columns | Date Range | Key Columns |
|-------|------|---------|------------|-------------|
| ... | ... | ... | ... | ... |

### Recommendation
[Can analysis proceed? With what caveats?]
- PROCEED: No blockers, warnings noted
- PROCEED WITH CAUTION: No blockers, significant warnings — note in findings
- BLOCKED: Blockers found — fix data before analyzing
```

## 示例

### 示例 1：干净的数据集
```markdown
### Summary
| Severity | Count | Details |
|----------|-------|---------|
| BLOCKER  | 0     | — |
| WARNING  | 1     | 8% null in `referral_source` column |
| INFO     | 2     | Weekend gaps in daily data; minor casing inconsistency in `country` |

### Recommendation
PROCEED — the null referral_source values should be noted as "unknown" in any segmentation by acquisition channel. All other columns are complete and consistent.
```

### 示例 2：有问题的数据集
```markdown
### Summary
| Severity | Count | Details |
|----------|-------|---------|
| BLOCKER  | 2     | Duplicate order IDs (1,247 rows); revenue column has negative values (-$45K total) |
| WARNING  | 3     | March 2025 data missing entirely; `device_type` has 12% nulls; conversion rates >1.0 for 89 rows |
| INFO     | 1     | `country` has mixed casing ("US" vs "us") |

### BLOCKERS
1. **Duplicate order_ids**: 1,247 rows have duplicate `order_id` values. This will inflate revenue calculations. Must deduplicate before analysis — keep earliest record per order_id.
2. **Negative revenue**: 342 rows have negative `revenue` values totaling -$45K. These may be refunds. Must classify and handle separately (exclude from revenue analysis or create separate refund analysis).

### Recommendation
BLOCKED — Fix duplicate order_ids and classify negative revenue before proceeding. Estimated fix time: 15 minutes with SQL dedup + refund classification.
```

## 反模式

1. **绝不因 "数据看起来没问题" 就跳过质量检查** —— 意外藏在尾部
2. **绝不对所有空值一视同仁** —— 非关键字段 2% 空值 ≠ 关键指标 50% 空值
3. **绝不静默修数据** —— 始终在质量报告中记录你改了什么、为什么
4. **绝不分析有已知阻断项的数据** —— 先修阻断项，否则整份分析都不可靠
5. **绝不假定日期是干净的** —— 检查未来日期、时区问题和格式不一致
6. **绝不忽视异常值** —— 调查它们是真实的（鲸鱼用户）还是错误的（测试账号、数据 bug）

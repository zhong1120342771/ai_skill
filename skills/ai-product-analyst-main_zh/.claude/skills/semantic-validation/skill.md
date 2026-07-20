# Skill: Semantic Validation

## 目的
编排完整的 4 层校验栈外加置信度评分，为任何分析输出产出一份全面的数据质量评估。

## 何时使用
- 在分析 agent 产出发现之后（在 Storytelling agent 之前）
- 当 Validation agent 运行其增强检查时（第 5a–5e 步）
- 当用户问"我对这些结果该有多大信心？"时

## 调用方式
作为 Validation agent 工作流的一部分自动应用。也可独立调用："Validate the quality of this analysis."

## 操作步骤

### 第 1 层：结构校验
使用 `helpers/structural_validator.py`：

```python
from helpers.structural_validator import (
    validate_schema, validate_primary_key,
    validate_referential_integrity, validate_completeness
)

# Check schema matches expected structure
schema_result = validate_schema(df, expected_columns, expected_types)

# Check primary key uniqueness
pk_result = validate_primary_key(df, key_columns)

# Check FK references exist in parent table
ri_result = validate_referential_integrity(child_df, parent_df, fk_column, pk_column)

# Check column completeness (null rates)
completeness_result = validate_completeness(df, thresholds={"warn": 0.05, "fail": 0.20})
```

把任何 FAIL 结果标记为 BLOCKER —— 建立在损坏数据之上的分析是无效的。

### 第 2 层：逻辑校验
使用 `helpers/logical_validator.py`：

```python
from helpers.logical_validator import (
    validate_aggregation_consistency, validate_trend_continuity,
    validate_segment_exhaustiveness, validate_temporal_consistency
)

# Parts must sum to whole
agg_result = validate_aggregation_consistency(parts_df, total_value, tolerance=0.01)

# No discontinuities in time series
trend_result = validate_trend_continuity(ts_df, date_col, value_col, max_gap_days=7)

# Segments must cover the full population
seg_result = validate_segment_exhaustiveness(segment_df, total_count)

# Date ranges across tables must overlap
temporal_result = validate_temporal_consistency(tables_dict, date_columns)
```

对逻辑不一致给出 WARN —— 它们提示存在计算错误。

### 第 3 层：业务规则校验
使用 `helpers/business_rules.py`：

```python
from helpers.business_rules import (
    validate_ranges, validate_rates, validate_yoy_change
)

# Check values fall within plausible ranges
range_result = validate_ranges(df, column, min_val, max_val)

# Check rates are 0-100% and denominators > 0
rate_result = validate_rates(numerator, denominator)

# Check YoY changes are plausible (not 10000%)
yoy_result = validate_yoy_change(current, previous, max_change_pct=500)
```

把不合理的取值标记为 WARN —— 它们可能是对的，但需要解释。

### 第 4 层：辛普森悖论检查
使用 `helpers/simpsons_paradox.py`：

```python
from helpers.simpsons_paradox import check_simpsons_paradox, scan_dimensions

# Check a specific aggregate vs segment breakdown
paradox = check_simpsons_paradox(df, metric_col, segment_col)

# Scan multiple dimensions for paradox risk
scan = scan_dimensions(df, metric_col, dimension_cols)
```

确认存在悖论时标记为 BLOCKER —— 此时聚合层面的发现是有误导性的。

### 置信度评分
4 层全部完成后，把结果综合成一个置信度分数：

```python
from helpers.confidence_scoring import score_confidence, format_confidence_badge

# Collect all validation results
validation_results = {
    "structural": [schema_result, pk_result, ri_result, completeness_result],
    "logical": [agg_result, trend_result, seg_result, temporal_result],
    "business_rules": [range_result, rate_result, yoy_result],
    "simpsons_paradox": [paradox_result],
    "sample_size": len(df)
}

score = score_confidence(validation_results)
badge = format_confidence_badge(score)

# score returns: {score: 0-100, grade: A-F, factors: {...}, flags: [...]}
# badge returns: "A (92/100)" or "C (58/100) — 2 warnings"
```

### 输出衔接
把置信度分数和徽章传给下游 agent：
- **Storytelling agent**：在执行摘要中包含徽章
- **Deck Creator**：在综合页（synthesis slide）上展示徽章
- **校验报告**：在校验报告中给出完整的因子拆解

### 严重程度映射
| Layer | FAIL → | WARN → |
|-------|--------|--------|
| Structural | BLOCKER (halt analysis) | WARNING (proceed with caution) |
| Logical | WARNING (check calculations) | INFO (note in report) |
| Business Rules | WARNING (explain outliers) | INFO (note in report) |
| Simpson's | BLOCKER (disaggregate) | WARNING (check segments) |

## 边界情况
- **缺少校验器：** 如果某个 helper 模块不可用，跳过该层，
  并把置信度上限封顶为 C 级
- **空数据：** 结构校验会捕获这种情况 —— 在其他层运行前就成为 BLOCKER
- **单表分析：** 跳过引用完整性和细分穷尽性检查
- **没有时间维度：** 跳过时间一致性和趋势连续性检查

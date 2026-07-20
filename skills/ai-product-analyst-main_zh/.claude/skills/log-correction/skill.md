# Skill: Log Correction

## 目的
记录分析师犯过的错误及其修正，让后续分析能从过往错误中学习。这是自动反馈采集（feedback capture）的人工对应手段。

## 何时使用
- 用户说"记录一条修正""那是错的，因为……"或类似表述
- feedback-capture skill 转到这里以录入详细的修正条目
- 在分析过程中发现并修复一个错误之后

## 操作步骤

### 第 1 步：收集细节

从对话上下文中提取，或向用户询问：

1. **错在哪里？** —— 用一句话描述这个错误
2. **正确答案是什么？** —— 修正方案或纠正后的做法
3. **涉及哪个数据集/表？** —— 数据集名称和受影响的表
4. **严重程度如何？** —— `critical`（分享了错误数字）| `high`（改变结论）| `medium`（方向正确）| `low`（无影响）
5. **修改前后的 SQL？** —— 如果错误涉及查询，把两个版本都记下来

如果任何必填字段不清楚，向用户询问。不要凭猜测判定严重程度。

### 第 2 步：分类

根据错误类型指定一个类别：

| Category | 说明 |
|----------|------|
| `sql` | 查询写错 —— join 不对、缺少过滤条件、聚合错误 |
| `metric` | 指标定义错误 —— 分子/分母错误、时间窗口错误 |
| `schema` | 列或表引用错误 —— schema 过时、字段名写错 |
| `logic` | 推理有缺陷 —— 漏掉辛普森悖论、幸存者偏差、比较口径错误 |
| `other` | 不属于上述任何一类的情况 |

### 第 3 步：写入修正

1. 用 `safe_read_yaml()` 读取 `.knowledge/corrections/index.yaml`
2. 推导下一个 ID：如果 `last_correction_id` 为 null，则用 `CORR-001`；否则
   解析数字后缀，加一，并补零到 3 位
3. 按 `.knowledge/corrections/log.template.yaml` 构建条目：

```yaml
- id: "CORR-{N}"
  date: "{YYYY-MM-DD}"
  severity: "{severity}"
  category: "{category}"
  dataset: "{dataset_name}"
  tables: ["{table1}", "{table2}"]
  description: "{what was wrong}"
  fix: "{what the correct approach is}"
  sql_before: "{original query, if applicable, else null}"
  sql_after: "{corrected query, if applicable, else null}"
  prevented_by: "{which validation layer should have caught this}"
```

4. 用 `safe_read_yaml()` 读取 `.knowledge/corrections/log.yaml`
5. 把新条目追加到 `corrections` 列表
6. 用 `atomic_write_yaml()` 写回

### 第 4 步：更新索引

1. 读取 `.knowledge/corrections/index.yaml`（第 3 步已加载）
2. 将 `total_corrections` 加一
3. 将匹配的 `by_severity.{severity}` 计数器加一
4. 将 `by_category.{category}` 加一（如果该键不存在则创建）
5. 把 `last_correction_id` 设为新 ID
6. 把 `last_updated` 设为今天的日期
7. 用 `atomic_write_yaml()` 写回

### 第 5 步：确认

向用户报告：

```
Correction logged: {id}
  Severity: {severity} | Category: {category}
  Description: {description}
  Fix: {fix}

Future analyses will check for this pattern during validation.
```

## 规则
1. 永远不要覆盖已有的修正 —— 始终追加
2. 写入前始终先读取当前状态（不要盲目覆盖）
3. 如果 `log.yaml` 或 `index.yaml` 缺失或损坏，则用 schema_version 1
   从零创建
4. `sql_before`/`sql_after` 里的 SQL 片段应裁剪到相关子句，
   而不是整段几百行的查询
5. `prevented_by` 应指向某个具体的校验层：structural、
   logical、business-rules、Simpson's check 或 source tie-out

## 边界情况
- **不涉及 SQL：** 把 `sql_before` 和 `sql_after` 设为 null
- **数据集未知：** 把 `dataset` 设为 "unknown" 并在 description 中说明
- **重复的修正：** 仍然记录 —— 反复出现的错误意味着系统性缺口
- **对一条修正的再修正：** 作为新条目记录，并在 description 中引用先前的 ID

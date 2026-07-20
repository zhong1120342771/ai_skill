# Skill: Switch Dataset

## 目的
切换当前活跃数据集。更新活跃指针、校验目标数据集存在，并以一份摘要确认现在激活的是哪个数据集。

## 何时使用
当用户想分析与当前活跃数据集不同的另一个数据集时，调用 `/switch-dataset {name}`。

## 操作步骤

### 第 1 步：校验目标数据集

1. 读取 `data_sources.yaml`，检查 `{name}` 是否作为已注册的数据源存在
2. 若未找到，尝试模糊匹配（不区分大小写、部分匹配）
3. 若仍未找到，列出可用数据集并请用户选择

### 第 2 步：校验 data brain 存在

1. 检查 `.knowledge/datasets/{name}/manifest.yaml` 是否存在
2. 若不存在，建议："Dataset '{name}' is registered but has no data brain. Run `/connect-data` to set it up."

### 第 3 步：更新活跃指针

1. 读取 `.knowledge/active.yaml`
2. 把 `active_dataset` 更新为 `{name}`
3. 追加到 `switch_history`（上限 20 条，先进先出）
4. 写回更新后的 `.knowledge/active.yaml`

### 第 4 步：确认切换

读取目标数据集的 `manifest.yaml` 并展示：

```
Switched to: {display_name}
Tables: {table_count}
Date range: {date_range}
Connection: {connection.type} ({connection.database}.{connection.schema})
Last analysis: {last_used or "none"}
Metrics defined: {count from metrics/index.yaml or 0}
```

## 反模式

1. **永远不要静默切换** —— 始终用摘要确认
2. **永远不要在分析中途切换** —— 如果 working/ 里有上一个数据集留下的产物，要警告："You have in-progress work for {old_dataset}. Switch anyway?"
3. **永远不要推断数据集** —— 只在通过本 skill 明确请求时才切换

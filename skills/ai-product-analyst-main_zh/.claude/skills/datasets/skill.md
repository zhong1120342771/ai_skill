# Skill: Datasets

## 用途
列出所有已连接的数据集，含状态、表数量和最近一次分析的日期。

## 何时使用
当用户想查看有哪些可用数据集时，以 `/datasets` 调用。

## 操作步骤

### 第 1 步：读取数据源注册表

读取 `data_sources.yaml`，获取已注册数据源的列表。

### 第 2 步：读取当前激活指针

读取 `.knowledge/active.yaml`，确定当前激活的是哪个数据集。

### 第 3 步：用 brain 数据补充信息

对每个已注册数据源，检查 `.knowledge/datasets/{name}/manifest.yaml` 是否存在。如果存在，读取汇总统计（table_count、date_range、analysis_count、last_used）。

### 第 4 步：展示列表

```
Connected Datasets:

  * your_dataset (active)
    Your Dataset Name — {table_count} tables, {date_range}
    Connection: {type} ({database})
    Analyses: 0

  - {other_dataset}
    {display_name} — {table_count} tables, {date_range}
    Connection: {type} ({details})
    Analyses: {count}

Commands:
  /switch-dataset {name}  — switch active dataset
  /connect-data           — connect a new dataset
  /data                   — inspect active dataset schema
```

用 `*` 标记当前激活的数据集，用 `-` 标记其他数据集。

## 反模式

1. **绝不显示连接凭证** —— 只展示类型和 database/schema，绝不展示 token 或密码
2. **绝不显示没有注册表条目的数据集** —— 对于没有 `data_sources.yaml` 条目的孤立 `.knowledge/datasets/` 目录，应忽略

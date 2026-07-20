# Skill: Runs

## 目的
浏览、查看、比较并清理过往的流水线运行。每次运行都是 `working/runs/`
下一个自包含的目录，拥有自己的工作文件、输出和流水线状态。

## 何时使用
- 用户说 `/runs`、`/runs list`、`/runs latest`、`/runs clean` 或 `/runs compare`
- 当用户想看看执行过哪些分析时

## 调用方式
- `/runs` 或 `/runs list` —— 列出所有过往运行
- `/runs latest` —— 显示最近一次运行的详情
- `/runs {id}` —— 显示某次运行的详情（支持部分匹配）
- `/runs clean` —— 删除超过 30 天的运行（需要确认）
- `/runs compare {id1} {id2}` —— 并排比较两次运行

## 操作步骤

### 第 1 步：扫描运行目录

读取 `working/runs/` 目录。每个子目录是一次运行，命名为：
```
{YYYY-MM-DD}_{DATASET}_{SHORT_TITLE}/
```

对每个运行目录，读取 `pipeline_state.json` 以提取：
- `pipeline_id` —— 时间戳标识
- `dataset` —— 数据集名称
- `question` —— 业务问题
- `status` —— `completed`、`failed`、`paused` 或 `running`
- `run_dir` —— 完整路径
- `started_at`、`completed_at` —— 时间信息
- `steps` —— agent 状态映射（用于计算 agent 数量）

如果 `pipeline_state.json` 缺失，把状态推断为 `unknown`，并从目录名
推导日期/数据集。

### 第 2 步：执行命令

**列表（`/runs` 或 `/runs list`）：**

按日期降序展示一个表格：

```
Pipeline Runs (working/runs/)

| # | Date       | Dataset   | Title                    | Status    | Agents |
|---|------------|-----------|--------------------------|-----------|--------|
| 1 | 2026-02-23 | acme-analytics | why-revenue-dropped-q3   | completed | 14/14  |
| 2 | 2026-02-21 | acme-analytics | activation-funnel-deep   | failed    | 8/14   |
| 3 | 2026-02-19 | hero      | churn-by-segment         | completed | 14/14  |

3 runs found. Use `/runs {#}` or `/runs {date_dataset_title}` for details.
```

`Agents` 列显示来自 step map 的 `{completed}/{total}`。

**最近一次（`/runs latest`）：**

读取 `working/latest` 符号链接的目标。显示详情视图（与 `/runs {id}` 相同）。

**详情（`/runs {id}`）：**

把 `{id}` 与运行目录名匹配（支持部分匹配 —— 例如
`/runs acme-analytics` 匹配最近一次的 acme-analytics 运行）。展示：

```
Run: {directory_name}
Status: {status}
Dataset: {dataset}
Question: {question}
Started: {started_at}
Completed: {completed_at} ({duration})

Agent Status:
  completed: {list}
  failed: {list with errors}
  skipped: {list}
  pending: {list}

Output Files:
  - {RUN_DIR}/outputs/{file1}
  - {RUN_DIR}/outputs/{file2}
  ...

Confidence: {grade from validation if available}
```

如果该次运行有校验报告，提取并显示置信度等级。

**清理（`/runs clean`）：**

1. 识别超过 30 天的运行（基于目录名的日期前缀）
2. 列出它们并请求确认：
   ```
   Found {N} runs older than 30 days:
     - {dir1} (completed, {date})
     - {dir2} (failed, {date})

   Delete these runs? This cannot be undone. [y/N]
   ```
3. 确认后，删除这些目录
4. 如果 `working/latest` 指向了被删除的运行，移除该符号链接

**比较（`/runs compare {id1} {id2}`）：**

从两次运行加载 `pipeline_state.json` 和关键输出文件。展示：

```
Comparing Runs:
  A: {dir1}
  B: {dir2}

| Dimension          | Run A              | Run B              |
|--------------------|--------------------|--------------------|
| Date               | {date_a}           | {date_b}           |
| Dataset            | {dataset_a}        | {dataset_b}        |
| Status             | {status_a}         | {status_b}         |
| Agents completed   | {count_a}          | {count_b}          |
| Confidence grade   | {grade_a}          | {grade_b}          |
| Charts generated   | {chart_count_a}    | {chart_count_b}    |
| Key findings       | {finding_count_a}  | {finding_count_b}  |
| Duration           | {duration_a}       | {duration_b}       |
```

如果两次运行分析的是同一数据集，还要比较：
- 各自的前 3 个发现（从分析报告中提取）
- 任何差异显著的指标

## 边界情况
- **没有 runs 目录：** 报告 "No pipeline runs found. Use `/run-pipeline` to start one."
- **runs 目录为空：** 同上提示
- **pipeline_state.json 损坏：** 以 `status: unknown` 显示该运行，并注明错误
- **部分匹配有歧义：** 如果多次运行都匹配，列出它们并请用户说得更具体
- **遗留运行（无运行目录）：** 注明："Found legacy `working/pipeline_state.json` -- not in per-run format. Use `/run-pipeline` to create a tracked run."

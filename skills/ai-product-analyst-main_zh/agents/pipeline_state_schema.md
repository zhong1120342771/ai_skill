# 流水线状态 Schema（OR-2.0）

## 目的
跟踪流水线执行状态，用于断点续跑和进度报告。
在 `/run-pipeline` 执行期间写入 `working/pipeline_state.json`。
由 `/resume-pipeline` 读取，以确定重启点。

## Schema（V2——按 agent 名键控）

V2 用 agent 名称键替换了数字步骤键。这消除了并行 agent 的歧义（例如第 5 步原本有三个备选），并让状态直接与 `registry.yaml` 中的 agent 名称对齐。

```json
{
  "schema_version": 2,
  "run_id": "2026-02-23_my_dataset_why-activation-dropped",
  "dataset": "my_dataset",
  "question": "Why did activation drop in Q3?",
  "started_at": "2026-02-23T09:30:00Z",
  "updated_at": "2026-02-23T10:15:00Z",
  "status": "running | completed | failed | paused",
  "agents": {
    "question-framing": {
      "status": "complete",
      "started_at": "2026-02-23T09:30:00Z",
      "completed_at": "2026-02-23T09:32:00Z",
      "output_file": "outputs/question_brief_2026-02-23.md"
    },
    "hypothesis": {
      "status": "complete",
      "started_at": "2026-02-23T09:32:00Z",
      "completed_at": "2026-02-23T09:35:00Z",
      "output_file": "outputs/hypothesis_doc_2026-02-23.md"
    },
    "data-explorer": {
      "status": "in_progress",
      "started_at": "2026-02-23T09:35:00Z"
    },
    "source-tieout": {
      "status": "pending"
    },
    "descriptive-analytics": {
      "status": "pending"
    },
    "chart-maker": {
      "status": "pending"
    },
    "opportunity-sizer": {
      "status": "degraded",
      "started_at": "2026-02-23T10:10:00Z",
      "completed_at": "2026-02-23T10:12:00Z",
      "error": "Insufficient data for sensitivity analysis"
    }
  }
}
```

### V1 → V2 迁移

| V1 字段 | V2 字段 | 说明 |
|----------|----------|-------|
| `pipeline_id` | `run_id` | 格式改变：`{date}_{dataset}_{slug}` 取代 ISO 时间戳 |
| `current_step` | _（移除）_ | 由 `status: in_progress` 的 agent 推导得出 |
| `steps.{n}` | `agents.{name}` | 按 agent 名称键控，而非步骤编号 |
| `steps.{n}.agent` | _（移除）_ | 冗余——键本身就是 agent 名称 |
| `steps.{n}.output_files` | `agents.{name}.output_file` | 单个字符串（主输出）。多输出的 agent 取首个声明的输出。 |
| _（新增）_ | `schema_version` | V2 状态文件恒为 `2` |
| _（新增）_ | `agents.{name}.error` | 仅当状态为 `degraded` 或 `failed` 时存在 |

## 字段说明

| 字段 | 类型 | 说明 |
|-------|------|-------------|
| `schema_version` | number | V2 状态文件恒为 `2` |
| `run_id` | string | 唯一运行标识：`{date}_{dataset}_{slug}` |
| `dataset` | string | 从 `.knowledge/active.yaml` 解析出的当前数据集名称 |
| `question` | string | 驱动本次流水线运行的业务问题 |
| `started_at` | ISO datetime | 流水线启动时间 |
| `updated_at` | ISO datetime | 本文件任一字段最后一次被修改的时间 |
| `status` | enum | 流水线总体状态：`running`、`completed`、`failed`、`paused` |
| `agents` | object | agent 名称到 agent 状态的映射。键与 `registry.yaml` 名称一致。 |

### Agent 状态字段

| 字段 | 类型 | 说明 |
|-------|------|-------------|
| `status` | enum | `pending`、`in_progress`、`complete`、`degraded`、`failed`、`skipped` |
| `started_at` | ISO datetime | agent 开始执行的时间。`pending` 时不存在。 |
| `completed_at` | ISO datetime | agent 结束的时间。`pending` 或 `in_progress` 时不存在。 |
| `output_file` | string | 主输出文件的相对路径。`pending` 时不存在。 |
| `error` | string | 错误信息。仅当状态为 `degraded` 或 `failed` 时存在。 |

### 合法状态

| 状态 | 含义 |
|--------|------|
| `pending` | agent 尚未开始。依赖未满足。 |
| `in_progress` | agent 正在执行。 |
| `complete` | agent 成功结束并产出了输出。 |
| `degraded` | 非关键 agent 失败。流水线带警告继续。 |
| `failed` | 关键 agent 失败。流水线中止。 |
| `skipped` | 本次运行不需要该 agent（例如条件性 agent、未选中的备选）。 |

## 状态转移

agent 级：
```
pending → in_progress → complete
pending → in_progress → degraded   (non-critical agent failed)
pending → in_progress → failed     (critical agent failed)
pending → skipped
complete  (terminal — no further transitions)
degraded  (terminal — pipeline continued)
failed    (terminal unless pipeline is resumed)
skipped   (terminal)
```

流水线级：
```
running → completed   (all agents complete, degraded, or skipped)
running → failed      (any critical agent failed and pipeline halted)
running → paused      (user paused or context limit reached)
paused  → running     (resumed via /resume-pipeline)
```

## 生命周期

1. 在流水线启动时（源解析阶段）**创建**。所有 agent 初始化为 `pending`。
2. 每个 agent 完成、降级或失败后**更新**。`updated_at` 推进。
3. 由 `/resume-pipeline` **读取**，找出状态为 `in_progress` 或 `pending` 的 agent，并从下一个可运行的 agent 重启。
4. 成功完成后，连同最终输出一起**归档**到 `.knowledge/analyses/`。

## 规则

- **原子写入**：始终先写入临时文件（`working/pipeline_state.tmp.json`），再重命名为 `working/pipeline_state.json`。这能防止 agent 写入中途失败时被读到不完整内容。
- **绝不删除**：运行期间原地覆盖。不要删除后重建。
- **只有一个活动状态文件**：任意时刻只存在一个 `working/pipeline_state.json`。启动新流水线会覆盖之前的状态。
- **agent 键与 registry 一致**：`agents` 中的 JSON 键必须与 `registry.yaml` 里的 agent `name` 值完全一致。
- **稀疏条目**：只包含本次运行涉及的 agent。未选中的 agent（例如选了 `descriptive-analytics` 时的 `cohort-analysis`）整体省略——不要把它们标为 `skipped`。
- **output_file 是相对路径**：`output_file` 中的路径相对仓库根目录（例如 `working/storyboard_my_dataset.md`、`outputs/question_brief_2026-02-23.md`）。

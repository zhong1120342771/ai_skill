# Skill: Resume Pipeline

## 目的
恢复被中断的分析流水线：读取 `working/pipeline_state.json`，判断哪些 agent 已完成，然后用 DAG 遍历器（DAG walker）从下一批 READY 的 agent 继续执行。

## 何时使用
在以下情况调用 `/resume-pipeline`：
- 上一次分析会话被中断（上下文上限、用户暂停、连接问题）
- 用户想继续在上一次对话中开始的分析
- 存在某次部分完成运行留下的流水线状态文件
- 流水线失败，且底层问题已被修复

## 操作步骤

### 第 1 步：定位流水线状态（按 per-run 目录感知）

按以下顺序查找最新的流水线状态：

1. **Per-run 目录（首选）：** 检查 `working/latest/pipeline_state.json`（指向最新运行的符号链接）。
   如找到，从符号链接目标设置 `RUN_DIR` 并进入第 2 步。
2. **指定运行：** 如果用户传入了 run ID（例如 `/resume-pipeline 2026-02-23_acme-analytics_why-revenue-dropped`），
   在 `working/runs/{id}/pipeline_state.json` 中查找。相应设置 `RUN_DIR`。
3. **遗留位置：** 检查 `working/pipeline_state.json`（per-run 目录之前的流水线）。
   如找到，读取它并在没有 `RUN_DIR` 的情况下进入第 2 步。
4. **未找到状态：** 退回到产物扫描（第 1b 步）。

**要提取的流水线状态字段（V2）：**
- `run_id` —— 标识本次运行
- `run_dir` —— per-run 目录路径（遗留运行可能没有）
- `dataset` —— 活跃数据集
- `question` —— 业务问题
- `status` —— `running`、`paused` 或 `failed`
- `agents` —— agent 名称到 agent 状态的映射（status、output_file、时间戳）

### 第 1a 步：V1 到 V2 状态迁移

加载状态文件后、做任何处理前，检查状态是否使用 V1（以步骤编号为键）
格式，如有需要则迁移到 V2。

```python
from helpers.pipeline_state import detect_schema_version, migrate_v1_to_v2

if detect_schema_version(state) < 2:
    # Resolve dataset from active.yaml or fall back to "unknown"
    dataset = state.get("dataset") or resolve_active_dataset() or "unknown"
    state = migrate_v1_to_v2(state, dataset=dataset)
    # Write migrated state back to disk (same location it was read from)
    write_pipeline_state(state_path, state)
    print("Migrated pipeline state from V1 -> V2 format")
```

**迁移细节**（由 `helpers/pipeline_state.py` 处理）：
- `pipeline_id`（ISO 时间戳）-> `started_at`；从日期 + 数据集 + 问题 slug 生成 `run_id`
- `steps.{n}.agent` 键 -> `agents.{agent_name}` 键
- `steps.{n}.output_files[0]` -> `agents.{name}.output_file`（取第一个）
- 状态值原样保留（V1 与 V2 兼容）
- 添加 `schema_version: 2` 并把 `updated_at` 设为当前时间
- 如果某个 V1 步骤的 `status: running`，则在流水线层面变为 `paused`（说明它被中断了）

迁移后，继续使用上面列出的 V2 字段。

### 第 1b 步：基于产物的回退（无 pipeline_state.json）

如果不存在状态文件，扫描 `working/` 和 `outputs/` 中的产物：

| Agent | Expected Artifact | Directory |
|-------|-------------------|-----------|
| question-framing | `question_brief_*.md` | `outputs/` |
| hypothesis | `hypothesis_doc_*.md` | `outputs/` |
| data-explorer | `data_inventory_*.md` | `outputs/` |
| source-tieout | `tieout_*.md` | `working/` |
| descriptive-analytics | `analysis_report_*.md` | `outputs/` |
| root-cause-investigator | `investigation_*.md` | `working/` |
| validation | `validation_*.md` | `outputs/` |
| opportunity-sizer | `sizing_*.md` | `working/` |
| story-architect | `storyboard_*.md` | `working/` |
| narrative-coherence-reviewer | `coherence_review_*.md` | `working/` |
| chart-maker | `charts/*.png` | `outputs/` |
| visual-design-critic | `design_review_*.md` | `working/` |
| storytelling | `narrative_*.md` | `outputs/` |
| deck-creator | `deck_*.md` | `outputs/` |

自上而下遍历该列表。如果某个产物存在且看起来完整（非空、没有 "NEEDS REVISION" 标记），就把对应 agent 标记为已完成。据此重建一个 pipeline_state.json。

### 第 2 步：从 DAG 计算 READY 集合

1. 读取 `agents/registry.yaml` 构建依赖图
2. 对 registry 中的每个 agent，检查 `state["agents"][agent_name]["status"]`：
   - 如果状态是 `complete`、`skipped` 或 `degraded` → 保持不变
   - 如果状态是 `failed` → 重置为 `pending`（将被重试）
   - 如果状态是 `in_progress` 或 `running` → 重置为 `pending`（之前被中断了）
3. 计算 READY 的 agent：那些 `status: pending` 且其所有依赖都为 `complete` 的 agent

### 第 3 步：构建上下文摘要

读取每个已完成 agent 的输出文件，并提取一段简短摘要：
- 从 question brief：已框定的问题和决策背景
- 从分析报告：关键发现（前 3 个）
- 从 storyboard：叙事节拍和视觉规划
- 从校验报告：置信度等级

汇编成一个上下文块，供恢复后的会话使用。

### 第 4 步：呈现恢复计划

显示：

```
Resuming pipeline {run_id}

Completed agents: {count}
  - {agent_name}: {one-line summary from outputs}
  - ...

Failed/interrupted agents (will retry): {count}
  - {agent_name}: {error or "interrupted"}

Next READY agents: {list}

Resume execution?
```

### 第 5 步：通过 DAG 遍历器恢复

确认后：
1. 更新 pipeline_state.json：设置 `status: running`，把 failed/running 重置为 pending
2. 交接给 run-pipeline skill 中的 DAG 遍历器（Phase 2）
3. 遍历器会从 READY 集合接续，按层（tier-by-tier）继续推进
4. 所有已完成的输出都会保留 —— 只执行 pending 的 agent

## 特殊情况

- **storyboard 带 "NEEDS ADDITIONS"：** 把 story-architect 标记为 `pending`，而非已完成
- **图表部分生成：** 比对已生成图表数与 storyboard 节拍数。若不完整，把 chart-maker 标记为 `pending`
- **source tie-out 失败：** 标记为 `failed`。用户必须先排查再恢复
- **数据过期（间隔 >24h）：** 警告底层数据自原始运行以来可能已发生变化

## 局限

- **上下文断层：** 恢复能还原产物，但还原不了对话中的推理过程。恢复后的分析可能比单次会话连贯性略差。
- **没有部分步骤恢复：** 如果某个 agent 在执行中途被中断，整个 agent 必须重跑。
- **以流水线状态为准：** 如果 pipeline_state.json 与产物不一致，以 pipeline_state.json 为准。

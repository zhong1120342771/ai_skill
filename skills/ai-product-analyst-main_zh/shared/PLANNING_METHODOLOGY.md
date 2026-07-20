# 规划与执行方法论

**目的：** 在本单体仓库中规划并执行多阶段构建的标准方法论。启动新项目时，先阅读本文件并按工作流执行。

---

## 阶段 0：范围与角色选择

规划前，先定义：

1. **项目简报** —— 我们要构建什么？成功是什么样子？有哪些约束？
2. **参考样例** —— 截图、现有实现、竞品案例、用户提供的灵感
3. **可用资产** —— 品牌 token（`shared/brand/tokens.json`）、团队照片、现有模板、共享基础设施
4. **角色** —— 选 3-5 个专家角色，其合并的专业覆盖整个范围

### 角色选择标准

每个角色应当：
- 拥有独立的专业领域（不重叠）
- 用一个能体现其视角的职位名命名
- 有清晰的"在意什么"，并由此驱动其计划
- 至少挑战另一个角色的假设

典型角色原型：
| 原型 | 在意什么 | 挑战谁 |
|-----------|-------------|------------|
| **终端用户倡导者** | UX、转化、心理 | 过度构建的工程师 |
| **技术架构师** | 自动化、可维护性、流水线设计 | 忽视约束的设计师 |
| **领域专家** | 工艺质量、还原度、行业标准 | 牺牲质量的捷径 |
| **增长/营销策略师** | 分发、参与度、指标 | 忽视受众的构建者 |
| **流水线/运维工程师** | 可复现、可恢复、可跟踪 | 因追求完美而无法完成 |

## 阶段 1：独立计划（第 1 轮）

**并行**启动所有角色 agent。每个 agent 接收：

```
You are [PERSONA_NAME], a [ROLE_DESCRIPTION].

Context: [PROJECT_BRIEF]
Reference: [EXAMPLES_AND_ASSETS]
Constraints: [BUDGET, TIMELINE, TECH_STACK]

Produce a detailed plan from YOUR perspective covering:
1. What needs to be built (your domain)
2. How it should be structured (files, agents, pipeline)
3. What the phases/waves should be
4. Dependencies on other domains
5. Risks and unknowns
6. What you'd push back on if another expert suggested shortcuts in your area

Format: Markdown with headers, tables, and specific file paths where possible.
```

**产出：** 每个角色把计划写到 `working/plans/round1/[persona-slug].md`

## 阶段 2：辩论与评审

启动**单个辩论 agent**，接收全部第 1 轮计划。它的任务：

```
You are a senior technical moderator. You have received [N] independent plans from these experts:
[LIST PERSONAS AND THEIR ROLES]

Your job:
1. Read all plans carefully
2. Identify AGREEMENTS (things 2+ personas align on)
3. Identify CONFLICTS (where personas disagree or have incompatible approaches)
4. Identify GAPS (things nobody addressed)
5. For each conflict, state both sides fairly and recommend a resolution with reasoning
6. For each gap, flag it and suggest which persona should own it
7. Produce a DEBATE SUMMARY with:
   - Consensus items (proceed as-is)
   - Resolved conflicts (with winner and why)
   - Open questions (need user input)
   - Gap assignments

Format: Structured markdown. Be specific — quote from the plans.
```

**产出：** `working/plans/debate-summary.md`

## 阶段 3：修订计划（第 2 轮）

再次**并行**启动所有角色 agent。每个 agent 接收：
- 它的第 1 轮原始计划
- 完整的辩论纪要
- 修订指令

```
You are [PERSONA_NAME] again. Here is:
1. Your original plan: [ROUND_1_PLAN]
2. The debate summary from cross-review: [DEBATE_SUMMARY]

Revise your plan to:
- Accept consensus items
- Incorporate resolved conflicts (even if you "lost" — adapt gracefully)
- Address any gaps assigned to you
- Flag remaining disagreements you feel strongly about (max 2)

Produce your REVISED plan.
```

**产出：** 每个角色写到 `working/plans/round2/[persona-slug].md`

## 阶段 4：对齐与综合

启动**单个综合 agent**，接收全部第 2 轮计划 + 辩论纪要：

```
You are the chief architect synthesizing [N] revised expert plans into one unified master plan.

Input:
- Round 2 plans from all personas
- Debate summary (for context on resolved conflicts)
- Project brief and constraints

Produce the MASTER PLAN with these exact sections:

1. **Executive Summary** — What we're building, key decisions, scope
2. **Wave Structure** — Summary table: wave number, name, task count, dependencies
3. **Detailed Waves** — For each wave:
   - Goal
   - Parallelism notes
   - Task specs (ID, description, file paths, agent type, inputs, outputs, dependencies)
4. **Dependency Graph** — ASCII diagram
5. **Files Changed Summary** — Table: wave, file, change type, description
6. **Open Questions** — Anything needing user decision before execution
```

**产出：** 在合适位置生成 `[PROJECT]_MASTER_PLAN.md`

## 阶段 5：构建状态跟踪器

主计划获批后，创建 BUILD_STATUS.yaml：

```yaml
project: [PROJECT_NAME]
master_plan: [PATH_TO_MASTER_PLAN]
protocol: shared/PLANNING_METHODOLOGY.md
current_wave: 0
total_waves: [N]
created: YYYY-MM-DD

tasks:
  - id: W0.1
    wave: 0
    description: "[Task description]"
    status: not_started       # not_started | in_progress | completed | failed
    depends_on: []            # Task IDs that must complete first
    output_files: []          # Files created/modified by this task
    agent_type: builder       # builder | reviewer | orchestrator
    parallel_group: "W0-A"   # Tasks in same group can run simultaneously
    session: null             # Session number when completed
    notes: ""

session_log:
  - session: 1
    date: "YYYY-MM-DD"
    wave: 0
    tasks_completed: []
    tasks_failed: []
    notes: ""
```

### 状态值
| 状态 | 含义 |
|--------|---------|
| `not_started` | 尚未开始 |
| `in_progress` | 正在进行 |
| `completed` | 成功完成 |
| `failed` | 已尝试但未完成 |

### 依赖规则
当满足以下条件时，任务处于 READY 状态：
- 状态为 `not_started`
- `depends_on` 中的所有任务状态都为 `completed`
- 其所属 wave 的前置条件已满足

## 阶段 6：执行

### 会话启动流程
1. 读取 BUILD_STATUS.yaml
2. 读取主计划（略读 —— 聚焦当前 wave）
3. 找出 READY 任务（not_started + 所有依赖已 completed）
4. 分组为并行批次（最多 3 个并发）
5. 宣布："Session N。Wave X。任务：[列表]。启动 [N] 个 builder。"

### 执行循环
```
1. Find READY tasks
2. Group into parallel batches (respect same-file conflicts)
3. Launch builder agents in parallel
4. Collect results
5. Update tracker: completed or failed with notes
6. If batch done → launch review agent
7. If review finds issues → fix → re-review
8. Repeat from 1
9. Wave complete → announce, checkpoint with user
```

### 跟踪器更新规则
- **启动 builder 前：** 把状态设为 `in_progress`
- **成功后：** 设为 `completed`，记录 output_files 和 session
- **失败后：** 设为 `failed`，在 notes 中记录错误
- **复核发现问题后：** 把受影响任务设回 `in_progress`
- **会话结束时：** 更新所有状态，写入 session_log 条目
- **绝不跳过跟踪器更新** —— 它是跨会话连续性的事实依据

### 上下文管理（崩溃恢复）
- **上下文变长：** 立即更新跟踪器，然后让压缩发生
- **会话即将结束：** 写入带最终状态的 session_log 条目
- **崩溃后恢复：** 读取跟踪器。任何 `in_progress` 任务都需重新检查
- **压缩后：** 重新读取跟踪器 + 主计划。跟踪器是唯一事实来源

### 质量门
进入下一 wave 前：
1. 当前 wave 的所有任务都为 `completed`
2. 复核 agent 已通过该 wave
3. 没有遗留的 `failed` 任务（已修复或明确推迟）
4. 已告知用户并获其批准

### 同文件冲突预防
绝不对同一输出文件并行运行多个 builder。如果多个任务编辑同一文件，无论依赖图怎么说，它们都必须串行运行。

---

## 速查：Agent 类型

| Agent | 用途 | 并行度 | 提示词模式 |
|-------|---------|-------------|----------------|
| **Builder** | 按规范创建/编辑一个文件 | 最多 3 个并发 | 任务 ID + 规范 + 依赖 + 模式参考 |
| **Reviewer** | 校验一批产出 | 每 wave 1 个 | 文件列表 + 检查清单 |
| **Orchestrator** | 读跟踪器、启动 agent、更新跟踪器 | 1（主上下文） | 绝不委派 |
| **Persona** | 从单一视角做专家规划 | 所有角色并行 | 简报 + 角色 + 约束 |
| **Debate Moderator** | 交叉评审并化解冲突 | 1 | 全部计划 + 冲突化解规则 |
| **Synthesizer** | 把计划合并为主计划 | 1 | 全部修订计划 + 辩论纪要 |

## 速查：文件命名

| 文件 | 位置 | 用途 |
|------|----------|---------|
| `[PROJECT]_MASTER_PLAN.md` | 项目目录 | 权威构建计划 |
| `BUILD_STATUS.yaml` | 项目目录 | 执行跟踪器（事实依据） |
| `PLANNING_METHODOLOGY.md` | `shared/`（本文件） | 如何规划（参考） |
| `working/plans/round1/*.md` | 项目目录 | 第 1 轮角色计划 |
| `working/plans/round2/*.md` | 项目目录 | 第 2 轮修订计划 |
| `working/plans/debate-summary.md` | 项目目录 | 辩论主持人产出 |

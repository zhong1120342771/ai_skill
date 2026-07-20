# Skill: Run Pipeline

## 目的
端到端分析的单一入口 —— 从原始数据到成品幻灯片。使用基于 DAG 的执行引擎：从 `agents/registry.yaml` 读取 agent 依赖、自动解析执行顺序，并支持 agent 并行执行、失败恢复和执行计划裁剪。

## 何时使用
通过以下方式调用：`/run-pipeline`、"run the full pipeline"、"analyze end-to-end"，或 "take this data through the full workflow"。

## 接受的参数

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `data_path` | Yes | — | Path to CSV, parquet, or directory of data files |
| `question` | Yes | — | The business question to answer |
| `context` | No | `"stakeholder readout"` | Presentation context: "stakeholder readout", "workshop", "talk", "team standup" |
| `theme` | No | `analytics` (light) | Theme override: "analytics" (light) or "analytics-dark" (dark) |
| `audience` | No | `"senior stakeholders"` | Who will see the deck — controls content density |
| `dataset_name` | No | Derived from data_path | Short name for file naming (e.g., "hawaii", "my_dataset") |
| `plan` | No | `full_presentation` | Execution plan: `full_presentation`, `deep_dive`, `quick_chart`, `refresh_deck`, `validate_only`, or inline agent list |
| `dry-run` | No | `false` | If `true`, print execution plan without running agents |
| `agents` | No | — | Inline agent allow-list (e.g., `agents=question-framing,hypothesis,data-explorer`) |

参数可以内联传入，也可以交互式提示：
```
/run-pipeline data_path=data/your_dataset/ question="What's driving the decline in revenue?" plan=deep_dive
/run-pipeline dry-run=true
/run-pipeline plan=refresh_deck
```

如果缺少必填参数，在继续前提示用户。

---

## 不可商量的规则（NON-NEGOTIABLE RULES）

这些规则覆盖任何默认行为。违反其中任何一条都是流水线失败。

### R1：主题默认为浅色
标准分析 → `analytics`（浅色主题）。暗色主题（`analytics-dark`）只在 `context` 为 "workshop" 或 "talk" 时使用，或用户显式传入 `theme=analytics-dark` 时使用。拿不准就用浅色。

### R2：图表标题 ≠ 幻灯片标题
图表内嵌的 `title`（SWD action title）必须不同于幻灯片标题。图表标题是带数字的具体数据论断。幻灯片标题是叙事性的框架。

| Slide Headline | Chart Title | Verdict |
|---------------|-------------|---------|
| "Payment issues drove the June spike" | "Payment issues drove the June spike" | **BAD** — identical |
| "Payment issues drove the June spike" | "Payment tickets jumped 147% while other categories grew <20%" | **GOOD** |

### R3：图表背景为 #F7F6F2
所有图表都用暖调灰白背景（#F7F6F2），绝不用纯白（#FFFFFF）。这由 `swd_style()` 设置 —— 每张图前都核实它被调用过。

### R4：建议按置信度排序
建议始终按 High → Medium → Low 置信度排序。绝不按字母序，绝不按主题。

### R5：用词 —— 禁用词
标题、过渡语和呼吸页绝不能用：**surgical、devastating、exploded、ticking time bomb、smoking gun、alarm/fire 类比喻、unprecedented**（除非字面属实）、**unleash、supercharge、game-changing、skyrocketed**。

### R6：每 3-4 张洞察页插一张呼吸页
连续的图表/洞察页绝不超过 4 张而不插一个节奏停顿。节奏用的 class：`impact`、`dark-impact`、`section-opener`、`takeaway`。

### R7：图表用标准 figsize
每张图都以 (10, 6) figsize / 150 DPI（约 1500x900px）生成，并直接用在幻灯片上。CSS `object-fit: contain` 处理所有的容纳问题。无需幻灯片变体。

### R8：agent 文件必须从磁盘读取
在每个阶段，从其磁盘路径读取 agent 文件。**不要**依赖缓存知识或记忆。

### R9：分析前先做 Source Tie-Out
在数据探索之后、分析之前，运行 Source Tie-Out 来核实数据加载的完整性。不一致就 HALT。

### R10：所有 Marp deck 必须使用 HTML 组件
每份 Marp deck 必须使用主题中至少 3 种不同的 HTML 组件类型（例如 `.kpi-row`、`.so-what`、`.finding`、`.rec-row`、`.chart-container`）。有效的幻灯片 class 包括 `chart-full`、`kpi`、`takeaway`、`recommendation`、`appendix`（新的"一页一职"class）以及所有现有 class（`insight`、`impact`、`chart-left`、`chart-right`、`two-col`、`diagram`、`section-opener`、`title`）。只含纯 markdown 的洞察页是流水线失败。deck-creator agent 必须读取 `templates/marp_components.md` 获取片段库、读取 `templates/deck_skeleton.marp.md` 获取骨架模板。Frontmatter 必须包含全部 6 个必需键：`marp`、`theme`、`size`、`paginate`、`html`、`footer`。运行 `helpers/marp_linter.py` 来校验。

### R11：流水线同时导出 PDF 和 HTML
在 deck 创建和 Checkpoint 4 之后，流水线必须用 `helpers/marp_export.py` 把 deck 导出为 PDF 和 HTML。导出路径记录在 `pipeline_state.json` 中。如果 Marp CLI 不可用，记录一条警告并跳过导出（不要 HALT）。导出的文件与 deck 放在一起：`outputs/deck_{{DATASET_NAME}}_{{DATE}}.pdf` 和 `outputs/deck_{{DATASET_NAME}}_{{DATE}}.html`。

---

## DAG 执行引擎

流水线运行在一个由 `agents/registry.yaml` 派生的 DAG（有向无环图）上。引擎不是用硬编码步骤，而是从 agent 依赖解析执行顺序。

### Step 0：执行前清理（崩溃恢复）

在校验之前，检测并清理上一次崩溃运行留下的产物。

1. **检测过期运行：** 检查 `working/pipeline_state.json`（或 `working/latest/pipeline_state.json`）是否存在且 `status: running`。
   - 解析 `updated_at` 并计算流逝时间。如果超过 30 分钟前，视为过期。
   - 打印：`"Found stale pipeline state from {updated_at}. Previous run may have crashed."`
   - 询问：`"Archive stale state and start fresh? (Y/n)"`
   - **如果是：** 把 `working/pipeline_state.json` 重命名为 `working/crashed_{run_id}_state.json`。继续到 Phase 0。
   - **如果否：** 转到 `/resume-pipeline` 尝试恢复上一次运行。到此停止。
   - 如果 `updated_at` 在 30 分钟以内，假定另一个运行处于活跃中。HALT 并提示：`"Pipeline state shows an active run from {updated_at}. Use /resume-pipeline or wait for it to finish."`

2. **清理临时文件：** 删除任何 `working/*.tmp.json` 文件（崩溃运行留下的部分原子写入）。

3. **校验 per-run 目录：** 如果上次运行留下了孤立的 `working/latest` 符号链接：
   - 移除过期的符号链接（新运行会在 Phase 1 创建自己的）。
   - 创建 `working/runs/{run_id}/` 目录结构，含 `working/`、`outputs/` 子目录。

4. **初始化全新状态：** 真正的 `pipeline_state.json` 创建发生在 Phase 1，带 `schema_version: 2` 且所有 agent 设为 `pending`。Step 0 只确保工作区是干净的。

清理完成后（若未发现过期状态则跳过），进入 Phase 0。

---

### Phase 0：预检校验

任何执行之前，校验 registry：

1. **读取 registry：** 解析 `agents/registry.yaml`。提取每个 agent 的 `name`、`file`、`pipeline_step`、`depends_on`、`depends_on_any`、`critical`、`inputs`、`outputs`、`knowledge_context`。

2. **文件存在检查：** 对每个 agent，核实 `agent.file` 处的文件在磁盘上存在。如果任何文件缺失，HALT 并提示：`"Agent file not found: {path}"`

3. **依赖解析：** 对每个 agent 的 `depends_on` 和 `depends_on_any` 列表，核实每个被引用的 agent 名都存在于 registry 中。如果有悬空引用，HALT 并提示：`"Unknown dependency: {agent} depends on {missing}"`

4. **环检测：** 对依赖图做拓扑排序。如果检测到环，HALT 并提示：`"Cycle detected: {cycle_path}"`
   - 算法：Kahn 算法 —— 迭代地移除入度为 0 的节点。如果没有更多节点可移除后仍有节点残留，那些节点构成一个环。

5. **计算执行层（tiers）：** 把 agent 分组成层，使一层中所有 agent 的依赖都由更早层的 agent 满足。
   ```
   Tier 0: agents with no dependencies (e.g., question-framing, data-explorer)
   Tier 1: agents depending only on Tier 0 agents (e.g., hypothesis, source-tieout)
   Tier 2: agents depending on Tier 0-1 agents (e.g., descriptive-analytics)
   ...
   ```

6. **应用执行计划：** 从 `plans.md` 加载计划（或使用默认的 `full_presentation`）。把 DAG 过滤到只含计划白名单中的 agent。不在计划中的 agent 被标记为 `skipped`。如果某个计划内 agent 依赖一个被跳过的 agent，警告：`"Agent {name} depends on skipped agent {dep}. Ensure required context exists."`

### Phase 1：初始化运行目录与流水线状态

**Per-run 目录设置：** 每次流水线运行都在 `working/runs/` 下获得一个隔离目录。

1. **创建运行目录：**
   ```
   RUN_DIR = working/runs/{YYYY-MM-DD}_{DATASET_NAME}_{SHORT_TITLE}/
   ```
   其中 `SHORT_TITLE` 由业务问题派生 —— 小写、连字符、最多 40 字符
   （例如 `2026-02-23_acme-analytics_why-revenue-dropped-q3`）。

2. **创建子目录：**
   ```
   {RUN_DIR}/working/       -- intermediate files (tie-outs, storyboards, reviews)
   {RUN_DIR}/outputs/       -- final deliverables (decks, charts, narratives)
   {RUN_DIR}/pipeline_state.json  -- run state (authoritative)
   {RUN_DIR}/pipeline_metrics.json -- execution timing
   ```

3. **创建符号链接：** `working/latest` -> `{RUN_DIR}`（若已存在则先移除）。

4. **向后兼容的别名：** 同时创建/维护遗留的 `working/` 和 `outputs/` 路径。
   所有 agent 照旧继续写入 `working/` 和 `outputs/`。流水线结束时，
   把最终产物复制进 `{RUN_DIR}/working/` 和 `{RUN_DIR}/outputs/`，让运行
   目录自包含。

**初始化 pipeline_state.json**，放在 `{RUN_DIR}/`，遵循 `agents/pipeline_state_schema.md` 中的 schema：
- 把 `pipeline_id` 设为当前 ISO 时间戳
- 把 `run_dir` 设为完整的运行目录路径
- 从活跃数据集设置 `dataset`
- 从用户输入设置 `question`
- 把所有纳入的 agent 初始化为 `pending`，被跳过的 agent 为 `skipped`
- 把流水线 `status` 设为 `running`

如果是**恢复**（pipeline_state.json 已存在且 `status: paused` 或 `status: failed`）：
- 读取已有状态（先查 `working/latest/pipeline_state.json`，再回退到 `working/pipeline_state.json`）
- 识别 `status: completed` 的 agent —— 保持不变
- 识别 `status: failed` 的 agent —— 重置为 `pending` 以重试
- 计算 READY 集合（依赖都已完成的 pending agent）
- 报告：`"Resuming from {N} completed agents. Next: {READY agent names}"`
- 跳到 Phase 2

### Phase 2：遍历 DAG

按层逐层执行 agent：

```
FOR each tier in execution_tiers:
  1. READY_SET = agents in this tier that satisfy BOTH:
     - ALL `depends_on` agents have completed (AND-gate)
     - At least ONE `depends_on_any` agent has completed, if specified (OR-gate)
     (after plan filtering and skipping)

  2. If READY_SET is empty AND pending agents remain → deadlock → HALT

  3. FOR each agent in READY_SET:
     a. Mark agent status: running in pipeline_state.json
     b. Record started_at timestamp
     c. Assemble dynamic context (see Context Assembly below)
     d. Read agent file from disk (R8)

  4. LAUNCH agents:
     - If Task tool available AND READY_SET has 2+ agents:
       Launch up to 3 parallel Tasks, each with agent file + context
     - Else: Execute sequentially inline

  5. WAIT for completion (with timeout — see Timeout Handling)

  6. FOR each completed agent:
     a. Record completed_at, output_files in pipeline_state.json
     b. Record timing in pipeline_metrics
     c. If FAILED and agent.critical is true (default): increment failure counter
     d. If FAILED and agent.critical is false (warn_on_failure):
        - Log warning: "⚠ Non-critical agent {name} failed: {error}. Continuing."
        - Write stub output to agent's first output path:
          `# {name} — SKIPPED (failure)\nReason: {error}\nTimestamp: {iso_now}`
        - Mark status as `degraded` in pipeline_state.json
        - Queue warning for display at next checkpoint
        - Do NOT increment tier failure counter

  7. CIRCUIT BREAKER: If 3+ critical agents failed in this tier → HALT pipeline
     Report: "Circuit breaker tripped: {N} failures in tier {T}. Failed: {names}"

  8. CHECKPOINT: If a checkpoint fires after this tier, run it (see Checkpoints)

  9. Update working/pipeline_summary.md with phase results

  10. ADVANCE to next tier
```

### 动态上下文组装

启动每个 agent 之前，解析它的运行时上下文：

1. **系统变量：**
   - `{{DATE}}` → 当前日期 YYYY-MM-DD
   - `{{DATASET_NAME}}` → 来自 `dataset_name` 参数或从 data_path 派生
   - `{{ACTIVE_DATASET}}` → 来自 `.knowledge/active.yaml`
   - `{{BUSINESS_CONTEXT_TITLE}}` → 从问题派生

2. **知识上下文：** 对 agent 在 registry 中 `knowledge_context` 里的每个路径：
   - 把 `{active}` 替换为活跃数据集名称
   - 读取该文件并把其内容作为该 agent 的上下文纳入

3. **依赖输出：** 对每个已完成的依赖 agent，从 pipeline_state.json 收集它的 `output_files`。这些成为当前 agent 的可用输入。

4. **流水线参数：** 把 `context`、`theme`、`audience`、`data_path` 中与该 agent 的 `inputs` 列表相关的项透传过去。

### Dry-Run 模式

当 `dry-run=true`：

1. 运行 Phase 0（预检校验）—— 检测任何问题
2. 打印执行计划：
   ```
   Execution Plan (dry-run):
   Plan: {plan_name}
   Agents: {count} active, {count} skipped

   Tier 0: [agent-a, agent-b]           (parallel)
   Tier 1: [agent-c]                    (sequential)
     Checkpoint 1: Frame Verification
   Tier 2: [agent-d, agent-e]           (parallel)
     Checkpoint 2: Analysis Verification
   ...

   Estimated steps: {count}
   Checkpoints: {list}
   ```
3. **不**执行任何 agent。打印后返回。

---

## CHECKPOINTS（检查点）

检查点是流水线各阶段之间的闸门。它们在推进前校验质量。检查点的触发取决于刚完成了哪些 agent，而非硬编码的步骤编号。

### Checkpoint 1 — Frame Verification（在 hypothesis 完成后）

**类型：** B（面向用户）。**计划：** full_presentation、deep_dive。

自检：
- [ ] 业务问题具体且面向决策
- [ ] 分析设计 spec 点明了具体的表/列
- [ ] 至少 3 个假设，跨多个原因类别
- [ ] agent 文件是从磁盘读取的

呈现摘要：
> "Questions framed. Design spec ready.
> - Business question: [summary]
> - Tables: [list]
> - Hypotheses: [count] across [N] categories
>
> Proceed to analysis?"

**跳过条件：** 用户说了"just do it"或提供了所有参数。

### Checkpoint 2 — Analysis Verification（在 opportunity-sizer 完成后）

**类型：** A（自动）。**计划：** full_presentation、deep_dive。

核实：
- [ ] source tie-out 通过
- [ ] 根因具体且可行动
- [ ] 发现已校验（SQL 抽查过）
- [ ] 数据质量问题已记录
- [ ] 机会量化包含敏感性分析

如果根因含糊，重跑 root-cause-investigator。

### Checkpoint 2.5 — Storyboard Review（在 narrative-coherence-reviewer 完成后）

**类型：** B（面向用户）。**计划：** 仅 full_presentation（L5）。

呈现 storyboard 摘要，含节拍标题和弧线结构。

**跳过条件：** 用户说了"just do it"或 reviewer 标记了问题（转去修订）。

### Checkpoint 3 — Story & Charts（在图表级 visual-design-critic 完成后）

**类型：** A（自动）。**计划：** full_presentation、quick_chart。

核实：R2（标题撞车扫描）、R3（背景）、R5（禁用词）、R7（图表 figsize）、故事弧线、图表分发结果。打印标题撞车表。

**修复循环（chart-maker-fixes）：**
在 visual-design-critic 完成后，读取 `working/design_review_{{DATASET}}.md` 并提取裁决：

1. **APPROVED** → 在 pipeline_state.json 中把 `chart-maker-fixes` 标记为 `skipped`。进入 storytelling 层。

2. **APPROVED WITH FIXES** → 从设计审查中提取修复报告章节。把 `chart-maker-fixes` 设为 `ready`。把修复报告作为 `FIX_REPORT` 输入传入。chart-maker-fixes agent（与 chart-maker 同一文件，但提供了 `FIX_REPORT`）只重新生成修复报告中列出的图表。完成后，重跑 visual-design-critic 做一次快速复查。如果复查后仍是 `APPROVED WITH FIXES`，照样推进（最多一次修复循环迭代）。

3. **NEEDS REVISION** → HALT 流水线，消息为：`"Design critic returned NEEDS REVISION. Manual intervention required. Review: working/design_review_{{DATASET}}.md"`。**不要**进入 storytelling。

### Checkpoint 4 — Final Deck（在 deck-creator 和幻灯片级 visual-design-critic 完成后）

**类型：** A（自动）。**计划：** full_presentation、refresh_deck。

核实：R1（主题）、R2（标题）、R3（背景）、R4（建议排序）、R5（禁用词）、R6（呼吸页）、R7（图表 figsize）、R10（HTML 组件）、R11（导出）、deck 大小 8-22 页、演讲者备注齐备。

**Marp Lint 闸门（R10）：**
对 deck 输出运行 `helpers/marp_linter.py`。打印 lint 报告。

```python
from helpers.marp_linter import lint_deck, format_report

result = lint_deck("outputs/deck_{{DATASET_NAME}}_{{DATE}}.marp.md")
print(format_report(result))

if not result["summary"]["pass"]:
    # FAIL checkpoint — report errors
    print(f"CHECKPOINT 4 FAIL: {result['summary']['errors']} lint errors")
    for issue in result["issues"]:
        if issue["severity"] == "ERROR":
            print(f"  - {issue['code']}: {issue['message']}")
```

会让 Checkpoint 4 FAIL 的 lint 错误：
- `FM-*`：缺失或错误的 frontmatter 键
- `COMP-MIN`：少于 3 种 HTML 组件类型
- `CLASS-INVALID`：无效的幻灯片 class（例如 `breathing`）
- `R2-COLLISION`：图表标题与幻灯片标题相同

会被报告但**不**导致检查点失败的 lint 警告：
- `COMP-PLAIN`：纯 markdown 的内容页
- `SLIDES-LOW` / `SLIDES-HIGH`：页数在 8-22 之外
- `R6-PACING`：连续内容页没有节奏停顿
- `IMG-BARE-MD`：裸 markdown 图片（`![](...)`）未包在 `.chart-container` 里

---

## 图表分发协议（Chart Fan-Out Protocol）

当 chart-maker 变为 READY（在 narrative-coherence-reviewer 之后）：

1. **解析 storyboard：** 读取 `working/storyboard_{{DATASET}}.md`。对每个节拍，遍历 `slides` 数组并收集 `type: chart-full`、`chart-left` 或 `chart-right` 的幻灯片。每个图表类幻灯片引用其父节拍的图表 spec。
2. **构建 chart_specs 列表：** `[{beat_number, slide_index, headline, chart_spec, output_name}, ...]`
3. **顺序执行：** 每个图表 spec 调用一次 Chart Maker，一次一个（无并行）。每次调用：
   - 传入具体的 `chart_spec`、`output_name` 和共享的流水线上下文
   - 图表以标准 (10, 6) figsize 生成（R7）
   - 追踪：`chart_results[beat] = {status, files, error}`
   - 失败时：记录错误，把该图标记为 `failed`，继续下一张图
4. **批量审查：** 所有图表生成后，用整套图表文件调用一次 Visual Design Critic 做批量审查。传入所有 `chart_results` 输出路径。
5. **核实：** 检查所有输出文件存在（每张图的基础 PNG + SVG）。在 Checkpoint 3 报告缺失/失败的图表以便重试。

---

## 超时处理（TIMEOUT HANDLING）

每个 agent 有 5 分钟执行超时：

1. agent 启动时，记录 `started_at`
2. 如果 5 分钟过去仍未完成：
   - 把该次尝试标记为超时
   - **用相同上下文重试一次**
3. 如果重试也超时：
   - 把 agent 标记为 `failed`，错误为：`"Timeout after 2 attempts (5min each)"`
   - 应用降级策略：如果该 agent 非关键（visual-design-critic、narrative-coherence-reviewer），带警告继续流水线。如果关键（source-tieout、validation），HALT。

**关键 agent**（超时即 HALT）：source-tieout、validation、data-explorer
**非关键 agent**（超时即降级）：visual-design-critic、narrative-coherence-reviewer、opportunity-sizer

---

## 熔断器（CIRCUIT BREAKER）

防止失控的失败耗尽资源：

- 按执行层追踪失败计数
- **阈值：单层 3 次失败** → HALT 流水线
- HALT 时，报告：
  ```
  Circuit breaker tripped in tier {N}.
  Failed agents: {list with error messages}
  Completed agents: {list}
  Suggestion: Fix the underlying issue and /resume-pipeline
  ```
- 熔断器**不**为被跳过的 agent 触发，只为失败的 agent 触发

---

## 执行指标（EXECUTION METRICS）

每个 agent 完成后（无论成功或失败），在 `working/pipeline_metrics.json` 中记录时间：

```json
{
  "pipeline_id": "2026-02-16T09:30:00Z",
  "started_at": "ISO datetime",
  "completed_at": "ISO datetime",
  "total_duration_seconds": 0,
  "agents": {
    "question-framing": {
      "tier": 0,
      "started_at": "ISO datetime",
      "completed_at": "ISO datetime",
      "duration_seconds": 0,
      "status": "completed",
      "retries": 0
    }
  },
  "tiers": {
    "0": {
      "agents": ["question-framing", "data-explorer"],
      "started_at": "ISO datetime",
      "completed_at": "ISO datetime",
      "duration_seconds": 0,
      "parallel_agents": 2,
      "sequential_duration_seconds": 0,
      "parallel_efficiency": 0.0
    }
  },
  "summary": {
    "total_agents": 0,
    "completed": 0,
    "failed": 0,
    "skipped": 0,
    "total_tiers": 0,
    "avg_parallel_efficiency": 0.0
  }
}
```

**并行效率** = sum(各 agent 时长) / 该层挂钟时长。值为 2.0 表示并行带来 2 倍提速。

每层完成后写入指标。最终摘要在流水线结束时写入。

---

## 进度报告

在每层（映射到各阶段）的开始和结束时，发出进度：

**阶段映射**（层到阶段，用于面向用户的消息）：

| Phase | Agents | Name |
|-------|--------|------|
| 1 | question-framing, hypothesis | Framing |
| 2 | data-explorer, source-tieout, descriptive-analytics, root-cause-investigator, validation, opportunity-sizer | Exploration & Analysis |
| 3 | story-architect, narrative-coherence-reviewer, chart-maker, visual-design-critic | Storytelling & Charts |
| 4 | storytelling, deck-creator, visual-design-critic-slides, close-the-loop | Deck & Delivery |

**开始格式：** `[Phase N/4: {Name}] Starting... ({agent_count} agents)`
**结束格式：** `[Phase N/4: {Name}] Complete. ({summary}) | Overall: {completed}/{total} agents done`

---

## 常见失败模式（COMMON FAILURE MODES）

| Failure | Root Cause | Prevention Rule | When Caught |
|---------|-----------|----------------|-------------|
| Dark theme on standard analysis | Deck Creator defaulted to dark | R1 | Checkpoint 4 |
| Chart title = slide headline | Story Architect wrote same text | R2 | Checkpoint 3, 4 |
| Chart on pure white background | `swd_style()` not called | R3 | Checkpoint 3 |
| Recommendations in random order | Listed by topic not confidence | R4 | Checkpoint 4 |
| Sensational language | Dramatic words in headlines | R5 | Checkpoint 3, 4 |
| Wall of charts, no pacing | No breathing slides | R6 | Checkpoint 4 |
| Tiny chart text on slides | Chart rendered at small figsize | R7 | Checkpoint 3 |
| Agent guidance not followed | Didn't read agent file from disk | R8 | All checkpoints |
| Analysis on corrupted data | Data loading error | R9 | Checkpoint 2 |
| Cycle in registry | New agent added with circular dep | Cycle detection | Pre-flight |
| Deadlock in DAG | Tier has no READY agents | Deadlock detection | Phase 2 loop |
| Runaway failures | Multiple agents failing | Circuit breaker | Phase 2 loop |
| No HTML components | Deck uses only plain markdown | R10 | Checkpoint 4 (lint) |
| Missing html:true | Components render as raw HTML text | R10 | Checkpoint 4 (lint) |
| Missing size:16:9 | Slides render at 4:3 with broken layouts | R10 | Checkpoint 4 (lint) |
| Export fails | Marp CLI not installed or crashes | R11 | Post-Checkpoint 4 |
| Stale pipeline state | Previous run crashed mid-execution | Step 0 cleanup | Pre-flight |
| Chart text overlap | Labels collide at rendered size | R7 | Checkpoint 3 + chart-maker HALT |
| Chart overflows slide | Bare `![](...)` image not in `.chart-container` | R10 | Checkpoint 4 (lint: IMG-BARE-MD) |

---

## Checkpoint 4 之后：Deck 导出（R11）

Checkpoint 4 通过后，把 deck 导出为 PDF 和 HTML：

```python
from helpers.marp_export import export_both, check_ready

deck_path = "outputs/deck_{{DATASET_NAME}}_{{DATE}}.marp.md"
theme = pipeline_args.get("theme", "analytics")

# Check if Marp CLI is available
status = check_ready()
if not status["marp_cli"]:
    print("WARNING: Marp CLI not available. Skipping PDF/HTML export.")
    print("  Install: npm install -g @marp-team/marp-cli")
    # Record skip in pipeline_state.json
    pipeline_state["export"] = {"status": "skipped", "reason": "marp_cli_unavailable"}
else:
    try:
        exports = export_both(deck_path, theme)
        print(f"PDF:  {exports['pdf']}")
        print(f"HTML: {exports['html']}")
        # Record in pipeline_state.json
        pipeline_state["export"] = {
            "status": "completed",
            "pdf": str(exports["pdf"]),
            "html": str(exports["html"]),
        }
    except Exception as e:
        print(f"WARNING: Export failed: {e}")
        pipeline_state["export"] = {"status": "failed", "error": str(e)}
```

导出是非阻塞的 —— 失败记为警告，而非让流水线 HALT。Marp
markdown deck 始终是主交付物；PDF/HTML 是便利输出。

---

## 流水线后：收尾运行目录

导出之后、指标捕获之前，整合运行目录：

1. **复制产物**，从 `working/` 和 `outputs/` 到 `{RUN_DIR}/working/` 和 `{RUN_DIR}/outputs/`
2. **更新 pipeline_state.json**（在 `{RUN_DIR}/` 中）：设置 `status: completed`，记录 `completed_at`
3. **核实符号链接：** 确认 `working/latest` 指向本次运行目录

运行目录现在是整个分析的自包含快照。

---

## 流水线后：指标捕获与归档

所有检查点通过后、报告完成之前：

**指标捕获钩子：**
1. 扫描分析报告中的指标引用
2. 对每个指标检查 `.knowledge/datasets/{active}/metrics/index.yaml`
3. 记下新指标："New metric detected: {name}. Use `/metrics` to define it."
4. 更新已有条目的 `last_used`

**归档钩子：**
1. 应用 archive-analysis skill（`.claude/skills/archive-analysis/skill.md`）
2. 捕获：标题、问题、等级、关键发现、用到的指标、调用的 agent、输出文件
3. 写入 `.knowledge/analyses/index.yaml`

## 流水线完成

所有检查点通过后，报告：
1. 输出文件（deck、图表、叙事路径、PDF/HTML 导出路径）
2. 检查点结果摘要（含 Marp lint 报告）
3. 执行指标摘要（时长、并行效率）
4. 指标状态（新增/更新）
5. 归档确认（分析 ID）
6. 导出状态（PDF/HTML 已生成，或带原因跳过）
6. 任何需要的人工后续

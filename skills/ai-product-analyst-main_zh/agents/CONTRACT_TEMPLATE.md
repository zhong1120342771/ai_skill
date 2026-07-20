# CONTRACT 块模板（OR-1.5）

## 目的
每个 agent 的 `.md` 文件都必须以一个 CONTRACT 块开头——它是一段写在 HTML 注释里、描述该 agent 接口的 YAML 声明。OR-3 DAG walker 读取这些 contract 来构建执行图。

CONTRACT 块在运行时对 agent 不可见（它是 HTML 注释），但对流水线编排、依赖解析和文档生成而言是机器可读的。

## 格式

```yaml
<!-- CONTRACT_START
name: agent-name
description: One-sentence description of what this agent does.
inputs:
  - name: INPUT_NAME
    type: str | file | query_result
    source: user | system | agent:other-agent-name
    required: true | false
  - name: ANOTHER_INPUT
    type: file
    source: agent:upstream-agent
    required: true
outputs:
  - path: working/output_{{VARIABLE}}.md
    type: markdown | csv | json | image
  - path: outputs/final_{{DATE}}.md
    type: markdown
depends_on:
  - upstream-agent-name
pipeline_step: 5
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
CONTRACT_END -->
```

## 实例

### 最简 contract（无依赖）

来自 `agents/question-framing.md`：

```yaml
<!-- CONTRACT_START
name: question-framing
description: Generate prioritized analytical questions from a business problem, producing a structured question brief with hypotheses and data requirements.
inputs:
  - name: BUSINESS_CONTEXT
    type: str
    source: user
    required: true
  - name: PRODUCT_DESCRIPTION
    type: str
    source: user
    required: true
  - name: AVAILABLE_DATA
    type: str
    source: user
    required: true
outputs:
  - path: outputs/question_brief_{{DATE}}.md
    type: markdown
depends_on: []
knowledge_context: []
pipeline_step: 1
CONTRACT_END -->
```

### 带上游依赖和知识上下文的 contract

来自 `agents/data-explorer.md`：

```yaml
<!-- CONTRACT_START
name: data-explorer
description: Discover what data exists in a source, profile its quality and completeness, identify tracking gaps, and recommend supported analyses.
inputs:
  - name: DATA_SOURCE
    type: str
    source: user
    required: true
  - name: ANALYSIS_GOALS
    type: str
    source: user
    required: false
outputs:
  - path: outputs/data_inventory_{{DATE}}.md
    type: markdown
  - path: working/data_inventory_raw.md
    type: markdown
depends_on: []
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: 4
CONTRACT_END -->
```

### 带 agent 来源输入的 contract

来自 `agents/story-architect.md`：

```yaml
<!-- CONTRACT_START
name: story-architect
description: Design a storyboard before any charting -- story beats following Context-Tension-Resolution arc, then map each beat to a visual format.
inputs:
  - name: ANALYSIS_RESULTS
    type: file
    source: agent:root-cause-investigator
    required: true
  - name: QUESTION_BRIEF
    type: file
    source: agent:question-framing
    required: false
  - name: DATASET
    type: str
    source: system
    required: true
  - name: CONTEXT
    type: str
    source: user
    required: false
outputs:
  - path: working/storyboard_{{DATASET}}.md
    type: markdown
depends_on:
  - opportunity-sizer
knowledge_context:
  - .knowledge/datasets/{active}/manifest.yaml
pipeline_step: 9
CONTRACT_END -->
```

## 字段说明

| 字段 | 是否必填 | 说明 |
|-------|----------|-------------|
| `name` | 是 | agent 标识。必须与去掉 `.md` 的文件名一致（例如 `question-framing.md` 对应 `question-framing`） |
| `description` | 是 | 一句话描述该 agent 做什么。用于流水线日志和摘要。 |
| `inputs` | 是 | agent 消费的输入变量列表。对仅读取知识上下文的 agent 可为空（`inputs: []`）。 |
| `inputs[].name` | 是 | 变量名，UPPER_SNAKE_CASE。必须与 agent 正文中的 `{{VARIABLE}}` 占位符一致。 |
| `inputs[].type` | 是 | `str`（文本值）、`file`（文件路径或文件内容）、`query_result`（来自 SQL 查询或 dataframe 的数据） |
| `inputs[].source` | 是 | `user`（用户在提示中提供）、`system`（自动解析：DATE、DATASET_NAME 等）、`agent:X`（来自 agent X 的输出） |
| `inputs[].required` | 是 | 布尔值。该 agent 没有此输入能否运行。可选输入应在 agent 正文中记录合理的默认行为。 |
| `outputs` | 是 | 该 agent 产出的文件列表。路径中可包含 `{{VARIABLES}}`。 |
| `outputs[].path` | 是 | 相对仓库根目录的路径。中间文件用 `working/`，最终交付物用 `outputs/`。 |
| `outputs[].type` | 是 | 文件类型：`markdown`、`csv`、`json`、`image` |
| `depends_on` | 是 | 必须在本 agent 运行前完成的 agent 名称列表。可为空（`depends_on: []`）。 |
| `pipeline_step` | 是 | 在 18 步流水线中的数字位置（见 CLAUDE.md Default Workflow）。不属于流水线的独立 agent 用 `null`。并行 agent 共用同一个步骤编号。 |
| `knowledge_context` | 是 | 运行前需加载的 `.knowledge/` 文件路径列表。用 `{active}` 作为当前数据集名称的占位符。可为空（`knowledge_context: []`）。 |
| `critical` | 否 | 布尔值。默认 `true`。为 `false` 时，agent 采用 **warn_on_failure** 降级策略：若失败，流水线记录警告并以 `status: degraded` 继续，而非中止。用于失败不阻塞的审查/估算类 agent。 |
| `depends_on_any` | 否 | OR 依赖列表。本 agent 运行前，列表中至少有一个 agent 必须完成。与 `depends_on`（AND——全部必须完成）相对。两个字段同时存在时，所有 AND 依赖加上至少一个 OR 依赖都需满足。 |

### `warn_on_failure` 行为

当一个非关键 agent（`critical: false`）失败时：
1. 流水线将该 agent 状态置为 `degraded`（而非 `failed`）。
2. 记录一条带错误信息的警告。
3. 依赖该降级 agent 的下游 agent 会在其上下文中收到 `DEGRADED_UPSTREAM` 标志，以便自适应（例如跳过可选章节）。
4. 流水线继续——**不会**中止。

## 输入来源类型

### `user`
由用户在提示中或交互过程中提供。例如：业务上下文、产品描述、分析目标。这些是启动流水线的主要输入。

### `system`
由编排器在运行时自动解析。标准系统变量有：

| 变量 | 解析方式 |
|----------|------------|
| `{{DATE}}` | 当前日期，YYYY-MM-DD 格式 |
| `{{DATASET_NAME}}` | 来自 `.knowledge/active.yaml` 的短名称 |
| `{{BUSINESS_CONTEXT_TITLE}}` | 由 `{{BUSINESS_CONTEXT}}` 派生的简短标题 |
| `{{DATA_SOURCE}}` | 来自当前数据集 manifest 的连接串或路径 |
| `{{THEME}}` | 演示主题（默认：workshop 用 `analytics-dark`，报告用 `analytics`） |

### `agent:X`
来自 agent X 的输出。编排器读取 agent X 的 `outputs` 定位文件，再把其路径或内容作为输入传入。这会建立一条显式依赖——agent X 必须先于本 agent 完成。

**示例：** `source: agent:question-framing` 表示本 agent 消费 `question-framing` agent 的输出（通常是 `outputs/question_brief_{{DATE}}.md`）。

## 规则

1. **CONTRACT 块必须在最前面。** 它必须是文件中第一个出现的内容，位于 `# Agent Name` 标题之前。前面不能有空行。

2. **CONTRACT 块是 HTML 注释。** 以 `<!-- CONTRACT_START` 开头，以 `CONTRACT_END -->` 结尾。这样当 agent 文件作为指令读取时它不可见，但 DAG walker 能解析。

3. **`depends_on` 必须与 `agent:X` 来源匹配。** `inputs[].source` 中每个 `agent:X` 引用，在 `depends_on` 里都要有对应条目。若某 agent 读取 `agent:question-framing` 的输出，则 `question-framing` 必须出现在 `depends_on` 中。

4. **`pipeline_step` 在每个串行位置必须唯一。** 串行运行的 agent 必须有不同的步骤编号。可并行运行的 agent 共用同一步骤编号（例如 `descriptive-analytics`、`overtime-trend` 和 `cohort-analysis` 都在第 5 步）。

5. **每个 `agent:X` 来源都必须可满足。** `agent:X` 中命名的 agent 必须作为文件存在于 `agents/` 中，且必须在其自己的 CONTRACT 块里声明被引用的那个输出。

6. **`name` 必须与文件名匹配。** CONTRACT 中的 `name` 字段必须与 agent 文件名去掉 `.md` 后缀后完全一致。`name: data-explorer` 位于 `agents/data-explorer.md`。

7. **knowledge_context 路径中用 `{active}`。** 不要硬编码数据集名称。编排器会把 `{active}` 替换为 `.knowledge/active.yaml` 中的当前数据集名称。

8. **可选输入需要默认行为。** 若 `required: false`，agent 正文必须说明该输入未提供时会发生什么。即便没有它，agent 也应能正确运行。

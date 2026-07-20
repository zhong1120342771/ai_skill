# 执行计划（Execution Plans）

执行计划定义一次流水线运行要包含哪些 agent。每个计划是一份白名单：不在计划中的 agent 会被跳过。依赖关系仍然受到尊重 —— 如果某个被跳过的 agent 的输出是必需的，流水线会发出警告。

## 计划：full_presentation（默认）

**何时使用：** 从业务问题到经过校验的幻灯片，端到端的完整分析。

```yaml
agents:
  - question-framing
  - hypothesis
  - data-explorer
  - source-tieout
  - descriptive-analytics   # or overtime-trend or cohort-analysis
  - root-cause-investigator
  - validation
  - opportunity-sizer
  - story-architect
  - narrative-coherence-reviewer
  - chart-maker
  - visual-design-critic
  - storytelling
  - deck-creator
  - visual-design-critic-slides
  - close-the-loop
checkpoints: [1, 2, 2.5, 3, 4]
```

## 计划：deep_dive

**何时使用：** 不做 deck 的深入分析。在机会量化（opportunity sizing）后停止。

```yaml
agents:
  - question-framing
  - hypothesis
  - data-explorer
  - source-tieout
  - descriptive-analytics
  - root-cause-investigator
  - validation
  - opportunity-sizer
checkpoints: [1, 2]
```

## 计划：quick_chart

**何时使用：** 用户只想从已有分析里出一张图。跳过 framing 和分析。

```yaml
agents:
  - chart-maker
  - visual-design-critic
checkpoints: [3]
skip_validation: true
requires_context:
  - working/storyboard_*.md OR explicit chart spec from user
```

## 计划：refresh_deck

**何时使用：** 从已有 storyboard 和图表重新生成 deck。跳过分析。

```yaml
agents:
  - storytelling
  - deck-creator
  - visual-design-critic
checkpoints: [4]
requires_context:
  - working/storyboard_*.md
  - outputs/charts/*.png
```

## 计划：validate_only

**何时使用：** 对已有分析重跑校验。不产出新的分析。

```yaml
agents:
  - validation
checkpoints: []
requires_context:
  - working/investigation_*.md OR outputs/analysis_report_*.md
```

## 计划选择逻辑

1. 如果用户传入 `plan=X`，就用该计划
2. 如果用户说"just make a chart"或类似，自动选择 `quick_chart`
3. 如果用户说"refresh the deck"或"rebuild slides"，自动选择 `refresh_deck`
4. 如果用户说"validate"或"re-check"，自动选择 `validate_only`
5. 如果 Question Router 分类为 L3/L4，自动选择 `deep_dive`
6. 默认：`full_presentation`

## 自定义计划

用户可以指定一个内联 agent 列表：
```
/run-pipeline agents=question-framing,hypothesis,data-explorer,source-tieout
```

这会创建一个只含所列 agent 的临时计划。依赖警告仍然适用。

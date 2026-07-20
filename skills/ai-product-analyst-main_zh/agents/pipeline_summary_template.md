# 流水线摘要模板（OR-1.4）

## 目的
在每个流水线阶段完成后生成的人类可读摘要。
执行期间写入 `working/pipeline_summary.md`，增量更新。
提供快速的状态概览，无需解析 `pipeline_state.json`。

## 阶段

为便于摘要，18 步流水线被归为五个阶段：

| 阶段 | 步骤 | 说明 |
|-------|-------|-------------|
| Question Framing | 1-3 | 业务问题、假设、分析设计 |
| Data Exploration | 4-4.5 | schema 发现、质量检查、源校验 |
| Analysis | 5-8 | 核心分析工作、验证、机会量化 |
| Storytelling | 9-14 | 故事板、图表、设计审查 |
| Delivery | 15-18 | 叙事、deck、幻灯片审查、闭环 |

## 模板

```markdown
# Pipeline Summary: {{BUSINESS_CONTEXT_TITLE}}

**Dataset:** {{DATASET_NAME}}
**Date:** {{DATE}}
**Pipeline ID:** {{PIPELINE_ID}}
**Status:** {{PIPELINE_STATUS}}

---

## Phase: Question Framing (Steps 1-3)
**Status:** completed | running | pending

- **Question:** [framed question from question-framing agent]
- **Decision this informs:** [one-sentence decision statement]
- **Hypotheses:** [count] hypotheses generated across [count] categories
- **Analysis design:** [confirmed / pending]
- **Files:**
  - `outputs/question_brief_{{DATE}}.md`
  - `working/hypotheses_{{DATASET_NAME}}.md`
  - `working/analysis_design_spec.md`

---

## Phase: Data Exploration (Steps 4-4.5)
**Status:** completed | running | pending

- **Tables explored:** [count]
- **Total rows:** [count across all tables]
- **Date range:** [earliest] to [latest]
- **Source tie-out:** PASS / FAIL
- **Quality issues:** [count] blockers, [count] warnings
- **Tracking gaps:** [count] gaps identified, [count] with workarounds
- **Files:**
  - `outputs/data_inventory_{{DATE}}.md`
  - `working/data_inventory_raw.md`
  - `working/source_tieout_{{DATASET_NAME}}.md`

---

## Phase: Analysis (Steps 5-8)
**Status:** completed | running | pending

- **Analyses run:** [list of agent names that executed, e.g. descriptive-analytics, root-cause-investigator]
- **Key findings:**
  - [finding 1 — one sentence]
  - [finding 2 — one sentence]
  - [finding 3 — one sentence]
- **Root cause:** [one-sentence root cause if identified, or "N/A"]
- **Opportunity size:** [dollar or percentage impact if sized, or "N/A"]
- **Validation:** PASS / FAIL / PASS WITH CAVEATS
- **Files:**
  - `working/descriptive_{{DATASET_NAME}}.md`
  - `working/root_cause_{{DATASET_NAME}}.md`
  - `working/validation_{{DATASET_NAME}}.md`
  - `working/opportunity_sizing_{{DATASET_NAME}}.md`

---

## Phase: Storytelling (Steps 9-14)
**Status:** completed | running | pending

- **Story arc:** [Context-Tension-Resolution summary in one sentence]
- **Story beats:** [count] beats
- **Narrative coherence review:** APPROVED / APPROVED WITH FIXES / NEEDS REVISION
- **Charts generated:** [count] charts ([count] base + [count] slide variants)
- **Design review:** APPROVED / APPROVED WITH FIXES / NEEDS REVISION
- **Charts revised:** [count] charts re-generated after design review
- **Files:**
  - `working/storyboard_{{DATASET_NAME}}.md`
  - `working/coherence_review_{{DATASET_NAME}}.md`
  - `outputs/charts/` — [list chart filenames]

---

## Phase: Delivery (Steps 15-18)
**Status:** completed | running | pending

- **Narrative:** [word count] words
- **Deck:** [slide count] slides, theme: {{THEME}}
- **Slide design review:** APPROVED / APPROVED WITH FIXES
- **Close-the-loop:** [count] action items, each with owner + follow-up date
- **Output files:**
  - `outputs/narrative_{{DATASET_NAME}}_{{DATE}}.md`
  - `outputs/deck_{{DATASET_NAME}}_{{DATE}}.md`
  - `outputs/close_the_loop_{{DATE}}.md`

---

## Errors & Warnings
[List any errors or warnings encountered during execution. Empty if clean run.]

- [step X]: [error or warning description]
```

## 生成规则

1. **在每个阶段完成后更新**，而不是在每个单独步骤后。一个阶段在其所有步骤都为 `completed` 或 `skipped` 时才算完成。
2. 摘要中**只包含已完成的阶段**。待处理的阶段只显示一行 `**Status:** pending`，不带细节。
3. **摘要保持简洁**——每个发现 1-3 个要点。不要复述完整的分析文字。
4. **引用执行期间产出的实际文件路径**，而非模板占位符。把 `{{VARIABLES}}` 替换为解析后的值。
5. **Errors & Warnings 章节**始终存在。若本次运行无问题，写 "None."。
6. **不要从头重新生成**——读取现有的 `working/pipeline_summary.md`，追加新完成的阶段后覆盖写回。这样能原样保留更早阶段的摘要。
7. **与 pipeline_state.json 保持一致**——摘要中的阶段状态必须与 `working/pipeline_state.json` 里的步骤状态一致。

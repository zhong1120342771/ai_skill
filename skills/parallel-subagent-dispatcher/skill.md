---
name: parallel-subagent-dispatcher
description: |
  Break complex multi-item tasks into parallel sub-agents, execute
  concurrently, and merge results into a unified output. Use this
  when analyzing multiple files, processing batch data, reviewing
  multiple modules, or any task where N independent items can be
  processed simultaneously. The skill defines dispatch rules,
  output schemas, merge strategies, and quality checks.
---

# Parallel Sub-agent Dispatcher

## When to Use

Apply this skill when the user's task involves **multiple independent
items** that can be processed without waiting for each other's results.

Signal phrases:
- "审查所有文件" / "review all files"
- "批量处理" / "batch process"
- "同时分析" / "analyze simultaneously"
- "分别检查" / "check each one"
- "对比多个" / "compare multiple"

**Skip this skill** for:
- Single-item tasks
- Items with sequential dependencies (B needs A's output)
- Tasks under 3 items (overhead > benefit)

---

## Phase 1: Decompose the Task

### Step 1.1 — Identify Independent Units

Scan the task and split into N independent work items:

| Task Pattern | Unit = | Example |
|---|---|---|
| Review files | One file | `src/a.py`, `src/b.py` |
| Analyze datasets | One dataset/table | `orders`, `users`, `products` |
| Compare options | One option each | Option A, B, C |
| Batch questions | One question each | Q1, Q2, Q3... |

**Rule:** If two items don't share mutable state or
input/output dependency → they're independent → parallel.

### Step 1.2 — Group and Bound

- **Group same-type items** together (same sub-agent type =
  same prompt template + same output schema)
- **Cap concurrency** at 5–8 sub-agents (more = diminishing
  returns + context thrashing)
- **Split oversized groups**: if 20 files → 3 waves of 7/7/6

### Step 1.3 — Define Output Schema

Every sub-agent in a group MUST return the same JSON schema.
Define it before spawning. Example for a code-review group:

```json
{
  "file": "string (required)",
  "findings": [
    {
      "severity": "high | medium | low",
      "line": "number",
      "issue": "string",
      "suggestion": "string"
    }
  ]
}
```

---

## Phase 2: Dispatch Sub-agents

### Step 2.1 — Build Prompts

For each item, construct a sub-agent prompt with:

1. **Item content** — the file/data/question to process
2. **Task instruction** — what to do (same for whole group)
3. **Output schema** — the JSON format to return (same for
   whole group)
4. **Context isolation flag** — mark that this sub-agent
   should NOT access other items' content

### Step 2.2 — Spawn in Parallel

Dispatch all sub-agents simultaneously. Each sub-agent:
- Has an isolated context (only its own item)
- Has access to necessary tools (read, search, code exec)
- Returns ONLY structured data (not human-facing prose)

### Step 2.3 — Monitor and Retry

- Wait for all sub-agents to complete
- If any sub-agent fails (error / timeout / no response):
  - Retry once with simplified prompt
  - If still fails → mark item as `null` in results, continue

---

## Phase 3: Merge Results

### Step 3.1 — Collect

Gather all sub-agent outputs into a flat array:

```
results = [sub1_output, sub2_output, ..., subN_output]
           .filter(Boolean)  // remove nulls from failed agents
```

### Step 3.2 — Deduplicate

For overlapping findings across items:
- **Same issue + same pattern** → keep the first, note others
  as "also found in: [files]"
- **Different severity for same issue** → keep the highest

### Step 3.3 — Sort and Rank

Sort merged findings by:
1. Severity (high → medium → low)
2. Item/File name (alphabetical)

### Step 3.4 — Produce Unified Report

Structure the final output:

```
## Summary
- {N} items processed, {M} findings total
- {X} high, {Y} medium, {Z} low severity
- {F} items failed (if any)

## Findings by Severity

### High ({X})
| Item | Line | Issue | Suggestion |
|------|------|-------|------------|

### Medium ({Y})
...

### Low ({Z})
...

## Failed Items (if any)
- {item}: {error reason}
```

---

## Phase 4: Quality Checks

Before presenting results, verify:

- [ ] All sub-agent outputs conform to the defined schema
- [ ] No duplicate findings remain after dedup
- [ ] Severity counts sum to total findings
- [ ] Failed items are documented with reasons
- [ ] Report is self-contained (reader doesn't need sub-agent
  internals to understand findings)

---

## Context Isolation (Why It Works)

Sub-agents have **independent context windows** that do NOT consume
the main agent's context budget. This is the key architectural
advantage:

```
Main Agent Context (small, clean):
  ├── skill.md instructions
  ├── task manifest (item list, schema)
  ├── sub-agent 1 result → structured JSON only
  ├── sub-agent 2 result → structured JSON only
  └── merge logic

Sub-agent 1 Context (isolated):
  ├── file_a.py content (full)
  ├── review instructions
  └── output schema → returns JSON, not prose

Sub-agent 2 Context (isolated):
  ├── file_b.py content (full)
  └── ... (same pattern)
```

**What stays OUT of the main agent's context:**
- Individual file/data contents (stays in sub-agent)
- Sub-agent internal reasoning chains
- Intermediate tool call results within sub-agents

**What comes back to the main agent:**
- Only the structured JSON result per sub-agent
- This follows the progressive disclosure pattern —
  load only what you need, when you need it.

**Concrete benefit:**
- Reviewing 5 files @ 500 lines each = 2500 lines of code
- Without isolation → all 2500 lines in main context
- With isolation → main context holds only 5 JSON objects (~200 lines)

---

## Anti-patterns

| ❌ Don't | ✅ Do |
|---|---|
| Spawn 20+ sub-agents at once | Cap at 5–8, use waves |
| Let sub-agents share mutable state | Isolate each sub-agent's context |
| Let sub-agents produce free-form text | Require structured JSON output |
| Present raw sub-agent output | Merge, dedup, sort, then present |
| Skip the schema definition phase | Define output schema BEFORE dispatch |
| Use for dependent tasks (B needs A) | Use sequential steps for dependencies |

---

## References

- `references/output-schemas.md` — catalog of reusable JSON schemas
- `references/merge-strategies.md` — advanced merge and dedup patterns
- `assets/report-template.md` — unified report template

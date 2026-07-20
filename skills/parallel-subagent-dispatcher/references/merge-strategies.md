# Merge & Dedup Strategies

After all parallel sub-agents return results, the main agent must
merge them into a coherent output. This file defines reusable
merge patterns.

---

## Strategy 1: Union Merge (default)

**When:** Each sub-agent reports on a different item (e.g.,
different files, different datasets). No cross-item overlap
expected.

**How:**
```python
all_findings = []
for result in results:
    for f in result.findings:
        all_findings.append({**f, "source": result.file})
all_findings.sort(key=lambda f: severity_order(f.severity))
```

No dedup needed — items are disjoint.

---

## Strategy 2: Cross-item Dedup

**When:** Multiple sub-agents may report the same systemic issue
(e.g., same library vulnerability in multiple files, same data
quality problem across tables).

**How:**
```python
seen = {}  # key: (category, normalized_issue_text) → first occurrence
deduped = []
for f in all_findings:
    key = (f.category, normalize(f.issue))
    if key not in seen:
        seen[key] = f
        f.also_found_in = []
        deduped.append(f)
    else:
        seen[key].also_found_in.append(f.source)
```

**Normalize:** lowercase, strip punctuation, remove variable
names/numbers. "SQL injection on line 42" and "SQL injection on
line 108" → same key.

---

## Strategy 3: Consensus Merge

**When:** Multiple sub-agents evaluate the SAME item from
different angles (e.g., one checks bugs, one checks security,
one checks performance).

**How:**
- If >= 2 agents flag same finding → **confirmed**
- If 1 agent flags alone → mark as **tentative, needs review**
- If 0 agents flag → **not a finding**

```python
confirmed = []
tentative = []
for finding in all_findings:
    votes = count_agents_reporting(finding, results)
    if votes >= 2:
        confirmed.append({**finding, "confidence": votes / len(results)})
    else:
        tentative.append({**finding, "confidence": "low"})
```

---

## Strategy 4: Scored Ranking

**When:** Sub-agents assign scores (e.g., comparing options).
Need to aggregate across dimensions.

**How:**
```python
merged = {}
for result in results:
    for dim in result.dimensions:
        if dim.name not in merged:
            merged[dim.name] = []
        merged[dim.name].append(dim.score)

# Average per dimension, compute weighted total
for name, scores in merged.items():
    avg = sum(scores) / len(scores)
    print(f"{name}: {avg:.1f}/10")
```

---

## Quality Gates After Merge

After applying any strategy, verify:

1. **No orphan findings** — every finding has a source item
2. **No phantom duplicates** — two findings with same source +
   same line/issue shouldn't coexist
3. **Severity consistency** — same issue across items should
   have same severity
4. **Count integrity** — total = sum of (per-source counts),
   minus deduped

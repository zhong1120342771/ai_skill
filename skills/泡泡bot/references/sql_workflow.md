# SQL Workflow

## Probe Order

Use this order for unknown Hive tables:

1. `describe table`
2. `show partitions table` or `describe formatted table`
3. `select * from table where dt='...' limit 20`

If `show partitions` fails, try `describe formatted` and inspect partition metadata. If the table has no partition, sample with plain `limit`.

If `describe` succeeds but `sample` or analytical `select` fails with permission denied, do not silently discard the table. Keep it as a candidate and judge it by semantic fit:

- If it is the best-fit table for the business question, tell the user explicitly that this is the preferred table but requires permission. Include the table name and the key fields found in `describe`, and suggest applying for access or switching organization/source as indicated by the error.
- Only present a readable substitute as a temporary fallback, and label the compromise in caliber, grain, or fields.
- Do not let access failure make a weaker readable table look like the recommended source.

## SQL Writing Rules

- Prefer CTEs with semantic names: `base_users`, `fact_orders`, `daily_metrics`, `final`.
- For metrics, make numerator and denominator explicit.
- For ratios, use ratio of sums unless the user asks for average of row-level ratios.
- Use `count(distinct key)` only when key uniqueness is not guaranteed.
- When joining snapshots and facts, confirm whether the snapshot date and fact date should match.
- When a table has `dt`, probes default to the latest known partition or `t-1`.
- Treat schema evidence as turn-local. Do not invent columns such as `timestamp`, `pay_ts`, `brand_name`, or `series_id` from memory; if they are not in the current prompt or current probe output, run `describe` with a focused `--columns` filter before using them.
- Track user-declared unreliable fields as "known bad" for the rest of the task. Do not reuse them for conclusions unless the user explicitly asks for a temporary approximation.
- Before switching source tables, state the reason for switching and the caliber loss or semantic change, such as query request grain vs result-product grain, exposure time vs request time, or query-intent attributes vs recalled-product attributes.
- When combining multiple tables, label each output field by source semantics in the SQL alias or response: for example, distinguish result-product brand/model from query-intention brand/model.
- Apply minimal patches when the user asks for a narrow change. Preserve their base SQL and only add the requested fields, filters, or CTEs unless a correctness blocker requires a rewrite.
- Prefer staged thinking for fragile analyses. Start by defining the narrow, auditable fact grain (`query + info_id + pv`, `user + day`, `order + item`, etc.), then layer classification or rates on top. This can be one runnable SQL with clear CTEs, or multiple materialized tables when the intermediate result needs user inspection or reuse.
- When the user supplies a simpler fact-layer CTE, preserve that shape and extend from it. Do not replace it with a broader framework unless there is a clear correctness blocker.
- For recall/precision style analysis, separate the layers explicitly: result fact layer first, intent/matching layer second, rate aggregation last. Keep request PV, result exposure PV, item count, and matched exposure PV as distinct columns.
- For any matching, tagging, classification, or attribution task, first check whether the fact table already has the needed structured fields, flags, labels, dimensions, or stable ids. If not, check whether an equality join through keys such as `info_id`, `order_id`, `uid`, `token`, `cate_id`, `brand_id`, or `model_id` can recover them. Prefer existing fields and equality joins before writing custom matching logic.
- Use self-written matching such as `instr(text, word)`, regex, fuzzy matching, or dictionary substring matching only when the business question specifically requires matching raw text or no structured field/key can answer it. Call out that this route is noisier, slower, and may create duplicate matches.
- Avoid raw non-equi joins such as `LEFT JOIN dict ON instr(text, word) > 0`; Hive often treats them as cartesian joins. If text matching is unavoidable, first reduce the candidate set or add an equality prejoin key, or use a precomputed/curated dictionary mapping table.

## StarRiver Execution

The local `xinghe-submit` command writes result files under:

```text
~/claude-output/sql_result_<task_id>.tsv
```

The wrapper script prints the detected result path and a preview. Use that path for further local analysis.

## Common Probe SQL

```sql
describe db.table;
```

```sql
describe formatted db.table;
```

```sql
show partitions db.table;
```

```sql
select *
from db.table
where dt = 'YYYY-MM-DD'
limit 20;
```

```sql
select dt, count(*) as cnt
from db.table
where dt between 'YYYY-MM-DD' and 'YYYY-MM-DD'
group by dt
order by dt desc
limit 30;
```

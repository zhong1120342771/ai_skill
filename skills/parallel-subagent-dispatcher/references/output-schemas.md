# Reusable Output Schemas

Each sub-agent in a parallel group MUST return the same JSON schema.
Pick one below, or extend to fit your domain.

---

## Schema 1: Code Review Findings

```json
{
  "file": "string",
  "language": "string",
  "findings": [
    {
      "severity": "high | medium | low",
      "category": "bug | security | performance | style | logic",
      "line": "number",
      "issue": "string (one-line description)",
      "suggestion": "string (actionable fix)",
      "code_snippet": "string (the problematic code, optional)"
    }
  ]
}
```

---

## Schema 2: Data Analysis Results

```json
{
  "dataset": "string",
  "row_count": "number",
  "column_count": "number",
  "findings": [
    {
      "severity": "high | medium | low",
      "category": "missing_data | outlier | distribution | correlation | anomaly",
      "column": "string",
      "detail": "string",
      "recommendation": "string"
    }
  ]
}
```

---

## Schema 3: Document Review

```json
{
  "document": "string",
  "word_count": "number",
  "findings": [
    {
      "severity": "high | medium | low",
      "category": "clarity | accuracy | completeness | tone | structure",
      "section": "string",
      "issue": "string",
      "suggestion": "string"
    }
  ],
  "overall_score": "1-10"
}
```

---

## Schema 4: Generic Comparison

```json
{
  "option": "string",
  "dimensions": [
    {
      "name": "string",
      "score": "1-10",
      "pros": ["string"],
      "cons": ["string"]
    }
  ],
  "total_score": "number",
  "verdict": "string (one-paragraph summary)"
}
```

---

## Schema Extension Rules

When creating your own schema:

1. **Flat, not nested** — max 3 levels deep
2. **Required fields marked** — sub-agents must know what's
   mandatory
3. **Enums for categories** — constrain values to enable
   reliable merging
4. **Include file/item identifier** — every schema must have
   a top-level field identifying the source item
5. **Keep it small** — schema under 15 fields total (large
   schemas = sub-agents miss fields)

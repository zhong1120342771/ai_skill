---
name: 一体化日报-数据分析
description: 一体化项目日报流水线第 2 步——把 5 个 CSV 聚合为 7 项北极星指标的 t-1 值与历史序列。当用户说"算一下 7 个指标""出 metrics_yiti_${dt}.json""算环比/7 日均值/月均"，或编排器在代码生成完成后需要算指标时使用本 skill。
metadata:
  type: sub-skill
  parent: 一体化项目日报数据bot
  step: 2
  inputs:
    - data_storage/yiti_xianshang_${dt}.csv
    - data_storage/yiti_xiansuo_${dt}.csv
    - data_storage/yiti_tongshou_${dt}.csv
    - data_storage/yiti_xiaoshida_${dt}.csv
  outputs:
    - analysis_reports/metrics_yiti_${dt}.json
    - analysis_reports/metrics_yiti_${dt}.summary.md
---

# 一体化日报-数据分析

## 定位

本 skill 在 [`data-explorer`](~/.claude/agents/data-explorer.md) 通用 agent 之上做窄化——只算 7 项北极星指标的「t-1 绝对值 / 日环比 / 7 日均值 / 当月均值 / 月度序列 / 30 日序列」，不画图、不下结论。

## 前置阅读

1. **[../../References/取数与产出说明.md](../../References/取数与产出说明.md)** — 7 项指标口径在这里。
2. **[../../References/output-schemas.md](../../References/output-schemas.md)** §一 — `metrics_yiti_${dt}.json` 字段契约，必须严格匹配。

## 执行方式

直接调固化脚本：

```bash
python ~/.claude/skills/一体化项目日报数据bot/scripts/compute_metrics.py --dt ${dt}
```

## 必算指标

| 字段 | 口径 |
|---|---|
| `tongcheng_orders` | yiti_xianshang 中按 dt 汇总 `本地订单量` |
| `tongcheng_share` | 同城订单量 / 总订单量 |
| `offline_leads` | yiti_xiansuo 中 `xs_uv` 汇总（默认全 tag；如业务定义"线下线索"特定 tag，按其过滤） |
| `lead_conv_total` | yiti_xiansuo 中 `pay_uv` 汇总 |
| `tongshou_orders` | yiti_tongshou 中 `同售单量` 汇总 |
| `tongshou_dongxiao_rate` | 同售单量 / 同售库存 |
| `xiaoshida_orders` | yiti_xiaoshida 中 `小时达订单量` 汇总 |

每项指标输出：`value`（t-1 绝对值或比率）、`mom`（环比，t-1 vs t-2，比率小数）、`wow_mean`（T-7 ~ T-1 均值）、`month_mean`（当月均值）。

另外输出：
- `monthly_series`：从 2026-01 起，每月各指标的「月均」（用于月维度趋势图）。
- `daily_series`：过去 30 日各指标的日值（用于 30 日趋势图）。

## 产出

### `analysis_reports/metrics_yiti_${dt}.json`

机器可读，schema 见 [output-schemas.md §一](../../References/output-schemas.md)。

### `analysis_reports/metrics_yiti_${dt}.summary.md`

一页纸摘要：7 项指标 t-1 值 + 环比箭头 + 一句话点评，下游 agent 拿这个直接写报告。

## 不要做的事

- 不要画图（Step 4 出图）。
- 不要下因果/优化建议（Step 4 出结论）。
- 不要改 metrics JSON 的字段名（schema 是契约）。

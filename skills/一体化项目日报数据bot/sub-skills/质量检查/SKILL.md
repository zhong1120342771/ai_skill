---
name: 一体化日报-质量检查
description: 一体化项目日报流水线第 3 步——结论生成前的质量闸口。当用户说"先校验下""quality check""一体化数据质量"，或编排器在分析完成后准备进入结论生成时使用本 skill。基于通用 quality-assurance agent 适配，覆盖 4 个 CSV 与 metrics JSON 的完备性/合理性。
metadata:
  type: sub-skill
  parent: 一体化项目日报数据bot
  step: 3
  inputs:
    - data_storage/yiti_*_${dt}.csv
    - analysis_reports/metrics_yiti_${dt}.json
  outputs:
    - analysis_reports/quality_check_yiti_${dt}.json
---

# 一体化日报-质量检查

## 定位

本 skill 在 [`quality-assurance`](~/.claude/agents/quality-assurance.md) 通用质量保障 agent 之上做窄化——校验对象固定为 4 个 CSV + metrics JSON，**只判定不修复**。硬失败阻断流水线进入结论生成。

## 前置阅读

1. **[../../References/取数与产出说明.md](../../References/取数与产出说明.md)** — 业务真源，校验阈值依据。
2. **[../../analysis_reports/metrics_yiti_${dt}.summary.md](../../analysis_reports/)** — 上游摘要，先读它形成今日数据形状预期。

## 执行方式

```bash
python ~/.claude/skills/一体化项目日报数据bot/scripts/qa_check.py --dt ${dt}
```

退出码：`0=passed`、`2=hard 失败应阻断`、`3=输入文件缺失`、`4=内部异常`。

## 校验维度

### 一、数据完整性

| 检查项 | 阈值 | 失败级别 |
|---|---|---|
| 4 个 CSV 都存在且行数 > 0 | 4/4 | 硬失败 |
| 每个 CSV 都包含 t-1 当天数据 | dt = ${dt} 至少 1 行 | 硬失败 |
| metrics_yiti_${dt}.json 7 项指标都有 `value` | 7/7 | 硬失败 |
| `value` 无 NaN/inf | 严格无 | 硬失败 |

### 二、业务合理性

| 检查项 | 阈值 | 失败级别 |
|---|---|---|
| `tongcheng_share` 在 [0, 1] | 是 | 硬失败 |
| `tongshou_dongxiao_rate` 在 [0, 1] | 是 | 硬失败 |
| 7 项 `value` 全 ≥ 0 | 是 | 硬失败 |
| 7 项 `mom` 绝对值 ≤ 100% | 是 | warn |

### 三、与历史的一致性

- 任一指标 t-1 值偏离 7 日均值 > 50% → warn（可能是数据异动或埋点异常）。
- `wow_mean` 数据点数 < 7 → soft 失败（暂不显著，结论可继续但要标注）。

## 产出

`analysis_reports/quality_check_yiti_${dt}.json`，schema 见 [output-schemas.md §二](../../References/output-schemas.md)。`passed = (hard_failures 为空)`。

## 失败处理

- **硬失败**：编排器停止，不进结论生成。失败明细写 stderr。
- **软失败/warn**：继续进入结论生成，但报告中要在「待复核」段显式列出。

## 不要做的事

- 不要修复数据（只判定）。
- 不要重新算指标（直接读 metrics JSON）。

---
name: 核心指标异动监控-质检
description: 转转核心指标异动监控bot 流水线第 5 步——结论生成前的硬质量闸口。当编排器完成发现异常+下钻后、进入结论生成前调用；hard_failures 非空时阻断流水线。
metadata:
  type: agent
  parent: 转转核心指标异动监控bot
  step: 5
  inputs:
    - analysis_reports/tidy_${dt}.csv
    - analysis_reports/anomaly_${dt}.csv
    - analysis_reports/drilldown_${dt}.md
  outputs:
    - analysis_reports/quality_check_core_${dt}.json
---

# 质检（Step 5）

结论生成前的硬闸口。`passed=false` 即停，不进结论步——避免把错口径/坏数据写进给业务方的报告。

## 基础与定位

流水线第 5 步、结论前的唯一硬闸口。职责边界：只判"能不能进结论步"，不改数据、不写结论。核心价值是拦住本表最容易犯的口径错误：把 `matched_dau_uv` 为 NULL 的行当 0 算 DAU 率、北极星与漏斗链不自洽。判定统一走 `qa_check.py`，不即兴改写检查逻辑。

## 前置阅读

- [../../references/字段映射与指标口径.md](../../references/字段映射与指标口径.md) — `matched_dau_uv` 口径核心、NULL 陷阱、漏斗链自洽性。
- [../../references/output-schemas.md](../../references/output-schemas.md) — 输入 `tidy`/`anomaly`/`drilldown` 与产出 `quality_check_core` 契约。

## 工作流

```bash
python ~/.claude/skills/转转核心指标异动监控bot/scripts/qa_check.py \
  --tidy ~/.claude/analysis_reports/tidy_${dt}.csv \
  --anomaly ~/.claude/analysis_reports/anomaly_${dt}.csv \
  --analyze-dt ${dt} --metric dau_pay_rate \
  --out ~/.claude/analysis_reports/quality_check_core_${dt}.json
```
`--metric` 传本次结论实际依赖的主指标（与发现异常步一致）。退出码 0=通过、1=有硬失败。

## 检查项

**硬失败（hard_failures，必停）：**
- 必需列缺失（tag_01/wd/exp_uv/detail_uv/order_uv/pay_pv/matched_dau_uv/dt）。
- 交叉行 `duan` 列解析失败率 > 5%（`wd` 拆分漏枚举值）。
- **北极星与漏斗链不自洽**：整体行 `dau_pay_rate` 与四环节连乘（曝光渗透×商详到达×下单率×支付率）偏差 > 5%，说明口径算错。

**软警告（soft_warnings，记录不阻断）：**
- `matched_dau_uv` 当日 NULL 率 > 2%（DAU 分母完整性闸门异常）。
- 主指标当日缺失率 > 30%。
- 环比基准日缺失、日期 < 3 天（趋势不可靠）。
- 异动清单为空（阈值可能过严）。

## 人工核对（脚本之外）
- 抽查 `drilldown_${dt}.md` 的下钻结论：定位到的维度是否真有对应异动数据支撑；有没有拿 NULL 行/小盘子行硬下结论。
- 比率结论是否都附了绝对量。

## 与其他 agent 的协作上下文
- **上游（发现异常 + 下钻步）**：读 `tidy`/`anomaly`/`drilldown`；`--metric` 必须与发现异常步一致。
- **下游（结论步）**：编排器读本步 `passed`。`passed=true` 才放行，软警告透传进报告标注。

## 失败处理
- `passed=false`：把 `hard_failures` 打到 stdout，停在这里，回退对应步修（口径不自洽回数据洞察步查派生；维度解析问题补 `analyze_dimension.py` 常量后从 Step 2 重跑）。
- `passed=true` 但有软警告：可进结论步，软警告在报告里如实标注。

## 产出
- `analysis_reports/quality_check_core_${dt}.json` — 结构对齐 output-schemas Step 5。

## 不要做的事
- 不要在 `passed=false` 时硬进结论步。
- 不要即兴改写检查逻辑——统一走 `qa_check.py`。

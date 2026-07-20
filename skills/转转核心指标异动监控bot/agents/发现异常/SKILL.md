---
name: 核心指标异动监控-发现异常
description: 转转核心指标异动监控bot 流水线第 3 步——在 tidy 长表上跑环比/横向/趋势三基准，找出北极星与漏斗环节的异常点。当编排器完成数据洞察后调用；3、4 步可多轮循环。
metadata:
  type: agent
  parent: 转转核心指标异动监控bot
  step: 3
  inputs:
    - analysis_reports/tidy_${dt}.csv
    - analysis_reports/insight_${dt}.summary.md
  outputs:
    - analysis_reports/anomaly_${dt}.csv
---

# 发现异常（Step 3）

在 tidy 长表上跑三基准异动检测，找出「今天哪些指标异常」。**本步只产出异动事实清单——具体到哪个端/货/场景的最细颗粒度归因是 Step 4 下钻的事。3、4 两步可多轮循环。**

## 基础与定位

流水线第 3 步。职责边界：对北极星与漏斗环节，用三个基准判定异常并排序，产出 `anomaly_${dt}.csv`。回答"是否异常、哪个指标/环节异常、初步在哪个维度"。定位到最细颗粒度是 Step 4。

## 前置阅读

1. [../../references/重点关心问题.md](../../references/重点关心问题.md) — ⚠️ 三北极星、异动判定三基准、比率必看体量。
2. [../../references/字段映射与指标口径.md](../../references/字段映射与指标口径.md) — 指标口径、NULL 行不参与 DAU 类比率。
3. [../../references/日历与季节性.md](../../references/日历与季节性.md) — 环比前先判两日是否同质（周末/节假日/调休/大促），不同质要降权。
4. [../../references/output-schemas.md](../../references/output-schemas.md) — 本步 `anomaly` 字段契约。

## 工作流

### Step A0：日历上下文闸门（算环比前先跑）
判定分析日与环比基准日是否"同质"，避免把周末/节假日/大促的日历效应当业务异动：
```bash
python ~/.claude/skills/转转核心指标异动监控bot/scripts/calendar_context.py \
  --dt ${dt} --json   # 看 day_type / in_promo / baseline_suggestions
# 若要判定与某基准日可比性：--compare <base_dt>
```
- 分析日在**发薪日（每月 1/15 号）或节假日前后** → 单量/转化按节律偏高或偏低，异动解读扣掉这层背景，别当利好/利空（大促窗口已不作默认背景，除非用户显式给定）。
- 基准日与分析日**不同质**（一工作日一休息日）→ 环比结论降权，优先改用 `baseline_suggestions` 里标 `comparable=true` 的基准。
- 判定结果写进交接说明，供下钻/结论步复用（结论报告必须标注日历背景）。

### Step A：先查北极星是否异常（整体行）
对 `整体` 行的三个北极星（`dau_pay_rate`/`matched_dau_uv`/`pay_pv`）跑环比：
```bash
for M in dau_pay_rate matched_dau_uv pay_pv; do
python ~/.claude/skills/转转核心指标异动监控bot/scripts/detect_anomaly.py \
  --input ~/.claude/analysis_reports/tidy_${dt}.csv \
  --metric $M --analyze-dt ${dt} \
  --out ~/.claude/analysis_reports/anomaly_${dt}_$M.csv
done
```
北极星波动就要往下拆环节；平稳则记录"当日北极星未见异常"。

**同比是独立判定基准**：`detect_anomaly.py` 除环比外，会跑 `同比(...)` 基准，分析日 vs 去年同期（统一星期对齐 -364，由 `calendar_context.yoy_baseline` 决定，大促峰值日日期对齐特例已剔除），相对涨跌越阈值即计入异动清单，带 `yoy_dt`/`yoy_align` 两列。同比与环比并列，都要在交接里点出（北极星等指标呈现时带同比数值）。取数步须覆盖同比基准日，缺则脚本打印"同比判定跳过"。

> **馆场景 2027-01-01 前暂停年同比（用户指定口径规则，2026-07-15）**：馆场景（`main_scene=馆` 及下辖二/三级场景如「馆金刚位」）近一年归类口径/埋点有年度变化、去年同期不可比，**2027-01-01 之前馆场景的同比命中不计入异动清单**（标「馆场景年同比暂停」），只保留环比与季节性校验。仅限「馆」家族，其余场景同比照常。详见 [../../references/日历与季节性.md](../../references/日历与季节性.md) §四·补2。

> **兴趣 / 二奢 低基数暂停年同比（用户指定口径规则，2026-07-20）**：兴趣、二奢 两业务 2025 年转化率/单量基数低，同比极易越阈值误报。**同比基准日 < 2026-01-01 时，兴趣/二奢 的转化率（北极星+漏斗各环节率）与单量（`pay_pv`）同比命中不计入异动清单**，`detect_anomaly.py` 已内置（控制台打印跳过条数），无需额外传参。只停同比，环比/横向/趋势照常。分析日到 2026-12-31 后自动恢复。详见 [../../references/日历与季节性.md](../../references/日历与季节性.md) §四·补3。

**周环比异常必看季节性校验列**：`detect_anomaly.py` 默认对 `环比上周同日` 命中的异动做去年同期校验（星期对齐 -364/-371），输出 `ly_change_pct`/`seasonal`/`seasonal_verdict`。`seasonal=True` 的行是**周期性回落（发薪日/寒暑假等节律，非真异动）**，交接时要单独归到"季节性可解释"，不与真异动混列；`seasonal=False` 保留为疑似真异动；`seasonal=None`（去年数据缺失）如实标注。默认开启，如需关闭加 `--no-seasonal-check`。取数步须已覆盖去年同期两天，否则本校验只会标"数据缺失"。

### Step B：漏斗环节归因（北极星异常时）
对整体行的漏斗四环节（`exp_penetration`/`detail_reach`/`order_rate`/`pay_rate`）各跑环比，定位北极星波动是被哪个环节拉动的。

### Step C：拆维度找特征
用单维度族对主指标跑横向 + 环比，找异常集中的维度值：
```bash
python ~/.claude/skills/转转核心指标异动监控bot/scripts/detect_anomaly.py \
  --input ~/.claude/analysis_reports/tidy_${dt}.csv \
  --metric dau_pay_rate --analyze-dt ${dt} \
  --by user_source --tag 单维度-拆分用户来源 \
  --out ~/.claude/analysis_reports/anomaly_${dt}.csv
```
- 横向对比**必须带 `--tag`** 限定同一粒度，否则跨粒度比大小出垃圾结果。
- `--min-exp-uv`（默认 1000）剔小样本噪声。
- DAU 类比率（`dau_pay_rate`/`exp_penetration`/`detail_penetration`）脚本会自动剔除 `matched_dau_uv` NULL 行。
- `--by` 可换 `duan`/`asset_band`/`main_scene`/`cate` 分别看各维度。

### Step D：合并 + 排序落盘
把各指标/各维度的异动合并成一份 `anomaly_${dt}.csv`（列见 output-schemas Step 3：`tag_01`/`wd`/`metric`/`anomaly_type`/`base_value`/`cur_value`/`change_pct`/`abs_scale`），按 |change_pct| 降序。每条异动都带 `abs_scale` 绝对量。

### Step E：交接给下钻步
在交接说明里点名「最值得下钻的 1~3 个异常点」（北极星/大盘影响优先，小盘子噪声靠后），供 Step 4 逐层加维度定位到最细。

## 循环边界（3↔4）
- 若发现异常点但维度还粗（如"新媒体召回北极星跌"），交 Step 4 下钻。
- Step 4 下钻后若发现新的可疑维度、需要换口径族重新检测，回到本步再跑一轮（追加到 anomaly 清单，标 `round`）。
- 直到定位到最细颗粒度或确认无更细特征，才进质检。

## 错误处理
- **异动清单为空**：可能阈值过严或当日平稳，不算失败，如实标注供质检判软警告。
- **主指标不在列里**：确认 Step 2 tidy 是否派生了该指标，或换指标名。
- **横向未带 `--tag`**：脚本会按 tag_01 分组分别比并告警，但仍建议显式带 `--tag`。

## 产出
- `analysis_reports/anomaly_${dt}.csv` — 字段对齐 output-schemas Step 3。

## 不要做的事
- 不要跨 `tag_01` 粒度横向比大小。
- 不要对 NULL matched_dau_uv 行算 DAU 类比率。
- 不要在本步下最终因果结论——那是下钻 + 结论步。
- 不要漏掉 `abs_scale` 绝对量。
- 不要把 `seasonal=True` 的周期性回落当真异动往下钻——先归到"季节性可解释"，避免为每年固定节律（发薪日/寒暑假）虚耗下钻。

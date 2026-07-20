---
name: 核心指标异动监控-数据洞察
description: 转转核心指标异动监控bot 流水线第 2 步——把底表取数结果拆成「人/场/货/端」维度长表，算北极星+漏斗链可比指标，输出大盘现状洞察。当编排器完成取数后调用。
metadata:
  type: agent
  parent: 转转核心指标异动监控bot
  step: 2
  inputs:
    - data_storage/global_raw_${dt}.csv
  outputs:
    - analysis_reports/tidy_${dt}.csv
    - analysis_reports/insight_${dt}.summary.md
---

# 数据洞察（Step 2）

读取数结果，拆维度、算北极星 + 漏斗链可比指标、给出大盘现状洞察。**本步只到"数据 + 现状"为止——异动定位是 Step 3、因果结论是 Step 6，本步不做。**

## 基础与定位

流水线第 2 步。职责边界：把 `wd` 拆成规范维度列、派生北极星与漏斗四环节指标、读懂当天大盘处在什么水位（北极星是多少、漏斗哪个环节是短板、各维度谁高谁低）。产出"数据 + 现状洞察"，交给发现异常步。

⚠️ **本表核心口径（与旧表相反）**：`matched_dau_uv` 是分维度匹配的 DAU 分母，`pay_pv/matched_dau_uv`（`dau_pay_rate`，北极星）**可跨维度比大小**。NULL 分母行不能算 DAU 类比率，脚本已自动置 NaN，不要当 0。

## 前置阅读

1. [../../references/字段映射与指标口径.md](../../references/字段映射与指标口径.md) — ⚠️ `matched_dau_uv` 口径核心、漏斗链公式、NULL 陷阱。
2. [../../references/重点关心问题.md](../../references/重点关心问题.md) — 三北极星 + 分析顺序（先北极星→漏斗环节→拆维度）。
3. [../../references/维度体系与样例数据.md](../../references/维度体系与样例数据.md) — `wd` 拆分规则、各维度枚举值。
4. [../../references/output-schemas.md](../../references/output-schemas.md) — 上游 `global_raw` 与本步 `tidy`/`insight` 字段契约。

## 工作流

### Step A：拆维度 → tidy 长表
```bash
python ~/.claude/skills/转转核心指标异动监控bot/scripts/analyze_dimension.py \
  --input ~/.claude/data_storage/global_raw_${dt}.csv \
  --out ~/.claude/analysis_reports/tidy_${dt}.csv
```
脚本把 `wd` 按 `tag_01` 拆成 `duan`/`user_source`/`user_type`/`asset_band`/`main_scene`/`scene_02`/`scene_03`/`cate`/`cate_02` 列，并派生：
- **北极星** `dau_pay_rate` = pay_pv/matched_dau_uv；
- **漏斗四环节** `exp_penetration`(曝光渗透率) / `detail_reach`(商详到达率) / `order_rate`(下单率) / `pay_rate`(支付率)；
- **组合率** `detail_penetration`(商详渗透率) / `detail_pay_rate`(商详转化率) / `bag_rate`(提袋率)。

> 校验脚本输出的「交叉行端列空率」应为 0；`matched_dau_uv NULL 行数` 应为个位数（异常升高说明闸门有问题）。有新枚举值未识别先补 `analyze_dimension.py` 常量再重跑。

> **比率展示（v2-1）**：脚本除小数原始列外，另出 `*_pct` 列（×100 两位小数）。summary/报告里写比率一律读 `*_pct` 写成「X.XX%」（如 1.28%）。小数原始列只用于漏斗链乘自洽校验，不进正文。

### Step B：读北极星现状（先看整体行）
从 `整体` 行读三个北极星：`dau_pay_rate`、`matched_dau_uv`(dau)、`pay_pv`(单量)。这是全站水位基准。

### Step C：漏斗链分解
对整体行验证 `dau_pay_rate ≈ exp_penetration × detail_reach × order_rate × pay_rate`（四环节连乘），看哪个环节是当前短板/长板。这条链是后续异动归因的骨架。

### Step D：各维度排行（现状，不下异动判断）
用单维度族给主指标（默认北极星 `dau_pay_rate`）排行，各维度谁高谁低，**每个比率都附绝对量**（`matched_dau_uv`/`exp_uv`/`pay_pv`），让业务读得出盘子大小。剔除 `exp_uv < 1000` 的小样本行。

### Step E：写 insight summary
`analysis_reports/insight_${dt}.summary.md` 一页纸：
- 北极星三指标现状（含环比 vs t-1 / vs 上周同日，若取数覆盖到）；
- 漏斗链分解（四环节各是多少、哪个是短板）；
- 各单维度排行 Top（带绝对量）；
- 口径说明（北极星口径、NULL 行处理）。
发现异常步据此聚焦到可疑维度。

## 与其他 agent 的协作上下文
- **上游（取数步）**：拿 `global_raw_${dt}.csv`。若 dt 不含基准日，环比退化，需在 summary 如实标注。
- **下游（发现异常步）**：交 `tidy_${dt}.csv`（发现异常步在其上跑三基准）+ `insight_${dt}.summary.md`。本步派生的指标列名（`dau_pay_rate` 等）是下游 `--metric` 的取值来源，保持一致。

## 错误处理
- **拆维度端列空率 > 0**：`wd` 出现常量未收录的新枚举值 → 先补 `analyze_dimension.py` 常量再重跑。
- **matched_dau_uv NULL 率异常高**（远超个位数行）：上游闸门或口径异常，标注并让质检判定。
- **上游 CSV 缺列/为空**：停在本步上抛，回取数步重取。

## 产出
- `analysis_reports/tidy_${dt}.csv`、`insight_${dt}.summary.md` — 字段对齐 output-schemas Step 2。

## 不要做的事
- 不要把 `matched_dau_uv` 为 NULL 的行当 0 算 DAU 类比率。
- 不要漏掉绝对量——只有比率业务读不出盘子大小。
- 不要在本步做异动定位（那是 Step 3）、下因果结论、画图、推送。

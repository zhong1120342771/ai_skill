# 产物契约（output-schemas）

流水线 6 步的跨步数据契约。每一步落盘的产物字段/结构以本文件为准；上游改字段先改这里，下游按这里读。所有产物落 `~/.claude/` 下，`${dt}` = 分析日（默认 t-1）。

口径定义（原子字段、`matched_dau_uv` 分维度匹配 DAU、NULL 闸门陷阱、北极星与漏斗链）见 [字段映射与指标口径.md](字段映射与指标口径.md)；维度枚举见 [维度体系与样例数据.md](维度体系与样例数据.md)；分析主线（三北极星、异动判定基准）见 [重点关心问题.md](重点关心问题.md)。本文件只定结构，不重复口径。

> 3、4 两步（发现异常 → 下钻）可多轮循环：下钻产物追加到同名文件（按 `round` 递增），直到定位到最细颗粒度。

---

## Step 1 取数 → `data_storage/global_raw_${dt}.csv`

从核心底表按日期区间 + 口径族拉取的原始行，utf-8-sig。列 = 底表原始字段：

| 列 | 类型 | 说明 |
|---|---|---|
| `tag_01` | string | 口径族（`整体`/`单维度-拆分用户来源`/`2维度交叉-端_业务/品类`/…） |
| `wd` | string | 维度值（族内的具体取值，如 `新媒体召回`、`转转APP_品类消费电子手机`） |
| `exp_pv` `exp_uv` | int | 曝光 PV/UV |
| `detail_pv` `detail_uv` | int | 商详 PV/UV |
| `order_pv` `order_uv` | int | 订单 PV/UV |
| `pay_pv` | int | 净支付 PV（=业务口径「单量」） |
| `matched_dau_uv` | int | 该维度**匹配到的 DAU 分母**（可 NULL，见口径陷阱） |
| `matched_duan` `matched_source` `matched_type` | string | DAU 分母匹配到的端/来源/资产归属（`ALL`=未细分，NULL=降级失败置空） |
| `dt` | string | 分区日 `yyyy-MM-dd`，覆盖分析日 + 环比基准 + 近 N 天 |

约束：
- 一次取够（分析日 + t-1 + 上周同日 + 近 N 天，若覆盖到去年同期更好），落本地再切，不反复查库。
- dt 覆盖必须含下游异动定位所需的基准日，否则 Step 2/3 做不了环比/趋势。

## Step 2 数据洞察 → 3 个产物

### `analysis_reports/tidy_${dt}.csv`（拆维度长表）
`analyze_dimension.py` 把 `wd` 按维度字典拆成规范列 + 派生可比指标：

| 列 | 说明 |
|---|---|
| `tag_01` `wd` `dt` | 透传 |
| `duan` `user_source` `user_type` `main_scene` `scene_02` `scene_03` `cate` `cate_02` | 从 `wd` 拆出的维度列（该族不含的维度为空） |
| `exp_pv`…`matched_dau_uv` | 透传底表原子指标 |
| `dau_pay_rate` | 北极星：`pay_pv/matched_dau_uv`（NULL 分母行为空，不填 0） |
| `exp_penetration` `detail_reach` `order_rate` `pay_rate` | 漏斗四环节：曝光渗透率/商详到达率/下单率/支付率 |
| `detail_penetration` `detail_pay_rate` `bag_rate` | 商详渗透率/商详转化率/提袋率 |
| 其余派生 | 见 `analyze_dimension.py` 常量 |

### `analysis_reports/insight_${dt}.summary.md`（洞察摘要）
北极星现状（整体行三指标 + 环比）+ 漏斗链分解 + 各维度排行，人读，交给发现异常步。

## Step 3 发现异常 → `analysis_reports/anomaly_${dt}.csv`

`detect_anomaly.py` 三基准（环比 vs t-1 / 环比 vs 上周同日 / 横向 MAD）+ 趋势拐点产出：

| 列 | 说明 |
|---|---|
| `tag_01` `wd` | 定位 |
| `metric` | 异动指标名（北极星/漏斗环节优先） |
| `anomaly_type` | `环比t-1`/`环比上周同日`/`同比(对齐方式)`/`横向`/`趋势` |
| `base_value` `cur_value` `change_pct` | 基准值/当前值/涨跌幅 |
| `abs_scale` | 体量（该行 `exp_uv`/`matched_dau_uv`/`pay_pv`），比率异动必带 |
| `yoy_dt` `yoy_align` | 同比基准日 / 对齐方式（统一 `星期对齐(-364天)`，大促峰值日日期对齐特例已剔除），仅 `同比` 行有值 |
| `flag` | 是否越阈值（默认环比/同比 15%、横向 ±3 MAD） |
| `ly_base_value` `ly_cur_value` | 去年同期（星期对齐）上周同日位 / 分析日位的指标值（仅 `环比上周同日` 行有值） |
| `ly_change_pct` | 去年同期周环比（=（ly_cur−ly_base）/ly_base），供与今年周环比同向/量级对比 |
| `seasonal` | 周环比异动的季节性判定：`True`=周期性回落(去年同向且量级相近,非真异动)/`False`=疑似真异动/空=去年数据缺失或非周环比行 |
| `seasonal_verdict` | 判定说明文本（今年 vs 去年周环比幅度、同向性、比值、结论）|

约束：横向对比**必须限定同一 `tag_01` 粒度内**；默认剔除 `exp_uv < 1000` 的小分母行；`matched_dau_uv` 为 NULL 的行不参与 DAU 类比率异动。**季节性校验只对 `环比上周同日` 命中的行做**（去年同期星期对齐 -364/-371 天）：`seasonal=True` 的行是周期性回落，应从真异动清单剔除、单独归"季节性可解释"，避免为发薪日/寒暑假等固定节律虚耗下钻；量级判定区间默认 `[0.5, 2.0]`（`--ly-ratio-low/high` 可调）；去年同期两天缺失则 `seasonal` 为空并标注，取数步须覆盖 -364/-371 两天。

## Step 4 下钻 → `analysis_reports/drilldown_${dt}.md`（可多轮）

发现异常步锁定的异常点，换含该维度的更高阶交叉族 + `wd LIKE` 逐层加维度，定位到最细颗粒度。每轮产出追加：

| 段 | 内容 |
|---|---|
| 异常点 | 来自 Step 3 的哪条（tag_01/wd/metric/change_pct） |
| 下钻路径 | 用了哪个交叉族、筛了哪个 `wd`、拆到哪个维度 |
| 结论 | 异常集中在哪个端/货/场景/来源/资产层，是哪个漏斗环节拉动 |
| 是否收敛 | 是否已到最细颗粒度（否则继续下一轮） |

### 可选中间产物 `analysis_reports/biz_diagnose_${dt}.csv`（分业务下钻捷径）
异常落在货维度时，`business_diagnose.py` 一次产出三大业务（消电/二奢/兴趣）+ 品类级诊断行：

| 列 | 说明 |
|---|---|
| `level` `biz` `name` | 粒度（业务/品类/场景）、所属业务、维度名 |
| `biz_anomaly` | 分业务今日异常判定（`level=业务` 行有效）：`True`=异常/`False`=正常/空=数据不足 |
| `biz_anomaly_verdict` | 判定标签，写核心结论用（如 `异常↓（单量 -15.1% 越 ±15%）`、`正常（北极星 +0.0%｜单量 -1.4%）`） |
| `biz_anomaly_reason` | 判定依据（北极星/单量的环比 + 同比 + 触发项 + 拖累环节） |
| `mom_basis` | 环比基准（`上周同日` 优先，缺则 `t-1`） |
| `pay_pv` `matched_dau_uv` `dau_pay_rate` | 单量/匹配DAU/北极星（绝对量） |
| `pay_pv_mom` `star_mom` | 单量/北极星环比（按 `mom_basis`） |
| `pay_pv_yoy` `star_yoy` | 单量/北极星同比（vs 去年同期，统一星期对齐 -364） |
| `pay_pv_delta` | 对大盘的 Δ单量贡献（正负） |
| `worst_stage` | 拖累最重的漏斗环节（曝光渗透/商详到达/下单率/支付率 + 跌幅） |

> 分业务异常判定口径：北极星 `dau_pay_rate` 或 单量 `pay_pv` 的**环比或同比**任一越 **±15%**（`--star-threshold` 可调）即 `biz_anomaly=True`，方向北极星优先。三业务效率统一看北极星 `dau_pay_rate`（与大盘/来源同口径可比）。消电/二奢/兴趣三业务的判定是**核心结论必答项**，结论生成步逐个点名进"结论先行"。

控制台按优先级先打「分业务异常判定」（每业务正常/异常+理由）+ 异常业务清单，再给「普降 vs 特征业务」判定 + 特征品类排行。结论生成可直接引用。

### 可选中间产物 `analysis_reports/scene_diagnose_${dt}.csv`（分场景流量/转化效率判定，改点3）
`scene_diagnose.py` 判各场景对大盘/各业务的流量分发与转化效率是否降低，业务×场景走弱的细拆到品类：

| 列 | 说明 |
|---|---|
| `level` | 粒度：`大盘场景`（各场景对大盘）/`业务场景`（消电/二奢/兴趣×场景）/`品类场景`（走弱业务×场景细拆到品类） |
| `biz` `scene` `cate_02` | 业务 / 场景（main_scene）/ 品类（仅品类场景行有值） |
| `scene_verdict` | 判定标签：`流量分发↓`/`转化效率↓`/`流量分发↓、转化效率↓`/`正常`（含基准说明） |
| `scene_reason` | 判定依据（曝光UV/曝光渗透率/提袋率环比明细） |
| `mom_basis` | 环比基准（`上周同日` 优先，缺则 `t-1`） |
| `exp_uv` `exp_uv_mom` | 曝光UV 当日值 / 环比（流量分发） |
| `exp_penetration` `exp_penetration_mom` | 曝光渗透率 当日值 / 环比（流量分发） |
| `bag_rate` `bag_rate_mom` | 提袋率 当日值 / 环比（转化效率＝商详到达率×商详转化率） |
| `pay_pv` `matched_dau_uv` | 单量 / 匹配DAU（绝对量，曝光渗透率分母组内有空则该行 exp_penetration 置空，绝不当0） |

> 判据：流量分发（曝光UV 或 曝光渗透率）或 转化效率（提袋率）环比（上周同日优先）任一 ≤ **-15%**（`--threshold` 可调）记为降低。**业务×场景与品类下钻依赖 tidy 含 `3维度交叉-端_业务/品类_场景` 族**（脚本按端聚合回业务×场景 / 品类×场景）；缺该族只出大盘×场景并告警。控制台先打大盘×场景，再打走弱的业务×场景，最后打品类下钻。

## Step 5 质检 → `analysis_reports/quality_check_core_${dt}.json`

`qa_check.py` 产出的闸口 JSON：

```json
{ "passed": true, "hard_failures": [], "soft_warnings": [], "info": {} }
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `passed` | bool | `hard_failures` 为空即 true；**false 则编排器必停，不进结论生成** |
| `hard_failures` | string[] | 硬失败（缺列/解析失败/把 NULL matched_dau_uv 当 0 算 DAU 率/北极星与漏斗链不自洽等） |
| `soft_warnings` | string[] | 软警告（小分母比率、维度值稀疏、matched_dau_uv NULL 率偏高等） |
| `info` | object | 行数/dt 覆盖/口径族分布/NULL 率等自检信息 |

## Step 6 结论生成 → 报告 + 图 + 飞书

- `final_report/核心指标异动_${dt}.md` — 进飞书文档(docx)的正式报告（是否异常→哪个环节→特征维度，结论先行、比率必附绝对量、口径透明标注），骨架见 [../assets/report-template.md](../assets/report-template.md)。**docx 结构维持原状不变**。
- `final_report/核心指标异动_${dt}.msg.md`（v8-0711）— P2P 飞书消息(post)正文（四段式结论 + 表1/表2/表3 markdown 表格文本 + 3 张趋势图 `<!--IMG-->` 标记），骨架见 [../assets/message-template.md](../assets/message-template.md)。
- `visualizations/${dt}/*.png` — 两类图：
  - `render_charts.py` 产漏斗分解/维度排行（`funnel_main_scene.png`/`funnel_stage_mom.png`/`metric_rank_by_main_scene.png`）。
  - `render_trend_charts.py` 产 3 张核心指标趋势图（`fmt_01_monthly.png` 月均 / `fmt_02_daily30.png` 近30日 / `fmt_03_weekly8.png` 近8周），各按整体/消费电子/二奢/兴趣拆 2x2 四宫格 + 去年同期对比线。均显式中文字体。
- 飞书产物（`feishu_publish.py` 产出，供失败重推复用）：P2P 走 `--post` 单条 post 图文交插（表格转文字、趋势图内嵌），产物 json 里 `im_push[].kind=post`；旧的逐张发表图（`im_push_image`）已被 post 内嵌取代。

```json
{
  "doc_url": "https://…",
  "doc_token": "…",
  "im_push": [{"receiver": "ou_…", "status": "ok"}],
  "im_image_push": [{"receiver": "ou_…", "status": "ok"}]
}
```

约束：文档已建但 IM 失败 → 复用 `doc_url` 只重推（`feishu_publish.py --skip-doc`），不回退到只发本地路径。对外成段文字交付前过 humanizer 去 AI 味（只改措辞，不动数字/口径/结论）。

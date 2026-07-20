---
name: 核心指标异动监控-下钻
description: 转转核心指标异动监控bot 流水线第 4 步——对发现异常步锁定的异常点，换更高阶交叉口径族逐层加维度，定位到最细颗粒度。当编排器完成发现异常后调用；3、4 步可多轮循环。
metadata:
  type: agent
  parent: 转转核心指标异动监控bot
  step: 4
  inputs:
    - analysis_reports/anomaly_${dt}.csv
    - analysis_reports/tidy_${dt}.csv
    - data_storage/global_raw_${dt}.csv
  outputs:
    - analysis_reports/drilldown_${dt}.md
---

# 下钻（Step 4）

对发现异常步锁定的异常点，基于已有底表逐层加维度，定位到**最细颗粒度**的问题点：异常到底集中在哪个端 × 货 × 场景 × 来源 × 资产层，是哪个漏斗环节拉动的。**3、4 两步可多轮循环，直到收敛。**

## 基础与定位

流水线第 4 步、异动归因的核心。职责边界：拿 Step 3 的异常点（如"新媒体召回北极星环比跌 25%"），沿维度层级往下钻——单维度→含该维度的交叉族→更高阶交叉族，每层用 `wd LIKE` 锁定异常值，直到定位到最细颗粒度或确认无更细特征。

## 前置阅读

1. [../../references/维度体系与样例数据.md](../../references/维度体系与样例数据.md) — ⚠️ 21 个口径族的下钻路径、`wd` 结构（决定往哪个交叉族下钻）。
2. [../../references/重点关心问题.md](../../references/重点关心问题.md) — 分析顺序、比率必看体量。
3. [../../references/字段映射与指标口径.md](../../references/字段映射与指标口径.md) — 漏斗链分解、NULL 陷阱。
4. [../../references/日历与季节性.md](../../references/日历与季节性.md) — 解释突变前先排除日历/大促原因（`calendar_context.py`）。
5. [../../references/output-schemas.md](../../references/output-schemas.md) — 本步 `drilldown` 结构。

## 下钻方法（逐层加维度）

**核心思路**：底表已把各种交叉预聚合好，下钻 = 换一个含目标维度的更高阶 `tag_01` 族 + `wd LIKE '%异常值%'` 筛选，不用自己做笛卡尔积。

下钻路径示例（异常点 = "新媒体召回北极星跌"）：
1. **确认环节**：在 `单维度-拆分用户来源` 看召回的漏斗四环节，定位跌在曝光渗透/商详到达/下单/支付哪一环。
2. **加端维度**：换 `2维度交叉-端_用户来源` 或 `3维度交叉-端_业务/品类_用户来源`，`wd LIKE '%新媒体召回%'`，看是哪个端把召回拉低。
3. **加货维度**：在 `3维度交叉-端_业务/品类_用户来源` 里进一步看是哪个业务/品类。
4. **加场景/资产**：若还需更细，换 `4维度交叉-端_业务/品类_用户来源_场景` 定位到最细组合。
5. **验证时间形态**：用环比/趋势确认是"一直如此"还是"当天/上周突变"。

> 若目标交叉族**不在底表 21 个 `tag_01` 里**（如"来源×资产分层"无对应族），回退取数步按需重新聚合，或换一个最接近的已有族并标注。

### 分业务下钻捷径（消电/二奢/兴趣）
异常点落在货维度时，直接用固化脚本 `business_diagnose.py` 一次拿三大业务的漏斗诊断，省得手写：
```bash
python ~/.claude/skills/转转核心指标异动监控bot/scripts/business_diagnose.py \
  --input ~/.claude/analysis_reports/tidy_${dt}.csv --analyze-dt ${dt} \
  --out ~/.claude/analysis_reports/biz_diagnose_${dt}.csv
# 品类→场景再下钻（tidy 需含含该品类的场景交叉族，否则脚本会提示回取数步补拉）：
#   --drill-scene 消费电子手机
```
脚本自动：① 业务级判「普降 vs 特征业务」（三业务是否同向走弱）；② 每业务内按 Δ单量贡献排出**特征品类**；③ 每行标注拖累最重的漏斗环节。环比基准上周同日优先、缺则回退 t-1。输出直接喂给下钻结论。

## 取数补充（下钻常需拉交叉族）
Step 1 若只拉了单维度族，下钻要更细维度时补取对应交叉族：
```python
import sys; sys.path.insert(0, "/Users/zhongmengting/.claude/skills/xinghe-data/scripts")
from xinghe_client import XingheExplorer
client = XingheExplorer()
# 用 query_global_table.sql 模板 B，tag_01 换成交叉族，wd LIKE 锁定异常值
eid = client.run_sql(sql, sql_engine=5); r = client.wait_and_get_result(eid, max_wait=180)
```
补取的数据落 `data_storage/`，用 `analyze_dimension.py` 拆维度后再看。

## 工作流
1. 读 `anomaly_${dt}.csv`，取交接点名的 1~3 个异常点。
2. 对每个异常点，按上面的下钻路径逐层加维度，每层记录：用了哪个族、筛了哪个 `wd`、拆到哪个维度、该层结论。
3. 每层判断是否**收敛**（已到最细颗粒度 / 盘子太小无意义 / 无更细特征）。未收敛且需换族重检，回 Step 3 再跑一轮。
4. 写 `drilldown_${dt}.md`（结构见 output-schemas Step 4）：异常点 → 下钻路径 → 定位结论（集中在哪个端/货/场景/来源/资产，哪个漏斗环节）→ 是否收敛。

## 与其他 agent 的协作上下文
- **上游（发现异常步）**：拿异常点清单。
- **循环（回 Step 3）**：下钻发现需换口径族重检时，回发现异常步追加一轮。
- **下游（质检步）**：交 `drilldown_${dt}.md`，质检核对下钻结论与数据是否自洽、口径有无误用。

## 错误处理
- **目标交叉族不存在**：回退取数重聚合，或换最接近的已有族并标注。
- **下钻到小盘子**（`exp_uv`/`matched_dau_uv` 很小）：比率抖动无意义，标注"盘子过小，非有效特征"，不强行下结论。
- **NULL matched_dau_uv**：该组合 DAU 分母不可用，改看漏斗内部比率（商详到达/下单/支付率，分母非 DAU）。

## 产出
- `analysis_reports/drilldown_${dt}.md` — 结构对齐 output-schemas Step 4，可多轮追加。

## 不要做的事
- 不要自己做笛卡尔积——用底表已有的交叉族。
- 不要在小盘子上硬下结论。
- 不要跨 `tag_01` 粒度混比。
- 不要在本步推送/画正式图——那是结论生成步。

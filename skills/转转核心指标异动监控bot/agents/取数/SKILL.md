---
name: 核心指标异动监控-取数
description: 转转核心指标异动监控bot 流水线第 1 步——从核心底表取数。当编排器需要按指定日期区间/口径族拉取分维度漏斗+DAU 数据时使用。
metadata:
  type: agent
  parent: 转转核心指标异动监控bot
  step: 1
  outputs:
    - data_storage/global_raw_${dt}.csv
---

# 取数（Step 1）

从核心底表 `hdp_zhuanzhuan_tmp_global.tmp_dws_zz_core_dataagent_zmt_v2_di`（分区 `dt`，已预聚合）拉取分维度漏斗 + DAU 分母数据，落 `data_storage/global_raw_${dt}.csv`，交给数据洞察步。

## 基础与定位

流水线第 1 步、唯一取数入口。职责边界：只负责「把对的日期区间 × 对的口径族从底表拉下来、落盘、自检」，不算转化率、不下结论、不画图。取数范围由用户问题决定，编排器透传 `dt`/`--by`/`--tag`。**一次取够、落本地再切**是核心纪律——漏了基准日下游就做不了异动定位。

异动监控的默认取数范围要一次覆盖：**分析日 + t-1 + 上周同日 + 近 7~14 天趋势 + 去年同期双口径（同比周 + 同比日 + 同比周上周同日）**。哪怕用户只问单日，也默认拉够基准日，供 Step 3 发现异常。口径族默认拉 `整体` + 全部单维度族 + `3维度交叉-端_业务/品类_场景`（最后一个是分场景判定的输入，见下表）。

**去年同期既是「同比独立判定基准」也是「周环比季节性校验」的必取基准（不是"更好"，是"必须"）**：Step 3 把同比（分析日 vs 去年同期）作为与环比并列的独立判定基准，同时对周环比异常交叉校验去年同期同一组周环比是否同向。**v9-0714 起同比呈现双口径，取数必须同时覆盖两个去年分区**（真源 `calendar_context.yoy_baseline`）：
- **同比周**＝**分析日 -364 天**（星期对齐，保持星期几一致），即 `yoy_baseline.aligned_dt`；再取其上周同日 `yoy_baseline.prev_week_dt`（-371）做去年侧周环比季节性校验。例：分析日 `2026-07-13`(周一) → 同比周 `2025-07-14`(周一) + 上周同日 `2025-07-07`(周一)。
- **同比日**＝**去年同一日历日**（分析日 -1 年、同月同日）。例：分析日 `2026-07-13` → 同比日 `2025-07-13`。
- 当分析日 -364 天恰好落在去年同一日历日时（少数情况），同比周=同比日，取一天即可、两列写同一数。大促峰值日的日期对齐特例已剔除，主判定口径统一用同比周（星期对齐）。

**取数前先跑 `calendar_context.py --dt ${dt} --json` 读 `yoy_baseline.aligned_dt`（同比周）与 `yoy_baseline.prev_week_dt`（去年上周同日）；同比日另行按分析日 -1 年同月同日算**（如 2026-07-13→2025-07-13）。**非大促日这三个去年分区通常是三个不同日期（同比周/同比日相差 1 天，加去年上周同日），三个都要取**。缺哪个，Step 3/6 对应口径标"去年同期数据缺失"。

## 前置阅读

1. [../../references/字段映射与指标口径.md](../../references/字段映射与指标口径.md) — 原子字段、`matched_dau_uv` 分维度匹配 DAU（北极星分母）与 NULL 闸门陷阱。
2. [../../references/维度体系与样例数据.md](../../references/维度体系与样例数据.md) — 21 个 `tag_01` 口径族、各族 `wd` 结构。
3. [../../references/output-schemas.md](../../references/output-schemas.md) — 本步产物字段契约（下游按此读）。
4. [../../scripts/query_global_table.sql](../../scripts/query_global_table.sql) — 取数模板。

## 工作流

### Step A：确定取数范围
| 问题类型 | 日期区间 | 口径族 `tag_01` |
|---|---|---|
| 日常异动监控（默认） | 分析日 + t-1 + 上周同日 + 近 7~14 天 + 去年同期双口径三天（同比周 `aligned_dt` + 同比日 -1年同日 + 去年上周同日 `prev_week_dt`；大促峰值日两口径重合取一天） | `整体` + 各单维度族 |
| 锁定某维度下钻 | 同上连续区间 + 同样补去年同期双口径 | 对应交叉族 |

> 去年同期是**同比独立判定基准 + 周环比季节性校验**的输入。v9-0714 同比双口径：**同比周**=去年星期对齐日（`aligned_dt`，-364）、**同比日**=去年同一日历日（-1年同月同日），再加去年上周同日（`prev_week_dt`，-371）做季节性校验；非大促日这三个通常是不同日期，都要取。大促峰值日两口径重合、只取去年同一日历日。

维度 → 口径族对照：

| 要看的维度 | `tag_01` |
|---|---|
| 大盘基准（北极星从这里读） | `整体` |
| 端 / 用户来源 / 资产分层 / 场景 / 品类 | `单维度-拆分端`/`拆分用户来源`/`拆分用户资产分层`/`拆分场景`/`拆分品类` |
| scene 二级/三级 | `单维度-拆分scene_02`/`拆分scene_03` |
| **业务/品类 × 场景（分场景判定必取，改点3）** | `3维度交叉-端_业务/品类_场景`（按端聚合回 业务×场景 / 品类×场景） |
| 端×货 / 端×货×来源 / 端×货×资产 | `2维度交叉-端_业务/品类` / `3维度交叉-端_业务/品类_用户来源` / `..._资产分层` |
| 端×货×来源×场景（最细） | `4维度交叉-端_业务/品类_用户来源_场景` |

> 表里没有的交叉（如"来源×资产分层"）底表不存在，换已有族或回退原始明细。**日常监控建议一次拉 `整体` + 全部单维度族 + `3维度交叉-端_业务/品类_场景`**（后者是 Step 6 分场景判定「各场景对大盘/各业务的流量分发与转化效率是否降低、并细拆到品类」的输入，缺它业务×场景与品类×场景判定做不了）。Step 3 定位到异常维度后 Step 4 再按需拉别的交叉族下钻。

### Step B：填模板执行（星河为主，One-Service 兜底）
把 `query_global_table.sql` 模板 A 的 `START_DT`/`END_DT`/`TAG_01` 替换为实际值。底表是 Hive 表，**主通道走星河**，Hive 引擎：

```python
import sys
sys.path.insert(0, "/Users/zhongmengting/.claude/skills/xinghe-data/scripts")
from xinghe_client import XingheExplorer
client = XingheExplorer()
sql = open("<填好的sql>").read()
execute_id = client.run_sql(sql, sql_engine=5)       # ⚠️ 参数名是 sql_engine 不是 engine；5=Hive
result = client.wait_and_get_result(execute_id, max_wait=180)
import urllib.request
urllib.request.urlretrieve(result["filename_excel"], "/Users/zhongmengting/.claude/data_storage/global_raw_${dt}.xlsx")
```
星河凭证走环境变量 `XINGHE_CLIENT_USER`/`XINGHE_CLIENT_SECRET`/`XINGHE_OA`；触发前先 `echo "USER=${XINGHE_CLIENT_USER:-MISSING}"` 自检。

⚠️ **Hive strict mode**：ORDER BY 必须带 LIMIT；必须有分区（`dt`）过滤；不能直接 ORDER BY 聚合函数（套子查询）。

**兜底通道**（星河不可用/权限不足）走 One-Service：
```bash
python ~/.claude/scripts/oneservice_cli.py --file <填好的sql> --output ~/.claude/data_storage/global_raw_${dt}.xlsx
```

### Step C：落盘 + 自检
- 统一存成 `data_storage/global_raw_${dt}.csv`（utf-8-sig，从下载的 xlsx 转）。
- 打印 shape、dt 覆盖、`tag_01` 分布、`matched_dau_uv` NULL 行数；确认日期区间与口径族符合预期，字段对齐 output-schemas Step 1 契约。
- 凭证只走环境变量，不写进 SQL/脚本/日志。

## 单点问答取数（快捷分支模式）

当编排器标注「**单点问答取数**」（路径 A 快捷问答，缓存未命中时）调用本 agent 时，取数纪律放宽为「够答一个数就行」：

- **只拉用户问的那一天**（或明确指定的日期），不用默认铺开「分析日 + t-1 + 上周同日 + 近 N 天」全基准。用户若要环比，才多拉对比那一天。
- **只拉相关口径族**：按问题维度选最小 `tag_01`（如问「新用户量级」→ `单维度-拆分用户资产分层` 取 z0，或 `单维度-拆分用户来源` 取两个新增；问「app 新用户」→ 交叉族 `2维度交叉-端_用户来源`）。
- 落盘仍到 `data_storage/global_raw_${dt}.csv`，但**不进 Step 2**——编排器自己 pandas 读数直接回答。
- 超出底表口径的指标（GMV/客单价/退款等本表无字段）不硬取，回上层「答不了」。

判据：编排器 prompt 里带「单点问答 / 快捷问答 / 只取值」等字样 → 走本模式；否则走下面的完整异动监控取数（拉全基准）。

## 与其他 agent 的协作上下文
- **上游**：编排器传 `dt`（默认 t-1）、分析维度 `--by`、口径族 `--tag`、主指标 `--metric`（默认北极星 `dau_pay_rate`）。
- **下游（数据洞察步）**：拿 CSV 做拆维度 + 漏斗链计算。本步 dt 覆盖**必须**含分析日 + 环比基准 + 近 N 天趋势（**单点问答模式除外**，见上节）。

## 错误处理
- **星河凭证 MISSING**：停下按 xinghe-data skill 引导配置，配好再取。
- **星河权限不足/查询失败**：读 `error_msg`，切 One-Service 兜底重试。
- **口径族在底表不存在**：不硬造，换已有族或回退原始明细，交接时标注。
- 两个通道都失败 → 停在本步上抛，不产出空/半截 CSV。

## 产出
- `data_storage/global_raw_${dt}.csv`（utf-8-sig）— 字段严格对齐 output-schemas Step 1。

## 不要做的事
- 不要每个维度单独查一次库——一次按区间拉全口径族，本地切。
- 不要在取数阶段算转化率结论。
- 不要漏掉环比/趋势基准日，也**不要漏去年同期双口径三天**（同比周 `aligned_dt` + 同比日 -1年同日 + 去年上周同日 `prev_week_dt`）——同比双口径独立判定 + 周环比季节性校验都要用。非大促日这三天通常互不相同，别只取一个星期对齐日就完事；大促峰值日两口径重合才取一天。
- 不要把 `matched_dau_uv` 为 NULL 的行过滤掉——原样保留，让下游按口径处理。

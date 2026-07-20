---
name: 一体化日报-代码生成
description: 一体化项目日报流水线第 1 步——SQL 取数脚本生成与执行。当用户说"取一体化数据""按 References 跑取数 SQL""出 yiti_xianshang/xiansuo/tongshou/xiaoshida/tongshou_yiti_city 5 个 CSV"，或编排器需要落 5 个 CSV 时使用本 skill。
metadata:
  type: sub-skill
  parent: 一体化项目日报数据bot
  step: 1
  inputs: ["dt (YYYY-MM-DD)"]
  outputs:
    - data_storage/yiti_xianshang_${dt}.csv
    - data_storage/yiti_xiansuo_${dt}.csv
    - data_storage/yiti_tongshou_${dt}.csv
    - data_storage/yiti_xiaoshida_${dt}.csv
    - data_storage/yiti_tongshou_yiti_city_${dt}.csv
---

# 一体化日报-代码生成

## 定位

本 skill 在 [`code-generator`](~/.claude/agents/code-generator.md) 通用代码生成 agent 之上做窄化适配——重点是 Hive SQL，跑 5 段一体化项目取数 SQL，落 5 个 CSV 给后续步骤消费。其中第 5 段（`05_tongshou_dongxiao_by_yiti_city.sql`）与第 3 段同源表（`dws_yth_ts_kc_ord_zmt_di`），只是把小店同售按城市拆三档（对照城市 / 一体化覆盖城市(小店) / 其他城市），口径同样是 `kc_ts/pay_pv`，保证拆解三档之和与主口径小店同售对得上账。

## 前置阅读（每次必读）

1. **[../../References/取数与产出说明.md](../../References/取数与产出说明.md)** — 业务真源（与飞书文档同步）；7 项北极星指标、表名、口径都在这里。
2. **[../../Scripts/](../../Scripts/)** 下的 5 个 SQL 模板：
   - `00_check_data_ready.sql` — 5 表 t-1 就绪检查
   - `01_xianshang_orders.sql` — 线上订单 by 城市
   - `02_yiti_xiansuo.sql` — 一体化线索量
   - `03_tongshou_dongxiao.sql` — 同售动销
   - `04_xiaoshida.sql` — 小时达订单

## 执行方式

直接调父 skill 下的固化脚本，**不要即兴 Python**：

```bash
# Step 1.0：先确认 5 表 t-1 数据已就绪
python ~/.claude/skills/一体化项目日报数据bot/scripts/check_data_ready.py --dt ${dt}

# Step 1.1：并行跑 5 段取数 SQL，落 5 个 CSV
python ~/.claude/skills/一体化项目日报数据bot/scripts/fetch_metrics.py --dt ${dt}
```

退出码：`0=就绪/取数成功`、`1=数据未就绪（编排器应只发提醒不空跑）`、`2=取数失败`、`3=输入参数缺失`、`4=内部异常`。

### 并行口径

`fetch_metrics.py` 内部把 **5 段取数 SQL 改成 ThreadPool 并行**（默认 `--workers=4`），不是串行：

- **为什么**：5 段 SQL 互相无依赖；过去常见 02_yiti_xiansuo 单段排队超过 5 分钟，串行下后面几段被白白阻塞，整体耗时 ≈ Σ(各段)；并行后整体耗时 ≈ max(各段)。
- **超时**：每段独立 `--max-wait=900s`（默认），避开星河 09:30 排队峰值。
- **重试**：每段失败自动重试一次（`--retries=1`），覆盖 60s 网关瞬断与偶发排队超时；两次都失败才进 failures。
- **隔离**：每个 worker 用独立 `XingheExplorer` 实例，避免共享 session 在并发轮询时互相影响。
- **失败语义保持不变**：任一段两次都失败 → 整体 RC=2，编排器停在原地等人工。

调参示例（一般不用动）：
```bash
# 单段给到 20 分钟、不重试（调试用）
python fetch_metrics.py --dt ${dt} --max-wait 1200 --retries 0
# 退回串行（仅在怀疑并发把星河打挂时用）
python fetch_metrics.py --dt ${dt} --workers 1
```

**`check_data_ready.py` 不并行**：先 union 5 表（180s 上限，能命中就秒级返回），超时再降级为逐表（900s/张），逻辑已经够稳，没必要并发再加复杂度。

## SQL 能力要求

- **分区取数**：所有 4 张取数表都按 `dt >= '2026-01-01'` 拉历史，**不要漏写 `dt`**，全表扫描会被平台拒绝。
- **同售门店类型**：仅 `小店` / `pro店` 两种，其余忽略。
- **`dws_yth_xs01_yykj_zmt_v1_di` vs `dws_yth_xs02_mdkh_zmt_v1_di`**：两张线索表通过 union all 合并，落表时保留 `来源表` 字段以便后续按线索类型/来源拆分。
- **引擎选择**：星河 Hive (`sql_engine=5`) 优先；个别表如果 StarRocks 上有对应映射可改 `sql_engine=4`，但默认 Hive。
- **凭证**：从 `$XINGHE_CLIENT_USER` / `$XINGHE_CLIENT_SECRET` / `$XINGHE_ACCESS_KEY` 读，**绝不硬编码**。

## 输出规范

5 个 CSV 文件命名固定为 `data_storage/yiti_{xianshang,xiansuo,tongshou,xiaoshida,tongshou_yiti_city}_${dt}.csv`，UTF-8 with BOM 编码。每个 CSV 同时落一个 `.meta.json`，记录行数、列名、SQL hash。

## 失败处理

- 5 表中任一 t-1 数据未就绪 → `check_data_ready.py` 退出码 1，编排器直接发"数据未就绪"提醒给钟梦婷，不进 Step 1.1。
- SQL 报错 → 写 `data_storage/yiti_error_${dt}.log`，退出码非 0。
- 任一 CSV 行数为 0 → 视为失败，不要把空文件交给下游。

## 不要做的事

- 不要重写 SQL，模板已固化在 `Scripts/`。
- 不要修改 References，那是飞书文档真源的本地副本。

---
name: 一体化项目日报数据bot
description: 线上线下一体化项目日报编排器 skill。每日串行执行「代码生成 → 数据分析 → 质量检查 → 结论生成」四步，产出 7 项北极星指标（同城订单量/占比、线下线索量、线索转化总量、同售订单量、同售动销率、小时达订单量）的 t-1 数据日报，含月趋势图 + 周趋势图 + 30 日趋势图 + t-1 汇总表，飞书机器人推送到一体化项目群（chat_id `oc_69bfbe82133fedc9592bc18c3307aa51`）。当用户提到"一体化日报""一体化数据 bot""跑一下今天的一体化数据""一体化项目数据""出一版一体化日报"，必须调用本 skill。**不要触发**：一体化项目语料/文档变更（走现有 `一体化项目` skill）；商详/搜索/转化漏斗（走通用 `claude-data-analysis`）；618 消电大促日报（走 `618消电数据日报机器人推送`）。
metadata:
  type: orchestrator
  schedule:
    cron: "31 9 * * *"
    timezone: Asia/Shanghai
    note: "每天 09:31 由**系统 crontab**（headless `claude -p`）触发，不再用 REPL CronCreate。crontab 行：`31 9 * * * ~/.claude/scripts/run_headless_report.sh ~/.claude/scripts/cron_prompts/yiti_daily.txt ~/.claude/logs/yiti-cron.log`。改用 headless 的原因：REPL cron 只在有交互窗口空闲时才投递，无人值守时会漏触发（2026-07-17 事故）。系统 crontab 到点自拉起一次性进程，不依赖窗口。不要再为本日报建 REPL CronCreate 任务，否则双触发双推群。错开 09:30 的 618 日报。数据未就绪则只发『数据未就绪』提醒，不空跑。"
  pipeline:
    - 代码生成
    - 数据分析
    - 质量检查
    - 结论生成
  requires:
    bins: ["lark-cli", "python3"]
    env: ["XINGHE_CLIENT_USER", "XINGHE_CLIENT_SECRET", "XINGHE_ACCESS_KEY"]
---

# 一体化项目日报数据bot（编排器）

线上线下一体化项目每日数据日报的串行流水线。本 skill 只做编排——按顺序调度 4 个子 skill，前一步落盘后才进下一步；指标口径、字段定义、失败阈值都在子 SKILL.md 与 References 里，本文件不重复。

## 何时使用

"跑一下今天的一体化日报""一体化数据出来了吗""按取数说明出 t-1 数据""推一下昨天的一体化数据"，以及每日 cron 触发，都走本 skill。其它一体化语料/文档同步走 `一体化项目` skill；非一体化主题走通用 `claude-data-analysis`。

## 业务背景与北极星指标

线上线下一体化项目的目标：通看全国线上+线下货盘，建立监控机制定位数据变化、判定业务动作效果、识别异常点。

**7 项北极星指标**：
1. 同城订单量
2. 同城订单占比 = 同城订单量 / 总订单量
3. 线下线索量
4. 线索转化总量
5. 同售订单量
6. 同售动销率 = 同售订单量 / 同售库存
7. 小时达订单量

详细口径与 SQL 见 [References/取数与产出说明.md](References/取数与产出说明.md)。

## 目录布局

```
一体化项目日报数据bot/
├── SKILL.md                  # 本编排器
├── References/               # 业务真源（人读）+ 跨步骤产物契约（机器读）
│   ├── 取数与产出说明.md       # 与飞书文档同步的业务真源
│   └── output-schemas.md     # metrics / quality_check / feishu_doc 三套 JSON 契约
├── Scripts/                  # 6 份 SQL 模板（数据就绪检查 + 5 段取数）
│   ├── 00_check_data_ready.sql
│   ├── 01_xianshang_orders.sql
│   ├── 02_yiti_xiansuo.sql
│   ├── 03_tongshou_dongxiao.sql
│   ├── 04_xiaoshida.sql
│   └── 05_tongshou_dongxiao_by_yiti_city.sql
├── scripts/                  # 固化 Python 脚本（消除即兴写代码的 token 螺旋）
│   ├── config.py             # 收件人 / 表名 / 路径常量
│   ├── check_data_ready.py   # Step 1 前置：5 表 t-1 就绪检查
│   ├── fetch_metrics.py      # Step 1 取数：跑 5 段 SQL → 落 5 个 CSV
│   ├── compute_metrics.py    # Step 2 分析：CSV → 7 项指标 metrics_yiti_${dt}.json
│   ├── qa_check.py           # Step 3 闸口
│   ├── render_charts.py      # Step 4 出 3 张图（月/周/日）
│   └── feishu_publish.py     # Step 4 飞书 P2P 推送
├── assets/
│   └── report-template.md    # 报告骨架，sub-agent 按此填充
└── sub-skills/
    ├── 代码生成/SKILL.md
    ├── 数据分析/SKILL.md
    ├── 质量检查/SKILL.md
    └── 结论生成/SKILL.md
```

产物落 `~/.claude/` 下的 `data_storage/`、`analysis_reports/`、`visualizations/${dt}/`、`final_report/`。

## 流水线契约

每一步必须等上一步产物落盘后再进入下一步，**不要并发**。下面只列「递给下一步」的产物；具体字段/阈值/失败处理见对应子 SKILL.md；跨步骤产物的字段契约见 [References/output-schemas.md](References/output-schemas.md)。

> **串行 vs 并行的边界**：4 步主流程之间严格串行（前一步产物落盘才进下一步）；但**步骤内部**的多任务（Step 1 的 5 段 SQL、Step 4 的 3 张图）已经在固化脚本里并行化，详见对应子 SKILL 的「并行口径」段。sub-agent 不要自己再加一层并行。

| 步骤 | 子 skill | 关键产物 |
|---|---|---|
| 1 | [代码生成](sub-skills/代码生成/SKILL.md) | `data_storage/yiti_{xianshang,xiansuo,tongshou,xiaoshida}_${dt}.csv` |
| 2 | [数据分析](sub-skills/数据分析/SKILL.md) | `analysis_reports/metrics_yiti_${dt}.json` + `metrics_yiti_${dt}.summary.md` |
| 3 | [质量检查](sub-skills/质量检查/SKILL.md) | `analysis_reports/quality_check_yiti_${dt}.json`（`passed=false` 即停） |
| 4 | [结论生成](sub-skills/结论生成/SKILL.md) | `final_report/一体化日报_${dt}.md` + `visualizations/${dt}/{monthly,weekly,daily}.png` + 飞书 P2P 推送 |

通过 Task 工具调度子 skill；日期参数 `dt` 默认 t-1，可由用户覆盖。

## 失败处理

- 前一步是后一步的硬依赖，不要静默重试或跳过。
- **数据未就绪**（Step 1 前置检查 5 表 max(dt) < target_dt）：直接发一条 P2P 提醒「{表名} t-1 数据未就绪，已跳过今日推送」给钟梦婷，**不空跑后续步骤**。
  - **例外：同售动销表 `dws_yth_ts_kc_ord_zmt_di` 未就绪 → 先走「回刷」再决定**，见下方「同售动销表回刷」。该表上游 ETL 常比 09:31 就绪检查晚到位（2026-07-19/07-20 连续两天 t-1 count=0 漏推，实为延迟非缺数），直接跳过会漏报。
- 失败步骤的 stderr + 最后落盘产物路径打到 stdout，停在那里等人工。
- 步骤 3 `hard_failures` 非空 → 必须停，不进入第 4 步。
- 步骤 4 飞书推送失败 → 仅重试推送，**不要**回退到只发本地路径。

### 同售动销表回刷（Step 1 兜底）

**触发条件**：Step 1 前置检查发现 `04_tongshou`（`hdp_zhuanzhuan_dw_global.dws_yth_ts_kc_ord_zmt_di`）t-1 分区 `count=0`，其余 4 表就绪。

**处理流程**：
1. 跑回刷脚本 `scripts/refresh_tongshou.py --dt ${dt}` —— 它对该表 t-1 分区做 `INSERT OVERWRITE` 重跑（SQL 本体在 `Scripts/06_refresh_tongshou.sql`），回刷后自动校验分区行数。
2. 回刷成功（分区 count>0）→ 回到 Step 1 重新就绪检查，5 表齐则正常往下跑取数→分析→质检→推送。
3. 回刷执行完但仍 count=0（退出码 1）→ 说明上游 ETL 本身有问题，此时才按原「数据未就绪」逻辑发 P2P 提醒，不空跑。

> ⚠️ **高风险 + 授权边界**：回刷是对**生产表**的 `INSERT OVERWRITE`，会覆盖目标分区。红线：
> - **仅在该分区 `count=0`（未就绪/缺数）时回刷**；已有数据的分区不覆盖（脚本默认拦截，除非显式 `--force`）。
> - SQL 本体（`Scripts/06_refresh_tongshou.sql`）取自业务方生产调度原文（用户 2026-07-20 提供完整版，只取「【调度】当日」insert overwrite 段、不含建表 DDL），已过星河 `EXPLAIN` 编译校验（语法/表名/字段引用全合法、多阶段执行计划生成，无 SemanticException）。首次真回刷后务必看脚本打印的 `[after] count`，行数落在历史量级（07-19 基线：pro店 4 / 仓 18 / 小店 149，合计 171 行）才算成功。
> - 凭证只走 env（星河 `XINGHE_CLIENT_USER`/`XINGHE_CLIENT_SECRET`/`XINGHE_ACCESS_KEY`），不硬编码。

## 全局约定

- 默认中文输出。
- 凭证只走环境变量：星河 `XINGHE_CLIENT_USER` / `XINGHE_CLIENT_SECRET` / `XINGHE_ACCESS_KEY`，任何脚本都不要硬编码。
- 飞书推送默认发**一体化项目群**（chat_id `oc_69bfbe82133fedc9592bc18c3307aa51`），不是 P2P。如需调整收件人，改 `LARK_YITI_RECEIVERS` 环境变量；多个 id 用空格分隔，独立计账；id 前缀决定通道：`oc_*` 走 `--chat-id`（群），`ou_*` 走 `--user-id`（P2P）。
- 飞书推送身份固定为 `--as bot`（应用：`菜的飞书cli`，`cli_aa8e16c998b89cc5`），用户在 IM 看到的发送方是机器人。
- 业务规则真源在 References/，对应飞书文档：飞书文档先变 → References 同步 → 再改 sub-skill 实现。
- 可视化必须显式设置中文字体（PingFang SC / Heiti SC / Arial Unicode MS / SimHei），避免方块乱码。

## ❌ / ✅ 速查

| ❌ Don't | ✅ Do |
|---|---|
| sub-agent 即兴写 QA / 画图 / 飞书发布 Python | 直接调 `scripts/` 下的固化脚本 |
| 5 表数据未就绪还硬跑后续步骤 | Step 1 先 `check_data_ready.py`，未就绪只发提醒不空跑 |
| sub-agent 自创字段名 | 严格按 References/output-schemas.md |
| `passed=false` 仍进 Step 4 | 硬失败必须停 |
| Step 4 推送失败回退发本地 md | 失败 = 失败，不能给业务方本地路径 |
| 在脚本/SKILL 写明文星河密码 / appSecret | 凭证只走 env var 与 lark-cli config |
| 把群推改回 P2P | 默认推一体化项目群（`oc_69bfbe82133fedc9592bc18c3307aa51`）；如需 P2P 必须当次显式说 |

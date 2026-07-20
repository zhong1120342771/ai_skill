---
name: 转转核心指标异动监控bot
description: 转转 App 核心底表（hdp_zhuanzhuan_tmp_global.tmp_dws_zz_core_dataagent_zmt_v2_di）的核心指标异动监控编排器，定位是一个专业的经营分析师。串行执行「取数 → 数据洞察 → 发现异常 → 下钻 → 质检 → 结论生成（含图表+飞书推送）」，其中发现异常↔下钻可多轮循环直到定位最细颗粒度。当用户要判断转转核心数据（北极星：dau-净支付pv转化率 / dau / 单量）是否异常、异常在哪个漏斗环节（曝光渗透/商详到达/下单/支付）、集中在哪个维度（人/场/货/端），或问「今天核心指标正常吗」「北极星为什么跌」「异动定位/复盘」时，必须调用本 skill。本表 matched_dau_uv 是分维度匹配 DAU，dau-净支付pv转化率可跨维度比（与旧表 uv_all 全局常数相反）。**不要触发**：首页模块曝光/点击专题（走「首页数据洞察」/「淑芬」）；一体化项目日报（走「一体化项目日报数据bot」）；与本底表无关的临时 SQL。
metadata:
  type: orchestrator
  table: hdp_zhuanzhuan_tmp_global.tmp_dws_zz_core_dataagent_zmt_v2_di
  pipeline:
    - 取数
    - 数据洞察
    - 发现异常
    - 下钻
    - 质检
    - 结论生成
---

# 转转核心指标异动监控bot（编排器）

围绕核心底表的指标异动监控流水线，整体定位一个专业的经营分析师：**定位转转核心数据表现是否异常，如果异常是什么异常**。本 skill 只做编排——按顺序调度 6 个子 agent，前一步落盘才进下一步；字段口径、维度体系、失败阈值都在 references 与子 SKILL.md 里，本文件不重复。

## 何时使用

本 skill 有两条路径，进来先按问题意图路由（判据见「路径路由」）：

**路径 A — 数据问答（快捷）**：只想知道一个数是多少，不需要异动归因。
- 「昨天 app 新用户量级是多少」「消费电子昨天单量多少」「新媒体召回的净支付转化率是多少」「找靓机 DAU 占比多少」。
- 只派发取数 agent（Step 1）取数 → 直接在对话里回文字结论，**跳过洞察/异常/下钻/质检/结论生成，不落盘报告、不推飞书**。详见「数据问答（快捷分支）」。

**路径 B — 完整异动监控（6 步流水线）**：判断是否异常、定位归因、复盘。
- **日常异动监控**：「今天核心指标正常吗」「跑一下核心指标异动」「北极星有没有异常」。
- **异动定位归因**：「dau-净支付pv转化率为什么跌」「单量掉了定位一下」「哪个环节/维度拉动的」。
- **专业复盘**：「核心数据复盘」「环比/同比异动分析」。

北极星三指标：**dau-净支付pv转化率**（`pay_pv/matched_dau_uv`）、**dau**（`matched_dau_uv`）、**单量**（`pay_pv`）。漏斗链：dau转化率 = 曝光渗透率 × 商详到达率 × 下单率 × 支付率。四大维度：**人**（来源4类 + 资产 z0~z5/三档）、**场**（三级场景）、**货**（业务4类/品类）、**端**（APP/小程序/找靓机）。

### 路径路由（进来先判）

| 信号 | 走哪条 |
|---|---|
| 问「是多少 / 量级 / 占比 / 有多少 / 多少单 / 转化率是几」等**取值型**，且只要一个/几个数 | **A 快捷问答** |
| 问「正常吗 / 为什么涨跌 / 哪个环节 / 哪个维度拉动 / 复盘 / 异动 / 定位」等**判断+归因型** | **B 完整流水线** |
| 取值型但同时要「跟上周比 / 是不是异常」 | 倾向 B（要基准和判定）；只要环比数值不要判定则 A 里带环比即可 |
| 问的指标**不在本底表口径内**（GMV/客单价/退款/留存/停留时长等） | 都不走，直说「本底表不含该指标」（见硬护栏） |

意图不明确时，按最省的 A 先取值回答，并说明「如需判断是否异常/归因，可跑完整异动监控」。

## 目录布局

```
转转核心指标异动监控bot/
├── SKILL.md                       # 本编排器
├── references/                    # 口径真源(人读) + 维度字典
│   ├── 字段映射与指标口径.md         # ⚠️ matched_dau_uv 分维度DAU + 北极星/漏斗链 + NULL陷阱(必读)
│   ├── 维度体系与样例数据.md         # 21个 tag_01 口径族 + 人/场/货/端枚举值字典
│   ├── 重点关心问题.md              # 分析主线:三北极星 + 异动判定基准
│   ├── 取数封装逻辑.md              # 底表怎么来的(理解口径用,日常不重跑)
│   ├── 日历与季节性.md              # 异动背景板:周内节奏/节假日/调休(calendar_context常量真源,大促窗口已剔除)
│   ├── output-schemas.md          # 6步产物 JSON/CSV 契约(跨步数据合约)
│   └── 历史数据回刷指南.md          # 底表缺分区怎么补(run_backfill 单天/滚动双模式+并发/引擎约束)
├── scripts/                       # 固化脚本(消除即兴写代码)
│   ├── query_global_table.sql     # 取数模板(区间/下钻/横向 三种)
│   ├── run_backfill.py            # 回刷提交器:给区间→查缺口→默认单天模式(每缺失日只写1分区)并发提交(SparkSQL)
│   ├── backfill_single_day.sql    # 单天回刷模板(默认,占位符 ${targetDay}/${infoSnapshotDt},只扫写1天)
│   ├── backfill_history.sql       # 31天滚动回刷模板(--mode window,占位符 ${outFileSuffix}/${infoSnapshotDt})
│   ├── analyze_dimension.py       # wd 拆维度 + 北极星/漏斗链派生 → tidy 长表
│   ├── detect_anomaly.py          # 环比/横向/趋势 三基准异动检测
│   ├── business_diagnose.py       # 分业务(消电/二奢/兴趣)漏斗诊断:普降vs特征品类,品类→场景下钻
│   ├── calendar_context.py        # 日历/季节性上下文:日型判定+对齐基准同质性(统一星期对齐,大促已剔除)
│   ├── qa_check.py                # 结论前质量闸口(NULL陷阱+链乘自洽)
│   ├── render_charts.py           # 漏斗分解/维度排行图
│   ├── render_trend_charts.py     # 图1月均/图2近30日/图3近8周(四宫格+去年同期,v8-0711)
│   └── feishu_publish.py          # docx + P2P 推送(--post 单条图文交插:表格转文字/趋势图内嵌)
├── assets/
│   ├── report-template.md         # 飞书文档(docx)骨架(详细报告,结构不变)
│   └── message-template.md        # P2P 飞书消息(post)骨架(四段结论+表格转文字+3趋势图内嵌,v8-0711)
└── agents/                        # 6 个子 agent 定义(编排器用 Agent 工具派发)
    ├── 取数/SKILL.md
    ├── 数据洞察/SKILL.md
    ├── 发现异常/SKILL.md
    ├── 下钻/SKILL.md
    ├── 质检/SKILL.md
    └── 结论生成/SKILL.md
```

产物落 `~/.claude/` 下：`data_storage/`（取数 csv）、`analysis_reports/`（tidy + 异动 + 下钻 + 质检）、`visualizations/${dt}/`（图）、`final_report/`（报告 md + 飞书产物）。产物字段契约见 [references/output-schemas.md](references/output-schemas.md)。中文文件名/路径在 shell 里加引号。

## 路径大小写硬约束（跨机器有效性）

磁盘上真实目录是小写 `references/`、`scripts/`、`agents/`、`assets/`。所有 skill 内部引用（链接、Agent 派发的 .md 绝对路径、脚本路径）必须与磁盘大小写**完全一致**——本机 macOS 大小写不敏感看不出，部署到区分大小写文件系统会找不到文件。改文件名或移目录后同步 grep 引用。

## 数据问答（快捷分支，路径 A）

只回答「一个数是多少」类取值型问题，**不走 6 步流水线**：取数 → 直接在对话里回文字结论。不落报告、不建 docx、不推飞书。

### 两个数据源：离线缓存优先，实时取数兜底

每周一自动构建一份「过去一周全量」离线缓存（见「离线周缓存」）。回答问答时按下表选源，**并且无论用哪个源，都必须在回答里告诉用户这个数的取数周期/数据日期**：

| 情形 | 用哪个源 |
|---|---|
| 问的日期落在缓存覆盖区间内，且没强调「最新/实时/今天刚出」 | **离线缓存**（读 `data_storage/latest_cache.json` 拿周期，再从对应 CSV 切行）。回答里注明「基于 {period_start}~{period_end} 缓存数据」 |
| 问的日期不在缓存区间（如问缓存构建后的新日期）、或用户强调时效性 | **实时取数**：派发取数 agent（Step 1）拉指定单日/单维度。回答里注明数据日期 = 实际 dt |
| 缓存文件不存在或读不出 | 直接实时取数，并提示「离线缓存暂不可用，已实时取」 |

先读指针判断能否命中缓存：

```bash
CACHE="/Users/zhongmengting/.claude/skills/转转核心指标异动监控bot/data_storage/latest_cache.json"
test -s "$CACHE" && python3 -c "import json;d=json.load(open('$CACHE'));print('缓存周期',d['period_start'],'~',d['period_end'],'| 行数',d['rows'],'| 构建于',d['built_at'])" || echo "无缓存，走实时取数"
```

命中缓存时，直接用 pandas 从 `csv_path` 按 `tag_01` + `wd` + `dt` 切出目标行读数，不重新查库。

### 命中缓存后怎么取数（示例：某日新用户量级）

```python
import pandas as pd, json
p = json.load(open('/Users/zhongmengting/.claude/skills/转转核心指标异动监控bot/data_storage/latest_cache.json'))
df = pd.read_csv(p['csv_path'])
# 新用户(资产口径 z0)：单维度-拆分用户资产分层 里 wd=='z0'
row = df[(df.tag_01=='单维度-拆分用户资产分层') & (df.wd=='z0') & (df.dt=='2026-07-08')]
print(row[['dt','wd','matched_dau_uv']])   # matched_dau_uv 即新用户活跃量级
```

新用户口径（来源口径 vs 资产口径 z0）见 [references/字段映射与指标口径.md](references/字段映射与指标口径.md) §一·补，回答时点明用的哪个口径。

### 实时取数（缓存未命中）

按「派发方式」派发**取数 agent（Step 1）**，prompt 里说明这是**单点问答取数**：只拉用户问的那一天 + 那个口径族（不用拉全基准区间），落 `data_storage/global_raw_${dt}.csv` 后自己 pandas 读数回答。取完直接出结论，不进 Step 2。

### 硬护栏（超出底表口径直说答不了）

本底表只含：漏斗（曝光/商详/下单/净支付 的 pv·uv）+ 匹配 DAU（`matched_dau_uv`）+ 各环节转化率，按人/场/货/端拆。问到**底表没有的指标**（GMV、客单价、退款、次日留存、停留时长、DAU 绝对新增数以外的口径等）→ **直接说「本核心底表不含该指标，答不了」**，不臆造、不擅自去串其他表。能答的就是上面这些字段及其派生率。

### 回答格式（对话里，简短）

- 给出数值 + 口径 + **数据来源与周期**（缓存周期 or 实时 dt）。比率按 `X.XX%` 两位小数（v2-1）。
- 用户要环比就多切一天算涨跌幅；只问值就只给值。
- 结尾一句可选提示：「如需判断是否异常/定位归因，可跑完整异动监控（路径 B）」。
- 对外若成段，过 humanizer 去 AI 味（不动数字/口径）。

## 离线周缓存（每周一自动构建）

- 脚本：`scripts/build_weekly_cache.py`。拉核心底表**过去一周全量**（默认 t-7 ~ t-1、全部 21 个口径族），落 `data_storage/【{start}~{end}】转转核心指标缓存数据.csv`（utf-8-sig）+ 更新 `data_storage/latest_cache.json` 指针。
- 定时：每周一自动跑（launchd 持久定时 `com.zmt.zzcore.weeklycache`，非 Claude cron；后者 7 天过期）。凭证走环境变量，wrapper `run_weekly_cache.sh` 先 `source ~/.zshrc`。
- 手动补跑：`python3 scripts/build_weekly_cache.py --start 2026-07-01 --end 2026-07-07`。
- **落盘后自动写飞书表格**：`build_weekly_cache.py` 末尾调 `push_cache_to_feishu.py`，把这份缓存写入 wiki 表「核心数据问答agent_缓存数据」(spreadsheet_token `WMkQsQ2RUhOPyZt9OYrcoY3Tnhc`) 的**新 sheet**，sheet 名=时间周期 `{start}~{end}`；同名已存在则跳过不重复建。加 `--no-feishu` 只落盘不推。
- **写入通道**：`push_cache_to_feishu.py` 用 `lark-cli sheets +csv-put --csv @./file`（cwd=`~/.claude`），整份 CSV 一次写完。**不要**退回 `+append --values` 内联 JSON——命令行参数 ~75KB 上限会把大表截断报 "invalid JSON"。

```bash
# 每周一构建过去一周缓存 + 自动推飞书（launchd wrapper 实际调用）
source ~/.zshrc && python3 "/Users/zhongmengting/.claude/skills/转转核心指标异动监控bot/scripts/build_weekly_cache.py"
# 只补缓存不推飞书：加 --no-feishu；只补推飞书：python3 scripts/push_cache_to_feishu.py [--csv <路径>]
```

## 流水线契约

> 下面是**路径 B（完整异动监控）**的 6 步契约；路径 A 快捷问答见上一节，不走这里。

每一步等上一步产物落盘后再进入下一步，**不要并发**。**发现异常(3)↔下钻(4) 可多轮循环**，直到定位到最细颗粒度或确认无更细特征，才进质检。下面只列「递给下一步」的产物；字段/阈值/失败处理见对应子 SKILL.md。

| 步骤 | 子 agent | 关键产物 |
|---|---|---|
| 1 | [取数](agents/取数/SKILL.md) | `data_storage/global_raw_${dt}.csv`（含分析日 + 环比基准 + 近 N 天，一次取够） |
| 2 | [数据洞察](agents/数据洞察/SKILL.md) | `analysis_reports/tidy_${dt}.csv` + `insight_${dt}.summary.md` |
| 3 | [发现异常](agents/发现异常/SKILL.md) | `analysis_reports/anomaly_${dt}.csv`（三基准异动清单） |
| 4 | [下钻](agents/下钻/SKILL.md) | `analysis_reports/drilldown_${dt}.md`（定位到最细颗粒度，可多轮） |
| 5 | [质检](agents/质检/SKILL.md) | `analysis_reports/quality_check_core_${dt}.json`（`passed=false` 即停） |
| 6 | [结论生成](agents/结论生成/SKILL.md) | `final_report/核心指标异动_${dt}.md` + `visualizations/${dt}/*.png` + 飞书 docx + P2P 推送 |

### Step 0：t-1 就绪检查 + 未就绪自动回刷兜底（派发 Step 1 前必跑）

派发取数 agent 之前，先确认底表 `dt=${dt}`（默认 t-1）分区已就绪。判据：`count(1)>0` 且 `max(dt)>=${dt}`。就绪 → 直接进 Step 1；**未就绪 → 先自动回刷 `${dt}` 单天分区，回刷成功再进 Step 1**，不再默认停在取数步、不再只发一条「未就绪」提醒（旧兜底已被回刷兜底取代）。

```bash
# 0.1 就绪检查（星河 Hive，凭证走 env）
cd ~/.claude && source ~/.zshrc 2>/dev/null && python3 -c "
import sys; sys.path.insert(0,'/Users/zhongmengting/.claude/skills/xinghe-data/scripts')
from xinghe_client import XingheExplorer
c=XingheExplorer()
e=c.run_sql(\"select count(1) c,max(dt) mx from hdp_zhuanzhuan_tmp_global.tmp_dws_zz_core_dataagent_zmt_v2_di where dt='${dt}'\",sql_engine=5)
r=c.wait_and_get_result(e,max_wait=180)
print('READY_CHECK',[str(x) for blk in (r.get('previews') or []) for row in blk for x in row])
"
```

- `count>0` → 就绪，跳过回刷，直接 Step 1。
- `count=0`（分区缺失/为空）→ **自动回刷这一天**：

```bash
# 0.2 未就绪则回刷 ${dt} 单天分区（默认单天模式，只写这 1 个分区；缺失日会被 gap 探测命中）
cd ~/.claude/skills/转转核心指标异动监控bot && source ~/.zshrc 2>/dev/null && \
python3 scripts/run_backfill.py --start ${dt} --end ${dt} --parallel 1 --max-wait 7200
# 若分区已存在但为空/需覆写，加 --force-all：
# python3 scripts/run_backfill.py --start ${dt} --end ${dt} --parallel 1 --force-all
```

- 回刷脚本会在批完成后自检分区行数，返回码 `0` = 成功且非空。
- 回刷成功 → **重跑 0.1 就绪检查确认 `count>0`，再进 Step 1**，流水线照常跑完 6 步并双推。
- 回刷仍失败/仍为空（返回码非 0，通常是上游 info/源表当天也没产出）→ 这才回落到「发一条 P2P 提醒钟梦婷说明 t-1 数据 + 回刷均未就绪、今日暂不推送」，不空跑后续步骤。
- **只回刷当天这一个分区**，不顺带补历史区间（历史缺口走 [references/历史数据回刷指南.md](references/历史数据回刷指南.md) 单独处理，别在日报路径里放大 blast radius）。

### 派发方式（Agent 工具）

每一步用 **`Agent` 工具**派发，`subagent_type` 固定 `general-purpose`，prompt 用绝对路径把子 agent 定义文件递给它自己 Read 执行（不要猜别的 subagent_type 名，会报 "Agent type not found"）：

```
Agent tool:
  subagent_type: general-purpose
  description: "Step N <名> - <一句话>"
  prompt: "dt = ${dt}
    分析维度 --by=<…>、口径族 --tag=<…>、主指标 --metric=<…>（默认北极星 dau_pay_rate，按用户问题透传）
    你的 agent 定义文件路径: /Users/zhongmengting/.claude/skills/转转核心指标异动监控bot/agents/<步名>/SKILL.md
    请完整 Read 该文件并严格执行其中的所有指令。"
```

`dt` 默认 t-1，可由用户覆盖；`--by`/`--tag`/`--metric` 由用户问题决定，各步保持一致（尤其 `--metric`，否则质检口径校验失配）。

> **循环控制**：Step 3 交接会点名 1~3 个最值得下钻的异常点。Step 4 下钻后若需换口径族重新检测，编排器再派发一次 Step 3（异动清单追加，标 `round`），如此往复直到收敛。编排器负责判断"是否收敛"（下钻结论已到最细维度 / 盘子过小 / 无更细特征）。
> **迁移提示**：prompt 是纯文本、不经 shell 展开，必须用**硬编码绝对路径**（写 `$HOME`/`~` 子 agent Read 时不解析）。换机器/用户名时，把这段 `/Users/zhongmengting/.claude/...` 前缀替换成目标机实际 `~/.claude` 绝对路径——各步各一处。

### 逐步产物校验（每步派发后、进下一步前跑）

```bash
# Step 1 后
test -s ~/.claude/data_storage/global_raw_${dt}.csv && wc -l ~/.claude/data_storage/global_raw_${dt}.csv || echo "STOP: 取数产物缺失"
# Step 2 后
for f in tidy_${dt}.csv insight_${dt}.summary.md; do test -s ~/.claude/analysis_reports/$f || echo "STOP: 缺 $f"; done
# Step 3 后
test -f ~/.claude/analysis_reports/anomaly_${dt}.csv && wc -l ~/.claude/analysis_reports/anomaly_${dt}.csv || echo "STOP: 缺异动清单"
# Step 4 后
test -s ~/.claude/analysis_reports/drilldown_${dt}.md || echo "STOP: 缺下钻结论"
# Step 5 后：读闸口，passed=false 必停
python3 -c "import json;d=json.load(open('$HOME/.claude/analysis_reports/quality_check_core_${dt}.json'));print('PASSED' if d['passed'] else 'STOP: '+str(d['hard_failures']))"
# Step 6 后
test -s ~/.claude/final_report/核心指标异动_${dt}.md && ls ~/.claude/visualizations/${dt}/*.png && test -s ~/.claude/final_report/核心指标异动_${dt}.feishu.json || echo "STOP: 结论产物不全"
```

## 异动判定方法（贯穿全流程）

判定「是否异常」时三个基准都要看（取数步据此决定拉几天）：

1. **环比**：分析日 vs t-1、vs 上周同日，看指标涨跌幅（`detect_anomaly.py` 默认阈值 15%，与分业务判定阈值一致）。
2. **同比（独立判定基准）**：分析日 vs 去年同期，涨跌越 ±15% 与环比并列计入异常；北极星等指标呈现时带同比数值。**对齐方式**：统一星期对齐（-364 天），大促峰值日日期对齐特例已剔除（大促节点非用户输入）。真源 `calendar_context.yoy_baseline`。
   - **⚠️ 兴趣 / 二奢 低基数同比抑制（用户输入 2026-07-20）**：这两个业务 2025 年的**转化率**（北极星 + 漏斗各环节率）与**单量**（`pay_pv`）基数低，同比极易越阈值、误报异常，因此**当同比基准日 < 2026-01-01 时，兴趣/二奢 的转化率与单量一律不做同比、不计入异常判定**（分析日到 2026-12-31 后同比基准日进入 2026 年自动恢复）。环比/横向/趋势不受影响；消费电子等其他业务不受影响。真源 `calendar_context.yoy_low_base_suppressed()`，`detect_anomaly.py` / `business_diagnose.py` 均已接入。
3. **横向对比**：同一指标在某维度各取值间排序，标出偏离中位 ±3 MAD 的格子。**必须限定在同一 `tag_01` 粒度内**（`--tag`），不能跨粒度比大小。
4. **近 N 天趋势**：拉 7~14 天序列，标记单日跳变拐点。

分析顺序（经营分析师主线）：**先看北极星（整体行）→ 漏斗环节归因 → 拆维度找特征 → 逐层下钻到最细**。

## 全局约定（违反就出错）

- **口径优先（本表核心，与旧表相反）**：`matched_dau_uv` 是**分维度匹配**的 DAU 分母，`pay_pv/matched_dau_uv`（`dau_pay_rate`，北极星）**可跨维度比大小**。⚠️ `matched_dau_uv` 为 NULL（每天约 6~8 行，闸门失败）的行**不能算任何 DAU 类比率、绝不当 0**。详见 [references/字段映射与指标口径.md](references/字段映射与指标口径.md)。质检会拦截 NULL 当 0、北极星与漏斗链不自洽。
- **比率看体量**：小分母下比率剧烈抖动，异动定位默认剔除 `exp_uv < 1000` 的行（`--min-exp-uv`）。报告里比率必带绝对量（DAU/曝光UV/商详UV/单量），让业务读得出盘子大小。
- **维度字典是常量**：人/场/货/端枚举值在 [references/维度体系与样例数据.md](references/维度体系与样例数据.md)，`analyze_dimension.py` 已固化拆分逻辑，**不要每次重新推断 `wd` 怎么拆**；新增枚举值同步改脚本常量。
- **取数通道：星河为主，One-Service 兜底**。底表是 Hive 表，默认走星河（`xinghe_client.py`，`run_sql(sql, sql_engine=5)`），星河不可用切 One-Service。Hive strict mode：ORDER BY 带 LIMIT、必须分区过滤。详见 [取数子 agent](agents/取数/SKILL.md)。
- **凭证只走环境变量**：星河 `XINGHE_CLIENT_USER`/`XINGHE_CLIENT_SECRET`/`XINGHE_OA`，One-Service `ONESERVICE_OA`/`ONESERVICE_ACCESS_KEY`，任何脚本不硬编码、不打印日志。
- **飞书推送默认只发钟梦婷 P2P**（`ou_5e572adca6deef8ef21c3b18dfade573`，纯文本，不推群），收件人改 `LARK_CORE_RECEIVERS` 环境变量。lark-cli v1.0.43 P2P 必须 `--user-id`、文本用 `--text` 内联。
- **对外成段文字过 humanizer 去 AI 味**（只改措辞，不动数字/口径/结论）。
- **可视化必须显式设中文字体**（`PingFang SC`/`Heiti SC`/`Arial Unicode MS`/`SimHei`）。
- 默认中文输出。

## 失败处理

- **t-1 未就绪 → 先自动回刷当天分区再跑**（Step 0）：不再默认停在取数步只发提醒。回刷成功就正常跑完 6 步双推；回刷仍失败/仍为空才发 P2P 提醒暂不推送。
- 前一步是后一步的硬依赖，不静默重试或跳过。
- 步骤 5 `hard_failures` 非空 → 必停，不进结论生成。
- 步骤 6 文档已建但 IM 推送失败 → 复用 `doc_url` 只重推（`feishu_publish.py --skip-doc`），不回退到只发本地路径。

## ❌/✅ 速查

| ❌ Don't | ✅ Do |
|---|---|
| 把 `matched_dau_uv` 为 NULL 的行当 0 算 DAU 率 | NULL 行跳过 DAU 类比率；漏斗内部率（到达/下单/支付）仍可算 |
| 以为 `dau_pay_rate` 像旧表 uv_all 那样不可比 | 本表 `dau_pay_rate` 是北极星、可跨维度比大小 |
| 横向对比把 4 维交叉和单维度混在一起比 | 横向只在同一 `tag_01` 粒度内比（`--tag`） |
| 比率异动不看体量，小分母噪声当信号 | `--min-exp-uv` 体量地板；报告比率必附绝对量 |
| 发现异常就直接下结论，不下钻到最细 | 3↔4 循环下钻，定位到最细颗粒度再出结论 |
| sub-agent 重新推断 `wd` 怎么拆 / 即兴写脚本 | 直接用 `scripts/` 固化脚本，维度字典见 references |
| 把 P2P 改群聊或硬编码凭证 | P2P 发钟梦婷；凭证走 env var |
| t-1 没数据就直接停、只发提醒 | 先自动回刷 `${dt}` 单天分区(Step 0)，回刷成功再跑完 6 步；只有回刷也失败才发提醒 |
| 日报路径里顺带回刷历史区间放大 blast radius | 只回刷当天 1 个分区；历史缺口走历史回刷指南单独处理 |


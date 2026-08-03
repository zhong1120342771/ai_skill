---
name: moscow-defense-monthly-biz-app
version: 1.0.0
description: "莫斯科保卫战月报编排器（仅 App 端）：数据源为 App 端专属表 tmp_dws_msk_zmt_app_v2_di，无「端」维度，用品类/场景/用户来源/用户资产分层四维拆解。通过 Agent 工具串行调度 4 个独立 sub-agent（代码生成→数据分析→质量检查→洞察结论生成，内嵌数据可视化），每步上下文隔离、产物落盘后才进下一步，自动产出飞书文档 + P2P 推送到钟梦婷。应用场景为每月月初分析上一个完整自然月的数据。当用户说「莫斯科保卫战月报_仅app端」「仅app端莫斯科月报」「app端保卫战月报」「app端莫斯科月报」「仅看app端的莫斯科月报」时必须调用本 skill。多端口径（含小程序/找靓机）的月报走 moscow-defense-monthly-biz。"
metadata:
  type: orchestrator
  pipeline:
    - 代码生成
    - 数据分析
    - 质量检查
    - 洞察结论生成
---

# 莫斯科保卫战月报 · 仅 App 端（编排器）

> 数据源：App 端专属表 `hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di`。无「端」维度，拆解走品类/场景/用户来源/用户资产分层四维。多端口径月报请走 `moscow-defense-monthly-biz`。

本 skill 只做编排——通过 `Agent` 工具按顺序调度 4 个独立子 agent（洞察结论生成内部再内嵌数据可视化），每个子 agent 拥有独立上下文空间，**不占用编排器的上下文预算**。编排器只负责：启动 sub-agent → 校验产物 → 进入下一步。指标口径、SQL 细节、报告格式、失败阈值都在子 agent 的 `agents/<name>.md` 里，本文件不重复。

**应用场景**：每月月初，分析上一个完整自然月（如 8 月初跑 7 月）的莫斯科保卫战 App 端数据。数据模块、重点指标、拆解维度、可视化基本对齐 App 端周报（`moscow-defense-weekly-biz-app`），仅把「周」口径改为「月」，并新增「同比」。App 端不设 KPI 目标，只报实际月均值。

## 唤醒关键词

- 莫斯科保卫战月报_仅app端 / 仅app端莫斯科月报 / app端保卫战月报 / app端莫斯科月报
- 仅看 app 端的莫斯科月报 / app 端月报数据整理
- 更新 YYYY-MM 的 app 端月报数据

## 目录布局

```
moscow-defense-monthly-biz-app/
├── SKILL.md                    # 本编排器
├── agents/                     # 5 个独立子 agent 定义
│   ├── 代码生成.md
│   ├── 数据分析.md
│   ├── 质量检查.md
│   ├── 洞察结论生成.md
│   └── 数据可视化.md            # Step 4 内嵌子 agent
├── scripts/                    # SQL 脚本 + Python 工具
│   ├── 00_check_partition.sql
│   ├── 01_panel_monthly.sql    # 月度全维度面板（核心，覆盖 KPI/漏斗/4维度/大盘图）
│   ├── 02_daily_metrics.sql    # 分日数据（质检交叉验证）
│   ├── gen_report_monthly.py   # 月环比+月同比计算 + KPI/漏斗/维度表 XML 构建
│   └── render_charts_monthly.py # 月度图（2 张：大盘趋势 + 维度同比对比）固化脚本
└── references/
    ├── monthly-report-requirements.md  # 月报分析要求与话术规范（业务真源）
    ├── chart_config.md                 # 图表格式规范
    ├── upload_template.py
    └── validate_data.py
```

产物落 `~/Downloads/msk_monthly_raw_app/${month}/`，文件名见各 agent。

---

## 参数确认

开始前确认以下参数（用户未指定时，默认取上一个完整自然月）：

| 参数 | 说明 | 默认值 |
|------|------|------|
| `month` | 目标月份，YYYY-MM，如 `2026-06` | 今天所在月 - 1（上一完整自然月） |
| `month_end` | 本月末日，YYYY-MM-DD，用作 `${outFileSuffix}` | month 的最后一天 |

派生值（子 agent 内部自算，编排器无需传）：`prev_month`（上月，月环比基准）、`yoy_month`（去年同月，同比基准）。

时间周期规则：自然月（1 号到月末）为一个完整周期，数据截止至上一个完整自然月（来自 `references/monthly-report-requirements.md`）。

**month_end 推导**：可用 `python3 -c "import calendar,sys; y,m=map(int,'${month}'.split('-')); print(f'{y}-{m:02d}-{calendar.monthrange(y,m)[1]}')"`。

---

## 流水线契约

### 调度机制

每个步骤通过 **`Agent` 工具** 调度为独立子 agent。编排器只负责：启动子 agent → 校验产物 → 进入下一步。

**编排器执行时必须严格遵守：**

1. **串行执行**：每步等上一步产物落盘后再启动下一步，**不跨步并发**。Step 1 内部多 SQL 可在 sub-agent 内并行。
2. **Agent 隔离**：每步通过 `Agent` 工具启动，prompt 模板见下文，子 agent 自己 Read 对应 `agents/<name>.md` 并执行。
3. **产物校验**：每步完成后编排器在主上下文跑简短 bash 验证文件存在+非空，通过才进下一步。
4. **失败即停**：任一步失败（Agent 返回错误 / 产物缺失 / 硬失败），立即停止，不跳过、不静默重试。
5. **日期参数**：`month` / `month_end` 由用户指定或默认上一完整自然月。

### 第一步：代码生成

**Agent 调用：**
```
Agent tool:
  description: "Step 1 代码生成 - 分区校验 + 并行取数"
  prompt: "month = ${month}
    month_end = ${month_end}
    你的 agent 定义文件路径: /Users/zhongmengting/.claude/skills/moscow-defense-monthly-biz-app/agents/代码生成.md
    请完整 Read 该文件并严格执行其中的所有指令。"
```

**产物校验**（缺一个即停）：
```bash
DIR=~/Downloads/msk_monthly_raw_app/${month}
for f in 01_panel.csv 02_daily.csv; do
  [ -s "$DIR/$f" ] || { echo "[FAIL] missing or empty: $f"; exit 1; }
done
# 穿月自检：01_panel 最大月份必须 == ${month}，不得出现更晚月份
python3 -c "
import csv
rows=list(csv.DictReader(open('$DIR/01_panel.csv',encoding='utf-8-sig')))
mx=max(r['月份'] for r in rows)
assert mx=='${month}', f'[FAIL] 穿月：01_panel 最大月份 {mx} != ${month}'
print('[OK] Step 1 取数完成，无穿月')
"
```

子 agent 文件：[agents/代码生成.md](agents/代码生成.md)

### 第二步：数据分析

**前置条件**：第一步全部 CSV 落盘。

**Agent 调用：**
```
Agent tool:
  description: "Step 2 数据分析 - 漏斗框架 + 4 维度拆解 + 月环比/同比"
  prompt: "month = ${month}
    你的 agent 定义文件路径: /Users/zhongmengting/.claude/skills/moscow-defense-monthly-biz-app/agents/数据分析.md
    请完整 Read 该文件并严格执行其中的所有指令。"
```

**产物校验：**
```bash
DIR=~/Downloads/msk_monthly_raw_app/${month}
[ -s "$DIR/analysis_result.json" ] || { echo "[FAIL] analysis_result.json 缺失"; exit 1; }
[ -s "$DIR/analysis_summary.md" ]  || { echo "[FAIL] analysis_summary.md 缺失"; exit 1; }
echo "[OK] Step 2 分析完成"
```

子 agent 文件：[agents/数据分析.md](agents/数据分析.md)

### 第三步：质量检查

**前置条件**：第二步 2 个产物落盘 + 第一步 CSV 仍在。

**Agent 调用：**
```
Agent tool:
  description: "Step 3 质量检查 - 数据/分析质量闸口"
  prompt: "month = ${month}
    你的 agent 定义文件路径: /Users/zhongmengting/.claude/skills/moscow-defense-monthly-biz-app/agents/质量检查.md
    请完整 Read 该文件并严格执行其中的所有指令。"
```

**产物校验**（编排器必须读 JSON 的 `passed` 字段）：
```bash
DIR=~/Downloads/msk_monthly_raw_app/${month}
[ -s "$DIR/quality_check.json" ] || { echo "[FAIL] quality_check.json 缺失"; exit 1; }
python3 -c "
import json, sys
q = json.load(open('$DIR/quality_check.json'))
hard = q.get('hard_failures', [])
passed = q.get('passed', False) and not hard
print('[OK]' if passed else '[FAIL]', 'passed=', passed, 'hard_failures=', hard)
sys.exit(0 if passed else 1)
"
```

- `passed=false` → 立即停止，不进入第四步
- `passed=true` 但 `hard_failures` 非空 → 同样停止（视为不可信）
- `passed = (hard_failures 为空)` 是铁律

子 agent 文件：[agents/质量检查.md](agents/质量检查.md)

### 第四步：洞察结论生成

**前置条件**：第三步 `passed=true` 且 `hard_failures` 为空。

**Agent 调用：**
```
Agent tool:
  description: "Step 4 洞察结论生成 - 报告撰写 + 飞书发布 + P2P 推送"
  prompt: "month = ${month}
    你的 agent 定义文件路径: /Users/zhongmengting/.claude/skills/moscow-defense-monthly-biz-app/agents/洞察结论生成.md
    请完整 Read 该文件并严格执行其中的所有指令。"
```

**产物校验：**
```bash
DIR=~/Downloads/msk_monthly_raw_app/${month}
[ -s "$DIR/feishu_doc.json" ] || { echo "[FAIL] feishu_doc.json 缺失（文档/推送记录）"; exit 1; }
python3 -c "
import json
m = json.load(open('$DIR/feishu_doc.json'))
assert m.get('doc_url'), 'doc_url 缺失'
assert m.get('p2p_push', {}).get('success'), 'P2P 推送未成功'
print('[OK] doc_url=', m['doc_url'])
"
```

子 agent 文件：[agents/洞察结论生成.md](agents/洞察结论生成.md)

### 流水线状态速查

| 步骤 | 子 agent | 输入 | 输出 | 闸口 |
|---|---|---|---|---|
| 1 | 代码生成 | month / month_end | `01_panel.csv` + `02_daily.csv`（2 个） | 全部存在且非空 + 无穿月 |
| 2 | 数据分析 | 2 个 CSV | `analysis_result.json` + `analysis_summary.md` | 2 个文件非空 |
| 3 | 质量检查 | 6 CSV + analysis_result.json | `quality_check.json` | **passed=true 且 hard_failures 为空** |
| 4 | 洞察结论生成 | analysis_result + analysis_summary + quality_check + 01_panel | `feishu_doc.json`（含 doc_url + p2p_push） | 文档创建 + 推送成功 |

---

## 失败处理

- 前一步是后一步的硬依赖，不静默重试或跳过。
- 子 agent 返回错误或产物缺失 → 编排器 stdout 打出失败步骤 + 缺失文件路径，停在那里等人工。
- Step 1 本月末日分区未就绪且刷新失败 → 停，等人工（月报必须用完整自然月）。
- Step 3 `hard_failures` 非空 → 必须停，不进 Step 4。
- Step 4 文档已建但 IM 推送失败 → 仅重推 IM（复用已有 `doc_url`），**不回退发本地路径**，更不重建文档。

---

## 全局约定

- **凭证只走环境变量**：星河 `XINGHE_CLIENT_USER` / `XINGHE_CLIENT_SECRET` / `XINGHE_OA`，One-Service `ONESERVICE_OA` / `ONESERVICE_ACCESS_KEY`，任何脚本/SKILL 都不写明文。
- **数据源硬约束**：App 端月报走 `hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di`（App 端专属表，唯一主源）。本表无「拆分端」维度，用品类/场景/用户来源/用户资产分层四维拆解。多端归因表 `tmp_dws_msk_zhibiao_zmt_v2_di` 是多端月报（moscow-defense-monthly-biz）的源，本 skill 不用。月报只用 app 专属表出 01_panel + 02_daily。
- **环比/同比口径**：月环比=本月 vs 上月，同比=本月 vs 去年同月，均由 Python 端基于月度面板算，SQL 不含窗口（这也规避了周报 01_kpi 的 Spark NPE）。
- **时间上界硬规则（防穿月）**：所有取数 SQL 必须有上界 `dt <= '${outFileSuffix}'`（本月末日）。分区常延伸到下月初（跑 6 月时 `dt_max` 已到 7-02），只写下界会捞进下月初分区、多切出残缺的下一月桶，污染趋势图和"最新完整月"判定。Step 1 落盘后必须自检 CSV 最大月份 == `${month}`，出现更晚月份即失败。
- **飞书推送**默认发钟梦婷个人 P2P（`ou_5e572adca6deef8ef21c3b18dfade573`），不推群聊。lark-cli 1.0.43 P2P 必须用 `--user-id` 不是 `--chat-id`；`--content` 必须 inline JSON。
- **落位与周报一致**：wiki space 7639643477596441545，父节点 PGlqwRjBIivjKnkInplcEEQ6ndg，标题「【${month_cn}】莫斯科保卫战月报·仅App端」（与多端月报同空间，标题加「·仅App端」区分）。
- 默认中文输出。对外结论/飞书文档/推送文字**默认调 `humanizer` skill 去 AI 味**（不改数字口径）。

---

## ❌/✅ 速查

| ❌ Don't | ✅ Do |
|---|---|
| 编排器自己写 SQL / 跑分析 / 画图 | 编排器只调 `Agent` 工具起子 agent |
| 跨步骤并发 4 个 agent | 严格串行；Step 1 内部 SQL 才可并发 |
| 跳过分区检查直接取数 | Step 1 先跑 `00_check_partition.sql`，本月末日就绪才取数 |
| 用未完整的当月跑月报 | 必须等上一个完整自然月末日分区就绪 |
| 在 SQL 里写月环比/同比窗口 | 环比/同比由 `gen_report_monthly.py` / 数据分析 agent 在 Python 端算 |
| Step 3 `passed=false` 或 `hard_failures` 非空时进 Step 4 | 停止，等人工 |
| Step 4 文档失败回退发本地 md 路径 | 文档失败 = Step 4 失败 |
| Step 4 IM 推送失败时重建文档 | 复用上次 doc_url，只重推 IM |
| 飞书推送改群聊 | P2P 是硬规则，除非用户明确说推群 |
| 脚本里硬编码凭证 | 凭证只走 `~/.zshrc` 环境变量 |
| 用多端归因源 `tmp_dws_msk_zhibiao_zmt_v2_di` | 用 App 端专属表 `tmp_dws_msk_zmt_app_v2_di` |
| 报告里保留「端」拆解章节 | 用品类/场景/用户来源/用户分层四维（App 端无「端」） |
| SQL 只写 `dt >= ...` 让下月初分区穿月 | 每段 SQL 加上界 `dt <= '${outFileSuffix}'`，Step 1 自检最大月份==`${month}` |

---

## 与周报的对应关系

| 维度 | 周报（moscow-defense-weekly-biz-app） | 月报（本 skill） |
|------|------|------|
| 周期 | 周一–周日完整周 | 完整自然月 |
| 对比口径 | 周环比 | 月环比 + 同比 |
| 取数 SQL | 11 段（含易错 union all 窗口 + 01_kpi NPE） | 2 段（月度面板 01_panel + 02_daily，规避 NPE） |
| KPI 表列 | 指标/本周均值/周环比（App 端无目标） | 指标/本月均值/月环比/月同比（App 端无目标） |
| 拆解维度 | 品类/场景/用户来源/用户分层（无端） | 品类/场景/用户来源/用户分层（无端） |
| 报告结构 | 一、周数据回顾 + 二、重要事项进展 | 仅「一、月数据回顾」（二已永久移除） |
| 趋势图 | 大盘月度 + 5 张分业务周趋势 | 大盘月度图 + 维度同比对比柱状（共 2 张） |
| 落位/推送 | wiki 同空间 / P2P 钟梦婷 | 完全一致，仅标题改月报 |

---

## 历史产出记录

| 月份 | 飞书文档 | 备注 |
|------|---------|------|
| （待首次运行填充） | | |

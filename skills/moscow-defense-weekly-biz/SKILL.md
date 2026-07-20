---
name: moscow-defense-weekly-biz
version: 4.0.0
description: "莫斯科保卫战周报编排器：通过 Agent 工具串行调度 4 个独立 sub-agent（代码生成→数据分析→质量检查→洞察结论生成），每步上下文隔离、产物落盘后才进下一步，自动产出飞书文档 + P2P 推送到钟梦婷。当用户说「莫斯科保卫战周报」「保卫战周报」「莫斯科周报」「周报数据整理」「跑一下本周保卫战数据」「更新 MMDD-MMDD 的周报」时必须调用本 skill。"
metadata:
  type: orchestrator
  pipeline:
    - 代码生成
    - 数据分析
    - 质量检查
    - 洞察结论生成
---

# 莫斯科保卫战周报（编排器）

本 skill 只做编排——通过 `Agent` 工具按顺序调度 4 个独立子 agent，每个子 agent 拥有独立上下文空间，**不占用编排器的上下文预算**。编排器只负责：启动 sub-agent → 校验产物 → 进入下一步。指标口径、SQL 细节、报告格式、失败阈值都在子 agent 的 `agents/<name>.md` 里，本文件不重复。

## 唤醒关键词

- 莫斯科保卫战周报 / 保卫战周报 / 莫斯科周报
- 周报制作 / 周报数据整理 / 莫斯科数据整理
- 更新 MMDD-MMDD 的周报数据

## 目录布局

```
moscow-defense-weekly-biz/
├── SKILL.md                    # 本编排器
├── agents/                     # 4 个独立子 agent 定义（Agent 工具调度入口）
│   ├── 代码生成.md
│   ├── 数据分析.md
│   ├── 质量检查.md
│   └── 洞察结论生成.md
├── scripts/                    # SQL 脚本 + Python 工具（由 agents 调用）
│   ├── 00_check_partition.sql
│   ├── 01_kpi_achievement.sql
│   ├── 02_overall_funnel.sql
│   ├── 03_dim_funnel_duan_scene_source.sql
│   ├── 04_dim_funnel_asset_category.sql
│   ├── 05_weekly_trend.sql
│   ├── 06_monthly_trend.sql
│   ├── 07_daily_metrics.sql
│   ├── gen_report.py
│   ├── supp1_traffic_payment_structure.sql
│   ├── supp2_shangxiang_upgrade.sql
│   ├── supp3_guan_penetration.sql
│   └── supp4_xinmei_xinke.sql
├── references/                 # 业务规则真源 + 跨步骤产物契约
│   ├── weekly-report-requirements.md  # 周报分析要求与话术规范
│   ├── chart_config.md                # 图表格式规范
│   ├── upload_template.py             # 飞书写入模板
│   └── validate_data.py               # 数据校验脚本
└── assets/
    ├── 样例数据周报.pdf                 # 报告样例参考
    └── 莫斯科保卫战周报补充数据格式.xlsx  # 分业务格式规范
```

产物落 `~/Downloads/msk_weekly_raw/${week_end}/`，文件名见各 agent。

---

## 参数确认

开始前确认以下参数（用户未指定时，默认取上周完整周期）：

| 参数 | 说明 | 默认值 |
|------|------|------|
| `week_end` | 本周结束日（周日），如 `2026-06-28` | 上周日 |
| `week_start` | 本周开始日（周一），如 `2026-06-22` | 上周一 |

时间周期规则：周一–周日为一个完整周期，数据截止至上周完整周期（来自 `references/weekly-report-requirements.md`）。

---

## 流水线契约

### 调度机制

每个步骤通过 **`Agent` 工具** 调度为一个独立子 agent。子 agent 拥有独立上下文空间，**不占用编排器的上下文预算**。编排器只负责：启动子 agent → 校验产物 → 进入下一步。每一步的业务逻辑、SQL/分析/校验/写文档细节、失败处理由对应 `agents/<name>.md` 定义。

**编排器执行时必须严格遵守：**

1. **串行执行**：每一步必须等上一步产物落盘后再启动下一步，**不要跨步并发**。Step 1 内部的多 SQL 可在 sub-agent 内并行。
2. **Agent 隔离**：每一步通过 `Agent` 工具启动，prompt 模板见下文，子 agent 自己 Read 对应 `agents/<name>.md` 并执行。
3. **产物校验**：每步完成后，编排器在主上下文跑一段简短 bash 验证文件存在 + 非空，通过后才进下一步。
4. **失败即停**：任一步失败（Agent 返回错误 / 产物缺失 / 硬失败），编排器立即停止，不跳过、不静默重试。
5. **日期参数**：`week_end` / `week_start` 由用户指定或默认上周完整周期。

### 第一步：代码生成

**Agent 调用：**
```
Agent tool:
  description: "Step 1 代码生成 - 分区校验 + 并行取数"
  prompt: "week_end = ${week_end}
    week_start = ${week_start}
    你的 agent 定义文件路径: /Users/zhongmengting/.claude/skills/moscow-defense-weekly-biz/agents/代码生成.md
    请完整 Read 该文件并严格执行其中的所有指令。"
```

**产物校验**（编排器逐项检查，缺一个即停）：
```bash
DIR=~/Downloads/msk_weekly_raw/${week_end}
for f in 01_kpi.csv 02_funnel.csv 03_dim_dss.csv 04_dim_ac.csv \
         05_trend.csv 06_monthly_trend.csv 07_daily.csv \
         supp1.csv supp2.csv supp3.csv supp4.csv; do
  [ -s "$DIR/$f" ] || { echo "[FAIL] missing or empty: $f"; exit 1; }
done
echo "[OK] Step 1 取数完成"
```

子 agent 文件：[agents/代码生成.md](agents/代码生成.md)

### 第二步：数据分析

**前置条件**：第一步全部 CSV 落盘。

**Agent 调用：**
```
Agent tool:
  description: "Step 2 数据分析 - 漏斗框架 + 5 维度拆解"
  prompt: "week_end = ${week_end}
    week_start = ${week_start}
    你的 agent 定义文件路径: /Users/zhongmengting/.claude/skills/moscow-defense-weekly-biz/agents/数据分析.md
    请完整 Read 该文件并严格执行其中的所有指令。"
```

**产物校验：**
```bash
DIR=~/Downloads/msk_weekly_raw/${week_end}
[ -s "$DIR/analysis_result.json" ] || { echo "[FAIL] analysis_result.json 缺失"; exit 1; }
[ -s "$DIR/analysis_summary.md" ]  || { echo "[FAIL] analysis_summary.md 缺失"; exit 1; }
echo "[OK] Step 2 分析完成"
```

子 agent 文件：[agents/数据分析.md](agents/数据分析.md)

### 第三步：质量检查

**前置条件**：第二步 2 个产物全部落盘 + 第一步 CSV 仍在。

**Agent 调用：**
```
Agent tool:
  description: "Step 3 质量检查 - 数据/分析质量闸口"
  prompt: "week_end = ${week_end}
    week_start = ${week_start}
    你的 agent 定义文件路径: /Users/zhongmengting/.claude/skills/moscow-defense-weekly-biz/agents/质量检查.md
    请完整 Read 该文件并严格执行其中的所有指令。"
```

**产物校验**（编排器必须读取 JSON 的 `passed` 字段）：
```bash
DIR=~/Downloads/msk_weekly_raw/${week_end}
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
  prompt: "week_end = ${week_end}
    week_start = ${week_start}
    你的 agent 定义文件路径: /Users/zhongmengting/.claude/skills/moscow-defense-weekly-biz/agents/洞察结论生成.md
    请完整 Read 该文件并严格执行其中的所有指令。"
```

**产物校验：**
```bash
DIR=~/Downloads/msk_weekly_raw/${week_end}
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

| 步骤 | 子 agent | 输入（来自上一步） | 输出（落盘产物） | 闸口 |
|---|---|---|---|---|
| 1 | 代码生成 | week_end / week_start | `~/Downloads/msk_weekly_raw/${week_end}/*.csv`（11 个） | 全部存在且非空 |
| 2 | 数据分析 | 11 个 CSV | `analysis_result.json` + `analysis_summary.md` | 2 个文件非空 |
| 3 | 质量检查 | 11 CSV + analysis_result.json | `quality_check.json` | **passed=true 且 hard_failures 为空** |
| 4 | 洞察结论生成 | analysis_result + analysis_summary + quality_check | `feishu_doc.json`（含 doc_url + p2p_push） | 文档创建 + 推送至少 1 人成功 |

---

## 失败处理

- 前一步是后一步的硬依赖，不要静默重试或跳过。
- 子 agent 返回错误或产物缺失 → 编排器 stdout 打出失败步骤 + 缺失的文件路径，停在那里等人工。
- Step 1 分区未就绪且刷新失败 → 停，等人工。
- Step 3 `hard_failures` 非空 → 必须停，不进入 Step 4。
- Step 4 文档已建但 IM 推送失败 → 编排器仅重推 IM（复用已有 `doc_url`），**不要**回退到只发本地路径，更不要重建文档。

---

## 全局约定

- **凭证只走环境变量**：星河 `XINGHE_CLIENT_USER` / `XINGHE_CLIENT_SECRET` / `XINGHE_OA`，One-Service `ONESERVICE_OA` / `ONESERVICE_ACCESS_KEY`，任何脚本/SKILL 都不写明文。
- **数据源硬约束**：莫斯科归因走 `hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zhibiao_zmt_v2_di`，**禁用** `tmp_dws_msk_zmt_app_v2_di`（同维度名但数差 5–10%）。
- **飞书推送**默认发钟梦婷个人 P2P（`ou_5e572adca6deef8ef21c3b18dfade573`），不推群聊。lark-cli 1.0.43 P2P 必须用 `--user-id` 不是 `--chat-id`；`--content` 必须 inline JSON，不吃 `@file`。
- 默认中文输出。

---

## ❌/✅ 速查

| ❌ Don't | ✅ Do |
|---|---|
| 编排器自己写 SQL / 跑分析 / 画图（挤占主流程上下文） | 编排器只调 `Agent` 工具起子 agent，不自己做业务逻辑 |
| 跨步骤并发 4 个 agent | 严格串行；Step 1 内部 SQL 才可并发 |
| 跳过分区检查直接取数 | Step 1 先跑 `00_check_partition.sql`，就绪才取数 |
| Step 3 `passed=false` 或 `hard_failures` 非空时进 Step 4 | 停止，等人工介入 |
| Step 4 文档失败回退发本地 md 路径 | 文档失败 = Step 4 失败；路径不能给业务方 |
| Step 4 IM 推送失败时把文档重建一遍 | 复用上次 doc_url，只重推 IM |
| 飞书推送改群聊 | P2P 是硬规则，除非用户在对话中明确说推群 |
| 脚本里硬编码凭证 | 凭证只走 `~/.zshrc` 环境变量 |
| 子 agent 即兴重写 SQL 模板 | 直接复用 `scripts/` 下已业务验证的 SQL |
| 用错归因数据源 `tmp_dws_msk_zmt_app_v2_di` | 用 `tmp_dws_msk_zhibiao_zmt_v2_di` |

---

## 历史产出记录

| 日期 | 周报区间 | 飞书表格 | 备注 |
|------|---------|---------|------|
| 20260608 | 0601-0607 | https://zhuanspirit.feishu.cn/sheets/HsL6sUaUuhcbhWtKSplcSym4npg | 首次全链路生成 |
| 20260616 | 0608-0614 | https://zhuanspirit.feishu.cn/docx/OcGkdneZTo0Pq5x0zflcPuGOnne | 首次使用 4 步流水线；01_kpi 拆 3 查询规避 UNION ALL |
| 20260622 | 0615-0621 | https://zhuanspirit.feishu.cn/docx/SxGodrEo8oDoDVxaEzOcQfAonOP | supp3 超时需单独重跑；XML 修正 tableRow→tr/th/td |
| 20260629 | 0622-0628 | https://zhuanspirit.feishu.cn/docx/MYlKdOfs0oxiYhxrkVpcpa5qn3g | 01_kpi Spark NPE 持续；改造前最后一版串读 sub-skill |

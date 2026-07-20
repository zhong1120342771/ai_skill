---
name: 转转用户分层
description: "转转站内整体用户分层的全流程编排器 Skill。基于增强版 RFM（R/F/M/L/A/P 六维）对全站活跃用户进行价值分层，产出分层方案报告（整体分布 + 各层特征 + 运营策略 + SQL 附录），写入飞书文档并推送给钟梦婷。当用户说「跑用户分层」「做用户分层报告」「用户分层结果」「出用户分层方案」「帮我分层一下用户」「运营分层」「RFM 分层」时必须调用本 skill，不要走通用 claude-data-analysis。"
metadata:
  type: orchestrator
  scheme_doc: "https://zhuanspirit.feishu.cn/docx/VkwQdxTTTobZ5xxHiLUcBV7rnpf"
  pipeline:
    - 代码生成
    - 数据分析
    - 质量检查
    - 报告生成
---

# 转转用户分层（编排器）

转转站内整体用户分层的串行流水线。本 Skill 只做编排——按顺序调度 4 个子 skill，前一步产物落盘后才进下一步；指标口径、字段定义、评分阈值都在子 SKILL.md 与 References/ 里，本文件不重复。

## 何时使用

"跑用户分层""出分层报告""按 RFM 分层用户""用户价值分层"，以及需要圈人运营时，都走本 skill。临时的单次 SQL 圈人走通用 claude-data-analysis。

## 目录布局

```
转转用户分层agent/
├── SKILL.md                    # 本编排器
├── References/
│   ├── 分层方案说明.md           # 业务规则真源（与飞书文档 VkwQdxTTTobZ5xxHiLUcBV7rnpf 同步）
│   └── output-schemas.md       # 各步骤产物字段契约
├── Scripts/
│   ├── rfmlap_score_query.sql  # Step 1 — 用户六维评分 SQL 模板
│   └── segment_label_query.sql # Step 1 — 分层标签打标 SQL 模板
├── scripts/
│   ├── qa_check.py             # Step 3 质量闸口（固化脚本）
│   └── feishu_publish.py       # Step 4 飞书文档创建 + IM 推送（固化脚本）
├── assets/
│   └── report-template.md     # 报告骨架
└── sub-skills/
    ├── 代码生成/SKILL.md        # Step 1
    ├── 数据分析/SKILL.md        # Step 2
    ├── 质量检查/SKILL.md        # Step 3
    └── 报告生成/SKILL.md       # Step 4
```

产物落 `~/.claude/` 下的 `data_storage/`、`analysis_reports/`、`final_report/`。

## 流水线契约

每一步必须等上一步产物落盘后再进入下一步，**不要并发**。

| 步骤 | 子 skill | 关键输入 | 关键产物 |
|---|---|---|---|
| 1 | [代码生成](sub-skills/代码生成/SKILL.md) | dt | `data_storage/user_segments_${dt}.csv`（每用户六维分+层级） + `data_storage/segment_distribution_${dt}.csv`（层级汇总） |
| 2 | [数据分析](sub-skills/数据分析/SKILL.md) | Step 1 产物 | `analysis_reports/seg_analysis_${dt}.json` + `analysis_reports/seg_analysis_${dt}.summary.md` |
| 3 | [质量检查](sub-skills/质量检查/SKILL.md) | Step 1+2 产物 | `analysis_reports/quality_check_seg_${dt}.json`（`passed=false` 即停） |
| 4 | [报告生成](sub-skills/报告生成/SKILL.md) | Step 2+3 产物 | `final_report/用户分层报告_${dt}.md` + 飞书 docx + P2P 推送 |

通过 Task 工具调度子 skill 对应的 agent；日期参数 `dt` 默认 t-1，可由用户覆盖。

## 失败处理

- 前一步是后一步的硬依赖，不要静默重试或跳过。
- 步骤 3 `hard_failures` 非空 → 必须停，不进入步骤 4。
- 步骤 4 文档已建但 IM 推送失败 → 仅重试推送，复用 `doc_url`，不回退只发本地路径。

## 全局约定

- 默认中文输出。
- **凭证只走环境变量**：星河 `XINGHE_CLIENT_USER` / `XINGHE_CLIENT_SECRET`，One-Service `ONESERVICE_OA` / `ONESERVICE_ACCESS_KEY`；脚本不硬编码。
- **飞书推送默认只发钟梦婷 P2P**：`ou_5e572adca6deef8ef21c3b18dfade573`，发送方 `--as bot`（菜的飞书cli）。如需加人，覆盖 `LARK_SEG_RECEIVERS` 环境变量。
- 业务规则真源在 `References/分层方案说明.md`，与飞书文档 `VkwQdxTTTobZ5xxHiLUcBV7rnpf` 同步。飞书文档先变 → References 同步 → 再改 sub-skill。
- 可视化必须显式设置中文字体（`PingFang SC` / `Heiti SC` / `Arial Unicode MS`），避免方块乱码。

## ❌/✅ 速查

| ❌ Don't | ✅ Do |
|---|---|
| sub-agent 即兴写 QA Python | 调 `scripts/qa_check.py` |
| sub-agent 即兴写飞书发布 | 调 `scripts/feishu_publish.py` |
| 把评分阈值写死在 SQL 里 | 阈值统一在 `References/分层方案说明.md` 和 `Scripts/` 模板里 |
| 步骤 4 失败回退发本地 md | 失败 = Step 4 失败；路径不能给业务方 |
| IM 推送失败时重建文档 | 复用 doc_url，只重推 IM |
| 把推送改成群聊 | P2P 是硬规则；如需改，用户显式说 |
| 凭证写进脚本/SKILL | 凭证只走 `lark-cli config` 与 `~/.zshrc` env var |

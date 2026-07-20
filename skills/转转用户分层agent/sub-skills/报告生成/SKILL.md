---
name: 用户分层-报告生成
description: 转转用户分层流水线第 4 步——生成完整分层报告并发布到飞书。报告包含分层方案说明、分布数据、各层特征、运营策略、特征人群、附录SQL脚本，写入飞书文档并推送给钟梦婷。
metadata:
  type: sub-skill
  parent: 转转用户分层
  step: 4
  inputs:
    - analysis_reports/seg_analysis_${dt}.json
    - analysis_reports/seg_analysis_${dt}.summary.md
    - analysis_reports/quality_check_seg_${dt}.json
  outputs:
    - final_report/用户分层报告_${dt}.md
    - 飞书文档(docx) — 标题「转转用户分层报告 · ${dt}」
    - 飞书 P2P 推送 — 发到钟梦婷个人会话
---

# 用户分层-报告生成

## 基础与定位

本 skill 整合 `report-writer` 叙事能力，把分析数据翻译为业务可读的完整分层报告，写入飞书文档并推送。

## 前置阅读（每次执行前必读）

1. **[../../References/分层方案说明.md](../../References/分层方案说明.md)** — 方案框架、评分规则、运营策略，报告第一章直接引用
2. **[../../analysis_reports/seg_analysis_${dt}.summary.md](../../analysis_reports/)** — 先读摘要，再决定强调哪些数字
3. **[../../analysis_reports/quality_check_seg_${dt}.json](../../analysis_reports/)** — 有 warn 的地方要在报告中标⚠
4. **[../../assets/report-template.md](../../assets/report-template.md)** — 报告骨架，按模板填充

## 报告结构（严格按此顺序）

```
一、分层方案说明（来自 References，概括介绍六维框架和分层定义）
二、分层结果数据
    2.1 整体分布（5层用户数 + 占比 + 均分表格 + 关键结论）
    2.2 各层特征画像（六维均值对比表，L5 vs L4 vs L3 vs L2 vs L1）
    2.3 9 个特征人群规模（人数 + 占比 + 主要特征）
三、运营策略（每层一段，对应方案说明中的策略）
四、附录
    SQL 脚本一：RFMLAP 评分取数脚本（~/skills/转转用户分层agent/Scripts/rfmlap_score_query.sql）
    SQL 脚本二：价格敏感性指标脚本（~/.claude/scripts/price_sensitivity_v1.sql）
    数据说明：quality_check warn 项
```

## 写作风格

- 像分析师写给运营方，不是技术文档
- 每条结论带具体数字（"L5 高价值用户 X 万，占比 X.X%，是核心投入重点"）
- 运营策略要有**可操作的具体建议**：圈人条件怎么写、投什么、控频怎么设
- 机会点带"待验证"标注（单次数据不下因果结论）
- 如有 quality warn，对应数字末尾加 ⚠

## 飞书发布（必做）

**直接调固化脚本：**

```bash
# 默认只推钟梦婷（P2P）
LARK_SEG_RECEIVERS="ou_5e572adca6deef8ef21c3b18dfade573" \
  python ~/.claude/skills/转转用户分层agent/scripts/feishu_publish.py --dt ${dt}
```

如需加收件人，覆盖 `LARK_SEG_RECEIVERS`（空格分隔多个 open_id），不改脚本和 SKILL 默认值。

### sub-agent 需自己产出两个文件（脚本不代写正文）

**`final_report/用户分层报告_${dt}.md`**：按 `../../assets/report-template.md` 骨架填充。

**`final_report/seg_message_${dt}.txt`**：飞书 P2P 推文，固定格式：

```
【${dt} 转转用户分层报告】
整体分层：L5 X万(X%) | L4 X万(X%) | L3 X万(X%) | L2 X万(X%) | L1 X万(X%)
高价值用户（L4+L5）：X万，占 X%，是核心投入对象
关键特征人群：搜而不买 X万 | 加购未付 X万 | 价值回流 X万
完整文档：${doc_url}
```

要点：数字用万（保留一位小数）；链接直接写 URL，不用 markdown 格式；`doc_url` 在建文档后回填。

## 失败处理

- 文档创建失败 → 退出码 3，不回退发本地路径
- 文档建好但 IM 推送失败 → 退出码 2，用 `feishu_publish.py --skip-doc` 只重推
- 切勿把推送目标改为群聊，除非用户当次对话里显式说"推到 XX 群"

## 不要做的事

- 不要重新算指标（分析 JSON 中已算好）
- 不要硬编码数字（人数/占比全部从 seg_analysis JSON 读）
- SQL 脚本内容放附录，正文不贴长代码

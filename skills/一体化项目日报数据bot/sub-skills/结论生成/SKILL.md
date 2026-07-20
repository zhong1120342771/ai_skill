---
name: 一体化日报-结论生成
description: 一体化项目日报流水线第 4 步——把指标数据翻译为业务结论文档与可视化，并飞书机器人推送到一体化项目群。当用户说"出今天的一体化日报""推一下今天数据""按取数说明出结论"，或编排器完成质量检查后需要产出 final_report 时使用本 skill。整合 report-writer 与 visualization-specialist，按 References 的产出格式严格输出。
metadata:
  type: sub-skill
  parent: 一体化项目日报数据bot
  step: 4
  inputs:
    - analysis_reports/metrics_yiti_${dt}.json
    - analysis_reports/metrics_yiti_${dt}.summary.md
    - analysis_reports/quality_check_yiti_${dt}.json
  outputs:
    - final_report/一体化日报_${dt}.md
    - visualizations/${dt}/yiti_monthly.png
    - visualizations/${dt}/yiti_weekly.png
    - visualizations/${dt}/yiti_daily.png
    - 飞书群推送（一体化项目群 oc_69bfbe82133fedc9592bc18c3307aa51）
    - final_report/feishu_push_${dt}.json
---

# 一体化日报-结论生成

## 定位

本 skill 在 [`report-writer`](~/.claude/agents/report-writer.md) + [`visualization-specialist`](~/.claude/agents/visualization-specialist.md) 之上做窄化——按 References 的产出格式输出 7 项指标的 t-1 日报，含 3 张趋势图（月/周/日）+ 1 张汇总表，飞书机器人推送到一体化项目群（chat_id `oc_69bfbe82133fedc9592bc18c3307aa51`）。

## 前置阅读

1. **[../../References/取数与产出说明.md](../../References/取数与产出说明.md)** — 业务真源，**报告格式严格对应这里的「产出形式」章节**。
2. **[../../analysis_reports/metrics_yiti_${dt}.summary.md](../../analysis_reports/)** — 上游摘要。
3. **[../../analysis_reports/quality_check_yiti_${dt}.json](../../analysis_reports/)** — 质量结果，warn 要在报告中带出来。

## 报告结构

业务方点开先看「文字结论」，所以**结论永远放最前**。完整骨架见 [`../../assets/report-template.md`](../../assets/report-template.md)。

## 必产出的可视化

直接调固化脚本：

```bash
python ~/.claude/skills/一体化项目日报数据bot/scripts/render_charts.py --dt ${dt}
```

3 张图：

| 图 | 说明 |
|---|---|
| `yiti_monthly.png` | 7 项指标 月维度趋势图（月均），从 2026-01 起，最新一月标注环比上月 |
| `yiti_weekly.png` | 7 项指标 8 周维度趋势图（周均，自然周周一起），最新一周标注环比上周 |
| `yiti_daily.png` | 7 项指标 30 日维度趋势图（日值），最新一日标注环比上一日 |

中文字体、配色、标注都已固化在 `render_charts.py`。要改样式 → 改脚本，不要在 sub-agent 里现写。

### 并行口径

`render_charts.py` 内部把 **3 张图改成 ProcessPool 并行**（默认 `--workers=3`）：
- 用 multiprocessing 不用 threads，是因为 matplotlib 的 pyplot 有全局 figure manager，多线程下并发 `savefig` 会偶发互踩。
- 串行调试：加 `--serial` 退回顺序执行。

## 飞书推送（必做）

```bash
# 默认推送一体化项目群（chat_id），无需显式配置：
python ~/.claude/skills/一体化项目日报数据bot/scripts/feishu_publish.py --dt ${dt}

# 临时切收件人：群 oc_xxx → --chat-id；个人 ou_xxx → --user-id；多个空格分隔
LARK_YITI_RECEIVERS="oc_69bfbe82133fedc9592bc18c3307aa51 ou_5e572adca6deef8ef21c3b18dfade573" \
  python ~/.claude/skills/一体化项目日报数据bot/scripts/feishu_publish.py --dt ${dt}
```

脚本做 3 件事：

1. 把 3 张趋势图（月 / 周 / 日）上传飞书拿 image_key（**身份 `--as bot`**）。
2. 拼接 markdown 富文本消息（结论 4 段 + 图1 + 图2 + 图3 + 表1）。
3. 对 `$LARK_YITI_RECEIVERS` 中每个 id 单发：`oc_*` 用 `--chat-id` 推群，`ou_*` 用 `--user-id` 推 P2P，**身份 `--as bot`**（用户看到发送方是「菜的飞书cli」机器人）。

### 消息格式

```
【YYYY-MM-DD 一体化数据日报】

【结论】
- 【同城订单&同城订单占比】同城订单 X（环比 ↑/↓Y%）；占比 X.X%（环比 ↑/↓Y%）
- 【线下线索量&线索量转化】线下线索 X（环比 ↑/↓Y%）；线索转化 X（环比 ↑/↓Y%）
- 【同售订单量&同售动销率】（三层，子层换行缩进展示）
    整体：同售订单 X（环比 ↑/↓Y%）；动销率 X.X%（环比 ↑/↓Y%）；
    小店&pro店：pro店 订单 X（环比 …）/动销率 …；小店 订单 X（环比 …）/动销率 …；
    城市拆解（小店同售）：一体化覆盖城市(小店) 订单 X（环比 …）/动销率 …；对照城市(重庆&西安) 订单 X（环比 …）/动销率 …；其他城市 订单 X（环比 …）/动销率 …
- 【小时达订单量】X（环比 ↑/↓Y%）

图1：从 2026-01-01 起 7 项指标月维度趋势
[image_key 月趋势图]

图2：过去 8 周 7 项指标周维度趋势
[image_key 周趋势图]

图3：过去 30 日 7 项指标日维度趋势
[image_key 日趋势图]

表1：t-1 当日 7 项指标汇总
| 指标 | t-1 值 | 环比 | 7 日均值 | 月均 |
|---|---|---|---|---|
...
```

### 凭证

- 发送方应用：`菜的飞书cli`，appId `cli_aa8e16c998b89cc5`，appSecret 由 `lark-cli config` 在本机维护。
- 跑前 `lark-cli auth status` 确认 appId 一致。

## 失败处理

- 推送全部失败 → 退出码 2，`feishu_publish.py --skip-image-upload` 仅重试 IM。
- 不要回退到只发本地路径。

## 写作风格

- 像分析师写给业务方，少用"综上所述"，多给具体数字。
- 每个结论带量级：「同城订单 1234 单，环比 +5.2%」，不要「同城订单表现良好」。
- 质量 warn 必须带出：标注「⚠ 数据待复核」。

## 不要做的事

- 不要重新算指标（直接读 metrics JSON）。
- 不要无视 quality warn。
- 不要在脚本/SKILL 里写明文 appSecret / 星河密码。

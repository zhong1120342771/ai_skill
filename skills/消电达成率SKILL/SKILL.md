---
name: 消电达成率SKILL
description: 转转 APP 消费电子（消电）目标指标达成率评估流水线。给一份消电分维度明细 CSV（tag_01/wd/dt + exp/detail/order/pay/uv_all 列）和一批目标指标（含目标提升%），产出四件事：①逐指标算达成率（实际提升=(末月-首月)/首月，达标=实际提升≥目标）②每指标 H1 逐月趋势图（达标绿/未达标红+目标虚线）③把结果整表写进飞书文档达成率表格（图作为图片实体嵌进单元格）④对未达标指标做漏斗归因并配图写进"未达标指标归因"章节。凡涉及"消电/消费电子达成率、H1目标达成、提袋率/曝光渗透率/商详渗透率达标情况、指标达没达标、达成率评估、未达标归因、把达成率写进飞书文档"等，都用本 skill。不要临时手搓口径——达成率算法和各指标分子分母口径都在本 skill 固定好了。
---

# 消电达成率评估流水线

把"消电目标指标达没达标 + 为什么没达标"这件事固化成可复跑的四步流水线。核心价值是**口径不用每次重推**：达成率算法、17 个指标的分子/分母、漏斗归因链路都已写死在 `references/calibers.md` 里，照用即可。

## 什么时候用

用户说"评估消电达成率""H1 这些指标达没达标""把达成率写进飞书文档""帮我看未达标指标为什么没达标"——就是它。既能只算达成率出表，也能一路做到归因配图写文档，按用户要到哪一步做到哪一步。

## 关键红线（先读，别踩）

- **达成率口径固定**：实际提升 = (末月比率 − 首月比率) / 首月比率，达标 = 实际提升 ≥ 目标提升。比率是"月内先加总分子分母再相除"。细节和每个指标的 num/den 见 `references/calibers.md`，**不要自己按行业惯例另编**。
- **目标值/当前值/期望值是用户输入，不是我生成的**。缺了就问用户或从底表实测，别默认填一个"看起来合理"的数（全局规则：不拿行业标准当用户输入）。
- **两个数据源分母不同不能混算**：明细 CSV 分母是 `uv_all`（消电大盘），底表是 `matched_dau_uv`（全站DAU）。跨源只横比曝光UV 增长率，涉及渗透率必须同源，产出加脚注。
- **数据可靠性先查**：某月曝光腰斩但后端没跌 = 埋点回刷不全，剔除该月。7 月不完整月默认排除。
- **对外文字过 humanizer 去 AI 味，但绝不改数字/口径/结论**。北极星"dau-净支付pv转化率"若出现用 `X.XXX%` 三位百分比。
- **飞书图必须是图片实体嵌在对应结论/单元格旁**，不许只写图名、不许全堆文末。`media-insert --file` 只吃 cwd 相对路径。

## 输入

1. **明细 CSV**：列含 `tag_01, wd, dt` + 指标用到的分子分母列（典型 `exp_pv,exp_uv,detail_pv,detail_uv,order_pv,order_uv,pay_pv,uv_all`）。`dt` 支持 `YYYY/M/D` 或 `YYYY-MM-DD`。用户通常直接给一个 Downloads 里的 CSV 路径。
2. **指标配置 JSON**：每个指标的 name/tag/wd/num/den/target/is_percent/lead。样例见 `references/metrics_config.example.json`（本轮 17 指标真实值）。**新一期评估先跟用户确认 target/current/expected 有没有变**，别沿用样例里的旧值当事实。
3. （写文档时）飞书文档 token + 达成率表格的 block_id。

## 四步流程

先在一个干净工作目录里跑（如 `~/Downloads/xd_<期次>_analysis/`）。

### Step 1 — 算达成率
```bash
python scripts/compute_achievement.py \
  --csv <明细.csv> --metrics <指标配置.json> --out result.json \
  --start-month 1 --end-month 6
```
产出 `result.json`（每指标含 6 个月比率 vals、actual 实际提升、meet 达标与否）+ 控制台达标清单。**先把这份清单给用户核对**再往下。

### Step 2 — 出趋势图
```bash
python scripts/make_charts.py --result result.json --out-dir ./charts
```
每指标一张 `chart_NN.png`，序号对齐 result.json。达标绿/未达标红，虚线=首月×(1+目标)。

### Step 3 — 写进飞书达成率表格
```bash
python scripts/fill_doc_table.py \
  --doc <doc_token> --table-block <表格block_id> \
  --result result.json --charts-dir ./charts
```
整表重建：前置业务列（方向/负责人/目标提升/当前值/期望值）取自 lead，加上末月值、最高月值、实际提升、趋势图（图片实体嵌进单元格）、达成情况（达标绿✅/未达标红❌）。脚本已封装"传图→拼表→block_replace→删临时块"，勿改顺序。表格 block_id 用 `lark-cli docs +fetch --api-version v2 --detail with-ids` 拿。

### Step 4 — 未达标归因（按需）
读 `references/attribution_playbook.md`。对未达标指标沿漏斗链拆解，判断卡前端（曝光渗透）还是后端（下单/支付），再按品类/场景/用户来源/业务下钻：
```bash
python scripts/drilldown.py --csv <明细.csv> --tasks tasks.json --first 1 --last 6
```
明细缺的维度（手表/耳机、业务对比）走星河底表补（`xinghe_client` 库，引擎5=Hive）。归因结论写进飞书"未达标指标归因"章节，每条配图插在正文锚点旁。文字先过 humanizer。

## 脚本清单

| 脚本 | 作用 |
|------|------|
| `scripts/compute_achievement.py` | 明细+配置 → result.json（达成率主计算） |
| `scripts/make_charts.py` | result.json → 每指标逐月趋势图 |
| `scripts/fill_doc_table.py` | result.json+图 → 飞书达成率表格整表写入 |
| `scripts/drilldown.py` | 漏斗拆解/维度下钻/曝光增长对比（归因用，含可调用函数库） |

## 参考文件

- `references/calibers.md` — 口径字典（达成率算法、各指标 num/den、漏斗链路、分母陷阱、数据可靠性坑）。**动手前必读。**
- `references/metrics_config.example.json` — 17 指标配置样例（真实口径，复制改）。
- `references/attribution_playbook.md` — 未达标归因叙事骨架 + tasks.json 结构 + 底表补数 + 插图写法。

## 依赖

- Python3 + matplotlib（PingFang 中文字体，macOS 自带）。
- `lark-cli`（v2 API，已登录 user 身份）写飞书文档。
- 星河 `xinghe_client`（`~/.claude/skills/xinghe-data/scripts/`）补底表，凭证走环境变量。

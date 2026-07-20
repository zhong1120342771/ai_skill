---
name: 一体化项目
version: 1.0.0
description: "线上线下一体化项目语料汇总：扫描主文档及关联子文档，识别新增/变更内容，总结关键信息并推送飞书。触发词：一体化、一体化项目、一体化周报、一体化数据。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# 线上线下一体化项目

**CRITICAL — 开始前 MUST 先用 Read 工具读取以下文件：**
1. [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md) — 认证、权限处理
2. [`../lark-doc/SKILL.md`](../lark-doc/SKILL.md) — 飞书文档操作
3. [`../lark-doc/references/lark-doc-fetch.md`](../lark-doc/references/lark-doc-fetch.md) — 文档读取
4. [`../lark-doc/references/lark-doc-update.md`](../lark-doc/references/lark-doc-update.md) — 文档更新
5. [`../lark-doc/references/lark-doc-xml.md`](../lark-doc/references/lark-doc-xml.md) — XML 语法规则
6. [`../lark-im/SKILL.md`](../lark-im/SKILL.md) — 飞书消息推送

## 适用场景

- "一体化项目有什么新进展"
- "帮我扫描一体化文档"
- "推送今天的一体化周报到飞书"
- 每日工作日上午 10 点自动推送（由 cron 触发）

## 文档体系

### 主文档：一体化项目语料汇总

- **飞书 URL**: `https://zhuanspirit.feishu.cn/wiki/V10oweRF9iuzJskjaXscxml5nMf`
- **Wiki Token**: `V10oweRF9iuzJskjaXscxml5nMf`
- **Doc Token**: `NKwodVIUIoIK3exUHDucZVlEnnh`
- **Space ID**: `7639643477596441545`

### 主文档章节结构

| 章节 | 标题 | block_id |
|------|------|----------|
| 1 | 2026 一体化数据周报持续更新 | `VKbzd6f0SoP5c1xAtX1c1m6Mnyb` |
| 2 | 20260424 一体化项目双城复盘--商分侧 | `JjjednKMxoQ2SlxZfTccwZSEnuc` |
| 3 | 20260326 线上线下一体化项目阶段性进展和待决策点对焦 | `UE3tdkxe6ozJWbxncD1cPh8Enue` |
| 4 | 一、项目介绍 | `HImdd0WALoVAeBxpKsVcw4hHnJh` |
| 5 | 二、双城试点阶段性项目数据 | `QHvodAKoUodfRAx3WlzceXL8nBg` |

### 关联子文档（由主文档引用）

| 文档 | Token | 说明 |
|------|-------|------|
| 线上线下一体化—周度表现 | `J533wLgH1ioz07knxjqcrwZKnMd` | 周度数据表现 |
| 一体化数据跟进—一期 | `UMyNwA44Kiz7O3kCcnHcvsx8nQc` | 一期数据跟进 |

## 项目背景

**线上线下一体化项目**：通看全国线上+线下货盘，分为三类：
- 线上在仓货盘（全国各中心仓）
- 门店同售货盘（全国各门店）
- 门店独占货盘

### 核心改动点（双城试点：成都、郑州）

1. **商品**：门店独占货盘日期从 18 天→3 天，双城门店取消自主定价，统一采用 CZC 定价
2. **中心仓**：同城用户提供小时达服务（同时支持免费快递），C 端有仓的独立表达
3. **门店商品**：同售后，同城小时达+C端独立门店表达+预约到店能力
4. **线上入口**：独立门店引导入口，用户可直接进入门店详情

### 预期价值

1. 中心仓商品同城强化表达+小时达 → 更高动销和转化
2. 门店同售商品强化表达+小时达 → 更高同售动销
3. 门店全链路强化表达 → 更高线下订单线索量和转化

### 双城试点关键数据

- 双城总共订单周日均 1599（线上 1253 + 线下 346）
- 同城商品提袋率高于大盘（0.05% vs 0.03%），3.6%曝光占比贡献 6.6%订单占比
- 门店同售动销增益预估未来可达 ~0.5%
- 线上导流线下效率：双城 0.173% vs 非双城 0.037%
- NPS：小时达 4.1 分 vs 线上非同售 4.0 分

### 待解决问题

1. 同城商品曝光不足，加强曝光后可进一步拉动动销
2. 计划扩展北京、深圳、（东莞），需解决库存问题：
   - 每新增一家门店需增加约 13 万采购额，180 店需 2340 万/月
   - 方案A：徐磊临时开额外货值 2-3 个月
   - 方案B：门店内部调整 OP 计划腾挪
3. 5 月更多数据后讨论全国覆盖：是否引入三方供应链、收益能否覆盖投入

## 工作流

### Step 1: 扫描主文档

```bash
lark-cli docs +fetch --api-version v2 --doc NKwodVIUIoIK3exUHDucZVlEnnh --scope outline --max-depth 3 --as user --format json
```

对比上次扫描结果，识别：
- 新增章节/段落
- 修订时间变化（`obj_edit_time`）
- 新增的引用文档链接

### Step 2: 扫描关联子文档

对每个关联子文档，用同样方式获取 outline 和最新修订时间，识别变更。

### Step 3: 读取新增/变更内容

对识别到的变更部分，用 `--scope section` 或 `--scope keyword` 获取详细内容。

### Step 4: 生成总结

汇总所有变更，按以下结构组织：
1. 新增内容摘要
2. 更新的数据/指标
3. 关键决策点
4. 待办事项

### Step 5: 推送到飞书

```bash
lark-cli im +messages-send \
  --user-id "ou_5e572adca6deef8ef21c3b18dfade573" \
  --msg-type post \
  --title "一体化项目日报 - YYYY-MM-DD" \
  --content @/tmp/yitihua_report.json
```

接收人：钟梦婷（open_id: `ou_5e572adca6deef8ef21c3b18dfade573`）

### 每日自动扫描流程

由 cron 定时任务在工作日 9:57 触发，执行上述 Step 1-5。

首次扫描或无法对比时，直接汇总当前文档全部内容。

## 参考

- [lark-shared](../lark-shared/SKILL.md) — 认证、权限
- [lark-doc](../lark-doc/SKILL.md) — 飞书文档操作
- [lark-doc-fetch](../lark-doc/references/lark-doc-fetch.md) — 文档读取
- [lark-doc-update](../lark-doc/references/lark-doc-update.md) — 文档更新
- [lark-im](../lark-im/SKILL.md) — 飞书消息推送

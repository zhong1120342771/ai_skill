---
name: 转转核心导购链路分析
description: "转转 App 核心导购链路（曝光→点击→商详→收银台→支付）全链路转化分析。按 5 个导购来源（搜索/feed/收藏/购物车/足迹）× 4 类业务（消费电子/兴趣/二奢/其他）拆解每一环节的 UV 与转化率，产出完整链路表 + 分业务×来源的曝光→点击、曝光→支付对比柱状图，写入飞书文档并 P2P 推送。当用户说「导购链路分析」「核心导购链路」「导购流程分析」「曝光到支付链路」「分来源分业务链路转化」「5 来源链路」「导购转化漏斗」时调用本 skill。埋点点位映射（infoId 如何解析）、来源识别的 actiontype+region 规则、场景归因 first_from/ori_firstfrom 口径、购物车时序链路都固化在本 skill 内。"
metadata:
  type: analysis-methodology
  domain: 转转App导购转化
---

# 转转核心导购链路分析

分析转转 App「导购」环节的全链路转化：从商品**曝光**，到用户**点击**，到进入**商详**，到**收银台**下单，到最终**支付**。核心是把这条链路按 **5 个导购来源 × 4 类业务** 两个维度拆开，看每个来源在每类业务上的分环节转化效率，定位「高曝光低转化」和「小流量高转化」的结构性差异。

这是一个**方法论 + 脚本 + 口径**型 skill，不是自动编排器。执行时按本文档的步骤顺序手动跑脚本、拼表、出图、写飞书。所有埋点点位映射和口径都在下面「口径真源」章节，改口径只改这一处。

## 唤醒关键词

- 导购流程分析 / 导购链路 / 导购转化漏斗
- 曝光到支付链路 / 曝光→点击→商详→收银台→支付
- 分来源分业务链路转化 / 5 来源链路 / 5 来源 × 分业务

## 分析对象与两个拆解维度

**链路 5 环节**（UV 口径，token 去重）：曝光 UV → 点击 UV → 商详 UV → 收银台 UV → 支付 UV。

**维度一：5 个导购来源**（用户从哪个入口看到/点到商品）
搜索、feed（首页推荐流）、收藏、购物车（加购）、足迹。

**维度二：4 类业务**（商品属于哪个业务）
消费电子、兴趣、二奢、其他。业务由 `info_id` 关联商品维表判定，规则见口径真源。

输出矩阵 = 5 来源 × 4 业务 = 20 条明细行，每行给出 5 个环节 UV + 4 段环节转化率 + 1 个曝光→支付整体转化率。

## 执行流程

数据源为星河（Xinghe）StarRocks/Hive，通过 `xinghe-data` skill 的 `xinghe_client.py` 跑 SQL。凭证走环境变量 `XINGHE_*`，绝不写进脚本或输出。

### Step 1 — 确定取数日期
默认 `dt = t-1`。大促期或指定日按用户给的日期。**日期是关键事实性输入，用户没指定就用 t-1，不要臆测某个促销日。**

### Step 2 — 跑三段取数（A 曝光 / B 点击 / C 商详·收银台·支付）
```bash
python3 scripts/run_full_chain.py 2026-08-11   # 不传参默认 t-1
```
脚本一次性提交 3 个 SQL job（A/B/C），把 job 信息写到 `/tmp/full5_jobs.json`。三段口径：
- **A 曝光**：`explosureGoods` 埋点，`goodsList` explode 出 `info_id`，按 5 来源的 actiontype+region 打标。
- **B 点击**：`zpmclick` 埋点，取 `datapool['infoId']`，按 region 打标 5 来源。
- **C 商详/收银台/支付**：走交易 dm 表场景归因（4 来源：搜索/feed/收藏/足迹）。商详用 `first_from`，收银台/支付用 `ori_firstfrom`。

轮询 job 结果拿到三段结果 JSON（A/B/C）。

### Step 3 — 购物车时序链路补数
购物车的 dm 交易表**没有 first_from 来源字段**，无法用场景归因。改走**时序链路**：以购物车曝光时间戳为锚点，判定其后是否发生商详/收银台/支付。
```bash
# scripts/cart_sequential_chain.sql，把 dt 替换成目标日期后在星河跑
```
产出购物车 4 业务的商详/收银台/支付 UV，填进 `assemble_chain.py` 的 `CART` 字典。

### Step 4 — 拼装完整链路表
把 A/B/C 三段结果 + 购物车时序结果填进 `assemble_chain.py`（脚本内 A/B/C_raw/CART 为上一次运行的实测值，重跑需用新数据替换），生成 `/tmp/full5_chain.csv`：
```bash
python3 scripts/assemble_chain.py
```
输出 25 行（20 明细 + 5 来源小计），列：`来源,业务,曝光UV,点击UV,商详UV,收银台UV,支付UV,曝光→点击,点击→商详,商详→收银台,收银台→支付,曝光→支付`。

### Step 5 — 生成表格 HTML（写飞书用）
```bash
python3 scripts/gen_table.py     # 读 full5_chain.csv → /tmp/table5.html
```
`gen_table.py` 默认**剔除小计行**，只保留 20 条明细；纯整数列加千分位；转化率保持百分比原样。若需保留小计，删掉脚本里 `if r[1]=='小计': continue` 两行。

### Step 6 — 出对比图（分业务 × 5 来源）
```bash
python3 scripts/plot_charts.py   # → /tmp/t5_expo_click.png, /tmp/t5_expo_pay.png
```
两张分组柱状图：曝光→点击转化率、曝光→支付转化率。每张图 4 个业务分组、组内 5 来源并排，来源固定配色（搜索蓝/feed 橙/收藏绿/购物车红/足迹紫）。

### Step 7 — 写飞书文档并 P2P 推送
按「飞书文档格式」章节的规范，h3 小标题 + 图片实体 + 表格。图必须作为图片实体插入正文对应结论旁（不能只写图名文字，不能堆文末）。P2P 默认推送钟梦婷个人会话（`--user-id ou_5e572adca6deef8ef21c3b18dfade573`）。对外结论文字先过 `humanizer` 去 AI 味，**绝不改数字/口径/结论**。

## 口径真源 · 埋点点位映射

这是本 skill 的核心。**infoId 如何解析、来源如何识别、场景如何归因**全部在这里。改口径只改本节和对应脚本，不散落到别处。详细版见 `references/埋点口径映射.md`。

### 来源识别（曝光 & 点击共用一套 actiontype + region）

| 来源 | actiontype | region | 说明 |
|------|-----------|--------|------|
| 搜索 | `E1007` | `e` | 搜索结果页商品 |
| feed | `G1001` | `g` | 首页推荐流 |
| 购物车 | `Q9753` | `q` | 加购列表 |
| 收藏 | `J2963` / `T2488` | `j` / `t` | 收藏（在线 + 离线两个入口） |
| 足迹 | `V4961` | `v` | 浏览足迹 |

### infoId 如何解析（两种埋点两种取法）

- **曝光**（`pagetype='explosureGoods'`）：商品 id 藏在 `datapool['goodsList']`，是 `&` 分隔的一串 gid。用 `LATERAL VIEW explode(split(datapool['goodsList'],'&'))` 展开成单个 `gid`，再 `CAST(gid AS BIGINT)` 作为 `info_id`。一次曝光埋点可能含多个商品。
- **点击**（`pagetype='zpmclick'`）：商品 id 在 `datapool['infoId']`，单值。取出后先过 `RLIKE '^[0-9]+$'` 过滤非数字脏值，再 `CAST AS BIGINT`。一次点击埋点对应一个商品。
- 两种埋点都要求 `token` 非空非空串，去重都在 `(src, token, info_id)` 粒度。

### 业务归类（info_id → 4 业务）

关联商品维表 `hdp_zhuanzhuan_dw_global.dw_mysql_info_full_1d`（dt 分区），过滤 `is_cp_flag='0'`（非 CP）、`is_live_flag='0'`（非直播），业务范围限 `cus_business_bu IN ('消费电子','长尾N','二奢')` 或 B2C 特定类目。归类逻辑：

```
消费电子:  cus_business_bu = '消费电子'
二奢:      cus_business_bu = '二奢' AND business_line_id IN (915051,915061)
兴趣:      cus_business_bu = '二奢'(非上述二奢) 或 '长尾N'
其他:      以上都不是（LEFT JOIN 未命中也归其他）
```

### 场景归因（商详/收银台/支付，走交易 dm 表 first_from / ori_firstfrom）

| 环节 | 交易表 | 来源字段 |
|------|--------|---------|
| 商详 | `dm_trade_visit_detail_1d` | `first_from` |
| 收银台 | `dm_trade_order_detail_1d` | `ori_firstfrom` |
| 支付 | `dm_trade_pay_detail_1d` | `ori_firstfrom` |

first_from / ori_firstfrom → 来源映射：
```
搜索:  search, recommend4Search
feed:  homepage_rec, homepage_rec_personal, homepage_filter, homepage_rec_mix
收藏:  getMyLoveInfosV3, getmyloveofflineinfoentrance
足迹:  getfootprint, getfootprint_invalid
```
App 端过滤：`terminal IN ('15','16')`。**收藏/足迹下游的收银台/支付必须用 `ori_firstfrom` 而非 `first_from`，否则成单归因会归零**（历史踩坑）。

### 购物车的特殊处理（无 first_from → 时序链路）

购物车在交易 dm 表里没有对应的 first_from 场景值，无法场景归因。改用**时序链路**：以「购物车曝光时间戳」为起点，在 `(token, info_id)` 粒度判定其后是否发生商详（visit）、收银台（order）、支付（pay），各环节时间戳 `>= 购物车曝光时间戳` 才算命中。SQL 见 `scripts/cart_sequential_chain.sql`。

### 已知数据现象（如实呈现，非计算错误）

- **足迹「点击→商详」>100%**：点击取自埋点（zpmclick），商详取自 dm 场景归因（first_from），两套数据源交叉统计口径不同所致。报告里如实标注，不做平滑。
- **feed 其他业务点击 UV=0**：埋点该切片缺失，柱状图上柱子空缺，不补造数。

## 结论话术骨架

分析结论围绕「结构性差异」，不堆形容词。参考骨架（数字每次重算）：

- **曝光→支付整体转化排序**：收藏 ≈ 购物车 > 足迹 > 搜索 ≫ feed。收藏/购物车是「强意图」来源，转化效率最高；feed 是「泛曝光」来源，量大但转化贴地。
- **量级 vs 效率的错位**：feed 曝光量最大（数百万级）但支付极少（曝光→支付 ~0.02%）；搜索消费电子曝光百万级、支付万级，是绝对成交量主力。
- **分业务看**：同一来源在不同业务上的转化差异（如消费电子普遍高于兴趣/二奢），指向货品供给或用户意图强度差异。

结论必须区分「事实/实测/推断」：转化率是实测；对「为什么」的解释若无数据支撑，标注「基于 xxx 逻辑推断」。

## 目录布局

```
转转核心导购链路分析/
├── SKILL.md                        # 本文件：流程 + 口径真源
├── scripts/
│   ├── run_full_chain.py           # Step2: A曝光/B点击/C商详收银台支付 三段取数
│   ├── cart_sequential_chain.sql   # Step3: 购物车时序链路补数
│   ├── assemble_chain.py           # Step4: 拼装完整链路表 → full5_chain.csv
│   ├── gen_table.py                # Step5: CSV → 飞书表格 HTML（默认剔小计）
│   └── plot_charts.py              # Step6: 分业务×来源 曝光→点击/曝光→支付 对比图
└── references/
    ├── 埋点口径映射.md              # 埋点点位/字段/映射详解（口径真源展开版）
    └── 飞书文档格式.md             # 飞书文档结构 + 图片插入规范
```

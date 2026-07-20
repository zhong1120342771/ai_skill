---
name: jgg-offline-analysis
description: >
  九宫格下线影响分析。xcx-九宫格 是小程序的高曝光低质渠道，2026-06-10 下线。
  本 skill 包含从星河 Xinghe 拉取分子端漏斗数据的 SQL，用于评估下线对小程序大盘
  在流量结构、漏斗转化率、净支付的影响（含 25 年同期 DiD 对照）。
  当用户提到"九宫格"、"九宫格下线"、"九宫格影响"、"小程序大盘漏斗对比"时触发。
metadata:
  type: data-analysis
  domain: 莫斯科保卫战 / 小程序渠道治理
  data_source: 星河 Xinghe (StarRocks/SparkSQL)
---

# 九宫格下线影响分析 (jgg-offline-analysis)

## 业务背景

- `xcx-九宫格` 是小程序原本的核心入口之一，曝光占比约 55%，但净支付转化率仅为非九宫格的 47%
- 业务方判断该渠道质量低，于 **2026-06-10** 推动下线
- 公司是电商，每年 **6.18 大促** 是核心节点，下线评估必须剔除大促节奏

## 数据来源

- 星河平台 (`xinghe-data` skill)
- 底表: `hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_belong02_v2_di`
- 推荐引擎: SparkSQL (`sql_engine=2`)
- 时间分区字段: `dt` (yyyy-MM-dd)

## 维度说明

| wd 取值 | 业务含义 |
|---------|---------|
| `转转小程序` | 小程序除九宫格外的所有入口（首页 / 搜索 / 推荐等） |
| `xcx-九宫格` | 九宫格入口（已于 2026-06-10 下线） |
| `转转APP` | APP 端（独立对照） |
| `找靓机` | 找靓机品牌（独立对照） |

**小程序大盘** = `转转小程序` + `xcx-九宫格`（下线前），下线后 ≈ `转转小程序`

## 关键指标字段

| 字段 | 含义 |
|---|---|
| `exp_pv` / `exp_uv` | 曝光 PV/UV |
| `detail_pv` / `detail_uv` | 商详 PV/UV |
| `order_pv` / `order_uv` | 下单 PV/UV |
| `pay_pv` | 净支付 PV |
| `uv_all` | DAU |
| `dau_pay_rate` | 净支付转化率 (pay_pv / uv_all 或类似口径) |
| `dau_sx_rate` | 商详渗透率 |
| `sx_pay_rate` | 商详转化率 |

## SQL 文件

- `scripts/jgg_belong02_raw.sql` — 原始查询（4 个月跨度 + 拆分端过滤）

## 历史结论锚点

- **D+5 (6.10–6.15) DiD 结果**：DAU 真实净效应 -35.7pp / 商详 UV -24.8pp / 净支付 PV 反事实缺口 -12.5%（日均少 954 单）/ 净支付转化率剔除大促后真实 +35.6%
- **飞书文档**：https://zhuanspirit.feishu.cn/docx/NCAbdFiCYoJb0TxuLInc5jX6nwd（含十节完整分析）
- **0622 更新**：扩窗到 D+12 (6.10–6.21)，含 618 当天 6.18 的承接能力验证

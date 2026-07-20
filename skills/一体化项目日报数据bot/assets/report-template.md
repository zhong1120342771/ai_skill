# 【${dt} 一体化数据日报】

## 【结论】

- 【同城订单&同城订单占比】${conclusion_tongcheng}
- 【线下线索量&线索量转化】${conclusion_xiansuo}
- 【同售订单量&同售动销率】${conclusion_tongshou}（含 pro店 / 小店 拆分）
- 【小时达订单量】${conclusion_xiaoshida}

> 数据时间：${dt}（t-1）
> 质量状态：${quality_summary}

---

## 图 1：2026 年至今 月维度趋势

![yiti_monthly](../visualizations/${dt}/yiti_monthly.png)

最新一月（${latest_month}）数据已标注环比上月。

---

## 图 2：过去 8 周 周维度趋势

![yiti_weekly](../visualizations/${dt}/yiti_weekly.png)

最新一周（${latest_week}）数据已标注环比上周。

---

## 图 3：过去 30 日 日维度趋势

![yiti_daily](../visualizations/${dt}/yiti_daily.png)

最新一日（${dt}）数据已标注环比上一日。

---

## 表 1：t-1 当日 7 项北极星指标汇总

| 指标 | t-1 绝对值 | 环比 (vs t-2) | 过去 7 日均值 | 当月均值 |
|---|---|---|---|---|
| 同城订单量 | ${tongcheng_orders.value} | ${tongcheng_orders.mom} | ${tongcheng_orders.wow_mean} | ${tongcheng_orders.month_mean} |
| 同城订单占比 | ${tongcheng_share.value} | ${tongcheng_share.mom} | ${tongcheng_share.wow_mean} | ${tongcheng_share.month_mean} |
| 线下线索量 | ${offline_leads.value} | ${offline_leads.mom} | ${offline_leads.wow_mean} | ${offline_leads.month_mean} |
| 线索转化总量 | ${lead_conv_total.value} | ${lead_conv_total.mom} | ${lead_conv_total.wow_mean} | ${lead_conv_total.month_mean} |
| 同售订单量 | ${tongshou_orders.value} | ${tongshou_orders.mom} | ${tongshou_orders.wow_mean} | ${tongshou_orders.month_mean} |
| 同售动销率 | ${tongshou_dongxiao_rate.value} | ${tongshou_dongxiao_rate.mom} | ${tongshou_dongxiao_rate.wow_mean} | ${tongshou_dongxiao_rate.month_mean} |
| 小时达订单量 | ${xiaoshida_orders.value} | ${xiaoshida_orders.mom} | ${xiaoshida_orders.wow_mean} | ${xiaoshida_orders.month_mean} |

---

## 待复核（如有）

${warnings}

# Output Schemas — 一体化项目日报数据 Bot

跨步骤产物的 JSON 字段契约，sub-skill 必须严格匹配字段名。

## 一、metrics JSON（数据分析步骤产出）

`analysis_reports/metrics_yiti_${dt}.json`

```json
{
  "dt": "2026-06-16",
  "north_star": {
    "tongcheng_orders":      {"value": 1234, "mom": 0.052, "wow_mean": 1190, "month_mean": 1180},
    "tongcheng_share":       {"value": 0.231, "mom": 0.003, "wow_mean": 0.225, "month_mean": 0.222},
    "offline_leads":         {"value": 567, "mom": -0.012, "wow_mean": 580, "month_mean": 575},
    "lead_conv_total":       {"value": 89,  "mom": 0.025,  "wow_mean": 87,  "month_mean": 86},
    "tongshou_orders":       {"value": 432, "mom": 0.018,  "wow_mean": 420, "month_mean": 415},
    "tongshou_dongxiao_rate":{"value": 0.045, "mom": 0.001, "wow_mean": 0.044, "month_mean": 0.043},
    "xiaoshida_orders":      {"value": 78,  "mom": -0.005, "wow_mean": 80,  "month_mean": 79}
  },
  "monthly_series": {
    "tongcheng_orders": [{"month": "2026-01", "mean": 1100}, ...]
  },
  "weekly_series": {
    "tongcheng_orders": [{"week_start": "2026-04-27", "mean": 1080}, ...]
  },
  "daily_series": {
    "tongcheng_orders": [{"dt": "2026-05-18", "value": 1080}, ...]
  },
  "tongshou_split": {
    "pro店": {"orders": 1234, "orders_mom": 0.12, "dongxiao_rate": 0.08, "dongxiao_rate_mom": 0.05},
    "小店":  {"orders": 870,  "orders_mom": -0.03, "dongxiao_rate": 0.04, "dongxiao_rate_mom": -0.01}
  },
  "tongshou_xiaodian_yiti": {
    "对照城市（重庆&西安）":     {"orders": 65,   "orders_mom": -0.14, "dongxiao_rate": 0.044, "dongxiao_rate_mom": -0.08},
    "一体化覆盖城市（小店）":     {"orders": 620,  "orders_mom": -0.11, "dongxiao_rate": 0.039, "dongxiao_rate_mom": -0.11},
    "其他城市":                 {"orders": 472,  "orders_mom": -0.30, "dongxiao_rate": 0.062, "dongxiao_rate_mom": -0.06}
  }
}
```

字段命名规则：
- `mom` = month-over-month 或 day-over-day 环比；本日报里指**日环比**（t-1 vs t-2），统一用比率小数（0.05 = 5%）。
- `wow_mean` = 过去 7 日均值（T-7 ~ T-1）。
- `month_mean` = 当月均值（含 t-1）。
- 比率指标（`tongcheng_share` / `tongshou_dongxiao_rate`）的 `value` 也是比率小数。
- `weekly_series`：**最近 8 周自然周**（周一起）周均；最近一周可能不足 7 天。
- `monthly_series`：从 2026-01 起每月月均；最近一月可能不足整月。
- `daily_series`：过去 30 日（含 t-1）。
- `tongshou_split`：t-1 当日同售指标按 `门店类型` 拆分（仅 `pro店` / `小店`）；`*_mom` 与上日同店型对比。
- `tongshou_xiaodian_yiti`：**仅小店**同售指标按「对照城市（重庆&西安）/ 一体化覆盖城市（小店，郑州&成都）/ 其他城市」拆三档；口径与主口径一致（`kc_ts/pay_pv`），三档 `orders` 之和 == `tongshou_split.小店.orders`（可作对账校验）；上游 CSV 缺失时为 `{}`，下游需容忍空。

## 二、quality_check JSON（质量检查产出）

`analysis_reports/quality_check_yiti_${dt}.json`

```json
{
  "dt": "2026-06-16",
  "passed": true,
  "hard_failures": [],
  "soft_failures": ["wow_mean 仅有 5 天数据，暂不显著"],
  "warnings":      ["小时达订单 t-1 偏离 7 日均值 35%，请人工核对"],
  "checks": {
    "tables_ready":     {"passed": true,  "detail": "5/5 tables have dt=2026-06-16"},
    "metric_present":   {"passed": true,  "detail": "7/7 metrics computed"},
    "ratio_in_range":   {"passed": true,  "detail": "shares within [0,1]"},
    "no_null_or_inf":   {"passed": true,  "detail": "no NaN/inf in north_star.value"}
  }
}
```

`passed = (hard_failures 为空)`。`hard_failures` 非空 → 结论生成步骤必须停。

## 三、feishu_doc JSON（推送结果记录）

`final_report/feishu_push_${dt}.json`

```json
{
  "dt": "2026-06-16",
  "im_push": [
    {"open_id": "ou_5e572adca6deef8ef21c3b18dfade573", "name": "钟梦婷", "status": "success", "message_id": "om_xxx"}
  ],
  "image_keys": {
    "monthly": "img_v3_xxx",
    "weekly":  "img_v3_yyy",
    "daily":   "img_v3_zzz"
  }
}
```

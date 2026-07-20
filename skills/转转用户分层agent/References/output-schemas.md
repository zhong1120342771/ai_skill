# Output Schemas

> 流水线四步之间的产物契约。任何步骤的字段名必须严格匹配，不允许 sub-agent 自行加字段——下游脚本（scripts/qa_check.py / scripts/feishu_publish.py）按这里的 key 直接读。

---

## 一、`data_storage/user_segments_${dt}.csv`（Step 1 用户评分产物）

每行一个 token（转转 APP 活跃用户），包含六维评分和综合分层。

| 列名 | 类型 | 说明 |
|---|---|---|
| `dt` | string | 数据日期 YYYY-MM-DD |
| `token` | string | 用户标识 |
| `user_type` | string | 现有系统分层（B2C核心业务，z0/z1/z2/z3/z4/z5） |
| `user_source` | string | 用户来源（新媒新增/新媒留存/自然新增/自然留存） |
| `regist_days` | int | 注册至今天数 |
| `r_last_pay_days` | int | 距最近一次净支付天数（无记录 = 9999） |
| `f_pay_cnt_180d` | int | 近 180 天净支付笔数 |
| `m_pay_amt_180d` | float | 近 180 天净支付总额（元） |
| `a_visit_pv_30d` | int | 近 30 天商详浏览次数 |
| `a_search_pv_30d` | int | 近 30 天搜索次数 |
| `a_love_pv_30d` | int | 近 30 天加购/收藏/下单次数 |
| `a_hist_order_cnt` | int | 近 365 天历史成交笔数（b2c） |
| `p_coupon_rate` | float | 近 90 天红包使用率 |
| `p_promo_rate` | float | 近 90 天秒杀/砍价等活动型订单占比 |
| `r_score` | int | R 维度得分 0-3 |
| `f_score` | int | F 维度得分 0-4 |
| `m_score` | int | M 维度得分 0-3 |
| `l_score` | int | L 维度得分 0-3 |
| `a_score` | int | A 维度得分 0-6 |
| `p_score` | int | P 维度得分 0-3 |
| `total_score` | int | 综合评分（公式见 References/分层方案说明.md） |
| `segment_level` | string | 层级标签：L5/L4/L3/L2/L1 |
| `personas` | string | 命中的特征人群列表（逗号分隔，可为空） |

同时输出 `.meta.json`（行数、空值率、各层级用户数）。

---

## 二、`data_storage/segment_distribution_${dt}.csv`（Step 1 层级汇总）

| 列名 | 类型 | 说明 |
|---|---|---|
| `dt` | string | 数据日期 |
| `segment_level` | string | L5/L4/L3/L2/L1 |
| `user_cnt` | int | 用户数 |
| `pct` | float | 占比 |
| `avg_score` | float | 层内均分 |
| `avg_r_last_pay_days` | float | 层内平均最近支付间隔 |
| `avg_f_pay_cnt` | float | 层内平均支付频次 |
| `avg_m_pay_amt` | float | 层内平均支付金额（元） |
| `med_regist_days` | float | 层内注册天数中位数 |

---

## 三、`analysis_reports/seg_analysis_${dt}.json`（Step 2 数据分析产物）

```jsonc
{
  "dt": "YYYY-MM-DD",
  "total_users": 3200000,
  "segment_distribution": {
    "L5": { "user_cnt": 12000, "pct": 0.0038, "avg_score": 31.2 },
    "L4": { "user_cnt": 105000, "pct": 0.033, "avg_score": 23.1 },
    "L3": { "user_cnt": 380000, "pct": 0.119, "avg_score": 16.4 },
    "L2": { "user_cnt": 800000, "pct": 0.25, "avg_score": 9.7 },
    "L1": { "user_cnt": 1903000, "pct": 0.595, "avg_score": 3.1 }
  },
  "dimension_profiles": {
    "L5": { "avg_r_days": 12, "avg_f_cnt": 6.2, "avg_m_amt": 24000, "avg_a_score": 5.1, "avg_p_score": 1.8 },
    // ... 其他层
  },
  "persona_counts": {
    "高频金主": 11000,
    "价值回流": 42000,
    "新用户活跃": 18000,
    "搜而不买": 310000,
    "加购未付": 95000,
    "沉睡老客": 88000,
    "高价值二奢": 7200,
    "价格敏感高频": 24000,
    "分期依赖": 9800
  },
  "conversion_comparison": {
    "L5_vs_L1_score_ratio": 10.1,
    "top_layer_pct": 0.037
  },
  "key_findings": [
    "L5+L4 合计占 3.7%，贡献约 60% GMV（待数据验证）",
    "L1 沉睡用户占比 ~60%，有效激活空间大",
    "新用户活跃人群 30 天内完成首单比例约 X%（待算）"
  ]
}
```

---

## 四、`analysis_reports/quality_check_seg_${dt}.json`（Step 3 质量闸口）

```jsonc
{
  "dt": "YYYY-MM-DD",
  "passed": true,
  "hard_failures": [],
  "soft_failures": [],
  "warnings": [],
  "row_counts": {
    "user_segments": 3200000,
    "segment_distribution": 5
  },
  "distribution_sanity": {
    "L5_pct": 0.0038,
    "L1_pct": 0.595,
    "threshold_L5_max": 0.02,
    "threshold_L1_min": 0.30,
    "ok": true
  },
  "score_sanity": {
    "max_score": 36,
    "p99_score": 33,
    "zero_score_pct": 0.12,
    "ok": true
  },
  "notes": ""
}
```

**契约要点：** `passed = (len(hard_failures) == 0)`。L5 占比 > 2% 或 L1 占比 < 30% 为硬失败（评分参数可能异常）。

---

## 五、`final_report/feishu_doc_${dt}.json`（Step 4 飞书发布产物）

```jsonc
{
  "dt": "YYYY-MM-DD",
  "doc_url": "https://zhuanspirit.feishu.cn/docx/<token>",
  "doc_token": "<token>",
  "uploaded_at": "ISO 8601",
  "im_push": [
    {
      "open_id": "ou_5e572adca6deef8ef21c3b18dfade573",
      "message_id": "om_...",
      "pushed_at": "ISO 8601",
      "status": "ok"
    }
  ]
}
```

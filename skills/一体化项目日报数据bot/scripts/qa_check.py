#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一体化项目日报 Step 3：质量闸口。

输入：data_storage/yiti_*_${dt}.csv + analysis_reports/metrics_yiti_${dt}.json
输出：analysis_reports/quality_check_yiti_${dt}.json

退出码：
  0 = passed
  2 = hard failure（编排器停 Step 4）
  3 = 输入文件缺失
  4 = 内部异常
"""
import argparse
import json
import math
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CSV_TPL, REPORT_DIR, METRIC_LABELS, METRICS_TPL, QC_TPL


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", default=None)
    args = ap.parse_args()
    dt = args.dt or (date.today() - timedelta(days=1)).isoformat()

    metrics_path = METRICS_TPL.format(dt=dt)
    if not os.path.exists(metrics_path):
        print(f"[fatal] 缺少 {metrics_path}", file=sys.stderr)
        return 3

    with open(metrics_path, encoding="utf-8") as f:
        metrics = json.load(f)

    hard, soft, warn = [], [], []
    checks = {}

    # 1) 4 csv 都存在且行数 > 0（仅做存在性，不重复读 csv 行数）
    missing = []
    for name in ("xianshang", "xiansuo", "tongshou", "xiaoshida"):
        p = CSV_TPL.format(name=name, dt=dt)
        if not os.path.exists(p) or os.path.getsize(p) < 50:
            missing.append(name)
    checks["csv_present"] = {"passed": not missing, "detail": f"missing={missing}"}
    if missing:
        hard.append(f"csv 缺失：{missing}")

    # 2) 7 项指标完备
    ns = metrics.get("north_star", {})
    miss_keys = [k for k in METRIC_LABELS if k not in ns or ns[k].get("value") is None]
    checks["metric_present"] = {"passed": not miss_keys, "detail": f"missing={miss_keys}"}
    if miss_keys:
        hard.append(f"metrics 缺指标：{miss_keys}")

    # 3) 无 NaN/inf
    bad_num = []
    for k, m in ns.items():
        v = m.get("value")
        if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
            bad_num.append(k)
    checks["no_null_or_inf"] = {"passed": not bad_num, "detail": f"bad={bad_num}"}
    if bad_num:
        hard.append(f"value 出现 NaN/inf：{bad_num}")

    # 4) 比率指标在 [0,1]
    bad_rate = []
    for k in ("tongcheng_share", "tongshou_dongxiao_rate"):
        v = ns.get(k, {}).get("value")
        if v is None or v < 0 or v > 1:
            bad_rate.append({"k": k, "v": v})
    checks["ratio_in_range"] = {"passed": not bad_rate, "detail": f"bad={bad_rate}"}
    if bad_rate:
        hard.append(f"比率越界：{bad_rate}")

    # 5) 7 项 value 全 ≥ 0
    bad_neg = []
    for k, m in ns.items():
        v = m.get("value")
        if v is not None and v < 0:
            bad_neg.append({"k": k, "v": v})
    checks["non_negative"] = {"passed": not bad_neg, "detail": f"bad={bad_neg}"}
    if bad_neg:
        hard.append(f"value 出现负值：{bad_neg}")

    # 6) 环比 |mom| ≤ 1（>100% 仅 warn）
    big_mom = []
    for k, m in ns.items():
        mom = m.get("mom")
        if mom is not None and abs(mom) > 1.0:
            big_mom.append({"k": k, "mom": mom})
    if big_mom:
        warn.append(f"环比 >100% 的指标：{big_mom}")

    # 7) value 偏离 7 日均值 > 50% → warn
    drift = []
    for k, m in ns.items():
        v, m7 = m.get("value"), m.get("wow_mean")
        if v is None or m7 is None or m7 == 0:
            continue
        if abs(v / m7 - 1.0) > 0.5:
            drift.append({"k": k, "value": v, "wow_mean": m7})
    if drift:
        warn.append(f"偏离 7 日均值 >50%：{drift}")

    # 8) 7 日均值数据点不足
    daily_count = len(metrics.get("daily_series", {}).get("tongcheng_orders", []))
    if daily_count < 7:
        soft.append(f"daily_series 仅 {daily_count} 天，wow_mean 暂不显著")

    passed = not hard
    out = {
        "dt": dt,
        "passed": passed,
        "hard_failures": hard,
        "soft_failures": soft,
        "warnings": warn,
        "checks": checks,
    }
    out_path = QC_TPL.format(dt=dt)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[done] {out_path}")
    print(f"[result] passed={passed} hard={len(hard)} soft={len(soft)} warn={len(warn)}")
    if not passed:
        for h in hard:
            print(f"  HARD: {h}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

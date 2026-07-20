#!/usr/bin/env python3
"""
用户分层流水线 Step 3 质量检查（固化版）。

按 References/output-schemas.md §四 输出 quality_check_seg_${dt}.json。
sub-agent 不要即兴写 pandas——直接调本脚本。

用法:
    python scripts/qa_check.py --dt 2026-06-18

入参:
    --dt      YYYY-MM-DD，必填
    --root    数据根目录，默认 ~/.claude

退出码:
    0 = passed（hard_failures 为空）
    2 = hard failure（上游应停）
    3 = 输入文件缺失
    4 = 内部异常
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

# ============================================================
# 阈值常量（如需调整，改此处，不要在 SKILL.md 另开一份）
# ============================================================
THRESHOLDS = {
    "L5_pct_max": 0.02,      # L5 占比超过 2% = 硬失败（评分异常）
    "L1_pct_deviation": 0.20, # L1 占比偏离预期（50-60%）超 20pp = 硬失败
    "L1_expected_min": 0.30,  # L1 占比下限（< 30% 视为极端偏离）
    "score_max": 39,
    "score_min": 0,
    "req_field_null_max": 0.001,  # token / segment_level 空值率上限 0.1%
    # 软失败阈值
    "L5_pct_min_warn": 0.001,   # L5 < 0.1% = warn
    "L1_pct_max_warn": 0.70,    # L1 > 70% = warn
    "p_zero_pct_warn": 0.80,    # p_score=0 占比 > 80% = warn
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dt", required=True, help="YYYY-MM-DD")
    parser.add_argument("--root", default="~/.claude")
    args = parser.parse_args()

    root = Path(args.root).expanduser()
    dt = args.dt

    seg_file = root / "data_storage" / f"user_segments_{dt}.csv"
    dist_file = root / "data_storage" / f"segment_distribution_{dt}.csv"
    analysis_file = root / "analysis_reports" / f"seg_analysis_{dt}.json"
    out_file = root / "analysis_reports" / f"quality_check_seg_{dt}.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # ---- 输入文件检查 ----
    missing = [str(f) for f in [seg_file, dist_file] if not f.exists()]
    if missing:
        print(f"[qa_check] 输入文件缺失: {missing}", file=sys.stderr)
        sys.exit(3)

    try:
        df = pd.read_csv(seg_file)
        dist = pd.read_csv(dist_file)
    except Exception as e:
        print(f"[qa_check] 读取 CSV 失败: {e}", file=sys.stderr)
        sys.exit(4)

    hard_failures, soft_failures, warnings = [], [], []

    # ---- 基础完整性 ----
    row_cnt = len(df)
    if row_cnt == 0:
        hard_failures.append({"check": "user_segments 非空", "actual": 0, "threshold": ">0"})

    for col in ["token", "segment_level"]:
        if col not in df.columns:
            hard_failures.append({"check": f"必备列 {col} 存在", "actual": "缺失", "threshold": "必须存在"})
        else:
            null_rate = df[col].isna().mean()
            if null_rate > THRESHOLDS["req_field_null_max"]:
                hard_failures.append({"check": f"{col} 非空率", "actual": round(1 - null_rate, 4),
                                       "threshold": f">{1-THRESHOLDS['req_field_null_max']:.3f}"})

    # ---- 层级分布合理性 ----
    if "segment_level" in df.columns:
        total = len(df)
        level_cnts = df["segment_level"].value_counts()
        l5_pct = level_cnts.get("L5", 0) / total if total > 0 else 0
        l1_pct = level_cnts.get("L1", 0) / total if total > 0 else 0

        if l5_pct > THRESHOLDS["L5_pct_max"]:
            hard_failures.append({"check": "L5 占比", "actual": round(l5_pct, 4),
                                   "threshold": f"< {THRESHOLDS['L5_pct_max']}", "detail": "L5 过高，疑似评分阈值异常"})
        if l1_pct < THRESHOLDS["L1_expected_min"]:
            hard_failures.append({"check": "L1 占比下限", "actual": round(l1_pct, 4),
                                   "threshold": f"> {THRESHOLDS['L1_expected_min']}", "detail": "L1 过低，分布极端偏离"})

        if l5_pct < THRESHOLDS["L5_pct_min_warn"]:
            soft_failures.append({"check": "L5 占比过低（评分阈值可能过严）",
                                   "actual": round(l5_pct, 4), "threshold": f"> {THRESHOLDS['L5_pct_min_warn']}"})
        if l1_pct > THRESHOLDS["L1_pct_max_warn"]:
            soft_failures.append({"check": "L1 占比过高", "actual": round(l1_pct, 4),
                                   "threshold": f"< {THRESHOLDS['L1_pct_max_warn']}"})

    # ---- 评分范围检查 ----
    if "total_score" in df.columns:
        score_min = df["total_score"].min()
        score_max = df["total_score"].max()
        if score_min < THRESHOLDS["score_min"] or score_max > THRESHOLDS["score_max"]:
            hard_failures.append({"check": "total_score 范围",
                                   "actual": f"[{score_min}, {score_max}]",
                                   "threshold": f"[{THRESHOLDS['score_min']}, {THRESHOLDS['score_max']}]"})

    # ---- P 维度数据质量 ----
    if "p_score" in df.columns:
        p_zero_rate = (df["p_score"] == 0).mean()
        if p_zero_rate > THRESHOLDS["p_zero_pct_warn"]:
            warnings.append({"check": "p_score=0 占比过高（P维度数据可能不全）",
                              "actual": round(p_zero_rate, 4), "threshold": f"< {THRESHOLDS['p_zero_pct_warn']}"})

    # ---- 抽样复算（取前 5 行验证评分公式） ----
    spot_ok = True
    if all(c in df.columns for c in ["r_score", "f_score", "m_score", "l_score", "a_score", "p_score", "total_score"]):
        sample = df.head(5)
        expected = sample["r_score"] * 2 + sample["f_score"] * 3 + sample["m_score"] + \
                   sample["l_score"] + sample["a_score"] * 2 + sample["p_score"]
        mismatch = (sample["total_score"] != expected).sum()
        if mismatch > 0:
            hard_failures.append({"check": "评分公式复算", "actual": f"{mismatch}/5 行不一致", "threshold": "0"})
            spot_ok = False

    # ---- 构造输出 ----
    passed = len(hard_failures) == 0
    result = {
        "dt": dt,
        "passed": passed,
        "hard_failures": hard_failures,
        "soft_failures": soft_failures,
        "warnings": warnings,
        "row_counts": {
            "user_segments": row_cnt,
            "segment_distribution": len(dist)
        },
        "distribution_sanity": {
            "L5_pct": round(level_cnts.get("L5", 0) / row_cnt, 4) if row_cnt > 0 else None,
            "L1_pct": round(level_cnts.get("L1", 0) / row_cnt, 4) if row_cnt > 0 else None,
        } if "segment_level" in df.columns and row_cnt > 0 else {},
        "score_sanity": {
            "max_score": int(df["total_score"].max()) if "total_score" in df.columns else None,
            "p99_score": int(df["total_score"].quantile(0.99)) if "total_score" in df.columns else None,
            "spot_recompute_ok": spot_ok,
        },
        "notes": ""
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    status = "PASSED" if passed else "FAILED"
    print(f"[qa_check] {status} — hard_failures={len(hard_failures)}, "
          f"soft={len(soft_failures)}, warn={len(warnings)}")
    print(f"[qa_check] output: {out_file}")

    sys.exit(0 if passed else 2)


if __name__ == "__main__":
    main()

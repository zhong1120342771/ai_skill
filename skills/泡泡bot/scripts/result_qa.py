#!/usr/bin/env python3
"""
跑数产物 QA 自检（固化版）。

跑完 SQL 后由跑数 skill 自动调用：读 result_path 的 TSV / xlsx，对照
output-schemas.md §1.2 输出 .meta.json 的 qa 字段。

sub-agent 不再即兴写 pandas 做 QA——所有阈值集中在本脚本，可审计。

用法:
    python3 result_qa.py --result-path /Users/zz/claude-output/sql_result_xxx.tsv \\
                         [--sql-file /Users/zz/claude-output/xxx.sql] \\
                         [--out /path/to/meta.json]   # 默认 <result_path>.meta.json
                         [--min-rows 1]
                         [--null-rate-warn 0.30]
                         [--other-pct-warn 0.15]

退出码：
    0 = passed
    2 = hard failure (上游应停)
    3 = 输入文件缺失
    4 = 内部异常
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("FAILED: 需要 pandas（pip install pandas）", file=sys.stderr)
    sys.exit(4)


OTHER_VALUES = {"其他", "其它", "unknown", "未知", "null", "None", "-"}


def load_result(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in (".tsv", ".txt"):
        return pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False, na_values=["", "NULL", "null"])
    if suffix == ".csv":
        return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=["", "NULL", "null"])
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path, dtype=str)
    # 兜底当 tsv
    return pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False, na_values=["", "NULL", "null"])


def extract_sql_dt_range(sql_text: str) -> dict | None:
    m = re.search(r"\bdt\s+between\s+'(\d{4}-\d{2}-\d{2})'\s+and\s+'(\d{4}-\d{2}-\d{2})'", sql_text, re.IGNORECASE)
    if m:
        return {"start": m.group(1), "end": m.group(2)}
    m = re.search(r"\bdt\s*=\s*'(\d{4}-\d{2}-\d{2})'", sql_text, re.IGNORECASE)
    if m:
        return {"start": m.group(1), "end": m.group(1)}
    return None


def qa_check(df: pd.DataFrame, min_rows: int, null_rate_warn: float, other_pct_warn: float) -> dict:
    """按 output-schemas.md §1.2 产出 qa 字段。"""
    qa: dict = {
        "row_count_check": {"ok": True, "value": int(len(df)), "min_expected": min_rows},
        "null_rate_per_col": {},
        "other_pct_per_col": {},
        "warnings": [],
        "hard_failures": [],
    }

    # 1) 行数检查（hard）
    if len(df) < min_rows:
        qa["row_count_check"]["ok"] = False
        qa["hard_failures"].append(
            f"row_count={len(df)} < min_expected={min_rows}（跑出 0 行或异常少，可能是分区/口径错误）"
        )

    # 2) 每列 null 率
    total = max(len(df), 1)
    for col in df.columns:
        null_count = df[col].isna().sum() + (df[col].astype(str).str.strip() == "").sum()
        rate = null_count / total
        qa["null_rate_per_col"][col] = round(rate, 4)
        if rate >= 1.0:
            qa["hard_failures"].append(f"列 '{col}' 全部为空")
        elif rate > null_rate_warn:
            qa["warnings"].append(f"列 '{col}' null 率 {rate:.1%} 超阈值 {null_rate_warn:.0%}")

    # 3) "其他/未知"占比（对疑似枚举列，distinct ≤ 50 视为枚举）
    # 分层阈值(2026-07-01 升级):
    # - >30% → hard_failure(映射规则严重不足,下游不能直接用,必须回头补映射)
    # - 15%-30% → warning(提醒但可继续)
    other_pct_hard = 0.30
    for col in df.columns:
        try:
            distinct = df[col].nunique(dropna=True)
        except Exception:
            continue
        if distinct == 0 or distinct > 50:
            continue
        other_count = df[col].isin(OTHER_VALUES).sum()
        if other_count == 0:
            continue
        pct = other_count / total
        qa["other_pct_per_col"][col] = round(pct, 4)
        if pct > other_pct_hard:
            qa["hard_failures"].append(
                f"列 '{col}' '其他/未知' 占比 {pct:.1%} 超硬阈值 {other_pct_hard:.0%},"
                f"映射规则严重不足,必须补映射后重跑(不能默默塞到'其他'里)"
            )
        elif pct > other_pct_warn:
            qa["warnings"].append(
                f"列 '{col}' '其他/未知' 占比 {pct:.1%} 超阈值 {other_pct_warn:.0%}，"
                f"映射规则可能有遗漏"
            )

    # 4) 单 distinct 列检测（warn）
    for col in df.columns:
        try:
            distinct = df[col].nunique(dropna=True)
        except Exception:
            continue
        if distinct == 1 and len(df) > 1:
            qa["warnings"].append(f"列 '{col}' 只有 1 个 distinct 值，可能 SQL 缺失维度拆分")

    qa["passed"] = len(qa["hard_failures"]) == 0
    return qa


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-path", required=True, help="跑数产物文件路径（.tsv / .csv / .xlsx）")
    parser.add_argument("--sql-file", help="对应的 SQL 文件（可选，用于提取 dt_range_in_sql）")
    parser.add_argument("--out", help="输出 meta.json 路径，默认 <result_path>.meta.json")
    parser.add_argument("--task-id", help="星河 task id（可选，写入 meta.json）")
    parser.add_argument("--min-rows", type=int, default=1, help="最小行数阈值，少于即 hard failure")
    parser.add_argument("--null-rate-warn", type=float, default=0.30, help="单列 null 率 warning 阈值")
    parser.add_argument("--other-pct-warn", type=float, default=0.15, help="'其他/未知' 占比 warning 阈值")
    parser.add_argument(
        "--no-xlsx",
        action="store_true",
        help="禁用自动生成 xlsx 副本（默认会把 tsv/csv 转一份 xlsx 出来）",
    )
    args = parser.parse_args(argv)

    result_path = Path(args.result_path)
    if not result_path.is_file():
        print(f"FAILED: 结果文件不存在: {result_path}", file=sys.stderr)
        return 3

    try:
        df = load_result(result_path)
    except Exception as e:
        print(f"FAILED: 读取 {result_path} 失败: {e}", file=sys.stderr)
        return 4

    qa = qa_check(df, args.min_rows, args.null_rate_warn, args.other_pct_warn)

    # 默认把 tsv/csv 转一份 xlsx，方便用户直接打开（用户全局要求：结果都存 excel）
    xlsx_path: Path | None = None
    if not args.no_xlsx and result_path.suffix.lower() in (".tsv", ".csv", ".txt") and qa["passed"]:
        try:
            xlsx_path = result_path.with_suffix(".xlsx")
            df.to_excel(xlsx_path, index=False)
        except Exception as e:
            print(f"⚠️ xlsx 副本生成失败（不影响主流程）: {e}", file=sys.stderr)
            xlsx_path = None

    meta = {
        "result_path": str(result_path),
        "xlsx_path": str(xlsx_path) if xlsx_path else None,
        "sql_file": str(Path(args.sql_file).resolve()) if args.sql_file else None,
        "dt": datetime.now().strftime("%Y-%m-%d"),
        "task_id": args.task_id,
        "line_count": int(len(df)) + 1,   # 含表头
        "row_count": int(len(df)),
        "columns": list(df.columns),
        "qa": qa,
    }

    # SQL dt 范围（从 SQL 文件提取）
    if args.sql_file and Path(args.sql_file).is_file():
        sql_text = Path(args.sql_file).read_text(encoding="utf-8", errors="replace")
        dt_range = extract_sql_dt_range(sql_text)
        if dt_range:
            meta["dt_range_in_sql"] = dt_range

    # 写 meta.json
    out_path = Path(args.out) if args.out else Path(str(result_path) + ".meta.json")
    out_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # 打印汇总
    verdict = "PASSED" if qa["passed"] else "HARD_FAILURE"
    print(f"{verdict}: {len(df)} 行 / {len(df.columns)} 列")
    print(f"meta_path: {out_path}")
    if xlsx_path:
        print(f"xlsx_path: {xlsx_path}")
    if qa["hard_failures"]:
        print(f"❌ hard_failures ({len(qa['hard_failures'])}):")
        for f in qa["hard_failures"]:
            print(f"  - {f}")
    if qa["warnings"]:
        print(f"⚠️ warnings ({len(qa['warnings'])}):")
        for w in qa["warnings"]:
            print(f"  - {w}")
    if qa["passed"] and not qa["warnings"]:
        print("✅ 无异常")

    return 0 if qa["passed"] else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

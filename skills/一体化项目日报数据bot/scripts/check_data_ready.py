#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一体化项目日报 Step 1.0：检查 5 张前置表 t-1 数据是否就绪。

策略：
  1) 先尝试 union 5 表的 count 一次过（max_wait=180s，省调度）
  2) union 超时/失败降级为逐表查询（每张表 max_wait=900s，避开 09:30 排队峰值）

退出码：
  0 = 全部就绪
  1 = 任意表 max(dt) < target_dt（数据未就绪，编排器只发提醒不空跑）
  3 = 输入参数缺失
  4 = 内部异常
"""
import argparse
import os
import sys
from datetime import date, timedelta
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/.claude/skills/xinghe-data/scripts"))

from config import PRECONDITION_TABLES


def _flatten_previews(raw):
    """previews: [[ [header], [row1], ... ]] —— 双层嵌套，第一行是表头。"""
    if raw and isinstance(raw[0], list) and raw[0] and isinstance(raw[0][0], list):
        return raw[0][1:]
    return raw or []


def _parse_row(r):
    if isinstance(r, dict):
        return r.get("tag"), r.get("cnt")
    return r[0], r[1]


def try_union(client, target_dt: str, max_wait: int) -> Optional[dict]:
    """一次性查 5 表；返回 {tag: cnt}；超时/失败返回 None 让上层降级。"""
    sql_parts = [
        f"select '{tag}' as tag, count(1) as cnt from {full} where dt = '{target_dt}'"
        for tag, full in PRECONDITION_TABLES
    ]
    sql = "\nunion all\n".join(sql_parts)
    try:
        eid = client.run_sql(sql, sql_engine=5)
        result = client.wait_and_get_result(eid, max_wait=max_wait)
    except Exception as e:
        print(f"[union] 失败，降级为逐表查询：{e}", file=sys.stderr)
        return None
    counts = {}
    for r in _flatten_previews(result.get("previews") or []):
        tag, cnt = _parse_row(r)
        try:
            counts[tag] = int(cnt)
        except Exception:
            counts[tag] = 0
    return counts


def per_table(client, target_dt: str, max_wait: int) -> dict:
    """逐表查询；任一张失败抛异常由上层接到 RC=4。"""
    counts = {}
    for tag, full in PRECONDITION_TABLES:
        sql = f"select '{tag}' as tag, count(1) as cnt from {full} where dt = '{target_dt}'"
        eid = client.run_sql(sql, sql_engine=5)
        result = client.wait_and_get_result(eid, max_wait=max_wait)
        rows = _flatten_previews(result.get("previews") or [])
        if not rows:
            counts[tag] = 0
            continue
        _, cnt = _parse_row(rows[0])
        try:
            counts[tag] = int(cnt)
        except Exception:
            counts[tag] = 0
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", default=None, help="目标日期 YYYY-MM-DD，默认 t-1")
    ap.add_argument("--union-max-wait", type=int, default=180,
                    help="union 一次过的最大等待秒数（默认 180s，超时降级逐表）")
    ap.add_argument("--per-table-max-wait", type=int, default=900,
                    help="降级后逐表的最大等待秒数（默认 900s）")
    args = ap.parse_args()
    target_dt = args.dt or (date.today() - timedelta(days=1)).isoformat()

    try:
        from xinghe_client import XingheExplorer
    except Exception as e:
        print(f"[fatal] 无法 import xinghe_client：{e}", file=sys.stderr)
        return 4

    client = XingheExplorer()

    counts = try_union(client, target_dt, args.union_max_wait)
    if counts is None:
        try:
            counts = per_table(client, target_dt, args.per_table_max_wait)
        except Exception as e:
            print(f"[fatal] 逐表查询异常：{e}", file=sys.stderr)
            return 4

    print(f"[check_data_ready] target_dt={target_dt}")
    not_ready = []
    # 严格按 PRECONDITION_TABLES 顺序输出，不依赖 union 返回顺序
    for tag, _ in PRECONDITION_TABLES:
        cnt_int = counts.get(tag, 0)
        ok = cnt_int > 0
        flag = "OK" if ok else "MISS"
        print(f"  [{flag}] {tag}: count(dt={target_dt})={cnt_int}")
        if not ok:
            not_ready.append((tag, cnt_int))

    if not_ready:
        names = ", ".join([f"{t}(cnt={m})" for t, m in not_ready])
        print(f"[result] 数据未就绪：{names}", file=sys.stderr)
        return 1
    print("[result] 5/5 tables ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())

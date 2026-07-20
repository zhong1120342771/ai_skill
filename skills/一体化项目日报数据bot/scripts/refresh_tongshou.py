#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一体化项目日报 — 同售动销表 (dws_yth_ts_kc_ord_zmt_di) 回刷脚本。

用途：当 Step 1 前置就绪检查发现同售表 t-1 分区 count=0（上游 ETL 未跑到位）时，
     用本脚本 insert overwrite 重跑该表 t-1 分区，再重新触发就绪检查。

⚠️ 高风险：这是对生产表 hdp_zhuanzhuan_dw_global.dws_yth_ts_kc_ord_zmt_di 的
   INSERT OVERWRITE，会覆盖目标分区。仅在确认该分区 count=0（未就绪/缺数）时使用，
   已有数据的分区不要盲目回刷。回刷前后都打日志留痕。

前置约束：
  - 凭证只走 env（星河 XINGHE_CLIENT_USER / XINGHE_CLIENT_SECRET / XINGHE_ACCESS_KEY），不硬编码。
  - SQL 本体存放在 Scripts/06_refresh_tongshou.sql，用 ${dt} 占位分区日期，
    运行时用目标日期字符串替换后提交。
  - sql_engine=5（hive），overwrite 写分区需 hive 引擎。

退出码：
  0 = 回刷成功且目标分区 count>0
  1 = 回刷执行完但目标分区仍 count=0（需人工排查上游）
  3 = 输入/文件缺失
  4 = 内部异常（提交失败/超时等）

用法：
  python3 refresh_tongshou.py --dt 2026-07-19
  python3 refresh_tongshou.py --dt 2026-07-19 --max-wait 1800
"""
import argparse
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/.claude/skills/xinghe-data/scripts"))

TONGSHOU_TABLE = "hdp_zhuanzhuan_dw_global.dws_yth_ts_kc_ord_zmt_di"
REFRESH_SQL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "06_refresh_tongshou.sql")


def load_refresh_sql(dt: str) -> str:
    """读取回刷 SQL 模板，把 ${dt} / ${outFileSuffix} 占位替换为目标分区日期。"""
    if not os.path.exists(REFRESH_SQL):
        print(f"[fatal] 缺回刷 SQL 模板：{REFRESH_SQL}", file=sys.stderr)
        print("        请把上游 insert overwrite 完整 SQL 存到该路径，用 ${dt} 占位分区日期。", file=sys.stderr)
        sys.exit(3)
    with open(REFRESH_SQL, encoding="utf-8") as f:
        raw = f.read()
    if "${" not in raw:
        print("[warn] SQL 模板未发现 ${dt}/${outFileSuffix} 占位符，将原样提交。", file=sys.stderr)
    return raw.replace("${dt}", dt).replace("${outFileSuffix}", dt)


def count_partition(client, dt: str, max_wait: int) -> int:
    sql = f"SELECT count(1) AS cnt FROM {TONGSHOU_TABLE} WHERE dt = '{dt}' LIMIT 1"
    eid = client.run_sql(sql, sql_engine=5)
    result = client.wait_and_get_result(eid, max_wait=max_wait)
    rows = result.get("previews") or []
    if rows and isinstance(rows[0], list) and rows[0] and isinstance(rows[0][0], list):
        rows = rows[0][1:]
    if not rows:
        return 0
    try:
        return int(rows[0][-1])
    except (ValueError, IndexError, TypeError):
        return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", default=None, help="目标回刷分区日期，默认 t-1")
    ap.add_argument("--max-wait", type=int, default=1800,
                    help="overwrite 作业最大等待秒数（默认 1800，回刷比查询慢）")
    ap.add_argument("--force", action="store_true",
                    help="即使目标分区已有数据也强制回刷（默认仅在 count=0 时回刷）")
    args = ap.parse_args()
    dt = args.dt or (date.today() - timedelta(days=1)).isoformat()

    try:
        from xinghe_client import XingheExplorer
    except ImportError as e:
        print(f"[fatal] 无法 import xinghe_client：{e}", file=sys.stderr)
        return 4
    client = XingheExplorer()

    print(f"[refresh_tongshou] target_dt={dt} table={TONGSHOU_TABLE}")

    # 1) 回刷前检查：已有数据且非 --force 则不覆盖
    try:
        before = count_partition(client, dt, max_wait=300)
    except Exception as e:
        print(f"[warn] 回刷前 count 失败（继续尝试回刷）：{e}", file=sys.stderr)
        before = 0
    print(f"[before] dt={dt} count={before}")
    if before > 0 and not args.force:
        print(f"[skip] dt={dt} 已有 {before} 行数据，未加 --force，跳过回刷。")
        return 0

    # 2) 执行 insert overwrite 回刷
    sql = load_refresh_sql(dt)
    print(f"[overwrite] 提交回刷作业（sql_engine=5, max_wait={args.max_wait}s）...")
    try:
        eid = client.run_sql(sql, sql_engine=5, submit_timeout=60)
        client.wait_and_get_result(eid, max_wait=args.max_wait)
    except Exception as e:
        print(f"[fatal] 回刷作业执行失败：{e}", file=sys.stderr)
        return 4

    # 3) 回刷后校验
    try:
        after = count_partition(client, dt, max_wait=300)
    except Exception as e:
        print(f"[fatal] 回刷后 count 校验失败：{e}", file=sys.stderr)
        return 4
    print(f"[after] dt={dt} count={after}")
    if after > 0:
        print(f"[result] 回刷成功，dt={dt} 现有 {after} 行。可重新触发就绪检查/流水线。")
        return 0
    print(f"[result] 回刷执行完但 dt={dt} 仍为 0 行，需人工排查上游 ETL。", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

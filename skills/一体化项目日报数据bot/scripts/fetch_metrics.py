#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一体化项目日报 Step 1.1：并行跑 5 段取数 SQL，落 5 个 CSV。

并行策略：
  5 段 SQL 之间无任何依赖关系，启动后扔进 ThreadPool（默认 5 worker）。
  好处：当某段 SQL 长尾（如 02_yiti_xiansuo 偶发 >5min），不会阻塞其它段；总耗时 ≈ 最慢的一段。
  失败语义：单段失败计入 failures，其它继续跑；最终任意一段失败仍然返回 RC=2。

超时与重试：
  每段 SQL 单独 max_wait=900s（避开星河 9:30 排队峰值），失败后自动重试一次再放弃。

用法：
  python fetch_metrics.py --dt 2026-06-16
  python fetch_metrics.py --dt 2026-06-16 --max-wait 1200 --workers 4 --retries 1

退出码：
  0 = 全部成功
  2 = 任一 SQL 失败 / 行数为 0
  3 = 输入参数缺失
  4 = 内部异常
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/.claude/skills/xinghe-data/scripts"))

from config import SCRIPTS_SQL_DIR, SQL_TASKS, CSV_TPL, META_TPL


def run_one(client, name: str, sql_file: str, dt: str, max_wait: int = 900) -> dict:
    """跑一段 SQL，下载 Excel，转 CSV。返回元信息字典。"""
    import pandas as pd

    sql_path = os.path.join(SCRIPTS_SQL_DIR, sql_file)
    sql = open(sql_path, encoding="utf-8").read()
    sql_hash = hashlib.md5(sql.encode("utf-8")).hexdigest()[:10]

    print(f"[fetch] {name}: running ({sql_file})...")
    eid = client.run_sql(sql, sql_engine=5)
    result = client.wait_and_get_result(eid, max_wait=max_wait)

    xlsx_url = result.get("filename_excel") or result.get("filename")
    if not xlsx_url:
        raise RuntimeError(f"{name} 无下载链接：{result}")

    tmp_xlsx = f"/tmp/yiti_{name}_{dt}.xlsx"
    urllib.request.urlretrieve(xlsx_url, tmp_xlsx)
    df = pd.read_excel(tmp_xlsx)

    csv_path = CSV_TPL.format(name=name, dt=dt)
    # UTF-8 with BOM 防 Excel 打开乱码
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    rows = len(df)
    print(f"[done] {name}: {csv_path} rows={rows}")

    meta = {
        "name": name,
        "dt": dt,
        "rows": rows,
        "columns": list(df.columns),
        "sql_file": sql_file,
        "sql_hash": sql_hash,
        "execute_id": eid,
    }
    with open(META_TPL.format(name=name, dt=dt), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    if rows == 0:
        raise RuntimeError(f"{name} 行数为 0")
    return meta


def run_with_retry(client, task: dict, dt: str, max_wait: int, retries: int) -> dict:
    """单段 SQL，失败自动重试 N 次。返回 {name, ok, meta?, error?, attempts}。"""
    last_err = None
    for attempt in range(retries + 1):
        try:
            meta = run_one(client, task["name"], task["sql"], dt, max_wait=max_wait)
            return {"name": task["name"], "ok": True, "meta": meta, "attempts": attempt + 1}
        except Exception as e:
            last_err = e
            print(f"[warn] {task['name']} attempt {attempt + 1} 失败：{e}", file=sys.stderr)
            if attempt < retries:
                time.sleep(2)  # 避免立即重试踩到同一窗口
    return {"name": task["name"], "ok": False, "error": str(last_err), "attempts": retries + 1}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", default=None)
    ap.add_argument("--max-wait", type=int, default=900,
                    help="单段 SQL 等待星河结果的最大秒数（默认 900s）")
    ap.add_argument("--workers", type=int, default=5,
                    help="并行线程数（默认 5，等于 SQL 段数）")
    ap.add_argument("--retries", type=int, default=1,
                    help="单段 SQL 失败自动重试次数（默认 1，含 60s 网关瞬断与偶发排队超时）")
    args = ap.parse_args()
    dt = args.dt or (date.today() - timedelta(days=1)).isoformat()

    try:
        from xinghe_client import XingheExplorer
    except Exception as e:
        print(f"[fatal] import xinghe_client 失败：{e}", file=sys.stderr)
        return 4

    # 每个 worker 用独立 client，避免共享 session 在并发轮询时互相影响
    def _worker(task):
        client = XingheExplorer()
        return run_with_retry(client, task, dt, args.max_wait, args.retries)

    print(f"[fetch] 并行启动 {len(SQL_TASKS)} 段 SQL（workers={args.workers}, max_wait={args.max_wait}s, retries={args.retries}）")
    t0 = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(_worker, t): t["name"] for t in SQL_TASKS}
        for fut in as_completed(futures):
            results.append(fut.result())

    elapsed = time.time() - t0
    failures = [r for r in results if not r["ok"]]
    ok_names = [r["name"] for r in results if r["ok"]]
    print(f"[fetch] 总耗时 {elapsed:.1f}s；成功 {len(ok_names)}/{len(SQL_TASKS)}：{ok_names}")
    if failures:
        for r in failures:
            print(f"[error] {r['name']} 失败（共 {r['attempts']} 次尝试）：{r['error']}", file=sys.stderr)
        print(f"[result] {len(failures)} 个任务失败", file=sys.stderr)
        return 2
    print("[result] 5/5 CSV 落盘成功")
    return 0


if __name__ == "__main__":
    sys.exit(main())

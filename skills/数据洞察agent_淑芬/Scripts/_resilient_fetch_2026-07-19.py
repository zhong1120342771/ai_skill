#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一次性兜底：data2-2/3-2/4-2 的星河查询在服务端仍 EXECUTING，
只是 get_progress 单次 HTTP poll 命中 58dp.58corp.com 的 30s read timeout 被中断。
本脚本复用已提交的 execute_id，用「poll 遇网络异常自动重试」的方式等结果，
下载沿用 run_step1 的 excel→CSV 全量→previews 兜底(≤100 行判截断 raise) 逻辑。
不重新提交查询，不改动共享 xinghe_client。
"""
import sys, os, json, hashlib, datetime, time, urllib.request
sys.path.insert(0, os.path.expanduser("~/.claude/skills/xinghe-data/scripts"))
import pandas as pd
from xinghe_client import XingheExplorer, XingheAPIError

DT = "2026-07-19"
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(SKILL_DIR, "Scripts")
DATA_DIR = os.path.expanduser("~/.claude/data_storage")

# name -> (execute_id 仍存活, 输出csv, sql模板)
JOBS = {
    "data2-2": (753853950, f"data2-2_homepage_exposure_淑芬_{DT}.csv", "data2-2_曝光_优化装配版.sql"),
    "data3-2": (753853949, f"data3-2_homepage_click_淑芬_{DT}.csv", "data3-2_点击_优化装配版.sql"),
    "data4-2": (753853948, f"data4-2_page_visit_duration_淑芬_{DT}.csv", "data4-2_访问_优化装配版.sql"),
}


def _read_sql(fname):
    return open(os.path.join(SCRIPTS, fname), encoding="utf-8").read().replace("${outFileSuffix}", DT)


def poll_with_retry(client, eid, max_wait=5400, poll_interval=8):
    """轮询，网络异常(超时/瞬断)自动重试，不因单次 poll 失败而中止。"""
    start = time.time()
    consec_err = 0
    while time.time() - start < max_wait:
        try:
            progresses = client.get_progress([eid])
            consec_err = 0
            if progresses:
                status = progresses[0].get("status")
                if status == "SUCCESS":
                    return client.get_result(eid)
                if status == "FAILED":
                    raise XingheAPIError(f"执行失败: {progresses[0].get('error_msg','未知错误')}")
        except XingheAPIError as e:
            # 区分“执行失败”与“网络层异常包成的 XingheAPIError”
            if "执行失败" in str(e):
                raise
            consec_err += 1
            print(f"[warn] {eid} poll 网络异常({consec_err}): {e}", flush=True)
            if consec_err >= 30:
                raise XingheAPIError(f"{eid} 连续 {consec_err} 次 poll 网络异常，放弃")
        except Exception as e:
            consec_err += 1
            print(f"[warn] {eid} poll 异常({consec_err}): {e}", flush=True)
            if consec_err >= 30:
                raise
        time.sleep(poll_interval)
    raise XingheAPIError(f"{eid} 等待超时 {max_wait}s")


def download(name, result):
    df = None
    excel_url = result.get("filename_excel")
    if excel_url:
        try:
            tmp = os.path.join(DATA_DIR, f"_{name}_{DT}_tmp.xlsx")
            urllib.request.urlretrieve(excel_url, tmp)
            df = pd.read_excel(tmp); os.remove(tmp)
        except Exception as e:
            print(f"[warn] {name} excel download failed: {e}; try csv", flush=True)
    if df is None:
        csv_url = result.get("filename_csv") or result.get("filename")
        if csv_url:
            csv_url = XingheExplorer().normalize_download_url(csv_url)
            for attempt in range(3):
                try:
                    tmp = os.path.join(DATA_DIR, f"_{name}_{DT}_tmp.csv")
                    urllib.request.urlretrieve(csv_url, tmp)
                    df = pd.read_csv(tmp, low_memory=False); os.remove(tmp)
                    break
                except Exception as e:
                    print(f"[warn] {name} csv download attempt {attempt+1} failed: {e}", flush=True)
                    time.sleep(10)
    used_preview = False
    if df is None:
        block = result.get("previews", [])[0]
        df = pd.DataFrame(block[1:], columns=block[0]); used_preview = True
    if len(df) == 0:
        raise RuntimeError(f"{name} 0 rows")
    if used_preview and len(df) <= 100:
        raise RuntimeError(f"{name} 仅拿到预览块 {len(df)} 行(疑似截断)——拒绝交付")
    return df


def write(name, csv_path, df, eid, sql):
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    meta = {
        "dt": DT, "rows": int(len(df)), "cols": int(df.shape[1]),
        "columns": list(df.columns),
        "null_rate": {c: round(float(df[c].isna().mean()), 4) for c in df.columns},
        "sql_sha256": hashlib.sha256(sql.encode("utf-8")).hexdigest(),
        "execute_id": eid,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    json.dump(meta, open(csv_path + ".meta.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


def main():
    client = XingheExplorer()
    errors = []
    for name, (eid, out, sqlf) in JOBS.items():
        csv_path = os.path.join(DATA_DIR, out)
        try:
            print(f"[info] {name} reuse execute_id={eid}, polling with retry...", flush=True)
            result = poll_with_retry(client, eid)
            df = download(name, result)
            write(name, csv_path, df, eid, _read_sql(sqlf))
            print(f"[done] {csv_path} rows={len(df)}", flush=True)
        except Exception as e:
            errors.append((name, str(e)))
            print(f"[fail] {name}: {e}", flush=True)
            with open(os.path.join(DATA_DIR, f"error_淑芬_{DT}.log"), "a", encoding="utf-8") as f:
                f.write(f"[{name}] {datetime.datetime.now().isoformat()} {e}\n")
    if errors:
        print(f"[fail] 兜底仍有失败：{[e[0] for e in errors]}", flush=True)
        sys.exit(1)
    print("[ok] data2-2/data3-2/data4-2 全部就绪", flush=True)


if __name__ == "__main__":
    main()

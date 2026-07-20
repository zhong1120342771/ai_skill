#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step1 断连重连补收器（dt=2026-07-16）。
run_step1 的 4 条并发里 data2-2/3-2/4-2 因长轮询连接被 reset 掉线，但对应
execute_id 在星河侧仍 EXECUTING。本脚本按已知 execute_id 重连轮询、取结果、
落 CSV+meta，避免重扫全天分区。sql_sha256 仍按原模板算，保持审计一致。
"""
import sys, os, json, hashlib, datetime, time
sys.path.insert(0, os.path.expanduser("~/.claude/skills/xinghe-data/scripts"))
from xinghe_client import XingheExplorer, XingheAPIError

DT = "2026-07-16"
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(SKILL_DIR, "Scripts")
DATA_DIR = os.path.expanduser("~/.claude/data_storage")

# execute_id -> (sql模板, 输出csv)  —— 映射来自 run_step1 首跑日志
JOBS = {
    752424322: ("data2-2_曝光_优化装配版.sql", f"data2-2_homepage_exposure_淑芬_{DT}.csv"),
    752424324: ("data3-2_点击_优化装配版.sql", f"data3-2_homepage_click_淑芬_{DT}.csv"),
    752424323: ("data4-2_访问_优化装配版.sql", f"data4-2_page_visit_duration_淑芬_{DT}.csv"),
}


def _sql_hash(fname):
    sql = open(os.path.join(SCRIPTS, fname), encoding="utf-8").read().replace("${outFileSuffix}", DT)
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


def robust_wait(client, eid, poll_interval=10, max_wait=5400):
    """容错轮询：单次 get_progress/网络超时不中止整体等待，退避后重试。
    只有星河明确 FAILED/KILLED 才抛。"""
    start = time.time()
    consec_err = 0
    while time.time() - start < max_wait:
        try:
            prs = client.get_progress([eid])
            consec_err = 0
            if not prs:
                time.sleep(poll_interval); continue
            st = prs[0].get("status")
            if st == "SUCCESS":
                # 取结果也容错重试几次
                for _ in range(5):
                    try:
                        return client.get_result(eid)
                    except Exception as e:
                        print(f"[warn] {eid} get_result 重试: {e}", flush=True)
                        time.sleep(8)
                raise XingheAPIError(f"{eid} SUCCESS 但 get_result 反复失败")
            if st in ("FAILED", "KILLED"):
                raise XingheAPIError(f"{eid} {st}: {prs[0].get('error_msg','')}")
        except XingheAPIError as e:
            # 区分：明确 FAILED/KILLED 直接抛；网络类(请求失败:)退避重试
            if "FAILED" in str(e) or "KILLED" in str(e):
                raise
            consec_err += 1
            print(f"[warn] {eid} 轮询瞬断#{consec_err}: {e}", flush=True)
            time.sleep(min(poll_interval * (1 + consec_err), 40))
            continue
        time.sleep(poll_interval)
    raise XingheAPIError(f"{eid} 等待超时 {max_wait}s")


def main():
    import pandas as pd
    client = XingheExplorer()
    fail = []
    for eid, (fname, out) in JOBS.items():
        csv_path = os.path.join(DATA_DIR, out)
        if os.path.exists(csv_path) and os.path.exists(csv_path + ".meta.json"):
            try:
                if int(json.load(open(csv_path + ".meta.json", encoding="utf-8")).get("rows", 0)) > 0:
                    print(f"[skip] {out} 已补收完成", flush=True); continue
            except Exception:
                pass
        try:
            print(f"[info] repoll execute_id={eid} -> {out}", flush=True)
            result = robust_wait(client, eid)
            df = None
            excel_url = result.get("filename_excel")
            if excel_url:
                try:
                    import urllib.request
                    tmp = os.path.join(DATA_DIR, f"_repoll_{eid}_tmp.xlsx")
                    urllib.request.urlretrieve(excel_url, tmp)
                    df = pd.read_excel(tmp)
                    os.remove(tmp)
                except Exception as e:
                    print(f"[warn] {out} excel dl failed: {e}; fallback previews", flush=True)
            if df is None:
                block = result.get("previews", [])[0]
                df = pd.DataFrame(block[1:], columns=block[0])
            if len(df) == 0:
                raise RuntimeError("0 rows")
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            meta = {
                "dt": DT, "rows": int(len(df)), "cols": int(df.shape[1]),
                "columns": list(df.columns),
                "null_rate": {c: round(float(df[c].isna().mean()), 4) for c in df.columns},
                "sql_sha256": _sql_hash(fname),
                "execute_id": eid,
                "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "note": "repolled after connection reset",
            }
            json.dump(meta, open(csv_path + ".meta.json", "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            print(f"[done] {csv_path} rows={len(df)}", flush=True)
        except Exception as e:
            fail.append((eid, out, str(e)))
            print(f"[fail] execute_id={eid} {out}: {e}", flush=True)
    if fail:
        print(f"[fail] repoll 有失败: {[f[1] for f in fail]}", flush=True)
        sys.exit(1)
    print("[ok] repoll 全部补收完成", flush=True)


if __name__ == "__main__":
    main()

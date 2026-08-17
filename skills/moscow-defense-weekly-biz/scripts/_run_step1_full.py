import subprocess, concurrent.futures, os, tempfile, time
from pathlib import Path

WEEK_END = os.environ.get("WEEK_END", "2026-08-16")
SCRIPTS = Path.home() / ".claude/skills/moscow-defense-weekly-biz/scripts"
OUT_DIR = Path.home() / f"Downloads/msk_weekly_raw/{WEEK_END}"
OUT_DIR.mkdir(parents=True, exist_ok=True)
ONESERVICE = Path.home() / ".claude/scripts/oneservice_cli.py"

SQL_MAP = {
    "01_kpi_achievement.sql":               "01_kpi.csv",
    "02_overall_funnel.sql":                "02_funnel.csv",
    "03_dim_funnel_duan_scene_source.sql":  "03_dim_dss.csv",
    "04_dim_funnel_asset_category.sql":     "04_dim_ac.csv",
    "05_weekly_trend.sql":                  "05_trend.csv",
    "06_monthly_trend.sql":                 "06_monthly_trend.csv",
    "07_daily_metrics.sql":                 "07_daily.csv",
    "supp1_traffic_payment_structure.sql":  "supp1.csv",
    "supp2_shangxiang_upgrade.sql":         "supp2.csv",
    "supp3_guan_penetration.sql":           "supp3.csv",
    "supp4_xinmei_xinke.sql":               "supp4.csv",
    "08_apple_funnel.sql":                  "08_apple_funnel.csv",
    "09_apple_weekly_trend.sql":            "09_apple_trend.csv",
}

ALL_DAU_TABLE = "hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zhibiao_zmt_v2_di"


def run_sql(sql_file, out_file, timeout=900):
    raw = (SCRIPTS / sql_file).read_text(encoding="utf-8").replace("${outFileSuffix}", WEEK_END)
    if "${ALIGN_DAY}" in raw or "${ALIGN_MONTH_25}" in raw:
        align_day = str(int(WEEK_END[8:10]))
        align_month_25 = "2025-" + WEEK_END[5:7]
        raw = raw.replace("${ALIGN_DAY}", align_day).replace("${ALIGN_MONTH_25}", align_month_25)
    if sql_file == "08_apple_funnel.sql":
        raw = raw.replace("${TERMINAL_FILTER}", "").replace("${DAU_TABLE}", ALL_DAU_TABLE)
        timeout = 1200
    if sql_file == "09_apple_weekly_trend.sql":
        raw = raw.replace("${TERMINAL_FILTER}", "").replace("${DAU_TABLE}", ALL_DAU_TABLE)
        timeout = 1500
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8") as tf:
        tf.write(raw); p = tf.name
    out = OUT_DIR / out_file
    t0 = time.time()
    proc = subprocess.run(
        ["python3", str(ONESERVICE), "--file", p, "--output", str(out), "--timeout", str(timeout)],
        capture_output=True, text=True)
    os.unlink(p)
    return sql_file, proc.returncode, time.time() - t0, (proc.stderr or "")[-300:]


def line_count(fp):
    try:
        with open(fp, "r", encoding="utf-8-sig") as f:
            return sum(1 for _ in f)
    except Exception:
        return -1


failures = []
results = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    fs = {pool.submit(run_sql, s, o): (s, o) for s, o in SQL_MAP.items()}
    for fut in concurrent.futures.as_completed(fs):
        name, rc, dur, tail = fut.result()
        results[name] = (rc, dur, tail)
        ok = "OK" if rc == 0 else "FAIL"
        print(f"[{ok}] {name} rc={rc} dur={dur:.1f}s", flush=True)
        if rc != 0:
            print(f"      tail: {tail}", flush=True)
            failures.append(name)

# retry failures once with 1500s timeout
retry = [f for f in failures if f != "01_kpi_achievement.sql"]
if retry:
    print(f"[retry] {retry} with timeout=1500", flush=True)
    still = []
    for name in retry:
        out_file = SQL_MAP[name]
        n2, rc2, dur2, tail2 = run_sql(name, out_file, timeout=1500)
        ok = "OK" if rc2 == 0 else "FAIL"
        print(f"[{ok}] (retry) {name} rc={rc2} dur={dur2:.1f}s", flush=True)
        if rc2 != 0:
            print(f"      tail: {tail2}", flush=True)
            (OUT_DIR / f"error_{name}.log").write_text(tail2, encoding="utf-8")
            still.append(name)
        else:
            failures.remove(name)
    failures = [f for f in failures if f in still or f == "01_kpi_achievement.sql"]

# report line counts
print("--- line counts ---", flush=True)
success = 0
for s, o in SQL_MAP.items():
    fp = OUT_DIR / o
    lc = line_count(fp) if fp.exists() else -1
    print(f"    {o}: {lc} lines", flush=True)
    if fp.exists() and lc > 1:
        success += 1

soft_known = {"01_kpi_achievement.sql"}
hard_failures = [f for f in failures if f not in soft_known]

print(f"[done] 取数完成，week_end={WEEK_END}，成功 {success}/{len(SQL_MAP)}", flush=True)
if hard_failures:
    raise SystemExit(f"hard failures: {hard_failures}")

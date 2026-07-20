#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
四页(G1001-G1004) 10 核心模块：有点击 vs 无点击用户的净支付转化率 & 客单价差异。

★ 2026-07-13 默认扩四页：SQL 按 page_id×module 切，产物多一列 page_id。
  page 白名单从 References/section-to-module.json 的 pages 注入(${pageInList})；
  把 pages 改成 ['G1001'] 或用环境无关的单页 config 即可退回单页模式。
  GMV 折算主排页仍是 primary_page(G1001,首页为主)，场馆页乘数供参考。

用途：为「机会计算器」(agents/机会计算器.md) 的 GMV 折算口径提供
      data-backed 的「点击→净支付转化率」与「客单价」两个乘数。
      该 agent 默认不自己拍这两个参数，本脚本就是它的数据来源。

跑法：
    python ~/.claude/skills/数据洞察agent_淑芬/Scripts/run_module_click_conv_aov.py [dt]
    dt 缺省 = t-1。

产物（落 ~/.claude/data_storage/淑芬/click_conv_aov/）：
    module_click_conv_aov_${dt}.csv         四页 × 11 模块（含 page_id 列，约 40 行）× 21 列
    module_click_conv_aov_${dt}.csv.meta.json
关键列：page_id / module / clicked_pv_conv_rate / notclk_pv_conv_rate / pv_conv_rate_diff
        clicked_aov_per_user / clicked_aov_per_order（喂客单价乘数；机会计算器主排页取 page_id=G1001）

强制产出契约（2026-07-01 起，用户要求）：
    这张表是「机会计算器」价值折算的必需乘数——单量/GMV 预估收益强制要算，不能缺。
    因此本脚本从「软产物」升级为「保证产出」：
      1. 当天取数带重试（星河偶发超时/瞬断，最多 MAX_TRIES 次、每次间隔 RETRY_GAP_S）。
      2. 重试全失败 / 0 行 → 自动取 OUT_DIR 里最近一个成功日的 CSV 兜底（近 N 日内，
         默认回看 FALLBACK_LOOKBACK_DAYS 天），复制为当天文件，meta 标 source=fallback_from:YYYY-MM-DD。
      3. 连兜底都找不到（近 N 日无任何成功产物）才 exit 1（真正无数据可用，需人工）。
    正常成功 meta 标 source=fresh。下游机会计算器据 meta.source 决定报告是否标注「乘数来自 X 月 X 日，非当日」。

凭证：星河走环境变量 $XINGHE_CLIENT_USER/$XINGHE_CLIENT_SECRET/$XINGHE_OA，绝不硬编码。
"""
import sys, os, json, hashlib, datetime, time, glob, re

MAX_TRIES = 3                 # 当天取数重试次数（含首次）
RETRY_GAP_S = 20              # 重试间隔秒
FALLBACK_LOOKBACK_DAYS = 14   # 兜底回看窗口：近 N 日内找最近一个成功产物

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL_PATH = os.path.join(SKILL_DIR, "Scripts", "模块点击转化客单价sql.sql")
MAP_PATH = os.path.join(SKILL_DIR, "References", "section-to-module.json")
OUT_DIR = os.path.expanduser("~/.claude/data_storage/淑芬/click_conv_aov")
sys.path.insert(0, os.path.expanduser("~/.claude/skills/xinghe-data/scripts"))
from xinghe_client import XingheExplorer


def _build_page_in_list():
    """从 section-to-module.json 的 pages 生成 SQL IN 白名单，如 'G1001','G1002',...
    单页模式(pages=['G1001'])只注入 'G1001'，其余口径不变。"""
    m = json.load(open(MAP_PATH, encoding="utf-8"))
    pages = m.get("pages") or [m.get("home_page", "G1001")]
    return ",".join(f"'{p}'" for p in pages)

def _try_fetch(sql, dt):
    """跑一次星河取数，成功返回非空 DataFrame，失败/0行抛异常。"""
    import pandas as pd
    client = XingheExplorer()
    eid = client.run_sql(sql, sql_engine=2)  # SparkSQL
    print(f"[info] execute_id={eid} engine=SparkSQL, waiting...", flush=True)
    # 重查询：四页×模块、关联原始点击日志。分级超时(0713 纪要 P0-1)给 1 小时。
    result = client.wait_and_get_result(eid, poll_interval=5, max_wait=3600)

    df = None
    excel_url = result.get("filename_excel")
    if excel_url:
        try:
            import urllib.request
            local_xlsx = os.path.join(OUT_DIR, f"module_click_conv_aov_{dt}.xlsx")
            urllib.request.urlretrieve(excel_url, local_xlsx)
            df = pd.read_excel(local_xlsx)
        except Exception as e:
            print(f"[warn] excel download failed: {e}; fallback to previews", flush=True)
    if df is None:
        block = result.get("previews", [])[0]
        df = pd.DataFrame(block[1:], columns=block[0])
    if len(df) == 0:
        raise RuntimeError("0 rows returned")
    return df, eid


def _find_fallback(dt):
    """当天取数失败时，回看近 FALLBACK_LOOKBACK_DAYS 天，找最近一个成功产物 CSV。
    返回 (src_csv_path, src_dt) 或 None。"""
    try:
        target = datetime.date.fromisoformat(dt)
    except ValueError:
        target = datetime.date.today()
    pat = re.compile(r"module_click_conv_aov_(\d{4}-\d{2}-\d{2})\.csv$")
    cands = []
    for p in glob.glob(os.path.join(OUT_DIR, "module_click_conv_aov_*.csv")):
        m = pat.search(os.path.basename(p))
        if not m:
            continue
        d = datetime.date.fromisoformat(m.group(1))
        # 只取严格早于目标日、且在回看窗口内的成功产物
        gap = (target - d).days
        if 0 < gap <= FALLBACK_LOOKBACK_DAYS:
            cands.append((d, p))
    if not cands:
        return None
    d, p = max(cands, key=lambda x: x[0])  # 最近的一天
    return p, d.isoformat()


def main():
    dt = sys.argv[1] if len(sys.argv) > 1 else (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    os.makedirs(OUT_DIR, exist_ok=True)
    page_in_list = _build_page_in_list()
    sql = (open(SQL_PATH, encoding="utf-8").read()
           .replace("${outFileSuffix}", dt)
           .replace("${pageInList}", page_in_list))
    print(f"[info] dt={dt} pages={page_in_list} sql_chars={len(sql)}", flush=True)

    csv_path = os.path.join(OUT_DIR, f"module_click_conv_aov_{dt}.csv")

    # 1) 当天取数带重试
    df = eid = None
    last_err = None
    for attempt in range(1, MAX_TRIES + 1):
        try:
            df, eid = _try_fetch(sql, dt)
            break
        except Exception as e:
            last_err = e
            print(f"[warn] conv_aov 取数第 {attempt}/{MAX_TRIES} 次失败: {e}", flush=True)
            if attempt < MAX_TRIES:
                time.sleep(RETRY_GAP_S)

    if df is not None:
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        meta = {
            "dt": dt, "rows": int(len(df)), "cols": int(df.shape[1]),
            "columns": list(df.columns),
            "sql_sha256": hashlib.sha256(sql.encode("utf-8")).hexdigest(),
            "execute_id": eid, "engine": "SparkSQL",
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "source": "fresh",
        }
        json.dump(meta, open(csv_path + ".meta.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"[done] {csv_path} rows={len(df)} source=fresh", flush=True)
        print(df.to_string(index=False), flush=True)
        return

    # 2) 当天全失败 → 近 N 日兜底
    print(f"[warn] conv_aov 当天取数 {MAX_TRIES} 次均失败({last_err})，尝试近 {FALLBACK_LOOKBACK_DAYS} 日兜底...", flush=True)
    fb = _find_fallback(dt)
    if fb:
        src_csv, src_dt = fb
        import pandas as pd
        df = pd.read_csv(src_csv)
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        meta = {
            "dt": dt, "rows": int(len(df)), "cols": int(df.shape[1]),
            "columns": list(df.columns),
            "sql_sha256": hashlib.sha256(sql.encode("utf-8")).hexdigest(),
            "execute_id": None, "engine": "SparkSQL",
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "source": f"fallback_from:{src_dt}",
            "fallback_reason": str(last_err),
        }
        json.dump(meta, open(csv_path + ".meta.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"[done] {csv_path} rows={len(df)} source=fallback_from:{src_dt} "
              f"(当天取数失败，用 {src_dt} 的乘数兜底；报告须标注非当日)", flush=True)
        return

    # 3) 连兜底都没有 → 真正无数据可用
    print(f"[fail] conv_aov 当天取数失败且近 {FALLBACK_LOOKBACK_DAYS} 日无成功产物可兜底，"
          f"价值折算缺乘数，需人工介入。last_err={last_err}", flush=True)
    sys.exit(1)


if __name__ == "__main__":
    main()

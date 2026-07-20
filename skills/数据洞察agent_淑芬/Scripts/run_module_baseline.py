#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
四页(G1001-G1004) 10 核心模块 + 逐页 home_overall 的「近 28 天日度基线」软产物 runner。

★ 2026-07-13 默认扩四页：SQL 多一列 page_id，按 dt×page_id×module 切。page 白名单
  从 References/section-to-module.json 的 pages 注入(${pageInList})；异动判定仍以
  primary_page(G1001,首页为主)为主，场馆页基线量小仅供参考。pages=['G1001'] 退回单页。

用途：给「数据分析」agent(Step2) 的异动判定提供历史窗。核心口径——
      不是拿 D-1 单基线比，而是各天在「当天范围内」单独去重算出模块
      exposure/click UV·PV·UV-CTR 的日序列，分析侧再对序列求：
        · 整窗均值/标准差 → 主判据 z-score
        · 同星期几分布   → 辅判据 z-score（去掉周一~周日的周内周期）
      两者都超阈值才算强异动，从而排除周期性波动带来的误判。

窗口：[dt-28, dt]（含当天）。dt-28..dt-1 共 28 天 = 4 整周，每个星期几恰好
      出现 4 次，整窗均值不被「星期几构成」带偏；当天 dt 行用同一 1/339 哈希桶
      算，保证「当天 vs 历史」本表内部完全同口径。

跑法：
    python3 ~/.claude/skills/数据洞察agent_淑芬/Scripts/run_module_baseline.py [dt] [--force]
    dt 缺省 = t-1。同 dt 已有 status=ok 的基线默认跳过重跑（幂等，省一次
    28 天全窗扫描）；加 --force 强制重跑。

产物（落 ~/.claude/data_storage/淑芬/module_daily_baseline/）：
    module_daily_baseline_${dt}.csv        （29 天 × 页数 ×（11 模块 + home_overall）行，含 page_id 列）
    module_daily_baseline_${dt}.csv.meta.json

软产物契约：本表是异动判定的增强项，不是硬依赖。当天星河跑不出 / 0 行 / 库缺
    历史分区时——重试 MAX_TRIES 次后仍失败则写一份 status=unavailable 的 meta、
    stdout 打 [warn]、退出码 0（不阻断主流水线）。分析侧读不到基线就退回 D-1
    单基线判异动并在报告标注「历史窗不可用」。

凭证：星河走环境变量 $XINGHE_CLIENT_USER/$XINGHE_CLIENT_SECRET/$XINGHE_OA，
      绝不硬编码。含 hash(token) 必须走 Hive 引擎(engine=5)。
"""
import sys, os, json, hashlib, datetime, time

MAX_TRIES = 3
RETRY_GAP_S = 20
WINDOW_DAYS = 28          # 参考窗 = dt-28..dt-1 共 28 天(4 整周)；SQL 另含当天 dt 行

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL_PATH = os.path.join(SKILL_DIR, "Scripts", "模块日度基线sql.sql")
MAP_PATH = os.path.join(SKILL_DIR, "References", "section-to-module.json")
OUT_DIR = os.path.expanduser("~/.claude/data_storage/淑芬/module_daily_baseline")
sys.path.insert(0, os.path.expanduser("~/.claude/skills/xinghe-data/scripts"))


def _build_page_in_list():
    """从 section-to-module.json 的 pages 生成 SQL IN 白名单，如 'G1001','G1002',...
    单页模式(pages=['G1001'])只注入 'G1001'，其余口径不变。"""
    m = json.load(open(MAP_PATH, encoding="utf-8"))
    pages = m.get("pages") or [m.get("home_page", "G1001")]
    return ",".join(f"'{p}'" for p in pages)


def _build_case_when():
    """从 section-to-module.json 生成 section_id → 模块 的 CASE 表达式，
    保持与主流水线切分完全一致，SQL 不自己写死 section_id。"""
    # 用「简单 CASE」form(CASE datapool['sectionId'] WHEN '100' THEN ...)——
    # 与已验证可跑的 模块点击转化客单价sql.sql 同款。星河 Hive(engine=5) 的解析器
    # 不接受「搜索 CASE」里把 map 下标放进 WHEN 布尔式(CASE WHEN datapool['x']='y')，
    # 会报 ParseException near 'WHEN' 'datapool' '['；简单 CASE 把 map 访问放在 CASE
    # 之后当值表达式则解析正常。section→module 是等值映射，简单 CASE 完全够用。
    m = json.load(open(MAP_PATH, encoding="utf-8"))
    s2m = m["section_to_module"]
    lines = ["CASE datapool['sectionId']"]
    for sid, mod in s2m.items():
        lines.append(f"        WHEN '{sid}' THEN '{mod}'")
    lines.append("        ELSE '其他' END")
    return "\n    ".join(lines)


def _write_meta(csv_path, dt, start_dt, end_dt, rows, cols, columns, sql, eid, status, reason=None):
    meta = {
        "dt": dt,
        "window_start": start_dt,
        "window_end": end_dt,
        "window_days": WINDOW_DAYS,
        "sampling": "hash_bucket_1_339",
        "rows": int(rows), "cols": int(cols), "columns": list(columns),
        "sql_sha256": hashlib.sha256(sql.encode("utf-8")).hexdigest(),
        "execute_id": eid, "engine": "Hive",
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "status": status,
    }
    if reason:
        meta["reason"] = str(reason)
    json.dump(meta, open(csv_path + ".meta.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


def _try_fetch(sql):
    import pandas as pd
    from xinghe_client import XingheExplorer
    client = XingheExplorer()
    # engine=2 SparkSQL：与已验证可跑的 模块点击转化客单价sql.sql 同引擎。
    # SparkSQL 支持 hash()/pmod()（1/339 哈希桶）且解析 `CASE datapool['x'] WHEN..` 正常；
    # engine=5 Hive 的解析器会对 map 下标 + CASE 组合报 ParseException（实测），故不用 Hive。
    # 基线是单条查询里 29 天自洽序列，用哪种 hash 算法不影响「当天 vs 历史」的内部一致性。
    eid = client.run_sql(sql, sql_engine=2)   # SparkSQL
    print(f"[info] execute_id={eid} engine=SparkSQL, waiting...", flush=True)
    # 重查询：单条查询里跑 29 天自洽基线序列。分级超时(0713 纪要 P0-1)给 1 小时。
    result = client.wait_and_get_result(eid, poll_interval=5, max_wait=3600)

    df = None
    excel_url = result.get("filename_excel")
    if excel_url:
        try:
            import urllib.request
            local_xlsx = os.path.join(OUT_DIR, f"_module_daily_baseline_tmp.xlsx")
            urllib.request.urlretrieve(excel_url, local_xlsx)
            df = pd.read_excel(local_xlsx)
            os.remove(local_xlsx)
        except Exception as e:
            print(f"[warn] excel download failed: {e}; fallback to previews", flush=True)
    if df is None:
        block = result.get("previews", [])[0]
        df = pd.DataFrame(block[1:], columns=block[0])
    if len(df) == 0:
        raise RuntimeError("0 rows returned")
    return df, eid


def _existing_ok(csv_path):
    """同 dt 已产出且 meta.status=ok、csv 有实际行时，返回 (rows, days) 供跳过；否则 None。"""
    meta_path = csv_path + ".meta.json"
    if not (os.path.exists(csv_path) and os.path.exists(meta_path)):
        return None
    try:
        meta = json.load(open(meta_path, encoding="utf-8"))
    except Exception:
        return None
    if meta.get("status") != "ok" or int(meta.get("rows", 0)) <= 0:
        return None
    return meta.get("rows"), meta.get("window_days")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv[1:]
    dt = args[0] if args else (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    end = datetime.date.fromisoformat(dt)
    start = end - datetime.timedelta(days=WINDOW_DAYS)   # dt-28
    start_dt, end_dt = start.isoformat(), end.isoformat()
    os.makedirs(OUT_DIR, exist_ok=True)
    csv_path = os.path.join(OUT_DIR, f"module_daily_baseline_{dt}.csv")

    # 幂等复用：同 dt 已有 status=ok 的基线，默认跳过重跑，省一次 28 天全窗扫描。
    if not force:
        prev = _existing_ok(csv_path)
        if prev is not None:
            print(f"[skip] 复用当天已产出基线 {csv_path} rows={prev[0]} "
                  f"status=ok（--force 可强制重跑）", flush=True)
            return

    sql = open(SQL_PATH, encoding="utf-8").read()
    # 防呆：每个占位符在模板里必须恰好出现 1 次（只在真正的 CTE 里）。
    # 若注释里误留字面量占位符，多行 CASE 注入进单行 `--` 注释会溢出成活 SQL（踩过的坑）。
    case_when = _build_case_when()
    page_in_list = _build_page_in_list()
    for tok in ("${startDt}", "${endDt}", "${moduleCaseWhen}", "${pageInList}"):
        cnt = sql.count(tok)
        if cnt != 1:
            print(f"[fail] 占位符 {tok} 在模板里出现 {cnt} 次（应为 1）——"
                  f"检查是否在注释里误留字面量。中止取数，避免注入污染。", flush=True)
            sys.exit(2)
    sql = (sql.replace("${startDt}", start_dt)
              .replace("${endDt}", end_dt)
              .replace("${moduleCaseWhen}", case_when)
              .replace("${pageInList}", page_in_list))
    print(f"[info] dt={dt} window=[{start_dt},{end_dt}] pages={page_in_list} sql_chars={len(sql)}", flush=True)

    df = eid = None
    last_err = None
    for attempt in range(1, MAX_TRIES + 1):
        try:
            df, eid = _try_fetch(sql)
            break
        except Exception as e:
            last_err = e
            print(f"[warn] 基线取数第 {attempt}/{MAX_TRIES} 次失败: {e}", flush=True)
            if attempt < MAX_TRIES:
                time.sleep(RETRY_GAP_S)

    if df is not None:
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        _write_meta(csv_path, dt, start_dt, end_dt, len(df), df.shape[1],
                    df.columns, sql, eid, "ok")
        n_days = df["dt"].nunique() if "dt" in df.columns else "?"
        print(f"[done] {csv_path} rows={len(df)} days={n_days} status=ok", flush=True)
        return

    # 软失败：写 unavailable meta，退出码 0，不阻断主流水线
    print(f"[warn] 基线取数 {MAX_TRIES} 次均失败({last_err})；写 unavailable 标记，"
          f"分析侧退回 D-1 单基线判异动，不阻断主流水线。", flush=True)
    # 仍写一个空 csv 占位，便于编排器 ls 到（分析侧靠 meta.status 判断）
    try:
        import pandas as pd
        pd.DataFrame(columns=["dt","page_id","module","exposure_uv","exposure_pv",
                              "click_uv","click_pv","uv_ctr"]).to_csv(
            csv_path, index=False, encoding="utf-8-sig")
    except Exception:
        open(csv_path, "w").close()
    _write_meta(csv_path, dt, start_dt, end_dt, 0, 8,
                ["dt","page_id","module","exposure_uv","exposure_pv","click_uv","click_pv","uv_ctr"],
                sql, None, "unavailable", reason=last_err)
    sys.exit(0)


if __name__ == "__main__":
    main()

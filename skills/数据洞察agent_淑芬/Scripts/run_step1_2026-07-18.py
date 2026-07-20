#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
首页洞察 Step1 取数编排器（dt=2026-07-18）。
两阶段执行：
  阶段A（串行阻塞）：data1 用户抽样池 → 落盘 + user_source 命中率 >=95% 校验。
  阶段B（并发提交）：data2-2 / data3-2 / data4-2 / dau_full 四条硬产物并发提交给星河。
data5(conv_aov)、data6(baseline) 由各自固化 runner 单独跑（各自内置重试/兜底/幂等）。

所有硬产物落 ~/.claude/data_storage/，走星河 Hive 引擎(engine=5，含 hash(token))。
dau_full 无 hash 依赖但同走星河即可。
硬产物同 dt 幂等：已存在且 meta 校验通过则 [skip]。

凭证全走环境变量（xinghe_config），绝不硬编码。
"""
import sys, os, json, hashlib, datetime, time
from concurrent.futures import ThreadPoolExecutor, as_completed

DT = "2026-07-18"
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(SKILL_DIR, "Scripts")
DATA_DIR = os.path.expanduser("~/.claude/data_storage")
sys.path.insert(0, os.path.expanduser("~/.claude/skills/xinghe-data/scripts"))

os.makedirs(DATA_DIR, exist_ok=True)

# 硬产物定义：name -> (sql模板文件, 输出csv名, engine)
HARD = {
    "data1": ("用户抽样&用户标签sql.sql", f"data1_user_sample_淑芬_{DT}.csv", 5),
    "data2-2": ("data2-2_曝光_优化装配版.sql", f"data2-2_homepage_exposure_淑芬_{DT}.csv", 5),
    "data3-2": ("data3-2_点击_优化装配版.sql", f"data3-2_homepage_click_淑芬_{DT}.csv", 5),
    "data4-2": ("data4-2_访问_优化装配版.sql", f"data4-2_page_visit_duration_淑芬_{DT}.csv", 5),
    "dau_full": ("dau_query.sql", f"dau_full_淑芬_{DT}.csv", 5),
}


def _read_sql(fname):
    return open(os.path.join(SCRIPTS, fname), encoding="utf-8").read().replace("${outFileSuffix}", DT)


def _meta_ok(csv_path, min_rows=1, check_hitrate=False):
    """幂等校验：csv 存在且 meta rows>0；data1 再查 user_source 命中率>=95%。"""
    meta_path = csv_path + ".meta.json"
    if not (os.path.exists(csv_path) and os.path.exists(meta_path)):
        return False
    try:
        meta = json.load(open(meta_path, encoding="utf-8"))
    except Exception:
        return False
    if int(meta.get("rows", 0)) < min_rows:
        return False
    if check_hitrate and float(meta.get("user_source_hit_rate", 0)) < 0.95:
        return False
    return True


def _fetch(name, engine, sql):
    """跑一条星河 SQL，返回 (df, execute_id)。"""
    import pandas as pd
    from xinghe_client import XingheExplorer
    client = XingheExplorer()
    eid = client.run_sql(sql, sql_engine=engine, submit_timeout=60)
    print(f"[info] {name} execute_id={eid} engine={engine}, waiting...", flush=True)
    result = client.wait_and_get_result(eid, poll_interval=5, max_wait=3600)
    df = None
    import urllib.request
    # 优先 excel；无 excel 时必须走 filename_csv/filename 全量下载。
    # ★ 2026-07-17 踩坑：大结果集(如 data2-2 曝光~53w行)星河只给 filename_csv、不给 filename_excel，
    #   旧逻辑直接 fallback 到 previews[0]——那是被截断的 ~50 行预览块，导致产物静默塌成 50 行、
    #   下游 token 子集/曝光量全崩且不报错。修复：excel 缺失时用 CSV 全量下载，previews 仅作最末兜底。
    excel_url = result.get("filename_excel")
    if excel_url:
        try:
            tmp = os.path.join(DATA_DIR, f"_{name}_{DT}_tmp.xlsx")
            urllib.request.urlretrieve(excel_url, tmp)
            df = pd.read_excel(tmp)
            os.remove(tmp)
        except Exception as e:
            print(f"[warn] {name} excel download failed: {e}; try csv", flush=True)
    if df is None:
        csv_url = result.get("filename_csv") or result.get("filename")
        if csv_url:
            csv_url = client.normalize_download_url(csv_url)  # storage->store 内网域名重写
            try:
                tmp = os.path.join(DATA_DIR, f"_{name}_{DT}_tmp.csv")
                urllib.request.urlretrieve(csv_url, tmp)
                df = pd.read_csv(tmp, low_memory=False)
                os.remove(tmp)
            except Exception as e:
                print(f"[warn] {name} csv download failed: {e}; fallback previews", flush=True)
    used_preview = False
    if df is None:
        block = result.get("previews", [])[0]
        df = pd.DataFrame(block[1:], columns=block[0])
        used_preview = True
    if len(df) == 0:
        raise RuntimeError(f"{name} 0 rows")
    # 预览块通常被截断到 ~50 行；若走了预览且行数正好卡在预览上限，判为截断失败而非静默交付。
    if used_preview and len(df) <= 100:
        raise RuntimeError(
            f"{name} 仅拿到预览块 {len(df)} 行(疑似截断，excel/csv 下载均失败)——"
            f"拒绝交付截断产物，需人工/重跑")
    return df, eid


def _write(name, csv_path, df, eid, sql, extra_meta=None):
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    meta = {
        "dt": DT, "rows": int(len(df)), "cols": int(df.shape[1]),
        "columns": list(df.columns),
        "null_rate": {c: round(float(df[c].isna().mean()), 4) for c in df.columns},
        "sql_sha256": hashlib.sha256(sql.encode("utf-8")).hexdigest(),
        "execute_id": eid,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    if extra_meta:
        meta.update(extra_meta)
    json.dump(meta, open(csv_path + ".meta.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


def run_one(name):
    """跑单个硬产物（阶段B用；data1 单独走）。返回 (name, rows) 或抛异常。"""
    fname, out, engine = HARD[name]
    csv_path = os.path.join(DATA_DIR, out)
    if _meta_ok(csv_path):
        rows = json.load(open(csv_path + ".meta.json", encoding="utf-8")).get("rows")
        print(f"[skip] {name} 已存在且 meta 达标 rows={rows}，复用", flush=True)
        return name, rows
    sql = _read_sql(fname)
    df, eid = _fetch(name, engine, sql)
    _write(name, csv_path, df, eid, sql)
    print(f"[done] {csv_path} rows={len(df)}", flush=True)
    if name == "dau_full":
        uv = int(df.iloc[0]["uv"]) if "uv" in df.columns else "?"
        print(f"[done] dau_full_淑芬_{DT}.csv uv={uv}", flush=True)
    return name, len(df)


def run_data1():
    """阶段A：data1 串行 + 命中率校验。"""
    fname, out, engine = HARD["data1"]
    csv_path = os.path.join(DATA_DIR, out)
    if _meta_ok(csv_path, check_hitrate=True):
        m = json.load(open(csv_path + ".meta.json", encoding="utf-8"))
        print(f"[skip] data1 已存在且命中率达标 rows={m.get('rows')} "
              f"hit={m.get('user_source_hit_rate')}，复用", flush=True)
        return
    sql = _read_sql(fname)
    df, eid = _fetch("data1", engine, sql)
    hit = float((df["user_source"].notna() & (df["user_source"].astype(str).str.strip() != "")).mean())
    print(f"[info] data1 rows={len(df)} user_source_hit_rate={hit:.4f}", flush=True)
    if hit < 0.95:
        raise RuntimeError(f"data1 user_source 命中率 {hit:.4f} < 0.95，判失败停流水线")
    _write("data1", csv_path, df, eid, sql, extra_meta={"user_source_hit_rate": round(hit, 4)})
    print(f"[done] {csv_path} rows={len(df)}", flush=True)


def main():
    errors = []
    # 阶段A：data1 阻塞
    try:
        run_data1()
    except Exception as e:
        print(f"[fail] data1 失败：{e}", flush=True)
        with open(os.path.join(DATA_DIR, f"error_淑芬_{DT}.log"), "a", encoding="utf-8") as f:
            f.write(f"[data1] {datetime.datetime.now().isoformat()} {e}\n")
        sys.exit(1)

    # 阶段B：4 条硬产物并发
    stageB = ["data2-2", "data3-2", "data4-2", "dau_full"]
    results = {}
    with ThreadPoolExecutor(max_workers=len(stageB)) as ex:
        futs = {ex.submit(run_one, n): n for n in stageB}
        for fut in as_completed(futs):
            n = futs[fut]
            try:
                _, rows = fut.result()
                results[n] = rows
            except Exception as e:
                errors.append((n, str(e)))
                print(f"[fail] {n} 失败：{e}", flush=True)
                with open(os.path.join(DATA_DIR, f"error_淑芬_{DT}.log"), "a", encoding="utf-8") as f:
                    f.write(f"[{n}] {datetime.datetime.now().isoformat()} {e}\n")

    if errors:
        print(f"[fail] Step1 硬产物有失败：{[e[0] for e in errors]}，停流水线", flush=True)
        sys.exit(1)

    print(f"[ok] Step1 硬产物全部就绪：data1 + {stageB}", flush=True)


if __name__ == "__main__":
    main()

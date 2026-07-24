#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""首页洞察 Step2 数据分析 —— dt=2026-07-15 一次性执行脚本。
产出 exploration JSON / summary.md / hypotheses.md。口径严格按 References/output-schemas.md §一。
"""
import json, math, os, sys
import numpy as np
import pandas as pd

# --- minimal stats without scipy (no network) ---
def chi2_2xk(observed):
    """observed: 2xK contingency (rows=clicked/notclicked, cols=layers). return chi2, df."""
    obs = np.array(observed, dtype=float)
    row = obs.sum(1, keepdims=True); col = obs.sum(0, keepdims=True); tot = obs.sum()
    if tot == 0:
        return 0.0, 0
    exp = row @ col / tot
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2 = np.nansum(np.where(exp > 0, (obs - exp) ** 2 / exp, 0.0))
    df = (obs.shape[0] - 1) * (obs.shape[1] - 1)
    return float(chi2), df

# chi2 critical value at p=0.05 for df=1..5 (lookup, avoids scipy)
CHI2_CRIT_05 = {1: 3.841, 2: 5.991, 3: 7.815, 4: 9.488, 5: 11.070}

def cramers_v(chi2, n, k_cols):
    return math.sqrt(chi2 / (n * (min(2, k_cols) - 1))) if n and k_cols > 1 else 0.0

DT = "2026-07-23"
BASE = "data_storage/"
REFDIR = "skills/数据洞察agent_淑芬/References/"
OUTDIR = "analysis_reports/"
BLDIR = "data_storage/淑芬/module_daily_baseline/"

with open(REFDIR + "section-to-module.json", encoding="utf-8") as f:
    CFG = json.load(f)
SEC2MOD = CFG["section_to_module"]          # {"101":"搜索框",...}
CORE = CFG["core_modules"]                  # 11 模块顺序
PAGES = CFG["pages"]                         # ["G1001",...]
PAGE_NAMES = CFG["page_names"]
PRIMARY = CFG["primary_page"]               # G1001
CAP_SEC = CFG["venue_tab_cap"]["section"]   # "106"
CAP_TH = CFG["venue_tab_cap"]["threshold"]  # 0.90
STRIP = CFG["page_ctr_offpage_strip"]
CONTAINER = set(CFG["container_sections"].keys())  # {113,115,741}

def norm_sec(x):
    """section_id 归一化为字符串整数;NaN→None"""
    if pd.isna(x):
        return None
    try:
        return str(int(float(x)))
    except (ValueError, TypeError):
        return str(x)

# ---------- Step A: load ----------
print("[StepA] loading ...", file=sys.stderr)
d1 = pd.read_csv(BASE + f"data1_user_sample_淑芬_{DT}.csv", dtype=str)
d2 = pd.read_csv(BASE + f"data2-2_homepage_exposure_淑芬_{DT}.csv", dtype=str)
d3 = pd.read_csv(BASE + f"data3-2_homepage_click_淑芬_{DT}.csv", dtype=str)
d4 = pd.read_csv(BASE + f"data4-2_page_visit_duration_淑芬_{DT}.csv", dtype=str)

for name, df in [("data1", d1), ("data2-2", d2), ("data3-2", d3), ("data4-2", d4)]:
    print(f"[StepA] {name} shape={df.shape}", file=sys.stderr)

n_users = d1.token.nunique()
# user layer collapse: z0 / z1-z3 / z4-z5
def layer(z):
    if z == "z0":
        return "z0"
    if z in ("z1", "z2", "z3"):
        return "z1-z3"
    if z in ("z4", "z5"):
        return "z4-z5"
    return None
d1["lyr"] = d1.user_type.map(layer)
# 分层 / 来源分布来自 data1 抽样用户名单
layer_dist = (d1.lyr.value_counts(normalize=True)).round(4).to_dict()
src_dist = d1.user_source.value_counts().to_dict()

# NOTE(数据事实): 事件表(data2/3/4)的 token 与 data1 token 采用不同哈希格式,
# 大小写归一后重合率仍<0.3%,无法按 token join。但事件表自带 user_type/user_source 列,
# 分层/来源切分一律用事件表【行内】user_type/user_source(下方 lyr/src 派生列),不做跨表 join。
# token_coverage 记录实际重合(极低),作为数据质量说明,不作为子集校验 hard 依据。
u1 = set(d1.token.str.upper())
def cov(df):
    tk = set(df.token.dropna().str.upper())
    return round(len(tk & u1) / len(tk), 4) if tk else None
token_cov = {"data2-2": cov(d2), "data3-2": cov(d3), "data4-2": cov(d4),
             "note": "事件表token与data1哈希格式不同,无法join;分层/来源用事件表行内列"}

# 事件表行内派生分层列
def add_lyr_src(df):
    df["lyr"] = df.user_type.map(layer)
    df["src"] = df.user_source
add_lyr_src(d2); add_lyr_src(d3); add_lyr_src(d4)
print(f"[StepA] n_users={n_users} layer_dist={layer_dist} token_cov={token_cov}", file=sys.stderr)

# 中文映射命中率(page_name_zh / section_name_zh)
pnz_hit = (d2.page_name_zh.notna().mean())
snz_hit = (d2[d2.sectionid.notna()].section_name_zh.notna().mean())

# ---------- Step B: module split ----------
for df in (d2, d3):
    df["sec"] = df.sectionid.map(norm_sec)
    df["mod"] = df.sec.map(lambda s: SEC2MOD.get(s) if s is not None else None)
    df["pg"] = df.actiontype

# unmapped exposure pv pct (primary page): rows w/ sec not in map & not container & not NaN
def unmapped_pct(df):
    dd = df[df["pg"] == PRIMARY]
    total = len(dd)
    unm = dd[(dd["sec"].notna()) & (~dd["sec"].isin(SEC2MOD.keys()))]
    return round(len(unm) / total, 4) if total else 0.0
unmapped_exposure_pv_pct = unmapped_pct(d2)

# clicked eventduration in d4 -> stay duration
d4["ed"] = pd.to_numeric(d4.eventduration, errors="coerce")

print("[StepB] module split done", file=sys.stderr)

def agg_uv_pv(df, tokens_filter=None):
    """return (uv, pv) for a frame"""
    if tokens_filter is not None:
        df = df[df.token.isin(tokens_filter)]
    return df.token.nunique(), len(df)

# ---------- per-page overall & module metrics ----------
def page_overall(pg):
    ex = d2[d2["pg"] == pg]
    ck = d3[d3["pg"] == pg]
    exposure_uv = ex.token.nunique()
    click_uv_full = ck.token.nunique()
    # offpage strip: which sections to remove from CTR numerator for this page
    strip_secs = set()
    if pg in STRIP["strip_venue_tab_pages"]:
        strip_secs.add(STRIP["strip_venue_tab_section"])
    if pg in STRIP["strip_bottom_nav_pages"]:
        strip_secs.add(STRIP["strip_bottom_nav_section"])
    # onpage click uv = users who clicked at least one non-strip section
    onpage_ck = ck[~ck["sec"].isin(strip_secs)]
    click_uv_onpage = onpage_ck.token.nunique()
    return {
        "exposure_uv": exposure_uv,
        "click_uv_full": click_uv_full,
        "click_uv_onpage": click_uv_onpage,
        "uv_ctr_onpage": round(click_uv_onpage / exposure_uv, 4) if exposure_uv else None,
        "uv_ctr_full": round(click_uv_full / exposure_uv, 4) if exposure_uv else None,
        "strip_secs": strip_secs,
    }

def module_metrics_for(ex_df, ck_df, exposure_uv_page, mod, cap_home_uv=None, cap_home_layer=None):
    """compute one module dict on a given page-scoped frame; handle venue tab cap."""
    e = ex_df[ex_df["mod"] == mod]
    c = ck_df[ck_df["mod"] == mod]
    exp_uv = e.token.nunique()
    exp_pv = len(e)
    clk_uv = c.token.nunique()
    clk_pv = len(c)
    capped = None
    denom = exp_uv
    if mod == "场馆tab" and cap_home_uv:
        ratio = exp_uv / cap_home_uv if cap_home_uv else 0
        if ratio < CAP_TH:
            capped = {
                "rule": "venue_tab_section_106",
                "raw_exposure_uv": exp_uv,
                "raw_exposure_pv": exp_pv,
                "raw_uv_ctr": round(clk_uv / exp_uv, 6) if exp_uv else None,
                "ratio_to_home": round(ratio, 4),
                "reason": "曝光埋点漏报,场馆tab是首页常驻tab,曝光UV理应≈该页曝光UV",
            }
            denom = cap_home_uv
    uv_ctr = round(clk_uv / denom, 6) if denom else None
    out = {
        "module": mod,
        "exposure_uv": denom if capped else exp_uv,
        "exposure_pv": exp_pv,
        "click_uv": clk_uv,
        "click_pv": clk_pv,
        "uv_ctr": uv_ctr,
    }
    if capped:
        out["exposure_capped"] = capped
    return out, exp_uv  # return raw exp_uv for internal use

print("[StepC] computing pages[] ...", file=sys.stderr)
pages_block = []
home_overall = None
for pg in PAGES:
    ov = page_overall(pg)
    ex = d2[d2["pg"] == pg]
    ck = d3[d3["pg"] == pg]
    # layer exposure uv on this page (事件表行内 lyr)
    layer_exposure_uv = {L: ex[ex["lyr"] == L].token.nunique() for L in ["z0","z1-z3","z4-z5"]}
    cap_home_uv = ov["exposure_uv"]
    # duration for page (from d4)
    dd = d4[d4["actiontype"] == pg]
    visit_uv = dd.token.nunique()
    pos = dd[dd.ed > 0]
    with_pos = pos.token.nunique()
    # per-user total positive duration
    dur_mean = None
    if with_pos:
        per_user = pos.groupby("token").ed.sum()   # eventduration already in seconds
        dur_mean = round(float(per_user.mean()), 1)
    # modules on this page
    mod_list = []
    for mod in CORE:
        m, raw = module_metrics_for(ex, ck, ov["exposure_uv"], mod, cap_home_uv=cap_home_uv)
        if m["exposure_uv"] == 0 and m["click_uv"] == 0 and mod not in ("场馆tab",):
            # module has no exposure on this page -> omit for pages[] (main modules[] keeps 11)
            continue
        # by_user_type for this page-module (事件表行内 lyr)
        e = ex[ex["mod"] == mod]
        c = ck[ck["mod"] == mod]
        but = {}
        for L in ["z0","z1-z3","z4-z5"]:
            eL = e[e["lyr"] == L]; cL = c[c["lyr"] == L]
            euv = eL.token.nunique()
            denomL = euv
            capL = None
            if mod == "场馆tab" and "exposure_capped" in m:
                denomL = layer_exposure_uv[L]; capL = True
            cuv = cL.token.nunique()
            but[L] = {
                "exposure_uv": denomL if capL else euv,
                "exposure_pv": len(eL),
                "click_uv": cuv,
                "click_pv": len(cL),
                "uv_ctr": round(cuv/denomL,6) if denomL else None,
            }
        m["by_user_type"] = but
        m["exposure_capped"] = m.get("exposure_capped", None)
        mod_list.append(m)
    # module_layer 三维
    module_layer = []
    for m in mod_list:
        for L in ["z0","z1-z3","z4-z5"]:
            b = m["by_user_type"][L]
            module_layer.append({
                "module": m["module"], "layer": L,
                "exposure_uv": b["exposure_uv"], "click_uv": b["click_uv"],
                "uv_ctr": b["uv_ctr"], "capped": bool(m.get("exposure_capped")),
            })
    page_entry = {
        "page_id": pg,
        "page_name": PAGE_NAMES[pg],
        "is_home": pg == PRIMARY,
        "overall": {
            "exposure_uv": ov["exposure_uv"],
            "click_uv_full": ov["click_uv_full"],
            "click_uv_onpage": ov["click_uv_onpage"],
            "uv_ctr_onpage": ov["uv_ctr_onpage"],
            "uv_ctr_full": ov["uv_ctr_full"],
            "visit_pv": len(dd),
            "duration_mean_seconds": dur_mean,
            "duration_coverage": {
                "visit_uv": visit_uv,
                "with_pos_duration_uv": with_pos,
                "no_duration_uv": visit_uv - with_pos,
                "no_duration_pct": round((visit_uv - with_pos)/visit_uv,3) if visit_uv else None,
            },
            "offpage_strip": {
                "venue_tab_106_stripped": CAP_SEC in ov["strip_secs"],
                "venue_tab_106_click_uv": ck[ck.sec==STRIP["strip_venue_tab_section"]].token.nunique(),
                "bottom_nav_500_stripped": STRIP["strip_bottom_nav_section"] in ov["strip_secs"],
                "bottom_nav_500_click_uv": ck[ck.sec==STRIP["strip_bottom_nav_section"]].token.nunique(),
            },
        },
        "modules": mod_list,
        "module_layer": module_layer,
        "layer_exposure_uv": layer_exposure_uv,
    }
    pages_block.append(page_entry)
    if pg == PRIMARY:
        home_overall = {
            "exposure_uv": ov["exposure_uv"],
            "exposure_pv": len(ex),
            "click_uv": ov["click_uv_onpage"],   # onpage for home overall
            "click_pv": len(ck[~ck["sec"].isin(ov["strip_secs"])]),
            "uv_ctr": ov["uv_ctr_onpage"],
        }

# ---------- primary modules[] main block (11 modules) ----------
print("[StepC] computing primary modules[] ...", file=sys.stderr)
ex_p = d2[d2["pg"] == PRIMARY]
ck_p = d3[d3["pg"] == PRIMARY]
home_exp_uv = home_overall["exposure_uv"]
home_lyr_uv = {L: ex_p[ex_p["lyr"]==L].token.nunique() for L in ["z0","z1-z3","z4-z5"]}
modules_main = []
for mod in CORE:
    m, raw = module_metrics_for(ex_p, ck_p, home_exp_uv, mod, cap_home_uv=home_exp_uv)
    m["exposure_coverage"] = round(m["exposure_uv"]/n_users, 6) if n_users else None
    m["exposure_pv_per_uv"] = round(m["exposure_pv"]/raw, 4) if raw else None
    e = ex_p[ex_p["mod"] == mod]
    c = ck_p[ck_p["mod"] == mod]
    but = {}
    for L in ["z0","z1-z3","z4-z5"]:
        eL=e[e["lyr"]==L]; cL=c[c["lyr"]==L]; euv=eL.token.nunique(); denomL=euv
        if mod=="场馆tab" and "exposure_capped" in m:
            denomL=home_lyr_uv[L]
        cuv=cL.token.nunique()
        but[L]={"exposure_uv":denomL if (mod=="场馆tab" and "exposure_capped" in m) else euv,
                "exposure_pv":len(eL),"click_uv":cuv,"click_pv":len(cL),
                "uv_ctr":round(cuv/denomL,6) if denomL else None}
    bus={}
    for S in e["src"].dropna().unique():
        eS=e[e["src"]==S]; cS=c[c["src"]==S]; euv=eS.token.nunique()
        cuv=cS.token.nunique()
        bus[S]={"exposure_uv":euv,"exposure_pv":len(eS),"click_uv":cuv,"click_pv":len(cS),
                "uv_ctr":round(cuv/euv,6) if euv else None}
    m["by_user_type"]=but
    m["by_user_source"]=bus
    modules_main.append(m)

# save intermediate for next stages
inter = {
    "n_users": n_users, "layer_dist": layer_dist, "src_dist": src_dist,
    "token_cov": token_cov, "pnz_hit": round(float(pnz_hit),4), "snz_hit": round(float(snz_hit),4),
    "unmapped_exposure_pv_pct": unmapped_exposure_pv_pct,
    "home_overall": home_overall, "modules": modules_main, "pages": pages_block,
}
os.makedirs(".tmp_shufen", exist_ok=True)
with open(".tmp_shufen/inter_stageC.json","w",encoding="utf-8") as f:
    json.dump(inter,f,ensure_ascii=False,default=str)
print("[StepC] done. duration scale check (home dur_mean):", home_overall, file=sys.stderr)
print("MODULES_MAIN_LEN", len(modules_main), file=sys.stderr)
for m in modules_main:
    print(f"  {m['module']:8s} expUV={m['exposure_uv']:6d} clkUV={m['click_uv']:6d} ctr={m['uv_ctr']}", file=sys.stderr)

# ========== Step D: 模式发现 ==========
print("[StepD] anomaly / patterns ...", file=sys.stderr)
import datetime as _dt
dt_obj = _dt.date.fromisoformat(DT)
dow_of_dt = dt_obj.weekday()  # 0=Mon..6=Sun

bl = pd.read_csv(BLDIR + f"module_daily_baseline_{DT}.csv")
bl["dt"] = bl["dt"].astype(str)
bl["_d"] = bl["dt"].map(_dt.date.fromisoformat)
bl["_dow"] = bl["_d"].map(lambda d: d.weekday())
win_start = dt_obj - _dt.timedelta(days=28)
win = bl[(bl["_d"] >= win_start) & (bl["_d"] <= dt_obj - _dt.timedelta(days=1))]

METRICS = ["uv_ctr", "exposure_uv", "click_uv", "exposure_pv", "click_pv"]
# today values from OUR computation (primary page) — use baseline row for scope where possible,
# but per contract 'today' should be current-day value. Use baseline's dt==DT row (same 1/339 sampling as window) for apples-to-apples.
today_bl = bl[bl["_d"] == dt_obj]

def baseline_anomaly():
    details = []
    scopes = ["home_overall"] + CORE
    for scope in scopes:
        w = win[(win["page_id"] == PRIMARY) & (win["module"] == scope)]
        tr = today_bl[(today_bl["page_id"] == PRIMARY) & (today_bl["module"] == scope)]
        if tr.empty:
            continue
        wdow = w[w["_dow"] == dow_of_dt]
        for metric in METRICS:
            today_v = float(tr.iloc[0][metric])
            vals = w[metric].dropna().astype(float).values
            dvals = wdow[metric].dropna().astype(float).values
            n_win = len(vals); n_dow = len(dvals)
            wmean = float(np.mean(vals)) if n_win else None
            wstd = float(np.std(vals, ddof=1)) if n_win > 1 else 0.0
            z_win = round((today_v - wmean) / wstd, 4) if (wmean is not None and wstd not in (0, None)) else None
            dmean = float(np.mean(dvals)) if n_dow else None
            dstd = float(np.std(dvals, ddof=1)) if n_dow > 1 else 0.0
            z_dow = round((today_v - dmean) / dstd, 4) if (dmean is not None and n_dow >= 2 and dstd not in (0, None)) else None
            if wstd == 0: z_win = None
            if n_dow < 2 or dstd == 0: z_dow = None
            anomaly = bool(z_win is not None and z_dow is not None and abs(z_win) >= 2 and abs(z_dow) >= 2 and (z_win > 0) == (z_dow > 0))
            direction = "flat"
            if wmean is not None:
                if today_v > wmean * 1.001: direction = "up"
                elif today_v < wmean * 0.999: direction = "down"
            details.append({
                "scope": scope, "metric": metric, "today": round(today_v, 6),
                "window_mean": round(wmean, 6) if wmean is not None else None,
                "window_std": round(wstd, 6) if wstd is not None else None,
                "z_window": z_win,
                "dow_mean": round(dmean, 6) if dmean is not None else None,
                "dow_std": round(dstd, 6) if dstd is not None else None,
                "z_dow": z_dow,
                "n_window_days": n_win, "n_dow_days": n_dow,
                "anomaly": anomaly, "direction": direction,
            })
    return details

baseline_meta_ok = True
try:
    with open(BLDIR + f"module_daily_baseline_{DT}.csv.meta.json", encoding="utf-8") as f:
        baseline_meta_ok = json.load(f).get("status") == "ok"
except Exception:
    baseline_meta_ok = False

anomaly_baseline = {
    "status": "ok" if baseline_meta_ok else "unavailable",
    "window_days": 28,
    "baseline_source": f"module_daily_baseline_{DT}.csv",
    "dow_of_dt": dow_of_dt,
    "details": baseline_anomaly() if baseline_meta_ok else [],
}

# anomaly vs D-1 and vs 7d (cross-ref), from baseline table
def simple_anomaly(ref_kind):
    details = []
    scopes = ["home_overall"] + CORE
    for scope in scopes:
        tr = today_bl[(today_bl["page_id"] == PRIMARY) & (today_bl["module"] == scope)]
        if tr.empty: continue
        for metric in METRICS:
            today_v = float(tr.iloc[0][metric])
            if ref_kind == "d1":
                pr = bl[(bl["_d"] == dt_obj - _dt.timedelta(days=1)) & (bl["page_id"] == PRIMARY) & (bl["module"] == scope)]
                prev = float(pr.iloc[0][metric]) if not pr.empty else None
            else:
                w7 = win[(win["_d"] >= dt_obj - _dt.timedelta(days=7)) & (win["page_id"] == PRIMARY) & (win["module"] == scope)]
                prev = float(w7[metric].mean()) if not w7.empty else None
            delta = round((today_v - prev) / prev, 4) if prev not in (None, 0) else None
            details.append({"scope": scope, "metric": metric, "today": round(today_v, 6),
                            "prev": round(prev, 6) if prev is not None else None,
                            "delta_pct": delta,
                            "anomaly": bool(delta is not None and abs(delta) >= 0.30)})
    return details
anomaly_d1 = {"status": "ok", "details": simple_anomaly("d1")}
anomaly_7d = {"status": "ok", "details": simple_anomaly("7d")}

# high-exposure low-uv-ctr candidates (primary, exclude capped venue_tab & zero-exposure)
mm = [m for m in modules_main if m["exposure_uv"] > 0 and m["uv_ctr"] is not None]
by_exp = sorted(mm, key=lambda m: -m["exposure_uv"])
by_ctr = sorted(mm, key=lambda m: m["uv_ctr"])
exp_rank = {m["module"]: i+1 for i, m in enumerate(by_exp)}
ctr_rank_bottom = {m["module"]: i+1 for i, m in enumerate(by_ctr)}
hi_exp_lo_ctr = []
median_ctr = float(np.median([m["uv_ctr"] for m in mm]))
for m in mm:
    if exp_rank[m["module"]] <= 5 and m["uv_ctr"] < median_ctr:
        hi_exp_lo_ctr.append({"module": m["module"], "rank_exposure": exp_rank[m["module"]],
                              "uv_ctr": m["uv_ctr"], "uv_ctr_rank_from_bottom": ctr_rank_bottom[m["module"]]})

# chi-square: layer vs clicked (per module, primary)
chi_rows = []
for m in modules_main:
    if m["exposure_uv"] == 0: continue
    obs = []  # rows: clicked, not-clicked ; cols: z0/z1-z3/z4-z5
    clicked = []; notclicked = []
    ok = True
    for L in ["z0", "z1-z3", "z4-z5"]:
        b = m["by_user_type"][L]
        cu = b["click_uv"]; eu = b["exposure_uv"]
        if eu is None or eu == 0: ok = False; break
        clicked.append(cu); notclicked.append(max(eu - cu, 0))
    if not ok: continue
    chi2, df = chi2_2xk([clicked, notclicked])
    crit = CHI2_CRIT_05.get(df)
    chi_rows.append({"module": m["module"], "df": df, "chi2": round(chi2, 2),
                     "threshold_p05": crit, "significant": bool(crit and chi2 > crit),
                     "cramers_v": round(cramers_v(chi2, sum(clicked)+sum(notclicked), 3), 4)})

# feed depth:商卡feed流(108) exposure events per user, by timestamp order (count) on primary
feed = d2[(d2["pg"] == PRIMARY) & (d2["sec"] == "108")].copy()
feed_cnt = feed.groupby("token").size()
def qd(s, q): return int(np.percentile(s, q)) if len(s) else None
feed_depth = {"global": {"user_count_with_feed_exposure": int(feed["token"].nunique()),
                         "p50": qd(feed_cnt, 50), "p90": qd(feed_cnt, 90),
                         "mean": round(float(feed_cnt.mean()), 2) if len(feed_cnt) else None,
                         "max": int(feed_cnt.max()) if len(feed_cnt) else None},
              "by_user_type": {}}
feed["lyr2"] = feed["lyr"]
for L in ["z0", "z1-z3", "z4-z5"]:
    fc = feed[feed["lyr2"] == L].groupby("token").size()
    feed_depth["by_user_type"][L] = {"user_count": int(len(fc)), "p50": qd(fc, 50), "p90": qd(fc, 90),
                                     "mean": round(float(fc.mean()), 2) if len(fc) else None}

# stay duration global (primary page visits from d4)
dd_home = d4[d4["actiontype"] == PRIMARY]
pos_home = dd_home[dd_home["ed"] > 0]
per_user_home = pos_home.groupby("token")["ed"].sum()
visit_uv_home = dd_home["token"].nunique()
stay_duration = {"p50_seconds": int(np.percentile(per_user_home, 50)) if len(per_user_home) else None,
                 "p90_seconds": int(np.percentile(per_user_home, 90)) if len(per_user_home) else None,
                 "n_users_with_duration": int(len(per_user_home)),
                 "visit_uv": int(visit_uv_home),
                 "coverage": round(len(per_user_home)/visit_uv_home, 4) if visit_uv_home else None}

# module co-exposure jaccard (primary, top pairs among high-exposure modules)
mod_users = {}
for mod in CORE:
    us = set(d2[(d2["pg"] == PRIMARY) & (d2["mod"] == mod)]["token"].unique())
    if us: mod_users[mod] = us
jac = []
mods_l = list(mod_users.keys())
for i in range(len(mods_l)):
    for j in range(i+1, len(mods_l)):
        a, b = mods_l[i], mods_l[j]
        inter_n = len(mod_users[a] & mod_users[b]); uni = len(mod_users[a] | mod_users[b])
        if uni: jac.append({"a": a, "b": b, "jaccard": round(inter_n/uni, 4)})
jac = sorted(jac, key=lambda x: -x["jaccard"])[:10]

# module_subelement_rank: modules with click_uv>=100, split by section_name_zh x sortName (x tabName)
sub_rank = []
ck_p2 = d3[d3["pg"] == PRIMARY].copy()
ex_p2 = d2[d2["pg"] == PRIMARY].copy()
for mod in CORE:
    cm = ck_p2[ck_p2["mod"] == mod]
    if cm["token"].nunique() < 100: continue
    sec_id = None
    secs = cm["sec"].dropna().unique()
    if len(secs): sec_id = secs[0]
    cm = cm.copy()
    cm["sn"] = cm["sortname"].fillna("").replace({"0": ""})
    cm["sn"] = cm["sn"].map(lambda x: x if x not in ("", "nan", "None") else "未命名")
    multi_tab = cm["tabname"].notna().any()
    grp_keys = ["sn"] + (["tabname"] if multi_tab else [])
    g = cm.groupby(grp_keys)["token"].nunique().reset_index(name="click_uv").sort_values("click_uv", ascending=False)
    total_click_uv = cm["token"].nunique()
    subs = []
    for _, r in g.head(10).iterrows():
        cu = int(r["click_uv"])
        subs.append({"sortName": r["sn"], "tabName": r.get("tabname") if multi_tab else None,
                     "click_uv": cu, "exposure_uv": None, "uv_ctr": None,
                     "click_uv_share": round(cu/total_click_uv, 4) if total_click_uv else None,
                     "sample_warn": bool(cu < 30)})
    if len(g) > 10:
        rest = int(g.iloc[10:]["click_uv"].sum())
        subs.append({"sortName": f"其余{len(g)-10}个子元素合计", "tabName": None,
                     "click_uv": rest, "exposure_uv": None, "uv_ctr": None,
                     "click_uv_share": round(rest/total_click_uv, 4) if total_click_uv else None,
                     "sample_warn": None})
    sub_rank.append({"module": mod, "section_id": sec_id, "subelements": subs})

# incremental: 4-page union vs home (full-count click)
home_full_ck = d3[d3["pg"] == PRIMARY]["token"].nunique()
home_full_ex = d2[d2["pg"] == PRIMARY]["token"].nunique()
union_ck = d3["token"].nunique()
union_ex = d2["token"].nunique()
per_mod_incr = []
for mod in CORE:
    incr_e = d2[(d2["pg"] != PRIMARY) & (d2["mod"] == mod)]["token"].nunique()
    incr_c = d3[(d3["pg"] != PRIMARY) & (d3["mod"] == mod)]["token"].nunique()
    if incr_e or incr_c:
        per_mod_incr.append({"module": mod, "incr_exposure_uv": int(incr_e), "incr_click_uv": int(incr_c)})
incremental = {
    "home": {"exposure_uv": int(home_full_ex), "click_uv_full": int(home_full_ck)},
    "union_4pages": {"exposure_uv": int(union_ex), "click_uv_full": int(union_ck)},
    "net_new": {"exposure_uv": int(union_ex - home_full_ex),
                "exposure_uv_pct": round((union_ex - home_full_ex)/home_full_ex, 4) if home_full_ex else None,
                "click_uv": int(union_ck - home_full_ck),
                "click_uv_pct": round((union_ck - home_full_ck)/home_full_ck, 4) if home_full_ck else None},
    "per_module_increment": per_mod_incr,
}

ranked_ctr = [m["module"] for m in sorted(mm, key=lambda m: -m["uv_ctr"])]
ranked_exp = [m["module"] for m in by_exp]

# notable findings
notable = []
anom_true = [d for d in anomaly_baseline["details"] if d["anomaly"]]
if anom_true:
    for d in anom_true:
        notable.append(f"去周期异动: {d['scope']} {d['metric']} {d['direction']} (z_window={d['z_window']}, z_dow={d['z_dow']})")
else:
    notable.append("primary_page(G1001) home_overall + 11模块的5指标去周期双判据(z_window&z_dow同号≥2)均未触发,当日落在正常波动/周期内")
notable.append(f"场馆tab(106)触发曝光cap(埋点漏报),分母用首页曝光UV;时长覆盖率仅 {stay_duration['coverage']}(仅有正时长记录者)")
notable.append("事件表token与data1哈希格式不同无法join,分层/来源用事件表行内user_type/user_source列")

result = {
    "dt": DT,
    "n_users": n_users,
    "user_layer_distribution": layer_dist,
    "user_source_distribution": src_dist,
    "token_coverage": token_cov,
    "home_overall": home_overall,
    "modules": modules_main,
    "module_unmapped_summary": {"exposure_pv_pct": unmapped_exposure_pv_pct},
    "chi_square_layer_vs_click": chi_rows,
    "high_exposure_low_uv_ctr_candidates": hi_exp_lo_ctr,
    "feed_depth": feed_depth,
    "stay_duration": stay_duration,
    "module_co_exposure_jaccard": jac,
    "anomaly_vs_d_minus_1": anomaly_d1,
    "anomaly_vs_7d": anomaly_7d,
    "anomaly_vs_baseline": anomaly_baseline,
    "ctr_data_quality_issues": [],
    "notable_findings": notable,
    "ranked_by_uv_ctr_desc": ranked_ctr,
    "ranked_by_exposure_desc": ranked_exp,
    "module_subelement_rank": sub_rank,
    "pages": pages_block,
    "incremental": incremental,
    "_meta": {"pnz_hit": round(float(pnz_hit), 4), "snz_hit": round(float(snz_hit), 4),
              "median_uv_ctr_primary": round(median_ctr, 6)},
}

def clean(o):
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(x) for x in o]
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)):
        f = float(o); return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else o
    return o

result = clean(result)
outpath = OUTDIR + f"exploration_淑芬_{DT}.json"
with open(outpath, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"[StepD] wrote {outpath}", file=sys.stderr)
print("[StepD] anomaly_true count:", len(anom_true), file=sys.stderr)
print("[StepD] hi_exp_lo_ctr:", [c["module"] for c in hi_exp_lo_ctr], file=sys.stderr)
print("[StepD] chi significant:", [c["module"] for c in chi_rows if c["significant"]], file=sys.stderr)
print("[done] exploration json", file=sys.stderr)

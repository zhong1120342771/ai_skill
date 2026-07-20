#!/usr/bin/env python3
"""
Step 3 质量检查闸口(固化版)。

按 references/output-schemas.md §二的 schema 输出 quality_check_淑芬_${dt}.json。
sub-agent 不再即兴写 pandas——直接调本脚本,所有阈值集中在此处可审计。

用法:
    python scripts/qa_check.py --dt 2026-06-15

入参:
    --dt           YYYY-MM-DD,必填
    --root         数据根目录,默认 ~/.claude
    --hard-only    只判 hard_failures,跳过 soft / warn(调试用)

退出码:
    0 = passed (hard_failures 为空)
    2 = hard failure (上游应停)
    3 = 输入文件缺失
    4 = 内部异常
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

SKILL_DIR = Path(__file__).resolve().parent.parent
SECTION_MAP_FILE = SKILL_DIR / "references" / "section-to-module.json"


def load_section_map() -> dict:
    with open(SECTION_MAP_FILE, encoding="utf-8") as f:
        return json.load(f)


def normalize_section_id(s: pd.Series) -> pd.Series:
    """sectionId 在 CSV 里是 float64('302.0'),映射前先转整数再转字符串,缺失保留 NaN。"""
    return pd.to_numeric(s, errors="coerce").astype("Int64").astype(str).where(lambda x: x != "<NA>")


def find_col(df: pd.DataFrame, *candidates: str) -> str | None:
    """按候选名查找列,兼容大小写差异(sectionId / sectionid / section_id)。"""
    lookup = {c.lower(): c for c in df.columns}
    for cand in candidates:
        actual = lookup.get(cand.lower())
        if actual:
            return actual
    return None


def aggregate_user_layer(s: pd.Series) -> pd.Series:
    """data1.user_type 是 z1/z2/z3/z4/z5 细粒度;按业务定义聚合到 z0 / z1-z3 / z4-z5。"""
    def _agg(v):
        if pd.isna(v) or str(v).lower() in ("nan", "none", ""):
            return "z0"
        v = str(v).lower()
        if v in ("z1", "z2", "z3"):
            return "z1-z3"
        if v in ("z4", "z5"):
            return "z4-z5"
        if v == "z0":
            return "z0"
        return "z0"
    return s.map(_agg)


def safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"missing input: {path}")
    return pd.read_csv(path, low_memory=False)


def check_data1(df: pd.DataFrame) -> tuple[list, list, list]:
    hard, soft, warn = [], [], []
    n = len(df)
    if n < 9000 or n > 11500:
        hard.append({"check": "data1 行数", "actual": n, "threshold": "[9000, 11500]"})
    elif n < 9500 or n > 11000:
        soft.append({"check": "data1 行数", "actual": n, "threshold": "[9500, 11000]",
                     "note": "1/339 哈希桶抽样的统计涨落,可放行"})
    for col in ("dt", "token", "user_source", "user_type"):
        if col not in df.columns:
            hard.append({"check": f"data1.{col} 字段", "actual": "missing", "threshold": "must exist"})
            continue
        nr = df[col].isna().mean()
        if nr > 0.01:
            hard.append({"check": f"data1.{col} 空值率", "actual": round(float(nr), 4), "threshold": "<= 0.01"})
    return hard, soft, warn


def check_token_subset(data1: pd.DataFrame, others: dict[str, pd.DataFrame]) -> tuple[list, dict]:
    hard = []
    coverage = {}
    base = set(data1["token"].dropna().astype(str))
    for name, df in others.items():
        if "token" not in df.columns or len(df) == 0:
            hard.append({"check": f"{name}.token 列", "actual": "missing or empty"})
            coverage[name] = 0.0
            continue
        sub = set(df["token"].dropna().astype(str))
        cov = len(sub & base) / max(len(sub), 1)
        coverage[name] = round(cov, 4)
        if cov < 1.0:
            hard.append({"check": f"{name}.token 是 data1 子集", "actual": cov, "threshold": "= 1.0"})
    return hard, coverage


# 只在场馆页(G1002/3/4)才有曝光的模块——首页(G1001)没有。单页模式(pages=['G1001'])
# 下这两个模块缺失属预期,不 hard 失败,降级 soft。
VENUE_ONLY_MODULES = {"品类tab", "品牌墙"}


def check_module_coverage(data22: pd.DataFrame, section_map: dict) -> tuple[list, list, dict]:
    hard, soft = [], []
    sid_col = find_col(data22, "sectionId", "sectionid", "section_id")
    if sid_col is None:
        hard.append({"check": "data2-2.sectionId 字段", "actual": "missing", "candidates_tried": ["sectionId", "sectionid", "section_id"]})
        return hard, soft, {}

    sid_to_mod = {str(k): v for k, v in section_map["section_to_module"].items()}
    sids = normalize_section_id(data22[sid_col])
    modules = sids.map(sid_to_mod)

    seen = set(modules.dropna().unique()) - {"其他"}
    expected = set(section_map["core_modules"])
    n_expected = len(expected)
    missing = sorted(expected - seen)

    # 页面范围:配了几页?只有 home_page 一页时,场馆页专属模块(品类tab/品牌墙)缺失属预期。
    pages = section_map.get("pages") or [section_map.get("home_page", "G1001")]
    home_only = set(pages) <= {section_map.get("home_page", "G1001")}
    hard_missing = [m for m in missing if not (home_only and m in VENUE_ONLY_MODULES)]
    soft_missing = [m for m in missing if home_only and m in VENUE_ONLY_MODULES]

    if hard_missing:
        hard.append({"check": f"{n_expected} 核心模块覆盖", "actual": sorted(seen), "threshold": "全部出现",
                     "detail": f"缺失:{hard_missing}"})
    if soft_missing:
        soft.append({"check": "场馆页专属模块(品类tab/品牌墙)", "actual": "缺失", "threshold": "单页模式可缺",
                     "detail": f"单页模式下缺 {soft_missing},属预期"})

    unmapped_pv = float(modules.isna().sum()) / max(len(modules), 1)
    return hard, soft, {"core_present": sorted(seen), "missing": missing,
                        "unmapped_exposure_pv_pct": round(unmapped_pv, 4), "n_expected": n_expected}


def check_page_coverage(data22: pd.DataFrame, section_map: dict) -> tuple[list, dict]:
    """校验 data2-2 覆盖 config 里配置的所有页面(page_id)。四页模式缺页 hard 失败。"""
    hard = []
    pages = section_map.get("pages") or [section_map.get("home_page", "G1001")]
    page_col = find_col(data22, "page_id", "pageid", "actiontype")
    if page_col is None:
        # 旧单页数据没有 page_id 列,视为仅 G1001,单页模式放行、四页模式 hard 失败
        if len(pages) > 1:
            hard.append({"check": "data2-2.page_id 字段", "actual": "missing",
                         "threshold": "四页模式必带", "detail": "无 page_id 列,无法确认四页覆盖"})
        return hard, {"pages_expected": pages, "pages_seen": ["(no page_id col)"]}
    seen = set(data22[page_col].dropna().astype(str).unique())
    missing = sorted(set(pages) - seen)
    if missing:
        hard.append({"check": "页面覆盖", "actual": sorted(seen), "threshold": pages,
                     "detail": f"缺页:{missing}"})
    return hard, {"pages_expected": pages, "pages_seen": sorted(seen), "missing": missing}


def check_user_layer_distribution(df: pd.DataFrame, section_map: dict) -> tuple[list, dict]:
    soft = []
    if "user_type" not in df.columns:
        return [{"check": "user_type 字段缺失"}], {}
    layer = aggregate_user_layer(df["user_type"])
    counts = layer.value_counts(normalize=True).to_dict()
    out = {l: round(float(counts.get(l, 0.0)), 4) for l in section_map["user_layers"]}
    for l, pct in out.items():
        if pct < 0.05:
            soft.append({"check": f"用户分层 {l} 占比", "actual": pct, "threshold": ">= 0.05"})
    return soft, out


def check_user_source(df: pd.DataFrame, min_kinds: int) -> tuple[list, dict]:
    soft = []
    if "user_source" not in df.columns:
        return [], {}
    vc = df["user_source"].value_counts().to_dict()
    if len(vc) < min_kinds:
        soft.append({"check": "用户来源种类", "actual": len(vc), "threshold": f">= {min_kinds}"})
    return soft, {k: int(v) for k, v in vc.items()}


def check_zh_mapping(df: pd.DataFrame, name: str) -> list:
    warn = []
    for col in ("page_name_zh", "section_name_zh"):
        if col in df.columns:
            cov = 1.0 - float(df[col].isna().mean())
            if cov < 0.95:
                warn.append({"check": f"{name}.{col} 中文映射成功率", "actual": round(cov, 4), "threshold": ">= 0.95"})
    return warn


def spot_recompute_ctr(data22: pd.DataFrame, data32: pd.DataFrame, exploration: dict, section_map: dict) -> tuple[list, list]:
    """对 exploration 中前 2 个 core_modules,从 CSV 重算 UV-CTR 验证一致性。

    PV-CTR 已废弃,本检查用 UV-CTR(distinct token):
      uv_ctr_csv = exp_uv / clk_uv 不对 — 是 click_uv / exposure_uv,基于 distinct token。
    """
    warn = []
    out = []
    sid_to_mod = {str(k): v for k, v in section_map["section_to_module"].items()}

    def add_module_col(df: pd.DataFrame) -> pd.Series:
        col = find_col(df, "sectionId", "sectionid", "section_id")
        if col is None:
            return pd.Series([None] * len(df))
        return normalize_section_id(df[col]).map(sid_to_mod)

    exp_mod = add_module_col(data22)
    clk_mod = add_module_col(data32)

    tok22 = find_col(data22, "token", "user_id")
    tok32 = find_col(data32, "token", "user_id")

    for mod in section_map["core_modules"][:2]:
        if tok22 is None or tok32 is None:
            warn.append({"check": f"{mod} UV-CTR 抽样复算跳过", "reason": "token 列缺失"})
            continue
        exp_uv = int(data22.loc[exp_mod == mod, tok22].nunique())
        clk_uv = int(data32.loc[clk_mod == mod, tok32].nunique())
        uv_ctr_csv = round(clk_uv / exp_uv, 6) if exp_uv else 0.0
        uv_ctr_exp = next(
            (round(m["uv_ctr"], 6) for m in exploration.get("modules", [])
             if m["module"] == mod and m.get("uv_ctr") is not None),
            None,
        )
        # venue_tab 触发 cap 后 exploration.uv_ctr 用 home_overall 分母,与 CSV 重算的不一致是预期,跳过
        is_capped = next(
            (("exposure_capped" in m) for m in exploration.get("modules", []) if m["module"] == mod),
            False,
        )
        delta = round(abs(uv_ctr_csv - uv_ctr_exp), 6) if uv_ctr_exp is not None and not is_capped else None
        out.append({
            "module": mod,
            "uv_ctr_from_csv": uv_ctr_csv,
            "uv_ctr_from_exploration": uv_ctr_exp,
            "delta": delta,
            "capped": is_capped,
        })
        if delta is not None and delta > 0.01:
            warn.append({"check": f"{mod} UV-CTR 抽样复算", "csv": uv_ctr_csv, "exploration": uv_ctr_exp, "delta": delta})
    return warn, out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", required=True)
    ap.add_argument("--root", default=os.path.expanduser("~/.claude"))
    ap.add_argument("--hard-only", action="store_true")
    args = ap.parse_args()

    dt = args.dt
    root = Path(args.root)
    storage = root / "data_storage"
    reports = root / "analysis_reports"
    out_path = reports / f"quality_check_淑芬_{dt}.json"

    try:
        section_map = load_section_map()
        data1 = safe_read_csv(storage / f"data1_user_sample_淑芬_{dt}.csv")
        data22 = safe_read_csv(storage / f"data2-2_homepage_exposure_淑芬_{dt}.csv")
        data32 = safe_read_csv(storage / f"data3-2_homepage_click_淑芬_{dt}.csv")
        data42 = safe_read_csv(storage / f"data4-2_page_visit_duration_淑芬_{dt}.csv")
        with open(reports / f"exploration_淑芬_{dt}.json", encoding="utf-8") as f:
            exploration = json.load(f)
    except FileNotFoundError as e:
        print(f"[qa_check] missing input: {e}", file=sys.stderr)
        return 3

    hard, soft, warn = [], [], []
    h, s, w = check_data1(data1)
    hard += h; soft += s; warn += w

    h, token_cov = check_token_subset(data1, {"data2-2": data22, "data3-2": data32, "data4-2": data42})
    hard += h

    h, s, mod_info = check_module_coverage(data22, section_map)
    hard += h; soft += s

    h, page_info = check_page_coverage(data22, section_map)
    hard += h

    if not args.hard_only:
        s, layer_dist = check_user_layer_distribution(data1, section_map)
        soft += s
        s, src_dist = check_user_source(data1, section_map["user_sources_expected_min"])
        soft += s
        for name, df in (("data2-2", data22), ("data3-2", data32), ("data4-2", data42)):
            warn += check_zh_mapping(df, name)
        if "modules" in exploration:
            spot_warn, spot_out = spot_recompute_ctr(data22, data32, exploration, section_map)
            warn += spot_warn
        else:
            spot_out = []
    else:
        layer_dist, src_dist, spot_out = {}, {}, []

    passed = len(hard) == 0
    completeness = max(0.0, 1.0 - 0.10 * len(hard) - 0.02 * len(soft))
    validity = max(0.0, 1.0 - 0.05 * len(warn))
    consistency = 1.0 if not any(w.get("check", "").endswith("CTR 抽样复算") for w in warn) else 0.85

    result = {
        "dt": dt,
        "passed": passed,
        "hard_failures": hard,
        "soft_failures": soft,
        "warnings": warn,
        "scores": {
            "completeness": round(completeness, 2),
            "validity": round(validity, 2),
            "consistency": round(consistency, 2),
        },
        "row_counts": {
            "data1": len(data1),
            "data2-2": len(data22),
            "data3-2": len(data32),
            "data4-2": len(data42),
        },
        "user_layer_distribution": layer_dist,
        "user_source_distribution": src_dist,
        "token_coverage": token_cov,
        "module_coverage": mod_info,
        "page_coverage": page_info,
        "spot_recompute": spot_out,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[done] {out_path} passed={passed} hard={len(hard)} soft={len(soft)} warn={len(warn)}")
    return 0 if passed else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[qa_check] internal error: {e}", file=sys.stderr)
        sys.exit(4)

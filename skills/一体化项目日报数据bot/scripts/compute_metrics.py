#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一体化项目日报 Step 2：把 5 个 CSV 聚合为 7 项北极星指标的 t-1 值与历史序列。

输入：data_storage/yiti_{xianshang,xiansuo,tongshou,xiaoshida,tongshou_yiti_city}_${dt}.csv
输出：
  analysis_reports/metrics_yiti_${dt}.json
  analysis_reports/metrics_yiti_${dt}.summary.md

退出码：
  0 = 成功
  3 = 输入文件缺失
  4 = 内部异常
"""
from typing import Optional
import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CSV_TPL, REPORT_DIR, METRIC_LABELS, METRIC_FMT, METRICS_TPL, METRICS_SUMMARY_TPL


def load_csv(name: str, dt: str) -> pd.DataFrame:
    path = CSV_TPL.format(name=name, dt=dt)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    df = pd.read_csv(path, encoding="utf-8-sig")
    # 标准化日期列：可能叫 "日期" / "dt"
    for col in ("日期", "dt"):
        if col in df.columns:
            df["_dt"] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d")
            break
    return df


def daily_aggregate(dfs: dict) -> pd.DataFrame:
    """把 4 张 csv 按日聚合成宽表"""
    # 1. 线上订单：sum 总订单量、本地订单量
    xs = dfs["xianshang"].groupby("_dt").agg(
        total=("总订单量", "sum"),
        local=("本地订单量", "sum"),
    ).reset_index()
    xs["tongcheng_orders"] = xs["local"]
    xs["tongcheng_share"]  = (xs["local"] / xs["total"]).where(xs["total"] > 0, 0.0)

    # 2. 线索：xs_uv 汇总 = 线下线索量；pay_uv 汇总 = 线索转化总量
    xl = dfs["xiansuo"].groupby("_dt").agg(
        offline_leads=("线索uv", "sum"),
        lead_conv_total=("支付uv", "sum"),
    ).reset_index()

    # 3. 同售：sum 单量 / sum 库存 → 动销率（仅 type_md ∈ {小店,pro店} ，SQL 已限定）
    ts = dfs["tongshou"].groupby("_dt").agg(
        ts_orders=("同售单量", "sum"),
        ts_stock=("同售库存", "sum"),
    ).reset_index()
    ts["tongshou_orders"]        = ts["ts_orders"]
    ts["tongshou_dongxiao_rate"] = (ts["ts_orders"] / ts["ts_stock"]).where(ts["ts_stock"] > 0, 0.0)

    # 4. 小时达
    xsd = dfs["xiaoshida"].groupby("_dt").agg(
        xiaoshida_orders=("小时达订单量", "sum"),
    ).reset_index()

    out = xs[["_dt", "tongcheng_orders", "tongcheng_share"]] \
        .merge(xl[["_dt", "offline_leads", "lead_conv_total"]],          on="_dt", how="outer") \
        .merge(ts[["_dt", "tongshou_orders", "tongshou_dongxiao_rate"]], on="_dt", how="outer") \
        .merge(xsd, on="_dt", how="outer")
    out = out.sort_values("_dt").reset_index(drop=True)
    # 缺失填 0（具体指标缺失也可能因为该日某张表没数据；保守填 0）
    return out.fillna(0.0)


def tongshou_split_by_type(df_tongshou: pd.DataFrame, dt: str) -> dict:
    """同售按 type_md 拆分（pro店 / 小店）：t-1 与 t-2 的 orders / dongxiao_rate / mom。"""
    prev_dt = (datetime.strptime(dt, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")

    def _agg_for(d: str) -> dict:
        sub = df_tongshou.loc[df_tongshou["_dt"] == d]
        if sub.empty:
            return {}
        g = sub.groupby("门店类型").agg(
            orders=("同售单量", "sum"),
            stock=("同售库存", "sum"),
        ).reset_index()
        out = {}
        for _, r in g.iterrows():
            stock = float(r["stock"])
            orders = float(r["orders"])
            out[str(r["门店类型"])] = {
                "orders": orders,
                "dongxiao_rate": (orders / stock) if stock > 0 else 0.0,
            }
        return out

    today = _agg_for(dt)
    prev  = _agg_for(prev_dt)

    result = {}
    for type_name in ("pro店", "小店"):
        cur = today.get(type_name, {"orders": 0.0, "dongxiao_rate": 0.0})
        pv  = prev.get(type_name)
        def _mom(now, before):
            if before is None or before == 0:
                return None
            return now / before - 1.0
        result[type_name] = {
            "orders":               cur["orders"],
            "orders_mom":           _mom(cur["orders"],        (pv or {}).get("orders")),
            "dongxiao_rate":        cur["dongxiao_rate"],
            "dongxiao_rate_mom":    _mom(cur["dongxiao_rate"], (pv or {}).get("dongxiao_rate")),
        }
    return result


def tongshou_xiaodian_yiti_city_split(df_yiti: pd.DataFrame, dt: str) -> dict:
    """小店同售按城市拆三档：对照城市 / 一体化覆盖城市（小店） / 其他城市。t-1 与 t-2 的 orders / dongxiao_rate / mom。"""
    prev_dt = (datetime.strptime(dt, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")

    def _agg_for(d: str) -> dict:
        sub = df_yiti.loc[df_yiti["_dt"] == d]
        if sub.empty:
            return {}
        g = sub.groupby("是否一体化城市").agg(
            orders=("同售单量", "sum"),
            stock=("同售库存", "sum"),
        ).reset_index()
        out = {}
        for _, r in g.iterrows():
            stock = float(r["stock"])
            orders = float(r["orders"])
            out[str(r["是否一体化城市"])] = {
                "orders": orders,
                "dongxiao_rate": (orders / stock) if stock > 0 else 0.0,
            }
        return out

    today = _agg_for(dt)
    prev = _agg_for(prev_dt)
    keys = ("对照城市（重庆&西安）", "一体化覆盖城市（小店）", "其他城市")
    result = {}
    for key in keys:
        cur = today.get(key, {"orders": 0.0, "dongxiao_rate": 0.0})
        pv = prev.get(key)

        def _mom(now, before):
            if before is None or before == 0:
                return None
            return now / before - 1.0

        result[key] = {
            "orders": cur["orders"],
            "orders_mom": _mom(cur["orders"], (pv or {}).get("orders")),
            "dongxiao_rate": cur["dongxiao_rate"],
            "dongxiao_rate_mom": _mom(cur["dongxiao_rate"], (pv or {}).get("dongxiao_rate")),
        }
    return result


def compute_metrics(daily: pd.DataFrame, dt: str, df_tongshou: pd.DataFrame,
                    df_tongshou_yiti: Optional[pd.DataFrame] = None) -> dict:
    metric_keys = list(METRIC_LABELS.keys())
    if dt not in set(daily["_dt"]):
        raise RuntimeError(f"daily 表中没有 dt={dt}")

    today = daily.loc[daily["_dt"] == dt].iloc[0]

    # 环比 t-1 vs t-2
    prev_dt = (datetime.strptime(dt, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    prev    = daily.loc[daily["_dt"] == prev_dt]
    prev    = prev.iloc[0] if len(prev) else None

    # 7 日均值（包含 t-1 在内的 T-7 ~ T-1）
    last7_min = (datetime.strptime(dt, "%Y-%m-%d") - timedelta(days=6)).strftime("%Y-%m-%d")
    last7 = daily.loc[(daily["_dt"] >= last7_min) & (daily["_dt"] <= dt)]

    # 当月均值
    month_prefix = dt[:7]
    month = daily.loc[daily["_dt"].str.startswith(month_prefix) & (daily["_dt"] <= dt)]

    north_star = {}
    for k in metric_keys:
        v = float(today[k])
        prev_v = float(prev[k]) if prev is not None else None
        mom = (v / prev_v - 1.0) if (prev_v is not None and prev_v != 0) else None
        north_star[k] = {
            "value":      v,
            "mom":        mom,
            "wow_mean":   float(last7[k].mean()) if len(last7) else None,
            "month_mean": float(month[k].mean()) if len(month) else None,
        }

    # monthly_series：每月所有指标的月均
    daily["_month"] = daily["_dt"].str[:7]
    monthly_series = {}
    for k in metric_keys:
        m = daily.groupby("_month")[k].mean().reset_index()
        monthly_series[k] = [{"month": r["_month"], "mean": float(r[k])} for _, r in m.iterrows()]

    # daily_series：过去 30 日（含 t-1）
    last30_min = (datetime.strptime(dt, "%Y-%m-%d") - timedelta(days=29)).strftime("%Y-%m-%d")
    last30 = daily.loc[(daily["_dt"] >= last30_min) & (daily["_dt"] <= dt)].sort_values("_dt")
    daily_series = {}
    for k in metric_keys:
        daily_series[k] = [{"dt": r["_dt"], "value": float(r[k])} for _, r in last30.iterrows()]

    # weekly_series：最近 8 周自然周（周一为周起；t-1 所在周往前共 8 周）
    target = datetime.strptime(dt, "%Y-%m-%d").date()
    this_monday = target - timedelta(days=target.weekday())
    week_windows = []
    for i in range(7, -1, -1):
        monday = this_monday - timedelta(weeks=i)
        sunday = monday + timedelta(days=6)
        week_windows.append((monday.isoformat(), sunday.isoformat()))
    weekly_series = {}
    for k in metric_keys:
        arr = []
        for monday, sunday in week_windows:
            sub = daily.loc[(daily["_dt"] >= monday) & (daily["_dt"] <= sunday)]
            mean = float(sub[k].mean()) if len(sub) else 0.0
            arr.append({"week_start": monday, "mean": mean})
        weekly_series[k] = arr

    tongshou_split = tongshou_split_by_type(df_tongshou, dt)
    tongshou_xiaodian_yiti = (
        tongshou_xiaodian_yiti_city_split(df_tongshou_yiti, dt)
        if df_tongshou_yiti is not None and not df_tongshou_yiti.empty
        else {}
    )

    return {
        "dt": dt,
        "north_star":     north_star,
        "monthly_series": monthly_series,
        "weekly_series":  weekly_series,
        "daily_series":   daily_series,
        "tongshou_split": tongshou_split,
        "tongshou_xiaodian_yiti": tongshou_xiaodian_yiti,
    }


def fmt_value(k: str, v):
    if v is None:
        return "—"
    if METRIC_FMT[k] == "rate":
        return f"{v*100:.2f}%"
    return f"{int(round(v)):,}"


def fmt_mom(v):
    if v is None:
        return "—"
    arrow = "↑" if v > 0 else ("↓" if v < 0 else "→")
    return f"{arrow}{abs(v)*100:.2f}%"


def render_summary(metrics: dict) -> str:
    dt = metrics["dt"]
    lines = [f"# 一体化日报指标摘要 · {dt}", "", "| 指标 | t-1 | 环比 | 7日均值 | 月均 |", "|---|---|---|---|---|"]
    for k, lab in METRIC_LABELS.items():
        m = metrics["north_star"][k]
        lines.append(
            f"| {lab} | {fmt_value(k, m['value'])} | {fmt_mom(m['mom'])} | "
            f"{fmt_value(k, m['wow_mean'])} | {fmt_value(k, m['month_mean'])} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", default=None)
    args = ap.parse_args()
    dt = args.dt or (date.today() - timedelta(days=1)).isoformat()

    try:
        names = ("xianshang", "xiansuo", "tongshou", "xiaoshida")
        dfs = {n: load_csv(n, dt) for n in names}
        try:
            dfs["tongshou_yiti_city"] = load_csv("tongshou_yiti_city", dt)
        except FileNotFoundError:
            dfs["tongshou_yiti_city"] = None
    except FileNotFoundError as e:
        print(f"[fatal] 缺少 CSV：{e}", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"[fatal] 加载 CSV 异常：{e}", file=sys.stderr)
        return 4

    try:
        daily = daily_aggregate(dfs)
        metrics = compute_metrics(
            daily, dt, dfs["tongshou"], dfs.get("tongshou_yiti_city")
        )
    except Exception as e:
        print(f"[fatal] 算指标异常：{e}", file=sys.stderr)
        return 4

    json_path    = METRICS_TPL.format(dt=dt)
    summary_path = METRICS_SUMMARY_TPL.format(dt=dt)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(render_summary(metrics))

    print(f"[done] {json_path}")
    print(f"[done] {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

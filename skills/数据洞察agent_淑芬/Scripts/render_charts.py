#!/usr/bin/env python3
"""
Step 4 可视化(固化版)。

读 analysis_reports/exploration_淑芬_${dt}.json,产 5 张基础图到 visualizations/${dt}/。
中文字体已在脚本顶部固定;sub-agent 不需要再处理 matplotlib 字体问题。

用法:
    python scripts/render_charts.py --dt 2026-06-15

退出码:
    0 = 5 张图全部产出
    3 = 输入 exploration JSON 缺失
    4 = 内部异常
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "Arial Unicode MS", "SimHei"]
matplotlib.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

# ---- SWD（Storytelling with Data）样式常量 ----
# 原则:一图一事;默认全灰,只给"讲故事的那个点"上色;标题陈述要点而非描述;去杂(去边框/网格)。
# 配色对色觉缺陷友好(琥珀#D97706 与红#DC2626 在红/绿色盲下仍可区分),且始终配直接标签做第二编码通道。
SWD = {
    "action":  "#D97706",  # Action Amber — 主高亮,唯一聚焦点
    "accent":  "#DC2626",  # Accent Red — 负向/下滑/警示
    "success": "#059669",  # Success Green — 正向(仅含义明确时)
    "gray900": "#1F2937",  # 标题/关键文字
    "gray600": "#6B7280",  # 轴标签/次要文字
    "gray400": "#9CA3AF",  # 网格线/边框
    "gray200": "#E5E7EB",  # 背景数据(非焦点柱/线)
    "bg":      "#F7F6F2",  # 暖米白背景
}


def _swd_axes(ax) -> None:
    """去杂:去掉上/右边框,弱化网格,背景米白。每张图保存前调一次。"""
    ax.set_facecolor(SWD["bg"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(SWD["gray400"])
    ax.tick_params(colors=SWD["gray600"], labelsize=9)
    ax.title.set_color(SWD["gray900"])
    ax.title.set_fontsize(13)
    ax.title.set_fontweight("bold")


def _save_swd(fig, out: Path) -> None:
    fig.patch.set_facecolor(SWD["bg"])
    fig.tight_layout()
    fig.savefig(out, facecolor=SWD["bg"], edgecolor="none")
    plt.close(fig)


CORE_LAYERS = ["z0", "z1-z3", "z4-z5"]

# venue_tab(section_id=106)曝光埋点漏报 cap 阈值。
# 详见 References/output-schemas.md §一 与 agents/洞察结论生成.md「场馆tab 曝光埋点 cap」。
VENUE_TAB_NAMES = {"场馆tab", "场馆Tab", "venue_tab"}
CAP_RATIO_THRESHOLD = 0.90


def _module_uv_ctr_with_cap(m: dict, home_overall: dict, home_layer: dict | None = None) -> tuple[float | None, bool]:
    """
    返回 (uv_ctr, capped):
    - 主指标 UV-CTR = click_uv / exposure_uv;PV-CTR 已废弃,本流水线不再计算
    - venue_tab 触发 cap 时:exposure_uv 用 home_overall.exposure_uv 顶替,uv_ctr 重算
    - home_layer 用于分层热力图(home_overall 缺分层 → 分层 UV-CTR cap 后置 None,符合 SKILL 规则)
    """
    exposure_uv = m.get("exposure_uv") or 0
    click_uv = m.get("click_uv") or 0

    # 优先读 sub-agent 已 cap 过的字段(若 exposure_capped 存在,说明上游已 cap,直接用)
    if "exposure_capped" in m:
        return (m.get("uv_ctr") if m.get("uv_ctr") is not None else (click_uv / exposure_uv if exposure_uv else None), True)

    if m.get("module") in VENUE_TAB_NAMES and exposure_uv:
        home_uv = (home_layer or home_overall or {}).get("exposure_uv") or 0
        if home_uv and exposure_uv / home_uv < CAP_RATIO_THRESHOLD:
            # 分层场景下若 home_layer 不存在,返回 None 让 heatmap 留空(SKILL 规则:cap 后分层 UV-CTR 不再算)
            if home_layer is None and home_overall:
                return (click_uv / home_overall["exposure_uv"], True) if home_overall.get("exposure_uv") else (None, True)
            elif home_layer is None:
                return (None, True)
            else:
                return (click_uv / home_uv, True)

    if m.get("uv_ctr") is not None:
        return (m["uv_ctr"], False)
    return (click_uv / exposure_uv if exposure_uv else None, False)


def chart_module_ctr_rank(exploration: dict, out: Path) -> None:
    home_overall = exploration.get("home_overall") or {}
    mods_raw = exploration["modules"]
    enriched = []
    for m in mods_raw:
        uv_ctr, capped = _module_uv_ctr_with_cap(m, home_overall)
        if uv_ctr is None:
            continue
        enriched.append((m["module"], uv_ctr, capped))
    enriched.sort(key=lambda x: x[1])  # 升序,水平条形图底部=最低
    names = [f"{n} (capped)" if c else n for (n, _, c) in enriched]
    ctrs = [v * 100 for (_, v, _) in enriched]
    # SWD:全灰打底,只高亮"利用效率最低、最该被关注"的那个非 cap 模块(机会点)。
    # cap 模块单独用浅灰描边标注,避免被误读成真实最低。
    non_cap_idx = [i for i, (_, _, c) in enumerate(enriched) if not c]
    focus = non_cap_idx[0] if non_cap_idx else None  # 升序排,首个非 cap = 最低
    colors = []
    for i, (_, _, c) in enumerate(enriched):
        if c:
            colors.append(SWD["gray200"])
        elif i == focus:
            colors.append(SWD["action"])      # 唯一高亮:最低 CTR 模块
        else:
            colors.append(SWD["gray200"])
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh(names, ctrs, color=colors)
    ax.set_xlabel("UV-CTR (%)", color=SWD["gray600"])
    focus_name = enriched[focus][0] if focus is not None else "—"
    ax.set_title(f"{focus_name} 利用效率最低,是首页头号机会点 · {exploration['dt']}")
    for i, (bar, v) in enumerate(zip(bars, ctrs)):
        lbl_color = SWD["gray900"] if (focus is not None and i == focus) else SWD["gray600"]
        ax.text(v + max(ctrs) * 0.01, bar.get_y() + bar.get_height() / 2, f"{v:.2f}%",
                va="center", fontsize=9, color=lbl_color)
    ax.set_xticks([])  # 数值已直接标在柱末,去掉冗余 x 轴刻度
    _swd_axes(ax)
    ax.spines["bottom"].set_visible(False)
    _save_swd(fig, out)


def chart_module_exposure_vs_ctr(exploration: dict, out: Path) -> None:
    home_overall = exploration.get("home_overall") or {}
    mods = exploration["modules"]
    pts = []  # (x_exposure_uv, y_ctr_pct, click_uv, label, capped)
    for m in mods:
        uv_ctr, capped = _module_uv_ctr_with_cap(m, home_overall)
        if uv_ctr is None:
            continue
        exposure_uv_for_plot = home_overall.get("exposure_uv") if capped else m.get("exposure_uv")
        if not exposure_uv_for_plot:
            continue
        pts.append((exposure_uv_for_plot, uv_ctr * 100, m.get("click_uv") or 0,
                    f"{m['module']} (capped)" if capped else m["module"], capped))
    if not pts:
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.text(0.5, 0.5, "无可绘模块", ha="center", va="center", fontsize=14, color=SWD["gray600"])
        ax.set_axis_off()
        _save_swd(fig, out)
        return
    # SWD:高曝光低 CTR = 右下象限 = 机会点。用"曝光高于中位 且 CTR 低于中位"判定焦点,高亮成 action,其余灰化。
    med_x = float(np.median([p[0] for p in pts]))
    med_y = float(np.median([p[1] for p in pts]))
    fig, ax = plt.subplots(figsize=(8, 6))
    for x, y, click_uv, lbl, capped in pts:
        is_focus = (not capped) and x >= med_x and y <= med_y
        color = SWD["action"] if is_focus else SWD["gray200"]
        edge = SWD["gray600"] if is_focus else SWD["gray400"]
        ax.scatter(x, y, s=max(60, click_uv / 50), alpha=0.85 if is_focus else 0.5,
                   c=color, edgecolors=edge, linewidths=0.8, zorder=3 if is_focus else 2)
        ax.annotate(lbl, (x, y), xytext=(5, 5), textcoords="offset points", fontsize=9,
                    color=SWD["gray900"] if is_focus else SWD["gray600"],
                    fontweight="bold" if is_focus else "normal")
    ax.axhline(med_y, color=SWD["gray400"], lw=0.8, ls="--")
    ax.axvline(med_x, color=SWD["gray400"], lw=0.8, ls="--")
    ax.set_xlabel("曝光 UV(对数轴)", color=SWD["gray600"])
    ax.set_ylabel("UV-CTR (%)", color=SWD["gray600"])
    ax.set_title(f"右下象限=曝光广但转化低,优先挖掘 · {exploration['dt']}")
    ax.set_xscale("log")
    _swd_axes(ax)
    _save_swd(fig, out)


def chart_user_layer_heatmap(exploration: dict, out: Path) -> None:
    home_overall = exploration.get("home_overall") or {}
    home_by_layer = home_overall.get("by_user_type") or {}
    mods = exploration["modules"]
    # cap 后分层 UV-CTR(home 缺分层时 venue_tab 这一行三档置 NaN,符合 SKILL 规则)
    matrix = []
    name_labels = []
    for m in mods:
        row = []
        for layer in CORE_LAYERS:
            sub = (m.get("by_user_type") or {}).get(layer) or {}
            home_layer = home_by_layer.get(layer) if home_by_layer else None
            v, _ = _module_uv_ctr_with_cap(sub | {"module": m["module"]}, home_overall, home_layer)
            row.append(np.nan if v is None else v * 100)
        matrix.append(row)
        is_capped = m.get("module") in VENUE_TAB_NAMES and any(np.isnan(x) for x in row)
        name_labels.append(f"{m['module']} (capped)" if is_capped else m["module"])
    matrix = np.array(matrix, dtype=float)
    fig, ax = plt.subplots(figsize=(7, 6))
    masked = np.ma.masked_invalid(matrix)
    cmap = plt.get_cmap("YlOrRd").copy()
    cmap.set_bad(color="#EEEEEE")
    im = ax.imshow(masked, cmap=cmap, aspect="auto")
    ax.set_xticks(range(len(CORE_LAYERS)))
    ax.set_xticklabels(CORE_LAYERS)
    ax.set_yticks(range(len(name_labels)))
    ax.set_yticklabels(name_labels)
    vmax = np.nanmax(matrix) if not np.all(np.isnan(matrix)) else 1.0
    for i in range(len(name_labels)):
        for j in range(len(CORE_LAYERS)):
            v = matrix[i, j]
            if np.isnan(v):
                ax.text(j, i, "—", ha="center", va="center", fontsize=9, color="#666")
            else:
                ax.text(j, i, f"{v:.2f}%", ha="center", va="center",
                        fontsize=8, color="black" if v < vmax * 0.6 else "white")
    fig.colorbar(im, ax=ax, label="UV-CTR (%)")
    ax.set_title(f"模块 × 用户分层 UV-CTR 热力图 · {exploration['dt']}\n(场馆tab 分层 cap 后不可计算,留空)")
    ax.title.set_color(SWD["gray900"])
    ax.title.set_fontsize(13)
    ax.title.set_fontweight("bold")
    ax.tick_params(colors=SWD["gray600"], labelsize=9)
    _save_swd(fig, out)


def chart_daily_trend(exploration: dict, out: Path) -> None:
    """D/D-1 异动:取 anomaly_vs_d_minus_1.details,横向条形展示 delta_pct。"""
    raw = exploration.get("anomaly_vs_d_minus_1") or {}
    items = raw.get("details") if isinstance(raw, dict) else raw
    items = items or []

    def _empty(msg: str) -> None:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=14, color=SWD["gray600"])
        ax.set_axis_off()
        _save_swd(fig, out)

    if not items:
        _empty("无 D/D-1 异动数据")
        return
    items_sorted = sorted(items, key=lambda x: abs(x.get("delta_pct", 0) or 0), reverse=True)
    # 过滤旧 PV-CTR 口径(metric == 'ctr')——本流水线不再产出 PV-CTR;'uv_ctr' 与绝对量保留
    items_sorted = [a for a in items_sorted if a.get("metric") != "ctr"][:10]
    if not items_sorted:
        _empty("无 D/D-1 异动数据(过滤 PV-CTR 后)")
        return
    labels = [f"{(a.get('scope') or a.get('module') or '?')}·{a.get('metric', '')}" for a in items_sorted]
    deltas = [(a.get("delta_pct") or 0) * 100 for a in items_sorted]
    # SWD:只让最大绝对变化那一条上色(跌=红/涨=琥珀),其余灰化打底。一图一事:今天最该看哪个异动。
    focus = int(np.argmax([abs(d) for d in deltas]))
    colors = []
    for i, d in enumerate(deltas):
        if i == focus:
            colors.append(SWD["accent"] if d < 0 else SWD["action"])
        else:
            colors.append(SWD["gray200"])
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(labels[::-1], deltas[::-1], color=colors[::-1])
    ax.axvline(0, color=SWD["gray400"], lw=0.8)
    ax.set_xlabel("vs D-1 变化 (%)", color=SWD["gray600"])
    f_lbl, f_delta = labels[focus], deltas[focus]
    direction = "下行" if f_delta < 0 else "上行"
    ax.set_title(f"{f_lbl} {direction} {abs(f_delta):.1f}%,当日最大异动 · {exploration['dt']}")
    for bar, d in zip(bars, deltas[::-1]):
        ax.text(d + (0.5 if d >= 0 else -0.5), bar.get_y() + bar.get_height() / 2,
                f"{d:+.1f}%", va="center", ha="left" if d >= 0 else "right",
                fontsize=9, color=SWD["gray600"])
    ax.set_xticks([])
    _swd_axes(ax)
    _save_swd(fig, out)


def chart_feed_depth(exploration: dict, out: Path) -> None:
    fd = exploration.get("feed_depth") or {}
    by_layer = fd.get("by_user_type") or {}
    if not by_layer:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "无 feed 深度数据", ha="center", va="center", fontsize=14, color=SWD["gray600"])
        ax.set_axis_off()
        _save_swd(fig, out)
        return

    layers = [l for l in CORE_LAYERS if l in by_layer]
    p50s = [by_layer[l].get("p50", 0) for l in layers]
    p90s = [by_layer[l].get("p90", 0) for l in layers]
    means = [by_layer[l].get("mean", 0) for l in layers]

    x = np.arange(len(layers))
    w = 0.25
    fig, ax = plt.subplots(figsize=(9, 5))
    # SWD:不用彩虹三色;P50/Mean 灰阶打底,P90(尾部深度=故事)用 action 高亮。直接标签替代图例。
    ax.bar(x - w, p50s, w, label="P50", color=SWD["gray200"])
    ax.bar(x, means, w, label="Mean", color=SWD["gray400"])
    ax.bar(x + w, p90s, w, label="P90", color=SWD["action"])
    for xi, (p50, mean, p90) in zip(x, zip(p50s, means, p90s)):
        ax.text(xi - w, p50, f"{p50}", ha="center", va="bottom", fontsize=8, color=SWD["gray600"])
        ax.text(xi, mean, f"{mean:.1f}" if isinstance(mean, float) else f"{mean}",
                ha="center", va="bottom", fontsize=8, color=SWD["gray600"])
        ax.text(xi + w, p90, f"{p90}", ha="center", va="bottom", fontsize=8,
                color=SWD["gray900"], fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(layers)
    ax.set_ylabel("feed 翻页深度(张数)", color=SWD["gray600"])
    ax.set_title(f"P90 深度按分层分化,尾部用户翻得更深 · {exploration['dt']}")
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    g = fd.get("global") or {}
    if g:
        ax.text(0.99, 0.86, f"全量 P50={g.get('p50','?')} / P90={g.get('p90','?')} / Mean={g.get('mean','?')}",
                transform=ax.transAxes, ha="right", va="top", fontsize=9, color=SWD["gray600"])
    _swd_axes(ax)
    _save_swd(fig, out)


# ============================================================
# 四页对比图(2026-07-13):读 exploration 的 pages[] + incremental 块。
# 单页模式(pages 只有 G1001)下 pages[] 只有一条,增量图 net_new≈0,仍能出图但意义弱化;
# 缺 pages[] 块(旧单页 exploration)则整组跳过,不报错(向后兼容)。
# 全量量级用 ratio = dau_full.uv / n_users 放大;取不到 dau_full 时 ratio=1,按抽样值画并在标题标注。
# ============================================================
PAGE_ORDER = ["G1001", "G1002", "G1003", "G1004"]


def _load_ratio(root: Path, dt: str, exploration: dict) -> tuple[float, bool]:
    """返回 (ratio, is_full)。dau_full 在则 ratio=dau_uv/n_users(全量),否则 (1.0, False)(抽样)。"""
    import csv
    n_users = exploration.get("n_users") or 0
    dau_csv = root / "data_storage" / f"dau_full_淑芬_{dt}.csv"
    if dau_csv.exists() and n_users:
        try:
            with open(dau_csv, encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
            if rows and "uv" in rows[0]:
                dau_uv = int(float(rows[0]["uv"]))
                return dau_uv / n_users, True
        except Exception:
            pass
    return 1.0, False


def _pages_sorted(exploration: dict) -> list[dict]:
    pages = exploration.get("pages") or []
    order = {p: i for i, p in enumerate(PAGE_ORDER)}
    return sorted(pages, key=lambda pg: order.get(pg.get("page_id"), 99))


def chart_page_overall_compare(exploration: dict, ratio: float, is_full: bool, out: Path) -> bool:
    """四页整体对比:曝光/点击 UV(全量,对数轴) 双柱 + uv_ctr_onpage 折线。"""
    pages = _pages_sorted(exploration)
    if len(pages) < 2:
        return False
    labels = [f"{p['page_id']}\n{p.get('page_name','')}" for p in pages]
    x = np.arange(len(pages))
    unit = 1e4 if is_full else 1.0
    exp = [(p["overall"].get("exposure_uv") or 0) * ratio / unit for p in pages]
    clk = [(p["overall"].get("click_uv_full") or p["overall"].get("click_uv_onpage") or 0) * ratio / unit for p in pages]
    ctr = [(p["overall"].get("uv_ctr_onpage") or 0) * 100 for p in pages]
    w = 0.38
    fig, ax1 = plt.subplots(figsize=(9, 5.2))
    ax1.bar(x - w/2, exp, w, label=f"曝光UV{'(万)' if is_full else '(抽样)'}", color=SWD["gray400"])
    ax1.bar(x + w/2, clk, w, label=f"点击UV{'(万)' if is_full else '(抽样)'}", color=SWD["action"])
    ax1.set_ylabel(f"UV{'（万，全量）' if is_full else '（抽样值）'}", color=SWD["gray600"])
    ax1.set_yscale("log")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax2 = ax1.twinx()
    ax2.plot(x, ctr, "o-", color=SWD["accent"], label="页内UV-CTR(%)", linewidth=2, markersize=8)
    ax2.set_ylabel("页内 UV-CTR (%)", color=SWD["gray600"])
    ax2.set_ylim(0, 100)
    for i, v in enumerate(ctr):
        ax2.annotate(f"{v:.1f}%", (x[i], v), textcoords="offset points", xytext=(0, 8),
                     ha="center", color=SWD["accent"], fontsize=9)
    l1, la1 = ax1.get_legend_handles_labels()
    l2, la2 = ax2.get_legend_handles_labels()
    ax1.legend(l1 + l2, la1 + la2, loc="upper right", frameon=False, fontsize=9)
    ax1.set_title(f"四页整体对比 · 曝光/点击UV + 页内UV-CTR · {exploration['dt']}")
    _swd_axes(ax1)
    _save_swd(fig, out)
    return True


def chart_page_module_ctr_matrix(exploration: dict, out: Path) -> bool:
    """page × module UV-CTR(%) 热力矩阵(* 标注场馆tab cap)。"""
    pages = _pages_sorted(exploration)
    if len(pages) < 2:
        return False
    mods = list(exploration.get("_core_modules") or [])
    if not mods:
        # 从各页模块并集补齐(按首页顺序优先)
        seen = []
        for p in pages:
            for m in p.get("modules", []):
                if m["module"] not in seen:
                    seen.append(m["module"])
        mods = seen
    labels = [f"{p['page_id']}\n{p.get('page_name','')}" for p in pages]
    M = np.full((len(mods), len(pages)), np.nan)
    cap_mark = np.zeros((len(mods), len(pages)), dtype=bool)
    for j, p in enumerate(pages):
        mdict = {m["module"]: m for m in p.get("modules", [])}
        for i, mod in enumerate(mods):
            m = mdict.get(mod)
            if m and m.get("uv_ctr") is not None:
                M[i, j] = m["uv_ctr"] * 100
                cap_mark[i, j] = bool(m.get("exposure_capped"))
    fig, ax = plt.subplots(figsize=(1.6 + len(pages) * 1.9, 0.5 + len(mods) * 0.55))
    masked = np.ma.masked_invalid(M)
    cmap = plt.get_cmap("YlOrRd").copy()
    cmap.set_bad(color="#EEEEEE")
    vmax = np.nanmax(M) if not np.all(np.isnan(M)) else 60
    im = ax.imshow(masked, cmap=cmap, aspect="auto", vmin=0, vmax=max(vmax, 1))
    ax.set_xticks(range(len(pages)))
    ax.set_xticklabels(labels)
    ax.set_yticks(range(len(mods)))
    ax.set_yticklabels(mods)
    for i in range(len(mods)):
        for j in range(len(pages)):
            if not np.isnan(M[i, j]):
                txt = f"{M[i,j]:.1f}" + ("*" if cap_mark[i, j] else "")
                ax.text(j, i, txt, ha="center", va="center", fontsize=8,
                        color="black" if M[i, j] < vmax * 0.6 else "white")
            else:
                ax.text(j, i, "无", ha="center", va="center", fontsize=8, color="#999")
    ax.set_title(f"page × module UV-CTR(%) 矩阵(* = 场馆tab cap) · {exploration['dt']}")
    ax.title.set_color(SWD["gray900"]); ax.title.set_fontsize(13); ax.title.set_fontweight("bold")
    ax.tick_params(colors=SWD["gray600"], labelsize=9)
    fig.colorbar(im, ax=ax, label="UV-CTR (%)")
    _save_swd(fig, out)
    return True


def chart_incremental_contribution(exploration: dict, ratio: float, is_full: bool, out: Path) -> bool:
    """扩页面增量贡献:各模块 G1001 曝光UV vs 三页增量曝光UV 堆叠条形。"""
    incr = exploration.get("incremental") or {}
    per_mod = incr.get("per_module_increment") or []
    pages = _pages_sorted(exploration)
    if not per_mod or len(pages) < 2:
        return False
    # G1001 各模块曝光 UV 从首页 modules[] 取
    home = next((p for p in pages if p.get("is_home") or p.get("page_id") == "G1001"), pages[0])
    home_exp = {m["module"]: (m.get("exposure_uv") or 0) for m in home.get("modules", [])}
    mods = [d["module"] for d in per_mod]
    unit = 1e4 if is_full else 1.0
    g1 = [home_exp.get(m, 0) * ratio / unit for m in mods]
    i3 = [(d.get("incr_exposure_uv") or 0) * ratio / unit for d in per_mod]
    y = np.arange(len(mods))
    fig, ax = plt.subplots(figsize=(9.5, 0.6 + len(mods) * 0.5))
    ax.barh(y, g1, color=SWD["gray400"], label="G1001首页 曝光UV")
    ax.barh(y, i3, left=g1, color=SWD["action"], label="G1002+3+4 增量曝光UV")
    ax.set_yticks(y); ax.set_yticklabels(mods); ax.invert_yaxis()
    for i, m in enumerate(mods):
        tot = g1[i] + i3[i]
        share = (i3[i] / tot * 100) if tot else 0
        if i3[i] > 0:
            ax.text(tot, i, f" +{share:.0f}%", va="center", fontsize=8, color=SWD["action"])
    ax.set_xlabel(f"曝光UV{'（万，全量）' if is_full else '（抽样值）'}", color=SWD["gray600"])
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    ax.set_title(f"扩页面增量贡献 · 各模块 G1001 vs 三页增量 曝光UV · {exploration['dt']}")
    _swd_axes(ax)
    _save_swd(fig, out)
    return True


def chart_page_module_layer_heatmap(exploration: dict, out: Path) -> bool:
    """page × module × user_layer UV-CTR 热力(1×N 网格,每页一张子图)。"""
    pages = _pages_sorted(exploration)
    if len(pages) < 2:
        return False
    layers = CORE_LAYERS
    # 模块顺序取并集(首页优先)
    mods = []
    for p in pages:
        for row in p.get("module_layer", []):
            if row["module"] not in mods:
                mods.append(row["module"])
    if not mods:
        return False
    fig, axes = plt.subplots(1, len(pages), figsize=(3.2 + len(pages) * 3.4, 1.0 + len(mods) * 0.5), sharey=True)
    if len(pages) == 1:
        axes = [axes]
    im = None
    for k, p in enumerate(pages):
        ax = axes[k]
        lookup = {(r["module"], r["layer"]): r for r in p.get("module_layer", [])}
        layer_uv = p.get("layer_exposure_uv") or {}
        H = np.full((len(mods), len(layers)), np.nan)
        for i, m in enumerate(mods):
            for j, L in enumerate(layers):
                r = lookup.get((m, L))
                if r and r.get("uv_ctr") is not None:
                    H[i, j] = r["uv_ctr"] * 100
        masked = np.ma.masked_invalid(H)
        cmap = plt.get_cmap("YlGnBu").copy()
        cmap.set_bad(color="#EEEEEE")
        im = ax.imshow(masked, cmap=cmap, aspect="auto", vmin=0, vmax=60)
        ax.set_xticks(range(len(layers)))
        ax.set_xticklabels([f"{L}\n({layer_uv.get(L, '?')})" for L in layers], fontsize=8)
        if k == 0:
            ax.set_yticks(range(len(mods)))
            ax.set_yticklabels(mods, fontsize=9)
        for i in range(len(mods)):
            for j in range(len(layers)):
                if not np.isnan(H[i, j]):
                    ax.text(j, i, f"{H[i,j]:.0f}", ha="center", va="center", fontsize=7,
                            color="black" if H[i, j] < 35 else "white")
                else:
                    ax.text(j, i, "无", ha="center", va="center", fontsize=7, color="#BBB")
        ax.set_title(f"{p['page_id']} {p.get('page_name','')}", fontsize=10, color=SWD["gray900"])
        ax.tick_params(colors=SWD["gray600"])
    fig.suptitle(f"page × module × 分层 UV-CTR(%)(括号=该页该层人数;场馆页分层样本小仅方向) · {exploration['dt']}",
                 fontsize=11, color=SWD["gray900"])
    if im is not None:
        fig.colorbar(im, ax=axes, label="UV-CTR (%)", fraction=0.02, pad=0.01)
    fig.savefig(out, facecolor=SWD["bg"], edgecolor="none", bbox_inches="tight")
    plt.close(fig)
    return True


CORE_SUMMARY_COLS = ["模块", "机会", "策略", "优先级", "收益"]
CORE_SUMMARY_TRACK_LABEL = {"data_flow": "数据洞察", "app_experience": "app体验"}
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}
PRIORITY_FILL = {"P0": "#DC2626", "P1": "#D97706", "P2": "#6B7280"}


def _wrap(text: str, width: int) -> str:
    """按显示宽度软换行（中文按 1 宽近似），空值给占位符。"""
    s = "" if text is None else str(text).strip()
    if not s:
        return "—"
    return "\n".join(textwrap.wrap(s, width=width, break_long_words=True) or ["—"])


def _load_core_summary_rows(root: Path, dt: str) -> list[dict]:
    """
    从 opportunity_priority JSON 读机会点，拼成核心汇总表行。
    两轨道（data_flow / app_experience）合并，按 P0→P1→P2 排；轨道用列内标签区分。
    收益列优先增量点击 UV/单量/GMV，缺失或不可量化则占位。
    """
    op_path = root / "final_report" / f"opportunity_priority_淑芬_{dt}.json"
    if not op_path.exists():
        return []
    with open(op_path, encoding="utf-8") as f:
        data = json.load(f)
    rows = []
    for op in data.get("opportunities", []):
        src = op.get("source", "data_flow")
        pr = op.get("priority", "P2")
        click_uv = op.get("impact_incremental_click_uv_full")
        orders = op.get("impact_incremental_orders_full")
        gmv = op.get("impact_gmv_full")
        if click_uv is not None:
            benefit_parts = [f"增量点击 {click_uv/10000:.1f}万/日" if click_uv >= 10000 else f"增量点击 {int(click_uv)}/日"]
            if orders is not None:
                benefit_parts.append(f"单量 ≈{int(orders)}/日")
            if gmv is not None:
                benefit_parts.append(f"GMV ≈¥{gmv/10000:.1f}万/日" if gmv >= 10000 else f"GMV ≈¥{int(gmv)}/日")
            benefit = "；".join(benefit_parts)
        elif op.get("verifiable") is False:
            benefit = "待真人/埋点验证，无法量化"
        else:
            benefit = "待业务参数"
        rows.append({
            "module": op.get("module") or CORE_SUMMARY_TRACK_LABEL.get(src, src),
            "opportunity": op.get("title") or "",
            "strategy": op.get("strategy") or "",
            "priority": pr,
            "benefit": benefit,
            "track": CORE_SUMMARY_TRACK_LABEL.get(src, src),
            "_sort": (PRIORITY_ORDER.get(pr, 9), 0 if src == "data_flow" else 1,
                      -(op.get("priority_score") or 0)),
        })
    rows.sort(key=lambda r: r["_sort"])
    return rows


def chart_core_summary_table(root: Path, dt: str, out: Path) -> bool:
    """核心汇总表渲染成 PNG（飞书消息末尾配图，与文档置顶表同口径）。无机会点则不出图。"""
    rows = _load_core_summary_rows(root, dt)
    if not rows:
        return False
    # 列宽（相对），中文按等宽近似排版
    wrap_w = {"module": 8, "opportunity": 16, "strategy": 20, "priority": 4, "benefit": 14}
    cells = []
    line_counts = []  # 每行最多的换行行数，用于定高
    for r in rows:
        row_cells = [
            _wrap(r["module"], wrap_w["module"]),
            _wrap(r["opportunity"], wrap_w["opportunity"]),
            _wrap(r["strategy"], wrap_w["strategy"]),
            r["priority"],
            _wrap(r["benefit"], wrap_w["benefit"]),
        ]
        cells.append(row_cells)
        line_counts.append(max(c.count("\n") + 1 for c in row_cells))
    n = len(cells)
    # 定高：表头 1 行 + 数据行按各自换行行数，行高随内容自适应（避免多行被截断）
    header_units = 1.0
    per_line = 1.0
    data_units = [max(1, lc) * per_line for lc in line_counts]
    total_units = header_units + sum(data_units)
    unit_inch = 0.34
    fig_h = 1.1 + total_units * unit_inch
    fig, ax = plt.subplots(figsize=(13, fig_h))
    ax.set_axis_off()
    fig.patch.set_facecolor("white")
    tbl = ax.table(cellText=cells, colLabels=CORE_SUMMARY_COLS,
                   colWidths=[0.11, 0.24, 0.30, 0.08, 0.27], loc="center", cellLoc="left")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(11)
    # 逐格设高：header 用 header_units，数据行用各自的换行行数（归一到 [0,1] 高度域）
    h_header = header_units / total_units
    for (ri, ci), cell in tbl.get_celld().items():
        cell.set_edgecolor(SWD["gray400"])
        cell.set_linewidth(0.6)
        cell.PAD = 0.04
        if ri == 0:  # 表头
            cell.set_facecolor(SWD["gray900"])
            cell.set_text_props(color="white", fontweight="bold", ha="center", va="center")
            cell.set_height(h_header)
        else:
            r = rows[ri - 1]
            cell.set_height(data_units[ri - 1] / total_units)
            cell.set_facecolor("#FFFFFF" if (ri % 2) else "#F5F5F3")
            if ci == 3:  # 优先级列上色 + 居中
                cell.set_text_props(color=PRIORITY_FILL.get(r["priority"], SWD["gray600"]),
                                    fontweight="bold", ha="center", va="center")
            else:
                cell.set_text_props(color=SWD["gray900"], ha="left", va="center")
    ax.set_title(f"首页数据洞察 · 核心机会汇总 · {dt}",
                 color=SWD["gray900"], fontsize=15, fontweight="bold", pad=14)
    fig.savefig(out, facecolor="white", edgecolor="none", bbox_inches="tight", dpi=150)
    plt.close(fig)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", required=True)
    ap.add_argument("--root", default=os.path.expanduser("~/.claude"))
    ap.add_argument("--only-summary", action="store_true",
                    help="只渲染核心汇总表（Step5 回填 opportunity JSON 后单独出图用）")
    args = ap.parse_args()

    dt = args.dt
    root = Path(args.root)
    exp_path = root / "analysis_reports" / f"exploration_淑芬_{dt}.json"
    out_dir = root / "visualizations" / dt
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_png = out_dir / "core_summary_table_淑芬.png"

    # --only-summary：Step5 回填 opportunity JSON 后单独出核心汇总表配图，不重画 5 张分析图
    if args.only_summary:
        ok = chart_core_summary_table(root, dt, summary_png)
        if ok:
            print(f"[done] {summary_png}")
            return 0
        print(f"[render_charts] no opportunities for summary table (opportunity_priority_淑芬_{dt}.json missing/empty)",
              file=sys.stderr)
        return 4

    if not exp_path.exists():
        print(f"[render_charts] missing: {exp_path}", file=sys.stderr)
        return 3

    with open(exp_path, encoding="utf-8") as f:
        exploration = json.load(f)

    base_charts = [
        (chart_module_ctr_rank, "module_ctr_rank_淑芬.png"),
        (chart_module_exposure_vs_ctr, "module_exposure_vs_ctr_淑芬.png"),
        (chart_user_layer_heatmap, "user_layer_heatmap_淑芬.png"),
        (chart_daily_trend, "daily_trend_淑芬.png"),
        (chart_feed_depth, "feed_depth_distribution_淑芬.png"),
    ]
    base_names = set()
    for fn, name in base_charts:
        fn(exploration, out_dir / name)
        base_names.add(name)

    # 四页对比图(默认四页产出;单页模式 pages 只有 G1001 时各函数返回 False 自动跳过,不报错)
    ratio, is_full = _load_ratio(root, dt, exploration)
    four_page = [
        (lambda e, o: chart_page_overall_compare(e, ratio, is_full, o), "page_overall_compare_淑芬.png"),
        (chart_page_module_ctr_matrix, "page_module_ctr_matrix_淑芬.png"),
        (lambda e, o: chart_incremental_contribution(e, ratio, is_full, o), "incremental_contribution_淑芬.png"),
        (chart_page_module_layer_heatmap, "page_module_layer_heatmap_淑芬.png"),
    ]
    n_four = 0
    for fn, name in four_page:
        try:
            if fn(exploration, out_dir / name):
                n_four += 1
                base_names.add(name)
        except Exception as e:
            print(f"[render_charts] 四页图 {name} 渲染失败(跳过,不阻断): {e}", file=sys.stderr)
    if n_four:
        print(f"[info] 四页对比图产出 {n_four}/4 张(exploration 含 pages[] 块)")
    else:
        print(f"[info] 未产出四页对比图(单页模式或 exploration 缺 pages[] 块,属预期)")

    # 核心汇总表：仅当 Step5 已回填 opportunity JSON 时才有内容；Step4 阶段通常还没有，跳过不报错
    if chart_core_summary_table(root, dt, summary_png):
        print(f"[done] {summary_png}")

    analysis_pngs = [p for p in sorted(out_dir.glob("*.png")) if p.name != summary_png.name]
    for p in sorted(out_dir.glob("*.png")):
        print(f"[done] {p}")
    # 闸口仍只看 5 张基础图(四页图是增量,单页模式下本就不产出)
    return 0 if len([p for p in analysis_pngs if p.name in base_names]) >= 5 else 4


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[render_charts] internal error: {e}", file=sys.stderr)
        sys.exit(4)

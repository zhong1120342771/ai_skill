#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一体化项目日报 Step 4 - 出图：
  - yiti_monthly.png：从 2026-01 起 7 项指标月趋势（月均），最新一月标注环比上月
  - yiti_weekly.png ：最近 8 周 7 项指标周趋势（周均），最新一周标注环比上周
  - yiti_daily.png  ：过去 30 日 7 项指标日趋势，最新一日标注环比上一日

并行策略：
  3 张图相互独立，用进程池并行（matplotlib pyplot 有全局 figure manager，多线程下不稳，
  所以用 multiprocessing 各自起独立解释器，避免互踩）。

用法：
  python render_charts.py --dt 2026-06-16
  python render_charts.py --dt 2026-06-16 --workers 3
  python render_charts.py --dt 2026-06-16 --serial   # 调试或排查时退回串行
"""
import argparse
import json
import os
import sys
from datetime import date, timedelta

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import REPORT_DIR, VIS_DIR_TPL, METRIC_LABELS, METRIC_FMT, METRICS_TPL

# 中文字体
for fp in [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf",
]:
    try:
        fm.fontManager.addfont(fp)
    except Exception:
        pass
plt.rcParams["font.family"] = ["STHeiti", "PingFang SC", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

COLORS = ["#E74C3C", "#3498DB", "#9B59B6", "#E67E22", "#1ABC9C", "#2ECC71", "#F39C12"]


def fmt_value(k: str, v: float) -> str:
    if v is None:
        return "—"
    if METRIC_FMT[k] == "rate":
        return f"{v*100:.2f}%"
    return f"{int(round(v)):,}"


def fmt_delta(v: float, prev: float) -> str:
    if prev is None or prev == 0:
        return ""
    d = v / prev - 1.0
    arrow = "↑" if d > 0 else ("↓" if d < 0 else "→")
    return f"{arrow}{abs(d)*100:.1f}%"


def draw_grid(metrics: dict, mode: str, out_path: str, title: str) -> None:
    """mode: 'monthly' / 'weekly' / 'daily'"""
    fig, axes = plt.subplots(3, 3, figsize=(18, 13))
    fig.patch.set_facecolor("#FAFAFA")

    keys = list(METRIC_LABELS.keys())
    for idx, k in enumerate(keys):
        row, col = divmod(idx, 3)
        ax = axes[row][col]
        ax.set_facecolor("white")
        color = COLORS[idx]
        label = METRIC_LABELS[k]

        if mode == "monthly":
            series = metrics["monthly_series"][k]
            xs = [s["month"] for s in series]
            ys = [s["mean"] for s in series]
        elif mode == "weekly":
            series = metrics["weekly_series"][k]
            xs = [s["week_start"] for s in series]
            ys = [s["mean"] for s in series]
        else:
            series = metrics["daily_series"][k]
            xs = [s["dt"] for s in series]
            ys = [s["value"] for s in series]

        if not ys:
            ax.set_title(f"{label}（无数据）", fontsize=10, color="#aaa")
            continue

        ax.plot(range(len(xs)), ys, color=color, marker="o", markersize=4, linewidth=2.0)

        # 最新一点的环比标注
        v = ys[-1]
        prev = ys[-2] if len(ys) >= 2 else None
        delta = fmt_delta(v, prev)
        ann = f"{fmt_value(k, v)}\n{delta}"
        ax.annotate(
            ann,
            xy=(len(xs) - 1, v),
            xytext=(-65, 18),
            textcoords="offset points",
            fontsize=8,
            color=color,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor=color, alpha=0.85),
            arrowprops=dict(arrowstyle="->", color=color, lw=1),
        )

        ax.set_title(label, fontsize=10, fontweight="bold", color="#333")
        # x 轴抽稀
        if mode == "monthly":
            ax.set_xticks(range(len(xs)))
            ax.set_xticklabels(xs, fontsize=7, rotation=45)
        elif mode == "weekly":
            # 8 个点全显示，"MM-DD" 周起日
            ax.set_xticks(range(len(xs)))
            ax.set_xticklabels([s[5:] for s in xs], fontsize=7, rotation=45)
        else:
            step = max(1, len(xs) // 10)
            ticks = list(range(0, len(xs), step))
            ax.set_xticks(ticks)
            ax.set_xticklabels([xs[i][5:] for i in ticks], fontsize=7, rotation=45)

        if METRIC_FMT[k] == "rate":
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v*100:.1f}%"))
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # 隐藏多余两个子图
    for j in (7, 8):
        r, c = divmod(j, 3)
        axes[r][c].set_visible(False)

    fig.suptitle(title, fontsize=14, fontweight="bold", color="#222", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="#FAFAFA")
    plt.close()
    print(f"[done] {out_path}")


def _draw_one(args):
    """子进程入口：(metrics_path, mode, out_path, title) → out_path"""
    import json as _json
    metrics_path, mode, out_path, title = args
    with open(metrics_path, encoding="utf-8") as f:
        m = _json.load(f)
    draw_grid(m, mode, out_path, title)
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", default=None)
    ap.add_argument("--workers", type=int, default=3, help="并行进程数（默认 3，等于图表数）")
    ap.add_argument("--serial", action="store_true", help="退回串行执行（调试用）")
    args = ap.parse_args()
    dt = args.dt or (date.today() - timedelta(days=1)).isoformat()

    metrics_path = METRICS_TPL.format(dt=dt)
    if not os.path.exists(metrics_path):
        print(f"[fatal] 缺少 {metrics_path}", file=sys.stderr)
        return 3
    with open(metrics_path, encoding="utf-8") as f:
        metrics = json.load(f)

    out_dir = VIS_DIR_TPL.format(dt=dt)
    os.makedirs(out_dir, exist_ok=True)

    jobs = [
        (metrics_path, "monthly",
         os.path.join(out_dir, "yiti_monthly.png"),
         f"一体化数据｜2026 至今 月维度趋势（月均，截至 {dt}）"),
        (metrics_path, "weekly",
         os.path.join(out_dir, "yiti_weekly.png"),
         f"一体化数据｜过去 8 周 周维度趋势（周均，截至 {dt}）"),
        (metrics_path, "daily",
         os.path.join(out_dir, "yiti_daily.png"),
         f"一体化数据｜过去 30 日 日维度趋势（截至 {dt}）"),
    ]

    if args.serial:
        for job in jobs:
            draw_grid(metrics, job[1], job[2], job[3])
        return 0

    # 多进程并行：每张图独立的 matplotlib 状态机，避免互踩
    from concurrent.futures import ProcessPoolExecutor, as_completed
    print(f"[render] 并行启动 {len(jobs)} 张图（workers={args.workers}）")
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(_draw_one, job) for job in jobs]
        for fut in as_completed(futures):
            fut.result()  # 让子进程异常上抛
    return 0


if __name__ == "__main__":
    sys.exit(main())

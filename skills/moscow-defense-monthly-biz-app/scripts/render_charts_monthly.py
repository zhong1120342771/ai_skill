"""
莫斯科保卫战月报 - 数据可视化（固化版）

输出 2 张图到 ~/Downloads/msk_monthly_raw_app/<month>/charts/：
- monthly_trend_25vs26.png   大盘整体 7 指标月度 25 vs 26（1 图 GridSpec 3+4）
- dim_cvr_mom_vs_yoy.png      4 维度各子项 净支付转化率 月环比 vs 月同比 分组柱状

数据源（月粒度）：
- ~/Downloads/msk_monthly_raw_app/<month>/01_panel.csv    大盘整体行 + 4 维度拆分行

用法：
    MONTH=2026-06 python3 render_charts_monthly.py
    python3 render_charts_monthly.py 2026-06

说明：原「二、重要事项进展」5 节及其 5 张图（搜推/商详商列/电子馆/分端/新客新媒）
已随报告结构精简移除，月报只保留「一、月数据回顾」。
"""

import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.rcParams['font.family'] = ['PingFang HK', 'STHeiti', 'Arial Unicode MS', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


class DataMissing(Exception):
    """数据源为空/缺列，非渲染故障，manifest 标 data_missing"""
    pass


def _resolve_month():
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1].strip()
    env = os.environ.get('MONTH', '').strip()
    if env:
        return env
    raise SystemExit("MONTH not provided. Pass as argv[1] or env MONTH (e.g. 2026-06).")


MONTH = _resolve_month()  # YYYY-MM
DIR = Path.home() / f"Downloads/msk_monthly_raw_app/{MONTH}"
CHARTS = DIR / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)

COLOR_ORANGE = '#E97132'
COLOR_BLUE   = '#0F9ED5'
COLOR_GREEN  = '#196B24'
COLOR_RED    = '#9B2335'
COLOR_PURPLE = '#7B5EA7'
COLOR_GRID   = '#BBBBBB'
COLOR_LABEL  = '#333333'

PALETTE = [COLOR_ORANGE, COLOR_BLUE, COLOR_GREEN, COLOR_RED, COLOR_PURPLE]

# 月度趋势默认展示窗口：最近 N 个月
TREND_MONTHS = 13

manifest = {"month": MONTH, "charts": []}


def style_ax(ax, ylabel=None):
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.tick_params(left=False)
    ax.yaxis.grid(True, linestyle='-', alpha=0.18, color=COLOR_GRID)
    ax.xaxis.grid(False)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9, color=COLOR_LABEL)


def fmt_pct(v):
    """v 可能是 0.0175 / '1.75%' / None"""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if isinstance(v, str):
        s = v.strip().rstrip('%')
        if not s or s.upper() == 'NULL':
            return None
        try:
            return float(s) / 100.0
        except ValueError:
            return None
    return float(v)


def annotate_group(ax, series, pct=False, fontsize=7.5):
    """多线感知标注：同一 x 处按 y 升序阶梯避让。series: List[(xs, ys, color)]"""
    from collections import defaultdict
    bucket = defaultdict(list)
    for li, (xs, ys, color) in enumerate(series):
        for x, y in zip(xs, ys):
            if y is None or (isinstance(y, float) and np.isnan(y)):
                continue
            bucket[x].append((y, color, li))
    for x, items in bucket.items():
        items.sort(key=lambda t: t[0])
        n = len(items)
        if n == 1:
            y, color, _ = items[0]
            txt = f"{y*100:.2f}%" if pct else (f"{int(round(y)):,}" if abs(y) >= 100 else f"{y:.2f}")
            ax.annotate(txt, (x, y), textcoords='offset points',
                        xytext=(0, 8), ha='center', va='bottom',
                        fontsize=fontsize, color=color)
            continue
        step = 13
        mid = (n - 1) / 2.0
        offsets = []
        for i in range(n):
            if i >= mid:
                offsets.append((0, 8 + step * (i - int(mid)), 'bottom'))
            else:
                rank_down = int(mid) - i if n % 2 else int(mid) - i + 1
                offsets.append((0, -10 - step * (rank_down - 1), 'top'))
        for (y, color, _), (dx, dy, va) in zip(items, offsets):
            txt = f"{y*100:.2f}%" if pct else (f"{int(round(y)):,}" if abs(y) >= 100 else f"{y:.2f}")
            ax.annotate(txt, (x, y), textcoords='offset points',
                        xytext=(dx, dy), ha='center', va=va,
                        fontsize=fontsize, color=color)


def force_month_ticks(ax, months):
    """把所有月份都强制设为 xtick（months 为 int 序号列表），避免自动稀疏丢掉最新月"""
    uniq = sorted({m for m in months if m is not None})
    if not uniq:
        return
    ax.set_xticks(uniq)
    ax.set_xticklabels([_month_label(m) for m in uniq], fontsize=8)
    span = (uniq[-1] - uniq[0]) if len(uniq) > 1 else 1
    pad = max(0.5, span * 0.05)
    ax.set_xlim(uniq[0] - pad, uniq[-1] + pad)


# 月份 YYYY-MM 与连续序号互转（序号 = year*12 + month，便于跨年画连续轴）
def _mkey(ym):
    s = str(ym).strip()
    # 幂等：已是连续序号(无 '-' 的整数)时原样返回，避免二次解析报错
    if '-' not in s:
        return int(s)
    y, m = int(s[:4]), int(s[5:7])
    return y * 12 + m


def _month_label(key):
    y, m = divmod(key, 12)
    if m == 0:
        y, m = y - 1, 12
    return f"{y}/{m}"


def _recent_month_keys(all_ym, n=TREND_MONTHS):
    keys = sorted({_mkey(v) for v in all_ym})
    return keys[-n:]


# ---------- 1. monthly_trend_25vs26.png（大盘，沿用周报逻辑，从 01_panel 取整体行） ----------

def render_monthly_trend():
    df = pd.read_csv(DIR / '01_panel.csv', encoding='utf-8-sig')
    df.columns = [c.strip().lstrip('﻿') for c in df.columns]
    overall = df[(df['tag_01'] == '整体') & (df['wd'] == '整体')].copy()
    overall['月份'] = overall['月份'].astype(str)
    overall['year'] = overall['月份'].str[:4]
    overall['month'] = overall['月份'].str[5:7].astype(int)
    overall = overall.sort_values('month')

    fig = plt.figure(figsize=(20, 12), dpi=150)
    fig.suptitle(f"大盘整体核心指标 月度趋势（2025 vs 2026）  ·  截至 {MONTH}",
                 fontsize=15, color=COLOR_LABEL, y=0.99)
    gs = fig.add_gridspec(2, 12, hspace=0.45, wspace=0.85,
                          left=0.04, right=0.98, top=0.91, bottom=0.07)

    def plot_one(ax, col, title, pct=False, fmt_int=False):
        series = []
        for yr, color in [('2025', COLOR_BLUE), ('2026', COLOR_ORANGE)]:
            sub = overall[overall['year'] == yr]
            xs = sub['month'].tolist()
            ys_raw = sub[col].tolist()
            ys = [fmt_pct(v) if pct else (float(v) if not (isinstance(v, str) and v.upper() == 'NULL') else None) for v in ys_raw]
            ax.plot(xs, ys, color=color, marker='o', markersize=5,
                    linewidth=2.0, linestyle='-', label=yr)
            series.append((xs, ys, color))
        annotate_group(ax, series, pct=pct, fontsize=8)
        style_ax(ax)
        ax.set_title(title, fontsize=11, color=COLOR_LABEL, pad=10)
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels([f'{m}月' for m in range(1, 13)], fontsize=8)
        ax.legend(loc='lower right', fontsize=8, frameon=False)
        if pct:
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f'{v*100:.1f}%'))
        elif fmt_int:
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f'{int(v):,}'))

    plot_one(fig.add_subplot(gs[0, 0:4]),  'dau-净支付pv转化率', 'dau-净支付pv转化率', pct=True)
    plot_one(fig.add_subplot(gs[0, 4:8]),  'dau_日均',          'DAU（日均）',        fmt_int=True)
    plot_one(fig.add_subplot(gs[0, 8:12]), '单量',              '净支付单量（月均）', fmt_int=True)
    plot_one(fig.add_subplot(gs[1, 0:3]),  '曝光渗透率', '曝光渗透率', pct=True)
    plot_one(fig.add_subplot(gs[1, 3:6]),  '商详到达率', '商详到达率', pct=True)
    plot_one(fig.add_subplot(gs[1, 6:9]),  '下单率',    '下单率',    pct=True)
    plot_one(fig.add_subplot(gs[1, 9:12]), '支付率',    '支付率',    pct=True)

    out = CHARTS / 'monthly_trend_25vs26.png'
    fig.savefig(out, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return out


# ---------- 2. dim_cvr_mom_vs_yoy.png（各维度项本月 CVR 环比 vs 同比 分组柱状） ----------

def render_dim_cvr_mom_vs_yoy():
    """4 个维度各一子图，x=维度项，成对柱：本月净支付转化率的月环比% vs 月同比%。
    同比缺失（去年无同月）的项不画同比柱。数据经 gen_report_monthly 统一口径。"""
    import csv as _csv
    sys.path.insert(0, str(Path.home() / ".claude/skills/moscow-defense-monthly-biz-app/scripts"))
    from gen_report_monthly import index_panel, metric_with_changes, DIM_TAG, _dim_items

    idx = index_panel(list(_csv.DictReader(
        open(DIR / '01_panel.csv', encoding='utf-8-sig'))))
    dims = list(DIM_TAG.items())  # [(品类,拆分品类), ...] 固定顺序（App 端无「端」维度）
    n = len(dims)

    fig, axes = plt.subplots(n, 1, figsize=(13, 3.0 * n), dpi=150)
    if n == 1:
        axes = [axes]
    fig.suptitle(f"各维度项 净支付转化率 月环比 vs 月同比  ·  {MONTH}",
                 fontsize=15, color=COLOR_LABEL, y=0.995)

    any_data = False
    for ax, (dim_name, tag) in zip(axes, dims):
        items = _dim_items(idx, tag, MONTH)
        moms, yoys, labels = [], [], []
        for wd in items:
            _, mom, yoy = metric_with_changes(idx, tag, wd, MONTH,
                                              'dau-净支付pv转化率', True)
            labels.append(wd)
            moms.append(mom)
            yoys.append(yoy)
        if not labels:
            ax.set_visible(False)
            continue
        any_data = True
        x = np.arange(len(labels))
        w = 0.38
        mom_v = [m if m is not None else 0 for m in moms]
        yoy_v = [y if y is not None else 0 for y in yoys]
        bars1 = ax.bar(x - w / 2, mom_v, w, label='月环比', color=COLOR_ORANGE)
        bars2 = ax.bar(x + w / 2, yoy_v, w, label='月同比', color=COLOR_BLUE)
        for bars, vals, srcs in ((bars1, mom_v, moms), (bars2, yoy_v, yoys)):
            for b, v, s in zip(bars, vals, srcs):
                if s is None:
                    ax.annotate('—', (b.get_x() + b.get_width() / 2, 0),
                                ha='center', va='bottom', fontsize=7.5, color='#999999')
                    continue
                va = 'bottom' if v >= 0 else 'top'
                dy = 3 if v >= 0 else -3
                ax.annotate(f'{v:+.1f}%', (b.get_x() + b.get_width() / 2, v),
                            textcoords='offset points', xytext=(0, dy),
                            ha='center', va=va, fontsize=7.5,
                            color=COLOR_ORANGE if bars is bars1 else COLOR_BLUE)
        ax.axhline(0, color=COLOR_LABEL, linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9)
        ax.set_title(dim_name, fontsize=11, color=COLOR_LABEL, pad=8)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f'{v:.0f}%'))
        for side in ('top', 'right'):
            ax.spines[side].set_visible(False)
        ax.yaxis.grid(True, linestyle='-', alpha=0.18, color=COLOR_GRID)
        ax.legend(loc='best', fontsize=8, frameon=False)

    if not any_data:
        plt.close(fig)
        raise DataMissing("no dimension items for CVR mom/yoy bars")

    fig.tight_layout(rect=[0, 0, 1, 0.985])
    out = CHARTS / 'dim_cvr_mom_vs_yoy.png'
    fig.savefig(out, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return out


# ---------- 主流程 ----------

def safe(name, fn, section, caption):
    try:
        out = fn()
        manifest['charts'].append({
            "file": out.name, "report_section": section,
            "caption": caption, "render_status": "ok"
        })
        print(f"[OK]   {name} -> {out}")
    except DataMissing as e:
        manifest['charts'].append({
            "file": f"{name}.png", "report_section": section,
            "caption": caption, "render_status": "data_missing",
            "error": str(e)
        })
        print(f"[MISS] {name}: {e}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        manifest['charts'].append({
            "file": f"{name}.png", "report_section": section,
            "caption": caption, "render_status": "render_error",
            "error": str(e)
        })
        print(f"[FAIL] {name}: {e}")


if __name__ == '__main__':
    safe('monthly_trend_25vs26', render_monthly_trend,
         '大盘整体', '25 vs 26 月度趋势 - 7 指标')
    safe('dim_cvr_mom_vs_yoy', render_dim_cvr_mom_vs_yoy,
         '数据拆解', '各维度项 净支付转化率 月环比 vs 月同比')

    (CHARTS / 'charts_manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    ok = sum(1 for c in manifest['charts'] if c['render_status'] == 'ok')
    print(f"[done] charts rendered {ok}/{len(manifest['charts'])}, manifest={CHARTS/'charts_manifest.json'}")

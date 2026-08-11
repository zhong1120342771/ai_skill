"""
莫斯科保卫战周报 - 数据可视化（固化版）

输出 6 张图到 ~/Downloads/msk_weekly_raw_app/<week_end>/charts/：
- monthly_trend_25vs26.png   大盘整体 10 指标月度 25 vs 26（1 图 GridSpec 4+4+2）
- soutui_bagrate.png         搜推场景提袋率（搜索来自飞书 sheet）
- shangxiang_upgrade.png     商详商列升级 4 指标 × 整体/手机/2_5
- guan_penetration.png       电子馆曝光UV + 渗透率
- category_trend.png         分品类 4 指标周趋势（消电 top5 品类）
- xinmei_xinke.png           新客/新媒 × 手机/2_5 CVR + 曝光渗透

数据源：
- ~/Downloads/msk_weekly_raw_app/<week_end>/05_trend.csv
- ~/Downloads/msk_weekly_raw_app/<week_end>/06_monthly_trend.csv
- ~/Downloads/msk_weekly_raw_app/<week_end>/supp2.csv
- ~/Downloads/msk_weekly_raw_app/<week_end>/supp3.csv
- ~/Downloads/msk_weekly_raw_app/<week_end>/supp4.csv
- 飞书 sheet WrB7sjN0VhvIgjttMn2cHuALnlf (sheet_id=eeecae)  搜索提袋率
  A 列 = Excel 日期序列（base=1899-12-30），B 列 = 提袋率小数

用法：
    WEEK_END=2026-06-28 python3 render_charts.py
    python3 render_charts.py 2026-06-28
"""

import json
import os
import sys
import subprocess
from datetime import date, timedelta
from pathlib import Path

import matplotlib
matplotlib.rcParams['font.family'] = ['PingFang HK', 'STHeiti', 'Arial Unicode MS', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np


def _resolve_week_end():
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1].strip()
    env = os.environ.get('WEEK_END', '').strip()
    if env:
        return env
    raise SystemExit("WEEK_END not provided. Pass as argv[1] or env WEEK_END (e.g. 2026-06-28).")


WEEK_END = _resolve_week_end()
DIR = Path.home() / f"Downloads/msk_weekly_raw_app/{WEEK_END}"
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

manifest = {"week_end": WEEK_END, "charts": []}


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


def annotate_line(ax, xs, ys, pct=False, offset=(0, 8), color=COLOR_LABEL, fontsize=8):
    for x, y in zip(xs, ys):
        if y is None or (isinstance(y, float) and np.isnan(y)):
            continue
        txt = f"{y*100:.2f}%" if pct else (f"{int(round(y)):,}" if abs(y) >= 100 else f"{y:.2f}")
        ax.annotate(txt, (x, y), textcoords='offset points',
                    xytext=offset, ha='center', fontsize=fontsize, color=color)


def annotate_group(ax, series, pct=False, fontsize=7.5):
    """
    多线感知的标注：同一 x 处所有线的 y 收集起来，按 y 大小排序，
    用 offset_pt 阶梯避让，避免重叠。

    series: List[(xs, ys, color)] —— 每条折线
    """
    # 按 x 聚合所有 (x -> [(y, color, line_idx)])
    from collections import defaultdict
    bucket = defaultdict(list)
    for li, (xs, ys, color) in enumerate(series):
        for x, y in zip(xs, ys):
            if y is None or (isinstance(y, float) and np.isnan(y)):
                continue
            bucket[x].append((y, color, li))

    # 每个 x 内部按 y 升序，从最低开始向下偏，从最高开始向上偏，中间项尽量贴近
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

        # n >= 2: 最低的往下放（offset 负），最高的往上放（offset 正），
        # 中间的按距上下边界排序穿插。两个相邻 label 间距 ≥ ~13pt 经验值
        step = 13
        # 给每个 item 计算上下方向 + 距离
        offsets = []
        # 简单策略：偶数 idx 朝上 step*(rank)；奇数 idx 朝下 -step*(rank+1)
        # 但更直觉是：最高朝上，最低朝下，中间按 sign 交错
        mid = (n - 1) / 2.0
        for i in range(n):
            if i >= mid:
                rank_up = i - int(mid)
                offsets.append((0, 8 + step * rank_up, 'bottom'))  # 朝上
            else:
                rank_down = int(mid) - i if n % 2 else int(mid) - i + 1
                offsets.append((0, -10 - step * (rank_down - 1), 'top'))  # 朝下

        for (y, color, _), (dx, dy, va) in zip(items, offsets):
            txt = f"{y*100:.2f}%" if pct else (f"{int(round(y)):,}" if abs(y) >= 100 else f"{y:.2f}")
            ax.annotate(txt, (x, y), textcoords='offset points',
                        xytext=(dx, dy), ha='center', va=va,
                        fontsize=fontsize, color=color)


def force_week_ticks(ax, weeks):
    """把所有周的日期都强制设为 xtick，避免 matplotlib 自动稀疏后丢掉最后一周"""
    uniq = sorted({d for d in weeks if d is not None})
    if not uniq:
        return
    ax.set_xticks(uniq)
    ax.set_xticklabels([d.strftime('%m-%d') for d in uniq], fontsize=8)
    # 给最右一个点留一点 margin，免得边缘标签被裁掉
    span = (uniq[-1] - uniq[0]).days if len(uniq) > 1 else 1
    pad = max(1, span * 0.05)
    ax.set_xlim(uniq[0] - pd.Timedelta(days=pad), uniq[-1] + pd.Timedelta(days=pad))


# ---------- 1. monthly_trend_25vs26.png ----------

def render_monthly_trend():
    df = pd.read_csv(DIR / '06_monthly_trend.csv', encoding='utf-8-sig')
    df.columns = [c.strip().lstrip('﻿') for c in df.columns]
    overall = df[(df['tag_01'] == '整体') & (df['wd'] == '整体')].copy()
    overall['月份'] = overall['月份'].astype(str)
    overall['year'] = overall['月份'].str[:4]
    overall['month'] = overall['月份'].str[5:7].astype(int)
    overall = overall.sort_values('month')

    # 行 1：净支付转化率 / DAU / 单量
    # 行 2：曝光渗透率 / 商详到达率 / 下单率 / 支付率
    # 行 3：商详渗透率 / 商详转化率
    fig = plt.figure(figsize=(20, 18), dpi=150)
    fig.suptitle(f"大盘整体核心指标 月度趋势（2025 vs 2026）  ·  截至 {WEEK_END}",
                 fontsize=15, color=COLOR_LABEL, y=0.99)
    gs = fig.add_gridspec(3, 12, hspace=0.42, wspace=0.85,
                          left=0.04, right=0.98, top=0.93, bottom=0.05)

    def plot_one(ax, col, title, pct=False, fmt_int=False):
        series = []
        for yr, color, style in [('2025', COLOR_BLUE, '-'), ('2026', COLOR_ORANGE, '-')]:
            sub = overall[overall['year'] == yr]
            xs = sub['month'].tolist()
            ys_raw = sub[col].tolist()
            ys = [fmt_pct(v) if pct else (float(v) if not (isinstance(v, str) and v.upper()=='NULL') else None) for v in ys_raw]
            ax.plot(xs, ys, color=color, marker='o', markersize=5,
                    linewidth=2.0, linestyle=style, label=yr)
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

    # 行 1（4 张，每张占 3 列）
    plot_one(fig.add_subplot(gs[0, 0:3]),  'dau-净支付pv转化率', 'dau-净支付pv转化率',     pct=True)
    plot_one(fig.add_subplot(gs[0, 3:6]),  'dau_日均',          'DAU（日均）',        fmt_int=True)
    plot_one(fig.add_subplot(gs[0, 6:9]),  '单量',              '净支付单量（月均）', fmt_int=True)
    plot_one(fig.add_subplot(gs[0, 9:12]), '商详uv',            '商详UV（日均）',     fmt_int=True)

    # 行 2（4 张，每张占 3 列）
    plot_one(fig.add_subplot(gs[1, 0:3]),  '曝光渗透率',  '曝光渗透率',  pct=True)
    plot_one(fig.add_subplot(gs[1, 3:6]),  '商详到达率',  '商详到达率',  pct=True)
    plot_one(fig.add_subplot(gs[1, 6:9]),  '下单率',      '下单率',      pct=True)
    plot_one(fig.add_subplot(gs[1, 9:12]), '支付率',      '支付率',      pct=True)

    # 行 3（2 张，每张占 6 列）
    plot_one(fig.add_subplot(gs[2, 0:6]),  '商详渗透率',  '商详渗透率',  pct=True)
    plot_one(fig.add_subplot(gs[2, 6:12]), '商详转化率',  '商详转化率',  pct=True)

    out = CHARTS / 'monthly_trend_25vs26.png'
    fig.savefig(out, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return out


# ---------- 2. soutui_bagrate.png（搜索从飞书 sheet 读取） ----------

def fetch_search_bagrate_from_sheet():
    """从飞书 sheet WrB7sjN0VhvIgjttMn2cHuALnlf 读取搜索提袋率，返回 [(week_end_date, rate), ...]"""
    cmd = ["lark-cli", "sheets", "+read",
           "--spreadsheet-token", "WrB7sjN0VhvIgjttMn2cHuALnlf",
           "--range", "eeecae!A1:B200", "--as", "user"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"lark-cli sheets read failed: {r.stderr}")
    data = json.loads(r.stdout)
    values = data['data']['valueRange']['values']
    base = date(1899, 12, 30)
    out = []
    for row in values[1:]:
        if not row or row[0] is None or row[1] is None:
            continue
        try:
            d = base + timedelta(days=int(row[0]))
        except (TypeError, ValueError):
            continue
        out.append((d, float(row[1])))
    return out  # 已按表里顺序，最新在最后


def render_soutui():
    # 商详同款推荐 + 首页金刚位 从 05_trend.csv 取（口径：拆分场景 + 提袋率）
    df = pd.read_csv(DIR / '05_trend.csv', encoding='utf-8-sig')
    df.columns = [c.strip().lstrip('﻿') for c in df.columns]
    scene = df[df['tag_01'] == '拆分场景'].copy()
    scene['week_end_d'] = pd.to_datetime(scene['week_end']).dt.date
    scene = scene.sort_values('week_end_d')
    scene['提袋率_f'] = scene['提袋率'].apply(fmt_pct)

    def pick(name):
        s = scene[scene['wd'] == name][['week_end_d', '提袋率_f']].dropna().tail(8)
        return s['week_end_d'].tolist(), s['提袋率_f'].tolist()

    x_sx_推, y_sx_推 = pick('商详同款推荐')
    x_jin, y_jin = pick('首页金刚位')

    # 搜索从外部 sheet 读取（含本周 6-28）
    search_rows = fetch_search_bagrate_from_sheet()
    # 与商详同款推荐 / 首页金刚位 的最近 8 周对齐
    weeks_main = set(x_sx_推) | set(x_jin)
    if weeks_main:
        latest = max(weeks_main)
        weeks_wanted = sorted({d for d in weeks_main if (latest - d).days <= 56})
    else:
        weeks_wanted = []
    search_map = dict(search_rows)
    x_search = list(weeks_wanted)
    y_search = [search_map.get(d) for d in x_search]

    fig, ax = plt.subplots(figsize=(13, 6.5), dpi=150)
    fig.suptitle(f"搜推场景提袋率 周度趋势  ·  截至 {WEEK_END}",
                 fontsize=14, color=COLOR_LABEL, y=0.97)

    ax.plot(x_search, y_search, color=COLOR_ORANGE, marker='o', linewidth=2.0,
            markersize=6, label='搜索')
    ax.plot(x_sx_推, y_sx_推, color=COLOR_BLUE, marker='o', linewidth=2.0,
            markersize=6, label='商详同款推荐')
    ax.plot(x_jin, y_jin, color=COLOR_GREEN, marker='o', linewidth=2.0,
            markersize=6, label='首页金刚位')

    annotate_group(ax, [
        (x_search, y_search, COLOR_ORANGE),
        (x_sx_推, y_sx_推, COLOR_BLUE),
        (x_jin, y_jin, COLOR_GREEN),
    ], pct=True, fontsize=7.5)

    style_ax(ax)
    ax.set_title('搜索 / 商详同款推荐 / 首页金刚位（搜索来自飞书 sheet，含本周）',
                 fontsize=10, color=COLOR_LABEL, pad=6)
    ax.set_xlabel('周（结束日）', fontsize=9)
    ax.legend(loc='upper right', fontsize=9, frameon=False)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f'{v*100:.2f}%'))
    force_week_ticks(ax, list(x_search) + list(x_sx_推) + list(x_jin))
    for lbl in ax.get_xticklabels():
        lbl.set_rotation(25); lbl.set_ha('right')
    fig.subplots_adjust(left=0.07, right=0.98, top=0.88, bottom=0.16)

    out = CHARTS / 'soutui_bagrate.png'
    fig.savefig(out, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return out


# ---------- 3. shangxiang_upgrade.png ----------

def render_shangxiang():
    df = pd.read_csv(DIR / 'supp2.csv', encoding='utf-8-sig')
    df.columns = [c.strip().lstrip('﻿') for c in df.columns]
    df['周（结束日）'] = pd.to_datetime(df['周（结束日）']).dt.date
    df = df.sort_values('周（结束日）')

    fig, axes = plt.subplots(2, 2, figsize=(20, 11), dpi=150)
    fig.suptitle(f"商详商列升级 周度趋势  ·  截至 {WEEK_END}",
                 fontsize=14, color=COLOR_LABEL, y=0.99)

    groups = [
        ('整体', '整体', COLOR_ORANGE),
        ('拆分品类', '1-手机', COLOR_BLUE),
        ('拆分品类', '2_5类目', COLOR_GREEN),
    ]
    metrics = [('商详转化率', True), ('商详渗透率', True),
               ('曝光渗透率', True), ('提袋率', True)]

    all_weeks = df['周（结束日）'].tolist()
    for ax, (metric, pct) in zip(axes.flat, metrics):
        series = []
        for tag, name, color in groups:
            sub = df[(df['tag_01'] == tag) & (df['分类'] == name)]
            xs = sub['周（结束日）'].tolist()
            ys = [fmt_pct(v) for v in sub[metric].tolist()]
            label = name if tag != '整体' else '整体'
            ax.plot(xs, ys, color=color, marker='o', linewidth=2.0,
                    markersize=5, label=label)
            series.append((xs, ys, color))
        annotate_group(ax, series, pct=pct, fontsize=7.5)
        style_ax(ax)
        ax.set_title(metric, fontsize=11, color=COLOR_LABEL, pad=8)
        ax.legend(loc='best', fontsize=8.5, frameon=False)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f'{v*100:.2f}%'))
        force_week_ticks(ax, all_weeks)
        for lbl in ax.get_xticklabels():
            lbl.set_rotation(25); lbl.set_ha('right')

    fig.subplots_adjust(left=0.05, right=0.98, top=0.93, bottom=0.07,
                        hspace=0.42, wspace=0.18)
    out = CHARTS / 'shangxiang_upgrade.png'
    fig.savefig(out, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return out


# ---------- 4. guan_penetration.png ----------

def render_guan():
    df = pd.read_csv(DIR / 'supp3.csv', encoding='utf-8-sig')
    df.columns = [c.strip().lstrip('﻿') for c in df.columns]
    df['周（结束日）'] = pd.to_datetime(df['周（结束日）']).dt.date
    df = df.sort_values('周（结束日）')

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(20, 6.5), dpi=150)
    fig.suptitle(f"电子馆周度趋势  ·  截至 {WEEK_END}",
                 fontsize=14, color=COLOR_LABEL, y=0.99)

    halls = list(dict.fromkeys(df['馆名称'].tolist()))
    colors = PALETTE[:len(halls)]
    all_weeks = df['周（结束日）'].tolist()

    series_uv = []
    series_pen = []
    for name, color in zip(halls, colors):
        sub = df[df['馆名称'] == name]
        xs = sub['周（结束日）'].tolist()
        y_uv = sub['馆曝光uv'].tolist()
        y_pen = [fmt_pct(v) for v in sub['馆渗透率'].tolist()]
        ax_l.plot(xs, y_uv, color=color, marker='o', linewidth=2.0,
                  markersize=5, label=name)
        ax_r.plot(xs, y_pen, color=color, marker='o', linewidth=2.0,
                  markersize=5, label=name)
        series_uv.append((xs, y_uv, color))
        series_pen.append((xs, y_pen, color))
    annotate_group(ax_l, series_uv, pct=False, fontsize=7.5)
    annotate_group(ax_r, series_pen, pct=True, fontsize=7.5)

    for ax, title, pct in [(ax_l, '馆曝光UV', False), (ax_r, '馆渗透率', True)]:
        style_ax(ax)
        ax.set_title(title, fontsize=11, color=COLOR_LABEL, pad=8)
        ax.legend(loc='best', fontsize=9, frameon=False)
        if pct:
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f'{v*100:.2f}%'))
        else:
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f'{int(v):,}'))
        force_week_ticks(ax, all_weeks)
        for lbl in ax.get_xticklabels():
            lbl.set_rotation(25); lbl.set_ha('right')

    fig.subplots_adjust(left=0.05, right=0.98, top=0.88, bottom=0.16, wspace=0.18)
    out = CHARTS / 'guan_penetration.png'
    fig.savefig(out, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return out


# ---------- 5. category_trend.png（分品类 8 周趋势 2x2，仅 App 端） ----------

def render_category():
    df = pd.read_csv(DIR / '05_trend.csv', encoding='utf-8-sig')
    df.columns = [c.strip().lstrip('﻿') for c in df.columns]
    cat = df[df['tag_01'] == '拆分品类'].copy()
    cat['week_end_d'] = pd.to_datetime(cat['week_end']).dt.date
    cat = cat.sort_values('week_end_d')

    fig, axes = plt.subplots(2, 2, figsize=(20, 11), dpi=150)
    fig.suptitle(f"分品类 周度趋势  ·  截至 {WEEK_END}",
                 fontsize=14, color=COLOR_LABEL, y=0.99)

    # 消电 top5 品类（7 类全画太挤，聚焦规模最大的 5 类；5 色体系）
    cats = ['1-手机', '2_5类目', '3-N聚合', '4-平板', '5-笔记本']
    colors = [COLOR_ORANGE, COLOR_BLUE, COLOR_GREEN, COLOR_RED, COLOR_PURPLE]
    metrics = [
        ('dau-净支付pv转化率', 'dau净支付pv转化率', True, False),
        ('单量', '净支付单量（周均）', False, True),
        ('商详渗透率', '商详渗透率', True, False),
        ('商详转化率', '商详转化率', True, False),
    ]

    all_weeks = cat['week_end_d'].tolist()
    for ax, (col, title, pct, fmt_int) in zip(axes.flat, metrics):
        series = []
        for name, color in zip(cats, colors):
            sub = cat[cat['wd'] == name]
            if sub.empty:
                continue
            xs = sub['week_end_d'].tolist()
            ys = [fmt_pct(v) for v in sub[col].tolist()] if pct else sub[col].tolist()
            ax.plot(xs, ys, color=color, marker='o', linewidth=2.0,
                    markersize=5, label=name)
            series.append((xs, ys, color))
        annotate_group(ax, series, pct=pct, fontsize=7.0)
        style_ax(ax)
        ax.set_title(title, fontsize=11, color=COLOR_LABEL, pad=8)
        ax.legend(loc='best', fontsize=9, frameon=False)
        if pct:
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f'{v*100:.2f}%'))
        elif fmt_int:
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f'{int(v):,}'))
        force_week_ticks(ax, all_weeks)
        for lbl in ax.get_xticklabels():
            lbl.set_rotation(25); lbl.set_ha('right')

    fig.subplots_adjust(left=0.05, right=0.98, top=0.93, bottom=0.07,
                        hspace=0.42, wspace=0.18)
    out = CHARTS / 'category_trend.png'
    fig.savefig(out, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return out


# ---------- 6. xinmei_xinke.png ----------

def render_xinmei_xinke():
    df = pd.read_csv(DIR / 'supp4.csv', encoding='utf-8-sig')
    df.columns = [c.strip().lstrip('﻿') for c in df.columns]
    df['周(结束日)'] = pd.to_datetime(df['周(结束日)']).dt.date
    df = df.sort_values('周(结束日)')

    fig, axes = plt.subplots(1, 2, figsize=(20, 6.5), dpi=150)
    fig.suptitle(f"新客 / 新媒 - 净支付PV CVR & 曝光渗透率  ·  截至 {WEEK_END}",
                 fontsize=14, color=COLOR_LABEL, y=0.99)

    groups = [
        ('新客_1-手机',   COLOR_ORANGE, '-', '新客 · 1-手机'),
        ('新客_2_5类目', COLOR_BLUE,   '-', '新客 · 2_5类目'),
        ('新媒用户_1-手机',   COLOR_ORANGE, ':', '新媒 · 1-手机'),
        ('新媒用户_2_5类目', COLOR_BLUE,   ':', '新媒 · 2_5类目'),
    ]
    metrics = [('dau-净支付pv转化率', 'dau净支付pv转化率', True),
               ('曝光渗透率',         '曝光渗透率',    True)]

    all_weeks = df['周(结束日)'].tolist()
    for ax, (col, title, pct) in zip(axes, metrics):
        series = []
        for tag2, color, ls, label in groups:
            sub = df[df['二级标签'] == tag2]
            xs = sub['周(结束日)'].tolist()
            ys = [fmt_pct(v) for v in sub[col].tolist()]
            ax.plot(xs, ys, color=color, marker='o', linewidth=2.0,
                    markersize=5, linestyle=ls, label=label)
            series.append((xs, ys, color))
        annotate_group(ax, series, pct=pct, fontsize=7.5)
        style_ax(ax)
        ax.set_title(title, fontsize=11, color=COLOR_LABEL, pad=8)
        ax.legend(loc='best', fontsize=8.5, frameon=False, ncol=2)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f'{v*100:.2f}%'))
        force_week_ticks(ax, all_weeks)
        for lbl in ax.get_xticklabels():
            lbl.set_rotation(25); lbl.set_ha('right')

    fig.subplots_adjust(left=0.05, right=0.98, top=0.88, bottom=0.16, wspace=0.18)
    out = CHARTS / 'xinmei_xinke.png'
    fig.savefig(out, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return out


# ---------- 7. apple_trend_*.png（苹果系列 8 周趋势，整体+5品类各一张） ----------

APPLE_CATS = ['苹果整体', '手机', '平板', '笔记本', '智能手表', '耳机']
APPLE_CAT_COLOR = {
    '苹果整体': COLOR_ORANGE, '手机': COLOR_BLUE, '平板': COLOR_GREEN,
    '笔记本': COLOR_RED, '智能手表': COLOR_PURPLE, '耳机': COLOR_LABEL,
}
# 12 指标：量级 4 个（整数）+ 北极星 + 提袋率 + 6 率（百分比），恰好填满 3×4
APPLE_METRICS = [
    ('曝光UV', '曝光UV（周日均）', False),
    ('商详UV', '商详UV（周日均）', False),
    ('下单UV', '下单UV（周日均）', False),
    ('支付PV', '支付PV（周日均）', False),
    ('dau-净支付pv转化率', 'dau-净支付pv转化率', True),
    ('提袋率', '提袋率（支付PV/曝光UV）', True),
    ('曝光渗透率', '曝光渗透率', True),
    ('商详渗透率', '商详渗透率', True),
    ('商详到达率', '商详到达率', True),
    ('商详转化率', '商详转化率', True),
    ('下单率', '下单率', True),
    ('支付率', '支付率', True),
]


def _apple_trend_df():
    df = pd.read_csv(DIR / '09_apple_trend.csv', encoding='utf-8-sig')
    df.columns = [c.strip().lstrip('﻿') for c in df.columns]
    # 用「对齐周结束」作 x（去年周已 +364 映射到今年日历，供本年/去年虚线叠加）
    df['x_d'] = pd.to_datetime(df['对齐周结束']).dt.date
    return df.sort_values('x_d')


def _apple_series(sub, col, pct):
    """取一段(某年某品类)的 (xs, ys)；pct 走 fmt_pct，量级转 float"""
    xs = sub['x_d'].tolist()
    if pct:
        ys = [fmt_pct(v) for v in sub[col].tolist()]
    else:
        ys = [None if (isinstance(v, str) and v.strip().upper() in ('', 'NULL')) else float(v)
              for v in sub[col].tolist()]
    return xs, ys


def _render_apple_one(df, cat):
    """单个品类一张图：12 指标 mini-trend 拼 3×4 GridSpec；本年实线(标注)+去年同期虚线(同色浅,不标注)"""
    sub_all = df[df['维度'] == cat].copy()
    if sub_all.empty:
        raise ValueError(f"09_apple_trend.csv 无维度={cat}")
    cur = sub_all[sub_all['年份'] == '本年'].sort_values('x_d')
    ly = sub_all[sub_all['年份'] == '去年'].sort_values('x_d')
    if cur.empty:
        raise ValueError(f"09_apple_trend.csv 维度={cat} 无本年数据")
    color = APPLE_CAT_COLOR.get(cat, COLOR_ORANGE)
    all_weeks = cur['x_d'].tolist()  # x 轴锚点以本年周为准

    fig = plt.figure(figsize=(22, 15), dpi=150)
    fig.suptitle(f"苹果系列 · {cat} 核心指标 8 周趋势（仅App端，实线本年/虚线去年同期）  ·  截至 {WEEK_END}",
                 fontsize=16, color=COLOR_LABEL, y=0.995)
    gs = fig.add_gridspec(3, 4, hspace=0.42, wspace=0.28,
                          left=0.04, right=0.98, top=0.92, bottom=0.06)

    for idx, (col, title, pct) in enumerate(APPLE_METRICS):
        ax = fig.add_subplot(gs[idx // 4, idx % 4])
        xs, ys = _apple_series(cur, col, pct)
        # 去年同期虚线（同色，浅、无标注）
        if not ly.empty:
            lxs, lys = _apple_series(ly, col, pct)
            ax.plot(lxs, lys, color=color, marker='o', markersize=3.5, linewidth=1.4,
                    linestyle='--', alpha=0.45)
        # 本年实线
        ax.plot(xs, ys, color=color, marker='o', markersize=5, linewidth=2.0)
        annotate_group(ax, [(xs, ys, color)], pct=pct, fontsize=7.5)
        style_ax(ax)
        ax.set_title(title, fontsize=11, color=COLOR_LABEL, pad=8)
        if pct:
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f'{v*100:.2f}%'))
        else:
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f'{int(v):,}'))
        force_week_ticks(ax, all_weeks)
        for lbl in ax.get_xticklabels():
            lbl.set_rotation(25); lbl.set_ha('right')

    safe_name = {'苹果整体': 'overall', '手机': 'phone', '平板': 'pad',
                 '笔记本': 'laptop', '智能手表': 'watch', '耳机': 'earphone'}[cat]
    out = CHARTS / f'apple_trend_{safe_name}.png'
    fig.savefig(out, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return out


def render_apple_trend():
    df = _apple_trend_df()
    results = []
    for cat in APPLE_CATS:
        try:
            results.append((cat, _render_apple_one(df, cat)))
        except Exception as e:
            import traceback; traceback.print_exc()
            results.append((cat, None))
            print(f"[FAIL] apple_trend {cat}: {e}")
    return results


# ---------- 主流程 ----------

def safe(name, fn, section, caption):
    try:
        out = fn()
        manifest['charts'].append({
            "file": out.name, "report_section": section,
            "caption": caption, "render_status": "ok"
        })
        print(f"[OK]   {name} -> {out}")
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
         '大盘整体', '25 vs 26 月度趋势 - 10 指标')
    safe('soutui_bagrate', render_soutui,
         '分业务-搜推', '搜索/商详同款推荐/首页金刚位 提袋率')
    safe('shangxiang_upgrade', render_shangxiang,
         '分业务-商详商列', '整体/手机/2_5 4 指标')
    safe('guan_penetration', render_guan,
         '分业务-馆', '馆曝光UV + 馆渗透率')
    safe('category_trend', render_category,
         '分业务-分品类趋势', '手机/2_5/N聚合/平板/笔记本 4 指标')
    safe('xinmei_xinke', render_xinmei_xinke,
         '分业务-新客新媒', '新客/新媒 × 手机/2_5 CVR + 曝光渗透')

    # 苹果系列 8 周趋势（整体+5品类各一张，插在苹果漏斗表下方）
    try:
        for cat, out in render_apple_trend():
            if out is None:
                manifest['charts'].append({
                    "file": f"apple_trend_{cat}.png", "report_section": "苹果系列",
                    "caption": f"苹果 {cat} 8 周趋势", "render_status": "render_error",
                    "apple_cat": cat})
                print(f"[FAIL] apple_trend {cat}")
            else:
                manifest['charts'].append({
                    "file": out.name, "report_section": "苹果系列",
                    "caption": f"苹果 {cat} 核心指标 8 周趋势", "render_status": "ok",
                    "apple_cat": cat})
                print(f"[OK]   apple_trend {cat} -> {out}")
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[FAIL] apple_trend (all): {e}")

    (CHARTS / 'charts_manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    ok = sum(1 for c in manifest['charts'] if c['render_status'] == 'ok')
    print(f"[done] charts rendered {ok}/{len(manifest['charts'])}, manifest={CHARTS/'charts_manifest.json'}")


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_trend_charts.py — 核心指标趋势图（图1月均 / 图2近30日 / 图3近8周）

三张图统一按 整体 / 消费电子 / 二奢 / 兴趣 拆成 2x2 四宫格，每格独立 y 轴，
并叠加去年同期对比线（实线今年、虚线去年同期）：
  fmt_01_monthly.png  月均趋势(起始月起)；当月未满按 MTD(截到分析日 day) 对齐，
                      去年同月也截同一 day 对齐；每格标 当月MTD值 + 月环比(vs上月同窗) + 月同比(vs去年同月同窗)
  fmt_02_daily30.png  近30日日度；去年同期按 -364 天星期对齐；末点标环比(vs上周同日)
  fmt_03_weekly8.png  近8周(56天)日度；去年同期 -364 天；末点标环比(vs上周同日)

数据源：长历史周期序列 CSV（列至少含 dt, segment, dau_pay_rate），
segment 取值 大盘/消费电子/二奢/兴趣。默认读 data_storage 下最新的 periodicity_series_*.csv。
中文字体显式设置，避免方块乱码。
用法：
  python render_trend_charts.py --dt 2026-07-11 --outdir ~/.claude/visualizations/2026-07-11 \
      [--series data_storage/periodicity_series_2025-01-01_2026-07-11.csv]
"""
import argparse, os, glob
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

for f in ['PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'SimHei']:
    try:
        font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams['font.sans-serif'] = [f]; break
    except Exception:
        continue
plt.rcParams['axes.unicode_minus'] = False

SEGS = ['大盘', '消费电子', '二奢', '兴趣']
COLOR = {'大盘': '#1f4e79', '消费电子': '#c00000', '二奢': '#7030a0', '兴趣': '#2e9e5b'}
LY = '#9aa0a6'  # 去年同期灰


def load_series(path, dt):
    if not path:
        cands = sorted(glob.glob(os.path.expanduser('~/.claude/data_storage/periodicity_series_*.csv')))
        if not cands:
            raise SystemExit('找不到 periodicity_series_*.csv，请用 --series 指定长历史序列文件')
        path = cands[-1]
    df = pd.read_csv(path)
    df['dt'] = pd.to_datetime(df['dt'])
    df['star_pct'] = df['dau_pay_rate'] * 100
    return df, path


def monthly_grid(df, last, cur_day, outdir, start_year, start_month):
    def series(seg, year):
        g = df[(df.segment == seg) & (df.dt >= pd.Timestamp(year, 1, 1)) & (df.dt <= pd.Timestamp(year, last.month, 28) + pd.Timedelta(days=4))].copy()
        g = g[g.dt <= pd.Timestamp(year, last.month, 1) + pd.offsets.MonthEnd(0)]
        rows = {}
        for m, sub in g.groupby(g['dt'].dt.month):
            if m == last.month:
                sub = sub[sub['dt'].dt.day <= cur_day]  # 当月/去年同月都截到分析日 day 对齐
            rows[m] = sub['star_pct'].mean()
        return rows

    def mtd(seg, y, m):
        s = pd.Timestamp(y, m, 1); e = pd.Timestamp(y, m, cur_day)
        return df[(df.segment == seg) & (df.dt >= s) & (df.dt <= e)]['star_pct'].mean()

    months = list(range(1, last.month + 1))
    mlabel = [f'{m}月' for m in months]
    fig, axes = plt.subplots(1, 4, figsize=(22, 5.2)); axes = axes.ravel()
    for i, seg in enumerate(SEGS):
        ax = axes[i]; c = COLOR[seg]
        cur_s = series(seg, last.year); ly_s = series(seg, last.year - 1)
        ax.plot(months, [cur_s.get(m) for m in months], marker='o', color=c, linewidth=2, label=f'今年({last.year})')
        ax.plot(months, [ly_s.get(m) for m in months], marker='s', color=LY, linewidth=1.6, linestyle='--', label=f'去年同期({last.year-1})')
        cur = mtd(seg, last.year, last.month); pm = mtd(seg, last.year, last.month - 1) if last.month > 1 else None
        ly = mtd(seg, last.year - 1, last.month)
        mom = (cur / pm - 1) * 100 if pm else 0; yoy = (cur / ly - 1) * 100 if ly else 0
        ax.annotate('%.3f%%' % cur, (last.month, cur_s.get(last.month)), textcoords='offset points',
                    xytext=(4, 6), fontsize=9, color=c, fontweight='bold')
        ax.set_title('%s  %d月MTD %.3f%%  月环比%+.1f%%  月同比%+.1f%%' % (seg, last.month, cur, mom, yoy),
                     fontsize=10.5, color=c)
        ax.set_xticks(months); ax.set_xticklabels(mlabel, fontsize=8)
        ax.grid(alpha=.3); ax.set_ylabel('dau转化率(%)', fontsize=8.5); ax.legend(fontsize=7.5, loc='best')
    fig.suptitle('dau-净支付pv转化率月均趋势', fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    p = os.path.join(outdir, 'fmt_01_monthly.png'); plt.savefig(p, dpi=130, bbox_inches='tight'); plt.close(); return p


def daily_grid(df, last, days, fname, title, outdir):
    fig, axes = plt.subplots(1, 4, figsize=(22, 5.2)); axes = axes.ravel()
    for i, seg in enumerate(SEGS):
        ax = axes[i]; c = COLOR[seg]
        g = df[df.segment == seg].sort_values('dt')
        cur = g[g.dt > last - pd.Timedelta(days=days - 1)]
        xs = cur['dt'].dt.strftime('%m-%d').tolist(); ys = cur['star_pct'].tolist()
        ly_map = {d: v for d, v in zip(g['dt'], g['star_pct'])}
        ly_ys = [ly_map.get(d - pd.Timedelta(days=364)) for d in cur['dt']]
        ax.plot(range(len(xs)), ys, marker='.', color=c, linewidth=1.5, label=f'今年({last.year})')
        ax.plot(range(len(xs)), ly_ys, marker='.', color=LY, linewidth=1.3, linestyle='--', label='去年同期(-364天)')
        v = ys[-1]; bdt = last - pd.Timedelta(days=7); br = cur[cur.dt == bdt]['star_pct']
        mom = (v / br.iloc[0] - 1) * 100 if len(br) and br.iloc[0] else None
        lbl = '%.3f%%' % v + (('  环比%+.1f%%' % mom) if mom is not None else '')
        ax.annotate(lbl, (len(xs) - 1, v), textcoords='offset points', xytext=(4, 6), fontsize=9, color=c, fontweight='bold')
        ax.set_title(seg, fontsize=11, color=c); ax.grid(alpha=.3); ax.set_ylabel('dau转化率(%)', fontsize=8.5)
        step = max(1, len(xs) // 14)
        ax.set_xticks(range(0, len(xs), step)); ax.set_xticklabels(xs[::step], rotation=90, fontsize=6.5)
        ax.legend(fontsize=7.5, loc='best')
    fig.suptitle(title, fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    p = os.path.join(outdir, fname); plt.savefig(p, dpi=130, bbox_inches='tight'); plt.close(); return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dt', required=True, help='分析日 t-1，如 2026-07-11')
    ap.add_argument('--outdir', required=True)
    ap.add_argument('--series', default=None, help='长历史序列 CSV；默认取 data_storage 下最新 periodicity_series_*.csv')
    ap.add_argument('--start-year', type=int, default=None, help='月均图起始年，默认分析日当年年初')
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    df, path = load_series(args.series, args.dt)
    last = pd.Timestamp(args.dt); cur_day = last.day
    made = []
    made.append(monthly_grid(df, last, cur_day, args.outdir, args.start_year or last.year, 1))
    made.append(daily_grid(df, last, 30, 'fmt_02_daily30.png',
                           'dau-净支付pv转化率近30日日度趋势', args.outdir))
    made.append(daily_grid(df, last, 56, 'fmt_03_weekly8.png',
                           'dau-净支付pv转化率近8周日度趋势', args.outdir))
    print(f'[OK] 趋势图 {len(made)} 张（源 {path}）→ {args.outdir}')
    for p in made:
        print('   ', p)


if __name__ == '__main__':
    main()

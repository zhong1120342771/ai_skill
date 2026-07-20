#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_category_exposure_charts.py — 品类×APP端 曝光UV/曝光渗透率趋势图

每个品类一张图，2x2 四宫格（格式参考 render_trend_charts.py 的近30日/近8周）：
  [0,0] 曝光UV 近30日      [0,1] 曝光UV 近8周(56天)
  [1,0] 曝光渗透率 近30日  [1,1] 曝光渗透率 近8周(56天)
今年实线、去年同期(-364天星期对齐)虚线；末点标环比(vs上周同日)。

数据源：category_app_exposure_*.csv（列 dt, wd, exp_uv, matched_dau_uv），
wd 形如 转转APP_品类<业务><品类>。曝光渗透率 = exp_uv / matched_dau_uv（APP端活跃DAU）。
仅出 APP 端；名称含「其他」的品类剔除。文件名按 业务→品类 排序，便于同业务品类相邻推送。
"""
import argparse, os
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

BIZ_ORDER = ['消费电子', '二奢', '兴趣', '其他']
BIZ_COLOR = {'消费电子': '#c00000', '二奢': '#7030a0', '兴趣': '#2e9e5b', '其他': '#5b6770'}
LY = '#9aa0a6'  # 去年同期灰
PREFIX = '转转APP_品类'
# 兴趣业务口径（用户 2026-07-15 定）：底表把 包袋/腕表/鞋服/饰品 也挂在兴趣下，与业务认知不符，剔除。
# 乐器/台球杆 原底表未从长尾N拆出，2026-07-15 用户改建表逻辑后已按 cate_id 拆分（乐器 1100003483/1100003484、台球杆 1100001943）。
# 兴趣保留 乐器/台球杆/骑行/潮玩/球拍 五个品类，其余兴趣品类不出报告。
INTEREST_KEEP = {'乐器', '台球杆', '骑行', '潮玩', '球拍'}


def parse_wd(wd):
    """转转APP_品类<业务><品类> -> (业务, 品类)"""
    rest = wd[len(PREFIX):] if wd.startswith(PREFIX) else wd
    for b in BIZ_ORDER:
        if rest.startswith(b):
            return b, rest[len(b):]
    return '其他', rest


def _panel(ax, g, last, days, ycol, color, ylabel, is_pct):
    cur = g[g.dt > last - pd.Timedelta(days=days - 1)]
    xs = cur['dt'].dt.strftime('%m-%d').tolist()
    ys = cur[ycol].tolist()
    ly_map = {d: v for d, v in zip(g['dt'], g[ycol])}
    ly_ys = [ly_map.get(d - pd.Timedelta(days=364)) for d in cur['dt']]
    ax.plot(range(len(xs)), ys, marker='.', color=color, linewidth=1.5, label='今年')
    ax.plot(range(len(xs)), ly_ys, marker='.', color=LY, linewidth=1.3, linestyle='--', label='去年同期(-364天)')
    v = ys[-1] if ys else None
    bdt = last - pd.Timedelta(days=7)
    br = cur[cur.dt == bdt][ycol]
    mom = (v / br.iloc[0] - 1) * 100 if (v is not None and len(br) and br.iloc[0]) else None
    if v is not None:
        vtxt = ('%.2f%%' % v) if is_pct else format(int(round(v)), ',d')
        lbl = vtxt + (('  环比%+.1f%%' % mom) if mom is not None else '')
        ax.annotate(lbl, (len(xs) - 1, v), textcoords='offset points', xytext=(4, 6),
                    fontsize=9, color=color, fontweight='bold')
    ax.grid(alpha=.3); ax.set_ylabel(ylabel, fontsize=8.5)
    step = max(1, len(xs) // 14)
    ax.set_xticks(range(0, len(xs), step)); ax.set_xticklabels(xs[::step], rotation=90, fontsize=6.5)
    ax.legend(fontsize=7.5, loc='best')


def render_one(g, biz, cat, last, outdir, seq):
    g = g.sort_values('dt')
    color = BIZ_COLOR.get(biz, '#5b6770')
    fig, axes = plt.subplots(2, 2, figsize=(16, 9))
    _panel(axes[0, 0], g, last, 30, 'exp_uv', color, '曝光UV', False)
    axes[0, 0].set_title('曝光UV · 近30日', fontsize=11, color=color)
    _panel(axes[0, 1], g, last, 56, 'exp_uv', color, '曝光UV', False)
    axes[0, 1].set_title('曝光UV · 近8周', fontsize=11, color=color)
    _panel(axes[1, 0], g, last, 30, 'exp_pen_pct', color, '曝光渗透率(%)', True)
    axes[1, 0].set_title('曝光渗透率 · 近30日', fontsize=11, color=color)
    _panel(axes[1, 1], g, last, 56, 'exp_pen_pct', color, '曝光渗透率(%)', True)
    axes[1, 1].set_title('曝光渗透率 · 近8周', fontsize=11, color=color)
    fig.suptitle('【%s】%s · APP端 曝光UV / 曝光渗透率趋势' % (biz, cat),
                 fontsize=15, fontweight='bold', y=1.0)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    fname = 'cat_%02d_%s_%s.png' % (seq, biz, cat)
    p = os.path.join(outdir, fname)
    plt.savefig(p, dpi=130, bbox_inches='tight'); plt.close()
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dt', required=True, help='分析日 t-1，如 2026-07-14')
    ap.add_argument('--src', required=True, help='category_app_exposure_*.csv')
    ap.add_argument('--outdir', required=True)
    ap.add_argument('--exclude-other', action='store_true', default=True,
                    help='剔除名称含「其他」的品类（默认开）')
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    df = pd.read_csv(args.src)
    df['dt'] = pd.to_datetime(df['dt'])
    df['exp_pen_pct'] = df['exp_uv'] / df['matched_dau_uv'] * 100
    biz_cat = []
    for wd in df['wd'].unique():
        if wd == '转转APP':      # APP端整体基准行(单维度-拆分端)，只当汇总表分母/基准，不出品类趋势图
            continue
        b, cat = parse_wd(wd)
        if args.exclude_other and '其他' in cat:
            continue
        if b == '兴趣' and cat not in INTEREST_KEEP:
            continue
        biz_cat.append((BIZ_ORDER.index(b) if b in BIZ_ORDER else 99, b, cat, wd))
    biz_cat.sort()  # 业务序 → 品类名
    last = pd.Timestamp(args.dt)
    made = []
    for seq, (_, b, cat, wd) in enumerate(biz_cat, 1):
        g = df[df.wd == wd]
        made.append(render_one(g, b, cat, last, args.outdir, seq))
    print('[OK] 品类曝光趋势图 %d 张 → %s' % (len(made), args.outdir))
    for p in made:
        print('   ', p)


if __name__ == '__main__':
    main()

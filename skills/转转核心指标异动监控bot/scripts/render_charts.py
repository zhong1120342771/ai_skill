#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_charts.py — 分维度分析通用图表

从 tidy 长表出图，落 visualizations/${dt}/：
  1) metric_rank_by_<dim>.png      某维度各取值的指标排行(横向对比)
  2) funnel_<dim>.png              各维度取值的漏斗转化图(曝光→商详→下单→净支付, 逐环节收窄+转化率标注)
  3) funnel_stage_mom.png          大盘漏斗四环节周环比(哪个环节在掉)
  (北极星近 N 天趋势线已按 v4-0711 改点1 删除)

图中所有维度名/指标名一律走中文映射(CN_DIM/CN_METRIC)，不出现英文列名。
中文字体必须显式设置，否则方块乱码。
用法：
  python render_charts.py --tidy tidy.csv --dt 2026-07-07 --by main_scene \
      --metric bag_rate --anomaly anomaly.csv --outdir ~/.claude/visualizations/2026-07-07
"""
import argparse, os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

FUNNEL = [('exp_uv', '曝光UV'), ('detail_uv', '商详UV'),
          ('order_uv', '下单UV'), ('pay_pv', '净支付单量')]

# 维度列 → 中文名（图里禁止出现英文列名，见 0711 改点5）
CN_DIM = {
    'user_source': '用户来源', 'main_scene': '场景', 'scene_02': '二级场景',
    'scene_03': '三级场景', 'asset_band': '资产分层', 'user_type': '用户类型',
    'duan': '端', 'cate': '业务/品类', 'cate_02': '品类', 'goods_level': '货层级',
    'biz': '业务', 'scene': '场景', 'wd': '维度值',
}
# 指标列 → 中文名（同上）
CN_METRIC = {
    'dau_pay_rate': 'dau-净支付pv转化率', 'exp_penetration': '曝光渗透率',
    'detail_reach': '商详到达率', 'order_rate': '下单率', 'pay_rate': '支付率',
    'detail_penetration': '商详渗透率', 'detail_pay_rate': '商详转化率',
    'bag_rate': '提袋率', 'matched_dau_uv': '活跃DAU', 'pay_pv': '单量',
    'exp_uv': '曝光UV', 'detail_uv': '商详UV', 'order_uv': '下单UV',
}
# 漏斗四环节 → 中文（大盘四环节周环比图用；曝光渗透率=曝光UV/活跃DAU 是首环）
STAGE_CN = [('exp_penetration', '曝光渗透率'), ('detail_reach', '商详到达率'),
            ('order_rate', '下单率'), ('pay_rate', '支付率')]
# 漏斗层间(曝光UV→商详UV→下单UV→净支付)的相邻环节转化率名，对应 FUNNEL 的 3 个 gap
FUNNEL_GAP_CN = ['商详到达率', '下单率', '支付率']


def cn_dim(name):
    return CN_DIM.get(name, name)


def cn_metric(name):
    return CN_METRIC.get(name, name)

# 比率类指标：展示用百分比（读 analyze_dimension 产出的 *_pct 列）
RATE_METRICS = {'dau_pay_rate','exp_penetration','detail_reach','order_rate','pay_rate',
                'detail_penetration','detail_pay_rate','bag_rate'}


def _disp_col(df, metric):
    """比率指标优先用 *_pct 列展示（百分比）；返回 (列名, 是否百分比)。"""
    if metric in RATE_METRICS and f'{metric}_pct' in df.columns:
        return f'{metric}_pct', True
    return metric, False


def rank_chart(df, by, metric, dt, outdir):
    """某维度各取值的指标排行。比率指标按曝光UV加权求均值(避免小分母行等权拉偏)。"""
    cur = df[(df.dt == dt) & df[by].notna()].copy()
    if cur.empty: return None
    col, is_pct = _disp_col(df, metric)
    if is_pct and 'exp_uv' in cur.columns:
        cur = cur[cur['exp_uv'].fillna(0) > 0]
        cur['_w'] = cur[col] * cur['exp_uv']
        num = cur.groupby(by)['_w'].sum()
        den = cur.groupby(by)['exp_uv'].sum()
        g = (num / den).sort_values(ascending=True)
    else:
        g = cur.groupby(by)[col].mean().sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(8, max(3, 0.5*len(g)+1)))
    ax.barh(g.index.astype(str), g.values, color='#4C78A8')
    unit = '（%）' if is_pct else ''
    ax.set_title(f'{dt} · 各「{cn_dim(by)}」的{cn_metric(metric)}排行{unit}')
    ax.set_xlabel(f'{cn_metric(metric)}{unit}')
    for i, v in enumerate(g.values):
        label = f' {v:.2f}%' if is_pct else f' {v:,.0f}'
        ax.text(v, i, label, va='center', fontsize=9)
    fig.tight_layout()
    p = os.path.join(outdir, f'metric_rank_by_{by}.png')
    fig.savefig(p, dpi=130); plt.close(fig); return p


def funnel_chart(df, by, dt, outdir):
    """真·大盘漏斗图：逐环节收窄，每层标绝对量，层间标相邻环节转化率
    (商详到达率/下单率/支付率)，直观看转化损耗。
    优先用整体行(tag_01=整体)——各场景的曝光UV会重复计人，汇总会虚高，故不按场景相加。"""
    o = df[(df.dt == dt) & (df.get('tag_01') == '整体')] if 'tag_01' in df.columns else df.iloc[0:0]
    if not o.empty:
        row = o.iloc[0]
        vals = [float(row.get(c, 0) or 0) for c, _ in FUNNEL]
        src = '整体'
    else:
        cur = df[(df.dt == dt) & df[by].notna()].copy()
        if cur.empty: return None
        vals = [cur[c].fillna(0).sum() for c, _ in FUNNEL]
        src = f'{cn_dim(by)}汇总'
    if not vals or vals[0] <= 0: return None
    labels = [z for _, z in FUNNEL]
    top = float(vals[0])
    fig, ax = plt.subplots(figsize=(8, 5.2))
    palette = ['#4C78A8', '#5B9BD5', '#72B7B2', '#54A24B']
    n = len(vals)
    # 宽度用 sqrt 归一化，避免下单/支付两层因量级差几十倍被压成看不见的细条
    import math
    def hw(v):
        r = (v / top) ** 0.5
        return max(r, 0.06) / 2.0  # 最小半宽地板，保证可见
    for i, v in enumerate(vals):
        half = hw(v)
        y = n - 1 - i
        ax.barh(y, half * 2, left=0.5 - half, height=0.62, color=palette[i % len(palette)])
        txt = f'{labels[i]}  {v:,.0f}'
        # 条太窄放不下文字就移到条右侧、用深色，避免被截断
        if half * 2 >= 0.28:
            ax.text(0.5, y, txt, ha='center', va='center',
                    fontsize=11, color='white', fontweight='bold')
        else:
            ax.text(0.5 + half + 0.01, y, txt, ha='left', va='center',
                    fontsize=10.5, color='#333', fontweight='bold')
        if i > 0 and vals[i-1] > 0:
            conv = v / vals[i-1] * 100
            gap_name = FUNNEL_GAP_CN[i-1] if i-1 < len(FUNNEL_GAP_CN) else '转化率'
            ax.text(0.015, y + 0.5, f'{gap_name} {conv:.2f}%',
                    ha='left', va='center', fontsize=9.5, color='#C44E52')
    ax.set_xlim(0, 1); ax.set_ylim(-0.6, n - 0.4)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_title(f'{dt} · 大盘漏斗转化（{src}）')
    fig.tight_layout()
    p = os.path.join(outdir, f'funnel_{by}.png')
    fig.savefig(p, dpi=130); plt.close(fig); return p


def _overall_row(df, dt):
    """取整体行(tag_01=整体)当天与上周同日，用于漏斗四环节周环比。"""
    from datetime import datetime, timedelta
    o = df[df['tag_01'] == '整体'].copy() if 'tag_01' in df.columns else df.iloc[0:0]
    if o.empty: return None, None, None
    d = datetime.strptime(dt, '%Y-%m-%d')
    wago = (d - timedelta(days=7)).strftime('%Y-%m-%d')
    cur = o[o.dt == dt]
    base = o[o.dt == wago]
    if cur.empty: return None, None, None
    return cur.iloc[0], (base.iloc[0] if not base.empty else None), wago


def funnel_stage_mom_chart(df, dt, outdir):
    """大盘漏斗四环节(曝光渗透/商详到达/下单/支付)周环比柱状图——直观显示哪个环节在掉。
    替代旧的 anomaly_waterfall(混噪声与多量纲、看不懂)。"""
    cur, base, wago = _overall_row(df, dt)
    if cur is None or base is None:
        return None
    names, moms, curvals = [], [], []
    for col, cn in STAGE_CN:
        pct_col = f'{col}_pct'
        cv = cur.get(pct_col, cur.get(col))
        bv = base.get(pct_col, base.get(col))
        if cv is None or bv is None or pd.isna(cv) or pd.isna(bv) or bv == 0:
            continue
        names.append(cn); curvals.append(float(cv))
        moms.append((float(cv) - float(bv)) / abs(float(bv)) * 100)
    if not names: return None
    colors = ['#E45756' if m < 0 else '#54A24B' for m in moms]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(range(len(names)), moms, color=colors, width=0.6)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels([f'{n}\n({v:.2f}%)' for n, v in zip(names, curvals)], fontsize=10)
    ax.axhline(0, color='#333', lw=0.8)
    ax.set_ylabel('周环比涨跌幅（%）')
    ax.set_title(f'{dt} · 大盘漏斗四环节周环比（对比上周同日 {wago}）')
    for b, m in zip(bars, moms):
        ax.text(b.get_x() + b.get_width()/2, m + (0.1 if m >= 0 else -0.1),
                f'{m:+.2f}%', ha='center', va='bottom' if m >= 0 else 'top', fontsize=9)
    fig.tight_layout()
    p = os.path.join(outdir, 'funnel_stage_mom.png')
    fig.savefig(p, dpi=130); plt.close(fig); return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tidy', required=True)
    ap.add_argument('--dt', required=True)
    ap.add_argument('--by', default='main_scene', help='排行/漏斗的维度列，默认场景(main_scene)')
    ap.add_argument('--metric', default='bag_rate',
                    help='排行图指标；场景/品类族用提袋率(bag_rate)体现自身转化效率，勿用dau_pay_rate(分母全站DAU、天然极低)')
    ap.add_argument('--trend-metric', default='dau_pay_rate',
                    help='(已弃用/v4删趋势图) 保留仅为兼容旧调用，不再产图')
    ap.add_argument('--anomaly', default=None, help='(已弃用/v4) 保留兼容旧调用')
    ap.add_argument('--outdir', required=True)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    df = pd.read_csv(args.tidy)
    df['dt'] = df['dt'].astype(str).str.slice(0, 10)
    anom = pd.read_csv(args.anomaly) if args.anomaly and os.path.exists(args.anomaly) else None

    made = []
    for fn in [rank_chart(df, args.by, args.metric, args.dt, args.outdir),
               funnel_chart(df, args.by, args.dt, args.outdir)]:
        if fn: made.append(fn)
    # 北极星趋势图已按 v4-0711 改点1 删除（不再出 trend_dau_pay_rate.png）
    # 大盘漏斗四环节周环比(替代旧异动Top图)
    fn = funnel_stage_mom_chart(df, args.dt, args.outdir)
    if fn: made.append(fn)

    print(f'[OK] 出图 {len(made)} 张 → {args.outdir}')
    for p in made: print('   ', p)


if __name__ == '__main__':
    main()

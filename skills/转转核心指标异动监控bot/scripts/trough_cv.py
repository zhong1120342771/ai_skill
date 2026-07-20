#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trough_cv.py — 各业务变异系数(CV) + 日序列局部波谷定位（纯数值驱动，不贴大促归因）

输入：长历史日序列 CSV（默认取 data_storage 下最新 periodicity_series_*.csv），
      需含列 dt / segment / pay_pv / dau_pay_rate。
输出：控制台打印 + 两块结果（CV 表、波谷清单），可 --md 落一份 markdown 片段供插文档。

设计红线（见全局规则「不拿行业通用标准当用户输入」）：
  波谷识别只用 pay_pv / dau_pay_rate 的数值本身找局部低谷，绝不引用 promo_name/
  is_promo_peak 这类"我编的大促标签"来解释波谷成因。波谷是客观数值事实，
  归因（是否春节/大促）留给用户或实测，脚本不替下判断。

口径：
  - CV = 日粒度 std / mean（全序列），无量纲，衡量相对波动，可跨业务/跨口径比。
  - 波谷 = 以 28 日居中滚动中位数为基线，某日既是前后 window 天内最低点、
    且相对基线偏离 < -depth_min，即记为波谷；相对基线偏离 < -0.15 记「大波谷」，否则「小波谷」。
    相邻 14 天内的波谷合并取更深者，避免同一低谷重复计数。

用法：
  python trough_cv.py                                  # 用最新日序列，打印 CV+大盘波谷
  python trough_cv.py --seg 大盘,消费电子,二奢,兴趣 --metric both
  python trough_cv.py --md out.md                      # 额外落 markdown 片段
"""
import argparse, glob, os, sys
from datetime import datetime
import pandas as pd
import numpy as np

WD = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
SEG_ORDER = ['大盘', '消费电子', '二奢', '兴趣']


def latest_series():
    base = os.path.expanduser('~/.claude/data_storage')
    files = sorted(glob.glob(os.path.join(base, 'periodicity_series_*.csv')))
    if not files:
        print('[ERR] data_storage 下无 periodicity_series_*.csv', file=sys.stderr)
        sys.exit(1)
    return files[-1]


def compute_cv(df):
    """各业务单量/转化率 CV。返回 list[dict]。"""
    rows = []
    for seg in SEG_ORDER:
        s = df[df.segment == seg]
        if s.empty:
            continue
        pv = s['pay_pv'].dropna()
        rt = s['dau_pay_rate'].dropna()
        rows.append({
            'segment': seg,
            'cv_pay_pv': round(pv.std() / pv.mean(), 3) if pv.mean() else None,
            'cv_dau_pay_rate': round(rt.std() / rt.mean(), 3) if rt.mean() else None,
            'mean_pay_pv': round(pv.mean(), 0) if not pv.empty else None,
            'mean_rate_pct': round(rt.mean() * 100, 3) if not rt.empty else None,
            'n_days': len(s),
        })
    return rows


def find_extrema(df, seg, col, kind, window=7, roll=28, dev_min=0.08, big=0.15):
    """某业务某指标的局部波峰/波谷（峰谷对称同阈值）：
      kind='trough' 波谷：前后 window 天最低 + 相对 roll 日居中中位数偏离 < -dev_min；
      kind='peak'   波峰：前后 window 天最高 + 相对中位数偏离 > +dev_min。
    |偏离| > big 记「大峰/大谷」，否则「小峰/小谷」。相邻 14 天合并取更极端者。
    纯数值驱动，不含大促归因。返回 list[dict]。"""
    g = df[df.segment == seg].sort_values('dt').reset_index(drop=True)
    s = g.set_index('dt')[col]
    base = s.rolling(roll, center=True, min_periods=roll // 2).median()
    dev = (s - base) / base
    raw = []
    for i in range(len(s)):
        lo, hi = max(0, i - window), min(len(s), i + window + 1)
        if kind == 'trough':
            hit = s.iloc[i] == s.iloc[lo:hi].min() and dev.iloc[i] < -dev_min
        else:
            hit = s.iloc[i] == s.iloc[lo:hi].max() and dev.iloc[i] > dev_min
        if hit:
            raw.append({'dt': s.index[i], 'value': s.iloc[i], 'dev': float(dev.iloc[i])})
    merged = []
    for t in raw:
        if merged and (t['dt'] - merged[-1]['dt']).days < 14:
            more_extreme = t['dev'] < merged[-1]['dev'] if kind == 'trough' else t['dev'] > merged[-1]['dev']
            if more_extreme:
                merged[-1] = t
        else:
            merged.append(t)
    big_lbl, small_lbl = ('大波峰', '小波峰') if kind == 'peak' else ('大波谷', '小波谷')
    for t in merged:
        t['weekday'] = WD[t['dt'].weekday()]
        t['kind'] = kind
        t['depth'] = big_lbl if abs(t['dev']) > big else small_lbl
    return merged


def fmt_val(col, v):
    if v is None or pd.isna(v):
        return 'NA'
    return f'{v*100:.3f}%' if col == 'dau_pay_rate' else f'{int(v):,}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', default=None, help='日序列 CSV，默认取最新 periodicity_series_*.csv')
    ap.add_argument('--seg', default='大盘,消费电子,二奢,兴趣', help='要出波谷的业务，逗号分隔')
    ap.add_argument('--metric', default='both', choices=['pay_pv', 'dau_pay_rate', 'both'],
                    help='波谷看哪个口径')
    ap.add_argument('--dev-min', type=float, default=0.08, help='波峰/波谷相对基线最小偏离(默认8%)')
    ap.add_argument('--md', default=None, help='额外落 markdown 片段到此路径')
    args = ap.parse_args()

    path = args.input or latest_series()
    df = pd.read_csv(path)
    df['dt'] = pd.to_datetime(df['dt'])
    df = df.sort_values('dt')
    date_lo, date_hi = df['dt'].min().date(), df['dt'].max().date()

    cv_rows = compute_cv(df)
    segs = [x.strip() for x in args.seg.split(',') if x.strip()]
    metrics = ['pay_pv', 'dau_pay_rate'] if args.metric == 'both' else [args.metric]

    # 控制台
    print(f'[数据源] {os.path.basename(path)}  {date_lo} ~ {date_hi}')
    print('\n=== 各业务变异系数 CV（日粒度 std/mean，全序列）===')
    print(f'{"业务":<6}{"单量CV":>9}{"转化率CV":>11}{"单量均值":>12}{"转化率均值":>12}{"天数":>7}')
    for r in cv_rows:
        print(f'{r["segment"]:<6}{r["cv_pay_pv"]:>9}{r["cv_dau_pay_rate"]:>11}'
              f'{int(r["mean_pay_pv"]):>12,}{r["mean_rate_pct"]:>11}%{r["n_days"]:>7}')

    # 峰谷都算：key=(seg, col, kind)
    ext_data = {}
    for seg in segs:
        for col in metrics:
            for kind in ('peak', 'trough'):
                ext = find_extrema(df, seg, col, kind, dev_min=args.dev_min)
                ext_data[(seg, col, kind)] = ext
            name = '单量' if col == 'pay_pv' else 'dau-净支付pv转化率'
            merged = sorted(ext_data[(seg, col, 'peak')] + ext_data[(seg, col, 'trough')],
                            key=lambda x: x['dt'])
            print(f'\n=== {seg} · {name} 局部峰谷（|偏离28日中位|>{args.dev_min:.0%}，前后7日极值）===')
            print(f'{"日期":<12}{"星期":<6}{"值":>12}{"较基线":>9}{"类型":>7}')
            for t in merged:
                print(f'{str(t["dt"].date()):<12}{t["weekday"]:<6}'
                      f'{fmt_val(col, t["value"]):>12}{t["dev"]*100:>8.1f}%{t["depth"]:>7}')

    if args.md:
        write_md(args.md, path, date_lo, date_hi, cv_rows, ext_data, segs, metrics)
        print(f'\n[md] 已落 {args.md}')


def write_md(md_path, src, date_lo, date_hi, cv_rows, ext_data, segs, metrics):
    L = []
    L.append(f'> 数据源：{os.path.basename(src)}（{date_lo} ~ {date_hi} 日粒度）｜'
             f'CV=日粒度标准差/均值；波峰/波谷=相对28日居中中位数偏离 >±8% 的局部极值，'
             f'|偏离|>15% 记大峰/大谷。峰谷仅标数值事实，不含大促归因。')
    L.append('')
    L.append('### 各业务波动性（变异系数 CV）')
    L.append('')
    L.append('| 业务 | 单量CV | dau-净支付pv转化率CV | 单量日均 | 转化率日均 | 样本天数 |')
    L.append('|---|---|---|---|---|---|')
    for r in cv_rows:
        L.append(f'| {r["segment"]} | {r["cv_pay_pv"]} | {r["cv_dau_pay_rate"]} | '
                 f'{int(r["mean_pay_pv"]):,} | {r["mean_rate_pct"]:.3f}% | {r["n_days"]} |')
    L.append('')
    L.append('> CV 越大越不稳。跨业务比：盘子越小的业务（二奢/兴趣）单日波动天然越剧烈，'
             'CV 显著高于大盘/消费电子；这是量级效应，不等于业务质量问题。')
    L.append('')
    for col in metrics:
        name = '单量' if col == 'pay_pv' else 'dau-净支付pv转化率'
        L.append(f'### 局部峰谷清单 · {name}')
        L.append('')
        L.append('> 大峰/大谷（|偏离|>15%）全列，小峰/小谷（8%~15%）只计数。')
        L.append('')
        for seg in segs:
            peaks = ext_data.get((seg, col, 'peak'), [])
            troughs = ext_data.get((seg, col, 'trough'), [])
            big_p = [t for t in peaks if t['depth'] == '大波峰']
            big_t = [t for t in troughs if t['depth'] == '大波谷']
            small_p = len(peaks) - len(big_p)
            small_t = len(troughs) - len(big_t)
            L.append(f'**{seg}**（大波峰 {len(big_p)}／大波谷 {len(big_t)}；'
                     f'另有小波峰 {small_p}、小波谷 {small_t} 个）')
            L.append('')
            big_all = sorted(big_p + big_t, key=lambda x: x['dt'])
            if not big_all:
                L.append('无大峰/大谷，波动均在 ±15% 内。')
                L.append('')
                continue
            L.append('| 日期 | 星期 | 值 | 较基线 | 类型 |')
            L.append('|---|---|---|---|---|')
            for t in big_all:
                L.append(f'| {t["dt"].date()} | {t["weekday"]} | {fmt_val(col, t["value"])} | '
                         f'{t["dev"]*100:+.1f}% | {t["depth"]} |')
            L.append('')
    open(md_path, 'w', encoding='utf-8').write('\n'.join(L))


if __name__ == '__main__':
    main()

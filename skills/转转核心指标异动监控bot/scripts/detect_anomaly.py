#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
detect_anomaly.py — 异动定位（环比 + 横向对比 + 近 N 天趋势）

输入：analyze_dimension.py 产出的 tidy 长表（含 dt + 拆好的维度列 + 漏斗链指标）
输出：异动清单 CSV + 控制台摘要

四种基准（见 references/重点关心问题.md §四）：
  1) 环比：分析日 vs t-1 / vs 上周同日，看指定指标涨跌幅
  2) 同比：分析日 vs 去年同期(统一星期对齐-364)，涨跌越阈值即计入异常
  3) 横向：分析日，同一指标在某维度各取值间排序，标出偏离中位 ±N 倍 MAD 的格子
  4) 趋势：近 N 天序列，标记单日涨跌 > 阈值 的拐点
另：周环比命中后还做去年同期季节性校验(是否周期性回落，非真异动)。

用法：
  python detect_anomaly.py --input tidy.csv --metric dau_pay_rate --analyze-dt 2026-07-07 \
      --by user_source --tag 单维度-拆分用户来源 --out anomaly.csv

北极星指标：dau_pay_rate（pay_pv/matched_dau_uv，跨维度可比）、matched_dau_uv、pay_pv。
漏斗四环节：exp_penetration / detail_reach / order_rate / pay_rate。
"""
import argparse, os, sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calendar_context import yoy_baseline, d as _d, yoy_low_base_suppressed  # 同比对齐(统一星期对齐-364,大促峰值日特例已剔除)真源 + 低基数业务同比抑制

DIM_COLS = ['duan','user_source','user_type','asset_band',
            'main_scene','scene_02','scene_03','goods_level','cate','cate_02']
# 该行体量列（比率异动必带绝对量，让业务读得出盘子大小）
SCALE_COLS = ['matched_dau_uv','exp_uv','detail_uv','order_uv','pay_pv']
# DAU 类比率：分母是 matched_dau_uv，NULL 行不参与
DAU_RATE = {'dau_pay_rate','exp_penetration','detail_penetration'}
# 低基数业务同比抑制覆盖的指标：转化率(北极星/漏斗各环节率) + 单量(pay_pv)
YOY_SUPPRESS_METRICS = {'dau_pay_rate','exp_penetration','detail_reach','detail_penetration',
                        'order_rate','pay_rate','pay_pv'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--metric', default='dau_pay_rate')
    ap.add_argument('--analyze-dt', required=True)
    ap.add_argument('--by', default=None, help='横向对比的维度列，如 user_source/asset_band/main_scene/cate')
    ap.add_argument('--tag', default=None,
                    help='横向对比限定在某个 tag_01 口径族内(强烈建议)，避免跨粒度比大小')
    ap.add_argument('--min-exp-uv', type=int, default=1000,
                    help='体量地板：曝光UV低于此值的行不参与异动(小样本比率不稳)')
    ap.add_argument('--mom-threshold', type=float, default=0.15, help='环比涨跌幅阈值(大盘/维度默认15%%)')
    ap.add_argument('--seasonal-check', dest='seasonal_check', action='store_true', default=True,
                    help='对周环比异常做去年同期季节性校验(默认开)')
    ap.add_argument('--no-seasonal-check', dest='seasonal_check', action='store_false',
                    help='关闭去年同期季节性校验')
    ap.add_argument('--ly-ratio-low', type=float, default=0.5,
                    help='季节性判定量级下界：去年同期周环比幅度 / 今年 ≥ 此值')
    ap.add_argument('--ly-ratio-high', type=float, default=2.0,
                    help='季节性判定量级上界：去年同期周环比幅度 / 今年 ≤ 此值')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.input)
    df['dt'] = df['dt'].astype(str).str.slice(0, 10)
    if 'exp_uv' in df.columns and args.min_exp_uv > 0:
        before = len(df)
        df = df[df['exp_uv'].fillna(0) >= args.min_exp_uv].copy()
        print(f'[info] 体量过滤 exp_uv>={args.min_exp_uv}: {before} → {len(df)} 行')
    m = args.metric
    if m not in df.columns:
        print(f'[ERR] 指标 {m} 不在列里：{list(df.columns)}', file=sys.stderr); sys.exit(1)
    # DAU 类比率：剔除 matched_dau_uv 为 NULL 的行（不能算，绝不当 0）
    if m in DAU_RATE and 'matched_dau_uv' in df.columns:
        before = len(df)
        df = df[df['matched_dau_uv'].notna()].copy()
        if before != len(df):
            print(f'[info] {m} 为 DAU 类比率，剔除 matched_dau_uv 为 NULL 的行: {before} → {len(df)}')

    adt = args.analyze_dt
    d = datetime.strptime(adt, '%Y-%m-%d')
    prev_day = (d - timedelta(days=1)).strftime('%Y-%m-%d')
    prev_week = (d - timedelta(days=7)).strftime('%Y-%m-%d')
    # 同比(去年同期)对齐：统一星期对齐(-364)。真源 calendar_context.yoy_baseline（大促峰值日特例已剔除）
    yb = yoy_baseline(_d(adt))
    yoy_dt = yb['aligned_dt']            # 同比基准日(分析日 vs 该日)
    yoy_align = yb['align_mode']
    # 周环比季节性校验用的去年同期两天：同比基准日 + 其上周同日(-7)
    ly_cur = yoy_dt
    ly_base = yb['prev_week_dt']

    scale_col = next((c for c in SCALE_COLS if c in df.columns), None)
    key = ['tag_01', 'wd']
    findings = []

    def scale_of(tag, wd):
        if not scale_col:
            return None
        sub = df[(df.dt == adt) & (df.tag_01 == tag) & (df.wd == wd)][scale_col]
        return None if sub.empty or pd.isna(sub.iloc[0]) else int(sub.iloc[0])

    def val_at(dt_str, tag, wd):
        sub = df[(df.dt == dt_str) & (df.tag_01 == tag) & (df.wd == wd)][m]
        return None if sub.empty or pd.isna(sub.iloc[0]) else float(sub.iloc[0])

    # 去年同期(星期对齐)周环比：判本次周环比回落是否周期性(发薪日/寒暑假等日历节律)
    def seasonal_verdict(tag, wd, cur_chg):
        lc, lb = val_at(ly_cur, tag, wd), val_at(ly_base, tag, wd)
        if lc is None or lb is None or lb == 0:
            return {'ly_base_value': lb, 'ly_cur_value': lc, 'ly_change_pct': None,
                    'seasonal': None,
                    'seasonal_verdict': f'去年同期数据缺失(需 {ly_cur} vs {ly_base})，无法判周期性'}
        ly_chg = (lc - lb) / lb
        same_dir = (ly_chg < 0) == (cur_chg < 0)
        ratio = abs(ly_chg) / abs(cur_chg) if cur_chg != 0 else None
        mag_close = ratio is not None and args.ly_ratio_low <= ratio <= args.ly_ratio_high
        base = f'今年周环比 {cur_chg:+.1%}｜去年同期(星期对齐 {ly_cur} vs {ly_base}) {ly_chg:+.1%}'
        if same_dir and mag_close:
            verdict = f'周期性回落(季节性可解释)：{base}，去年同向且量级相近(比值 {ratio:.2f})'
            seasonal = True
        elif same_dir:
            verdict = f'去年同向但量级不匹配(比值 {ratio:.2f} 出 [{args.ly_ratio_low},{args.ly_ratio_high}])，疑似真异动，{base}'
            seasonal = False
        else:
            verdict = f'去年反向或无同期回落，判真异动：{base}'
            seasonal = False
        return {'ly_base_value': round(lb, 6), 'ly_cur_value': round(lc, 6),
                'ly_change_pct': round(ly_chg, 4), 'seasonal': seasonal,
                'seasonal_verdict': verdict}

    # ---- 基准1：环比 ----
    cur = df[df.dt == adt].set_index(key)[m]
    for base_dt, label in [(prev_day, '环比t-1'), (prev_week, '环比上周同日')]:
        base = df[df.dt == base_dt].set_index(key)[m]
        joined = pd.concat([cur.rename('cur'), base.rename('base')], axis=1).dropna()
        joined['chg'] = (joined['cur'] - joined['base']) / joined['base'].replace(0, np.nan)
        hit = joined[joined['chg'].abs() >= args.mom_threshold]
        for (tag, wd), row in hit.iterrows():
            rec = {'anomaly_type': label, 'tag_01': tag, 'wd': wd, 'metric': m,
                   'cur_value': round(row['cur'], 6), 'base_value': round(row['base'], 6),
                   'change_pct': round(row['chg'], 4), 'abs_scale': scale_of(tag, wd)}
            # 周环比异常才做去年同期季节性校验(t-1 环比不适用星期对齐)
            if args.seasonal_check and label == '环比上周同日':
                rec.update(seasonal_verdict(tag, wd, row['chg']))
            findings.append(rec)

    # ---- 基准2：同比(去年同期) —— 独立判定基准 ----
    # 分析日 vs 去年同期(统一星期对齐-364)，相对涨跌越阈值即计入异常。
    yoy_base = df[df.dt == yoy_dt].set_index(key)[m]
    yoy_joined = pd.concat([cur.rename('cur'), yoy_base.rename('base')], axis=1).dropna()
    # 低基数业务同比抑制：兴趣/二奢 且同比基准日<2026-01-01，转化率/单量指标一律不做同比
    suppress_yoy = m in YOY_SUPPRESS_METRICS
    if not yoy_joined.empty:
        yoy_joined['chg'] = (yoy_joined['cur'] - yoy_joined['base']) / yoy_joined['base'].replace(0, np.nan)
        yhit = yoy_joined[yoy_joined['chg'].abs() >= args.mom_threshold]
        skipped_low_base = 0
        for (tag, wd), row in yhit.iterrows():
            if suppress_yoy and yoy_low_base_suppressed(wd, yoy_dt):
                skipped_low_base += 1
                continue
            findings.append({'anomaly_type': f'同比({yoy_align})', 'tag_01': tag, 'wd': wd, 'metric': m,
                             'cur_value': round(row['cur'], 6), 'base_value': round(row['base'], 6),
                             'change_pct': round(row['chg'], 4), 'abs_scale': scale_of(tag, wd),
                             'yoy_dt': yoy_dt, 'yoy_align': yoy_align})
        if suppress_yoy and skipped_low_base:
            print(f'[info] 低基数业务同比抑制：兴趣/二奢 同比基准日 {yoy_dt}<2026-01-01，'
                  f'{m} 跳过 {skipped_low_base} 条同比异动（25年基数低易误报）')
    else:
        print(f'[info] 同比基准日 {yoy_dt}({yoy_align}) 无数据，同比判定跳过（取数步需覆盖该日）')

    # ---- 基准3：横向对比（限定同一 tag_01 粒度）----
    if args.by and args.by in df.columns:
        cur_df = df[(df.dt == adt) & df[args.by].notna()].copy()
        if args.tag:
            cur_df = cur_df[cur_df['tag_01'] == args.tag]
        else:
            print('[warn] 未指定 --tag，横向对比将在每个 tag_01 粒度内分别进行', file=sys.stderr)
        for tag_val, grp in cur_df.groupby('tag_01'):
            vals = grp[m].dropna()
            if len(vals) < 3:
                continue
            med = vals.median()
            mad = (vals - med).abs().median() or 1e-9
            grp = grp.copy()
            grp['dev'] = (grp[m] - med) / (1.4826 * mad)
            out = grp[grp['dev'].abs() >= 3]
            for _, row in out.iterrows():
                findings.append({'anomaly_type': f'横向(by {args.by}@{tag_val})', 'tag_01': row['tag_01'],
                                 'wd': row['wd'], 'metric': m, 'cur_value': round(row[m], 6),
                                 'base_value': round(med, 6), 'change_pct': round(row['dev'], 2),
                                 'abs_scale': scale_of(row['tag_01'], row['wd'])})

    # ---- 基准4：趋势拐点 ----
    trend = df[df.dt <= adt].sort_values('dt')
    for (tag, wd), g in trend.groupby(key):
        g = g.dropna(subset=[m])
        if len(g) < 3:
            continue
        g = g.tail(8).copy()
        g['d1'] = g[m].pct_change()
        last = g.iloc[-1]
        if pd.notna(last['d1']) and abs(last['d1']) >= args.mom_threshold:
            findings.append({'anomaly_type': '趋势拐点', 'tag_01': tag, 'wd': wd, 'metric': m,
                             'cur_value': round(last[m], 6), 'base_value': round(g.iloc[-2][m], 6),
                             'change_pct': round(last['d1'], 4), 'abs_scale': scale_of(tag, wd)})

    cols = ['tag_01','wd','metric','anomaly_type','base_value','cur_value','change_pct','abs_scale',
            'yoy_dt','yoy_align','ly_base_value','ly_cur_value','ly_change_pct','seasonal','seasonal_verdict']
    res = pd.DataFrame(findings)
    if res.empty:
        print('[OK] 未发现超阈值异动')
        pd.DataFrame(columns=cols).to_csv(args.out, index=False, encoding='utf-8-sig')
        return
    for c in cols:
        if c not in res.columns:
            res[c] = None
    res = res.reindex(res['change_pct'].abs().sort_values(ascending=False).index)
    res = res[cols]
    res.to_csv(args.out, index=False, encoding='utf-8-sig')
    print(f'[OK] {len(res)} 条异动 → {args.out}')
    print(res.head(15).to_string(index=False))
    # 周期性回落单列提示：这些周环比异动去年同期同向且量级相近，季节性可解释，非真异动
    seas = res[res['seasonal'] == True]
    if not seas.empty:
        print(f'\n[季节性] {len(seas)} 条周环比异动经去年同期校验为周期性回落(非真异动)：')
        for _, r in seas.iterrows():
            print(f"  · {r['tag_01']}/{r['wd']} {r['metric']}: {r['seasonal_verdict']}")


if __name__ == '__main__':
    main()

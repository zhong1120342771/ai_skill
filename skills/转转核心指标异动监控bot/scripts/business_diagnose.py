#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
business_diagnose.py — 分业务漏斗诊断（普降 vs 特征品类，品类→场景下钻）

输入：analyze_dimension.py 产出的 tidy 长表（含 dt + 拆好的维度列 + 漏斗链指标）。
输出：诊断明细 CSV + 控制台判定摘要。

职责（发现异常↔下钻步用）：针对三大重点业务 消费电子 / 二奢 / 兴趣，
  1) 业务级：拉漏斗绝对量（曝光/商详/下单/净支付 UV·单量 + 匹配DAU）+ 漏斗四环节率 + 北极星，
     算环比（vs t-1、vs 上周同日）。
  2) 判定「普降」还是「特征业务/品类」：三业务是否同向走弱，还是集中在某一块。
  3) 品类下钻：每个业务内按 单量环比 + 对大盘的贡献量 排序，锁定特征品类。
  4) 场景下钻（--drill-scene 品类名）：若 tidy 里有含该品类的场景交叉族，拆到场景。

口径要点（见 references/字段映射与指标口径.md）：
  - 北极星 dau_pay_rate = pay_pv/matched_dau_uv，可跨维度比；NULL 分母行不算 DAU 率，绝不当 0。
  - 单量 = pay_pv（净支付pv）。比率必附绝对量。小分母(exp_uv<1000)默认剔除。
  - 业务级：tag_01='单维度-拆分品类' 且 goods_level='业务'（cate=业务名）。
    品类级：同族 goods_level='品类'（cate_02=业务名+品类名，按业务名前缀归属）。

用法：
  python business_diagnose.py --input tidy.csv --analyze-dt 2026-07-07 --out diag.csv
  python business_diagnose.py --input tidy.csv --analyze-dt 2026-07-07 --drill-scene 消费电子手机 --out diag.csv
"""
import argparse, os, sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calendar_context import yoy_baseline, d as _d, yoy_low_base_suppressed  # 同比对齐(统一星期对齐-364,大促峰值日特例已剔除)真源 + 低基数业务同比抑制

# 重点关心的三大业务（真源 references/维度体系与样例数据.md §货）
FOCUS_BIZ = ['消费电子', '二奢', '兴趣']
FUNNEL_ABS = ['exp_uv', 'detail_uv', 'order_uv', 'pay_pv', 'matched_dau_uv']
FUNNEL_RATE = ['exp_penetration', 'detail_reach', 'order_rate', 'pay_rate']
STAR = 'dau_pay_rate'
CATE_TAG = '单维度-拆分品类'


def pct(cur, base):
    if base is None or pd.isna(base) or base == 0 or cur is None or pd.isna(cur):
        return None
    return round((cur - base) / base, 4)


def row_metrics(df, dt, mask):
    """取 dt 当天、满足 mask 的单行指标 dict（若无则空 dict）。"""
    sub = df[(df.dt == dt) & mask]
    if sub.empty:
        return {}
    r = sub.iloc[0]
    return {c: (None if pd.isna(r.get(c)) else r.get(c)) for c in
            FUNNEL_ABS + FUNNEL_RATE + [STAR]}


def biz_mask(df, biz):
    return (df.tag_01 == CATE_TAG) & (df.get('goods_level') == '业务') & (df.get('cate') == biz)


def cate_mask(df, biz):
    # 品类级：goods_level='品类'，cate_02 以业务名开头
    return (df.tag_01 == CATE_TAG) & (df.get('goods_level') == '品类') & \
           (df.get('cate_02').astype(str).str.startswith(biz))


def diagnose_unit(df, adt, prev_day, prev_week, level, name, mask, yoy_dt=None):
    cur = row_metrics(df, adt, mask)
    if not cur:
        return None
    d1 = row_metrics(df, prev_day, mask)
    w1 = row_metrics(df, prev_week, mask)
    y1 = row_metrics(df, yoy_dt, mask) if yoy_dt else {}
    rec = {'level': level, 'name': name}
    for c in FUNNEL_ABS:
        rec[c] = cur.get(c)
    rec[STAR] = cur.get(STAR)
    for c in FUNNEL_RATE:
        rec[c] = cur.get(c)
    # 环比：单量 + 北极星（主看），漏斗四环节率（定位环节）
    rec['pay_pv_mom_t1'] = pct(cur.get('pay_pv'), d1.get('pay_pv'))
    rec['pay_pv_mom_w1'] = pct(cur.get('pay_pv'), w1.get('pay_pv'))
    rec['star_mom_t1'] = pct(cur.get(STAR), d1.get(STAR))
    rec['star_mom_w1'] = pct(cur.get(STAR), w1.get(STAR))
    # 同比：单量 + 北极星 vs 去年同期（统一星期对齐-364，缺则 None）
    # 低基数业务抑制：兴趣/二奢 且同比基准日<2026-01-01 → 25年基数低易误报，同比一律不算
    yoy_suppressed = yoy_low_base_suppressed(name, yoy_dt)
    if yoy_suppressed:
        rec['pay_pv_yoy'] = None
        rec['star_yoy'] = None
        rec['yoy_suppressed'] = '25年低基数,同比抑制'
    else:
        rec['pay_pv_yoy'] = pct(cur.get('pay_pv'), y1.get('pay_pv'))
        rec['star_yoy'] = pct(cur.get(STAR), y1.get(STAR))
        rec['yoy_suppressed'] = None
    # 主环比基准：上周同日优先（消解周内节奏），缺则回退 t-1
    if w1.get('pay_pv') is not None:
        rec['pay_pv_mom'] = rec['pay_pv_mom_w1']; rec['star_mom'] = rec['star_mom_w1']
        rec['mom_basis'] = '上周同日'; base = w1
    else:
        rec['pay_pv_mom'] = rec['pay_pv_mom_t1']; rec['star_mom'] = rec['star_mom_t1']
        rec['mom_basis'] = 't-1'; base = d1
    for c in FUNNEL_RATE:
        rec[f'{c}_mom_w1'] = pct(cur.get(c), w1.get(c))
        rec[f'{c}_mom'] = pct(cur.get(c), base.get(c))
    # 对大盘的贡献量：单量绝对变化（用主环比基准）
    base_pay = base.get('pay_pv')
    rec['pay_pv_delta'] = (None if cur.get('pay_pv') is None or base_pay is None
                           else int(cur['pay_pv'] - base_pay))
    return rec


def worst_stage(rec):
    """在漏斗四环节里挑环比跌得最狠的一环，作为归因指向。"""
    cand = [(c, rec.get(f'{c}_mom')) for c in FUNNEL_RATE]
    cand = [(c, v) for c, v in cand if v is not None]
    if not cand:
        return None
    c, v = min(cand, key=lambda x: x[1])
    zh = {'exp_penetration': '曝光渗透', 'detail_reach': '商详到达',
          'order_rate': '下单率', 'pay_rate': '支付率'}
    return f'{zh[c]}({v:+.1%})' if v < 0 else None


def biz_anomaly_verdict(rec, star_th, yoy_align=None):
    """分业务异常判定（核心结论必答项）。
    口径：北极星 dau_pay_rate 与 单量(pay_pv) 的【环比】(上周同日优先、缺则 t-1) 与【同比】(去年同期)，
    任一相对涨跌幅越 ±star_th（默认 0.15）即判异常；方向以北极星优先，北极星缺失时用单量。
    环比、同比基准都缺 → 判定不了，返回 '数据不足'。
    返回 (is_anomaly: bool|None, verdict: str, reason: str)。"""
    star = rec.get('star_mom')
    pay = rec.get('pay_pv_mom')
    star_y = rec.get('star_yoy')
    pay_y = rec.get('pay_pv_yoy')
    basis = rec.get('mom_basis') or '环比'
    has_star = star is not None and not pd.isna(star)
    has_pay = pay is not None and not pd.isna(pay)
    has_star_y = star_y is not None and not pd.isna(star_y)
    has_pay_y = pay_y is not None and not pd.isna(pay_y)
    if not has_star and not has_pay and not has_star_y and not has_pay_y:
        return None, '数据不足', f'北极星与单量的环比({basis})、同比基准均缺失，无法判定，建议补取数'
    star_s = f'{star:+.1%}' if has_star else 'NA'
    pay_s = f'{pay:+.1%}' if has_pay else 'NA'
    star_ys = f'{star_y:+.1%}' if has_star_y else 'NA'
    pay_ys = f'{pay_y:+.1%}' if has_pay_y else 'NA'
    ya = yoy_align or '去年同期'
    stg = rec.get('worst_stage')
    stg_s = f'，拖累环节 {stg}' if stg else ''
    # 触发项：北极星/单量的 环比 或 同比 任一越阈
    star_hit = has_star and abs(star) >= star_th
    pay_hit = has_pay and abs(pay) >= star_th
    star_y_hit = has_star_y and abs(star_y) >= star_th
    pay_y_hit = has_pay_y and abs(pay_y) >= star_th
    reason = (f'{basis}：北极星 {star_s} / 单量 {pay_s}；同比({ya})：北极星 {star_ys} / 单量 {pay_ys}')
    if star_hit or pay_hit or star_y_hit or pay_y_hit:
        # 方向：北极星环比优先，其次北极星同比，再单量
        lead = (star if star_hit else star_y if star_y_hit else pay if pay_hit else pay_y)
        arrow = '↓' if lead < 0 else '↑'
        trig = []
        if star_hit: trig.append(f'北极星环比 {star_s}')
        if pay_hit: trig.append(f'单量环比 {pay_s}')
        if star_y_hit: trig.append(f'北极星同比 {star_ys}')
        if pay_y_hit: trig.append(f'单量同比 {pay_ys}')
        return True, f'异常{arrow}（{"、".join(trig)} 越 ±{star_th:.0%}）', \
            f'{reason}，{"、".join(trig)} 触发阈值 ±{star_th:.0%}{stg_s}'
    return False, f'正常（北极星环比 {star_s}｜同比 {star_ys}）', \
        f'{reason}，环比与同比均在 ±{star_th:.0%} 阈值内'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True, help='tidy CSV（analyze_dimension.py 产出）')
    ap.add_argument('--analyze-dt', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--min-exp-uv', type=int, default=1000,
                    help='体量地板：曝光UV低于此值的品类行不参与下钻（小样本噪声）')
    ap.add_argument('--decline-threshold', type=float, default=0.10,
                    help='单量环比跌幅阈值，判定"走弱"（默认 10%）')
    ap.add_argument('--star-threshold', type=float, default=0.15,
                    help='分业务异常判定阈值：北极星环比相对涨跌幅越 ±此值判异常（默认 15%）')
    ap.add_argument('--drill-scene', default=None,
                    help='指定品类名（如 消费电子手机），拆到场景（需 tidy 含含该品类的场景交叉族）')
    args = ap.parse_args()

    df = pd.read_csv(args.input)
    df['dt'] = df['dt'].astype(str).str.slice(0, 10)
    for c in ['goods_level', 'cate', 'cate_02']:
        if c not in df.columns:
            df[c] = np.nan

    adt = args.analyze_dt
    d = datetime.strptime(adt, '%Y-%m-%d')
    prev_day = (d - timedelta(days=1)).strftime('%Y-%m-%d')
    prev_week = (d - timedelta(days=7)).strftime('%Y-%m-%d')
    # 同比基准日：统一星期对齐(-364)。真源 calendar_context.yoy_baseline（大促峰值日特例已剔除）
    yb = yoy_baseline(_d(adt))
    yoy_dt = yb['aligned_dt']
    yoy_align = yb['align_mode']

    rows = []
    # ---- 业务级 ----
    biz_recs = {}
    for biz in FOCUS_BIZ:
        rec = diagnose_unit(df, adt, prev_day, prev_week, '业务', biz, biz_mask(df, biz), yoy_dt=yoy_dt)
        if rec:
            rec['worst_stage'] = worst_stage(rec)
            is_anom, verdict, reason = biz_anomaly_verdict(rec, args.star_threshold, yoy_align=yoy_align)
            rec['biz_anomaly'] = is_anom          # True/False/None(数据不足)
            rec['biz_anomaly_verdict'] = verdict  # 简短标签，写核心结论
            rec['biz_anomaly_reason'] = reason    # 判定依据（北极星环比+单量辅证+环节）
            biz_recs[biz] = rec
            rows.append(rec)

    # ---- 品类级下钻（每个业务内） ----
    for biz in FOCUS_BIZ:
        cm = cate_mask(df, biz)
        cates = df[(df.dt == adt) & cm]
        if 'exp_uv' in cates.columns and args.min_exp_uv > 0:
            cates = cates[cates['exp_uv'].fillna(0) >= args.min_exp_uv]
        for _, cr in cates.iterrows():
            cname = str(cr.get('cate_02'))
            rec = diagnose_unit(df, adt, prev_day, prev_week, '品类', cname,
                                (df.tag_01 == CATE_TAG) & (df.get('cate_02') == cr.get('cate_02')),
                                yoy_dt=yoy_dt)
            if rec:
                rec['biz'] = biz
                rec['worst_stage'] = worst_stage(rec)
                rows.append(rec)

    # ---- 场景下钻（可选）----
    scene_note = None
    if args.drill_scene:
        target = args.drill_scene
        # 找含该品类且带场景的交叉族行（cate_02==target 且 main_scene/scene_02 非空）
        scmask = (df.get('cate_02') == target) & (
            df.get('main_scene').notna() if 'main_scene' in df.columns else False)
        sc = df[(df.dt == adt) & scmask]
        if sc.empty:
            scene_note = f'tidy 中无含品类「{target}」的场景交叉族行；需回取数步补拉 3/4维交叉族(端_业务/品类_场景)。'
        else:
            for _, sr in sc.iterrows():
                sname = sr.get('main_scene')
                tag = sr.get('tag_01')
                rec = diagnose_unit(df, adt, prev_day, prev_week, '场景',
                                    f'{target}@{sname}',
                                    (df.tag_01 == tag) & (df.get('cate_02') == target) &
                                    (df.get('main_scene') == sname), yoy_dt=yoy_dt)
                if rec:
                    rec['biz'] = target
                    rec['worst_stage'] = worst_stage(rec)
                    rows.append(rec)

    if not rows:
        print('[ERR] 三大业务在 tidy 里都取不到（检查是否含 单维度-拆分品类 族、dt 是否覆盖）',
              file=sys.stderr)
        sys.exit(1)

    res = pd.DataFrame(rows)
    front = ['level', 'biz', 'name', 'biz_anomaly', 'biz_anomaly_verdict', 'biz_anomaly_reason',
             'mom_basis', 'pay_pv', 'matched_dau_uv', STAR,
             'pay_pv_mom', 'star_mom', 'pay_pv_yoy', 'star_yoy', 'yoy_suppressed',
             'pay_pv_mom_w1', 'pay_pv_mom_t1',
             'star_mom_w1', 'star_mom_t1', 'pay_pv_delta', 'worst_stage']
    front = [c for c in front if c in res.columns]
    rest = [c for c in res.columns if c not in front]
    res = res[front + rest]
    res.to_csv(args.out, index=False, encoding='utf-8-sig')

    # ---- 分业务异常判定（核心结论必答项，最优先打印）----
    print(f'[分业务异常判定] 口径：北极星 dau_pay_rate 或 单量 的 环比(上周同日优先) 或 同比({yoy_align}={yoy_dt}) '
          f'任一越 ±{args.star_threshold:.0%} 判异常｜均在阈值内判正常')
    anom_biz = []
    for biz in FOCUS_BIZ:
        r = biz_recs.get(biz)
        if not r:
            print(f'   {biz}: 数据不足（tidy 未取到该业务 业务级行）')
            continue
        star = r.get(STAR)
        star_s = f'{star*100:.2f}%' if star is not None and not pd.isna(star) else 'NA'
        print(f'   {biz}: {r["biz_anomaly_verdict"]}｜北极星 {star_s}｜{r["biz_anomaly_reason"]}')
        if r.get('biz_anomaly') is True:
            anom_biz.append(biz)
    print(f'[分业务结论] ' + (f'异常业务：{"、".join(anom_biz)}（需在核心结论前置）'
                          if anom_biz else '三大业务北极星环比均在阈值内，无分业务异常'))

    # ---- 普降 vs 特征 判定（业务级，主看单量环比：上周同日优先，缺则 t-1）----
    th = args.decline_threshold
    moms = {b: r.get('pay_pv_mom') for b, r in biz_recs.items()
            if r.get('pay_pv_mom') is not None}
    basis = next((r.get('mom_basis') for r in biz_recs.values()), '上周同日')
    print(f'[诊断] 分析日={adt}（环比基准 t-1={prev_day} / 上周同日={prev_week}）')
    print(f'       重点业务单量环比(vs {basis}): ' +
          (', '.join(f'{b} {v:+.1%}' for b, v in moms.items()) or '（基准数据不足）'))
    if len(moms) >= 2:
        declining = [b for b, v in moms.items() if v <= -th]
        rising = [b for b, v in moms.items() if v >= th]
        if len(declining) == len(moms):
            verdict = f'普降：三大业务单量同步走弱（阈值 -{th:.0%}），非单一业务问题，优先查大盘/共性环节。'
        elif declining:
            worst = min(moms, key=lambda b: moms[b])
            verdict = (f'特征业务：{("、".join(declining))} 走弱，'
                       f'其中「{worst}」最重({moms[worst]:+.1%})；'
                       f'{("其余业务持平/上涨" if not rising else "、".join(rising)+" 反向上涨")}，'
                       f'建议下钻「{worst}」到品类。')
        else:
            verdict = '三大业务单量未见明显走弱（未越跌幅阈值），大盘平稳。'
    else:
        verdict = '重点业务环比基准数据不足（上周同日缺失），改看 vs t-1 或补取数。'
    print(f'[判定] {verdict}')

    # 特征品类：跌幅最大且对大盘贡献量为负的前几个
    cate_rows = res[res['level'] == '品类'].copy()
    if not cate_rows.empty and 'pay_pv_delta' in cate_rows.columns:
        drops = cate_rows[cate_rows['pay_pv_delta'].fillna(0) < 0].sort_values('pay_pv_delta')
        if not drops.empty:
            print(f'[特征品类] 单量下滑贡献最大(Δ单量 vs {basis})：')
            for _, r in drops.head(5).iterrows():
                stg = f' | 拖累环节 {r["worst_stage"]}' if r.get('worst_stage') else ''
                mom = r.get('pay_pv_mom')
                mom_s = f'{mom:+.1%}' if mom is not None and not pd.isna(mom) else 'NA'
                print(f'   {r["name"]}: Δ{int(r["pay_pv_delta"])} 单, '
                      f'环比 {mom_s}, 北极星 {r.get(STAR)}{stg}')
    if scene_note:
        print(f'[场景下钻] {scene_note}')
    print(f'[OK] 诊断明细 {len(res)} 行 → {args.out}')


if __name__ == '__main__':
    main()

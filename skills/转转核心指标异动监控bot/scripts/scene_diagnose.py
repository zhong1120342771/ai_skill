#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scene_diagnose.py — 分场景流量分发 + 转化效率诊断（v2-0710 改点3）

判各场景对【大盘】和【各业务】的两件事是否降低：
  · 流量分发：曝光UV(exp_uv) + 曝光渗透率(exp_penetration = 曝光UV/活跃DAU)
  · 转化效率：提袋率(bag_rate = 商详到达率 × 商详转化率 = 单量/曝光UV)
若某业务在某场景的流量或转化效率有问题，再细拆定位到是哪个品类。

输入：analyze_dimension.py 产出的 tidy 长表。
输出：诊断明细 CSV + 控制台判定摘要。

口径要点（见 references/字段映射与指标口径.md）：
  · 提袋率、曝光UV 分母不是活跃DAU，跨场景/业务聚合(求和)安全。
  · 曝光渗透率分母是 matched_dau_uv（分维度匹配DAU），业务×场景按端求和聚合为近似口径，
    组内任一行 matched_dau_uv 为空则不算(绝不当0)，输出标注近似。
  · 环比基准：上周同日优先(消解周内节奏)，缺则回退 t-1。

用法：
  python scene_diagnose.py --input tidy.csv --analyze-dt 2026-07-09 --out scene_diag.csv
  # 阈值(降低多少算异常)、体量地板可调
  python scene_diagnose.py --input tidy.csv --analyze-dt 2026-07-09 --out scene_diag.csv \
      --threshold 0.15 --min-exp-uv 1000
"""
import argparse, sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

FOCUS_BIZ = ['消费电子', '二奢', '兴趣']
SCENE_TAG = '单维度-拆分场景'                 # 大盘×场景
BIZ_SCENE_TAG = '3维度交叉-端_业务/品类_场景'  # 业务/品类×场景（含端，按端聚合回业务/品类×场景）
ABS = ['exp_uv', 'detail_uv', 'pay_pv', 'matched_dau_uv']
# 判定用指标：流量分发(曝光UV/曝光渗透率) + 转化效率(提袋率)
FLOW = [('exp_uv', '曝光UV'), ('exp_penetration', '曝光渗透率')]
EFF = [('bag_rate', '提袋率')]


def pct(cur, base):
    if base is None or pd.isna(base) or base == 0 or cur is None or pd.isna(cur):
        return None
    return round((cur - base) / base, 4)


def _num(v):
    return None if v is None or pd.isna(v) else float(v)


def agg_metrics(sub):
    """把一组行(可能跨端)求和聚合成一份指标 dict（提袋率/曝光渗透率从汇总绝对量重算）。"""
    if sub.empty:
        return {}
    s = {c: sub[c].sum(min_count=1) for c in ABS}
    exp, det, pay, dau = s['exp_uv'], s['detail_uv'], s['pay_pv'], s['matched_dau_uv']
    # 曝光渗透率：分母是分维度匹配DAU，组内有空则不算(近似口径，绝不当0)
    dau_ok = sub['matched_dau_uv'].notna().all() and dau and dau > 0
    m = {'exp_uv': _num(exp), 'detail_uv': _num(det), 'pay_pv': _num(pay),
         'matched_dau_uv': _num(dau) if dau_ok else None}
    m['exp_penetration'] = round(exp / dau, 5) if (dau_ok and exp is not None) else None
    m['bag_rate'] = round(pay / exp, 5) if (exp and exp > 0 and pay is not None) else None
    return m


def one_unit(df, adt, pd_dt, pw_dt, mask, label_level, name, biz=None):
    """算某个粒度(大盘场景/业务场景/品类场景)在分析日+两个基准日的指标与环比+判定。"""
    cur = agg_metrics(df[(df.dt == adt) & mask])
    if not cur or cur.get('exp_uv') in (None, 0):
        return None
    d1 = agg_metrics(df[(df.dt == pd_dt) & mask])
    w1 = agg_metrics(df[(df.dt == pw_dt) & mask])
    base, basis = (w1, '上周同日') if w1.get('exp_uv') is not None else (d1, 't-1')
    rec = {'level': label_level, 'biz': biz, 'scene': name, 'mom_basis': basis}
    for k in ['exp_uv', 'exp_penetration', 'bag_rate', 'matched_dau_uv', 'detail_uv', 'pay_pv']:
        rec[k] = cur.get(k)
    for k, _ in FLOW + EFF:
        rec[f'{k}_mom'] = pct(cur.get(k), base.get(k))
    return rec


def verdict(rec, th):
    """流量分发/转化效率是否降低：任一指标环比 <= -th 记为降低。返回(降标签, 降原因)。"""
    flow_hits, eff_hits = [], []
    for k, zh in FLOW:
        v = rec.get(f'{k}_mom')
        if v is not None and v <= -th:
            flow_hits.append(f'{zh} {v:+.1%}')
    for k, zh in EFF:
        v = rec.get(f'{k}_mom')
        if v is not None and v <= -th:
            eff_hits.append(f'{zh} {v:+.1%}')
    tags = []
    if flow_hits:
        tags.append('流量分发↓')
    if eff_hits:
        tags.append('转化效率↓')
    rec['flow_down'] = bool(flow_hits)
    rec['eff_down'] = bool(eff_hits)
    rec['scene_verdict'] = ('、'.join(tags) if tags else '正常') + f'（基准 {rec["mom_basis"]}）'
    detail = []
    if flow_hits:
        detail.append('流量:' + '、'.join(flow_hits))
    if eff_hits:
        detail.append('转化:' + '、'.join(eff_hits))
    rec['scene_reason'] = '；'.join(detail) if detail else (
        f'曝光UV {fmt_pct(rec.get("exp_uv_mom"))}｜曝光渗透率 {fmt_pct(rec.get("exp_penetration_mom"))}'
        f'｜提袋率 {fmt_pct(rec.get("bag_rate_mom"))} 均未越 -{th:.0%}')
    return rec


def fmt_pct(v):
    return f'{v:+.1%}' if v is not None and not pd.isna(v) else 'NA'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True, help='tidy CSV（analyze_dimension.py 产出）')
    ap.add_argument('--analyze-dt', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--threshold', type=float, default=0.15,
                    help='降低判定阈值：流量/转化效率环比 <= -此值 记为降低（默认15%）')
    ap.add_argument('--min-exp-uv', type=int, default=1000,
                    help='体量地板：曝光UV低于此值的场景/品类行不判（小样本噪声）')
    args = ap.parse_args()

    df = pd.read_csv(args.input)
    df['dt'] = df['dt'].astype(str).str.slice(0, 10)
    for c in ['main_scene', 'goods_level', 'cate', 'cate_02'] + ABS:
        if c not in df.columns:
            df[c] = np.nan
    for c in ABS:
        df[c] = pd.to_numeric(df[c], errors='coerce')

    adt = args.analyze_dt
    d = datetime.strptime(adt, '%Y-%m-%d')
    pd_dt = (d - timedelta(days=1)).strftime('%Y-%m-%d')
    pw_dt = (d - timedelta(days=7)).strftime('%Y-%m-%d')
    th = args.threshold

    rows = []
    # ---- 1) 大盘 × 场景（单维度-拆分场景）----
    scenes = sorted(df[(df.dt == adt) & (df.tag_01 == SCENE_TAG) &
                       (df.main_scene.notna())]['main_scene'].unique().tolist())
    dp_scene_recs = {}
    for sc in scenes:
        mask = (df.tag_01 == SCENE_TAG) & (df.main_scene == sc)
        rec = one_unit(df, adt, pd_dt, pw_dt, mask, '大盘场景', sc)
        if rec and (rec.get('exp_uv') or 0) >= args.min_exp_uv:
            verdict(rec, th)
            dp_scene_recs[sc] = rec
            rows.append(rec)

    # ---- 2) 业务 × 场景（3维度交叉-端_业务/品类_场景，按端聚合回 业务×场景）----
    biz_scene_flagged = []  # (biz, scene) 需要下钻到品类
    if (df.tag_01 == BIZ_SCENE_TAG).any():
        for biz in FOCUS_BIZ:
            for sc in scenes:
                mask = ((df.tag_01 == BIZ_SCENE_TAG) & (df.goods_level == '业务') &
                        (df.cate == biz) & (df.main_scene == sc))
                rec = one_unit(df, adt, pd_dt, pw_dt, mask, '业务场景', sc, biz=biz)
                if rec and (rec.get('exp_uv') or 0) >= args.min_exp_uv:
                    verdict(rec, th)
                    rows.append(rec)
                    if rec['flow_down'] or rec['eff_down']:
                        biz_scene_flagged.append((biz, sc))
    else:
        print('[warn] tidy 缺 3维度交叉-端_业务/品类_场景 族，业务×场景判定跳过；'
              '如需完整分场景×业务，取数步补拉该族。', file=sys.stderr)

    # ---- 3) 品类下钻：对被标记的 (业务,场景) 拆到品类 ----
    drill_notes = []
    for biz, sc in biz_scene_flagged:
        cmask = ((df.tag_01 == BIZ_SCENE_TAG) & (df.goods_level == '品类') &
                 (df.cate_02.astype(str).str.startswith(biz)) & (df.main_scene == sc))
        cates = df[(df.dt == adt) & cmask]['cate_02'].dropna().unique().tolist()
        if not cates:
            drill_notes.append(f'{biz}×{sc}: tidy 无该业务×场景的品类级行，需取数补 品类×场景 交叉。')
            continue
        found = False
        for cn in cates:
            mask = ((df.tag_01 == BIZ_SCENE_TAG) & (df.cate_02 == cn) & (df.main_scene == sc))
            rec = one_unit(df, adt, pd_dt, pw_dt, mask, '品类场景', f'{sc}', biz=biz)
            if rec and (rec.get('exp_uv') or 0) >= args.min_exp_uv:
                rec['cate_02'] = cn
                verdict(rec, th)
                rows.append(rec)
                found = True
        if not found:
            drill_notes.append(f'{biz}×{sc}: 品类级行体量均低于 {args.min_exp_uv}，不细拆。')

    if not rows:
        print('[ERR] 分场景诊断无有效行（检查 tidy 是否含 单维度-拆分场景 族、dt 覆盖）',
              file=sys.stderr)
        pd.DataFrame(columns=['level', 'biz', 'scene', 'cate_02', 'scene_verdict']).to_csv(
            args.out, index=False, encoding='utf-8-sig')
        sys.exit(1)

    res = pd.DataFrame(rows)
    front = ['level', 'biz', 'scene', 'cate_02', 'scene_verdict', 'scene_reason', 'mom_basis',
             'exp_uv', 'exp_uv_mom', 'exp_penetration', 'exp_penetration_mom',
             'bag_rate', 'bag_rate_mom', 'pay_pv', 'matched_dau_uv']
    front = [c for c in front if c in res.columns]
    res = res[front + [c for c in res.columns if c not in front]]
    res.to_csv(args.out, index=False, encoding='utf-8-sig')

    # ---- 控制台摘要 ----
    print(f'[分场景诊断] 分析日={adt}（基准 t-1={pd_dt} / 上周同日={pw_dt}）｜'
          f'降低阈值 -{th:.0%}｜流量=曝光UV+曝光渗透率，转化效率=提袋率')
    print('【大盘×场景】各场景对大盘的流量分发/转化效率是否降低：')
    dp_down = []
    for sc, r in dp_scene_recs.items():
        print(f'   {sc}: {r["scene_verdict"]}｜曝光UV {fmt_pct(r.get("exp_uv_mom"))}'
              f'、曝光渗透率 {fmt_pct(r.get("exp_penetration_mom"))}、提袋率 {fmt_pct(r.get("bag_rate_mom"))}')
        if r['flow_down'] or r['eff_down']:
            dp_down.append(sc)
    print(f'[大盘场景结论] ' + (f'走弱场景：{"、".join(dp_down)}' if dp_down
                           else '各场景对大盘的流量分发与转化效率均未见明显降低'))

    biz_rows = res[res['level'] == '业务场景']
    down_biz = biz_rows[(biz_rows['flow_down']) | (biz_rows['eff_down'])] if not biz_rows.empty else biz_rows
    if not down_biz.empty:
        print('【业务×场景】走弱清单（需下钻品类）：')
        for _, r in down_biz.iterrows():
            print(f'   {r["biz"]}×{r["scene"]}: {r["scene_verdict"]}｜{r["scene_reason"]}')
    else:
        print('【业务×场景】三大业务在各场景的流量/转化效率未见明显降低。')

    cate_rows = res[res['level'] == '品类场景']
    if not cate_rows.empty:
        print('【品类×场景下钻】走弱业务×场景细拆到品类：')
        for _, r in cate_rows.iterrows():
            print(f'   {r["biz"]}×{r["scene"]}×{r.get("cate_02")}: {r["scene_verdict"]}｜{r["scene_reason"]}')
    for n in drill_notes:
        print(f'   [下钻备注] {n}')
    print(f'[OK] 分场景诊断 {len(res)} 行 → {args.out}')


if __name__ == '__main__':
    main()

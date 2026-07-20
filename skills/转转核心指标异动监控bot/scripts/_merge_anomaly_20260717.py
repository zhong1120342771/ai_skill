#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性合并脚本：把 Step3 各指标/各维度 anomaly 分片合成 anomaly_2026-07-17.csv
逻辑：去重 -> 剔 inf/0基数趋势噪声 -> 馆场景同比暂停 -> 标 real_anomaly/seasonal
按 |change_pct| 降序。列对齐 output-schemas Step3 + 附 round/is_real 便于下钻。"""
import pandas as pd, glob, numpy as np, os

AR = os.path.expanduser('~/.claude/analysis_reports')
parts = sorted(glob.glob(f'{AR}/anomaly_2026-07-17_*.csv'))
# 排除本合并产物自身（若已存在）
parts = [p for p in parts if not p.endswith('anomaly_2026-07-17.csv')]

frames = []
for p in parts:
    df = pd.read_csv(p)
    if df.empty:
        continue
    frames.append(df)
allp = pd.concat(frames, ignore_index=True)

COLS = ['tag_01','wd','metric','anomaly_type','base_value','cur_value','change_pct','abs_scale',
        'yoy_dt','yoy_align','ly_base_value','ly_cur_value','ly_change_pct','seasonal','seasonal_verdict']
for c in COLS:
    if c not in allp.columns:
        allp[c] = np.nan

# 去重（同一条异动可能被多个 --by 分片重复算出）
allp = allp.drop_duplicates(subset=['tag_01','wd','metric','anomaly_type'])

# 剔 inf / 基数=0 的趋势拐点噪声（0→极小值，change_pct=inf，无业务意义）
allp = allp[np.isfinite(allp['change_pct'].astype(float))]
allp = allp[~((allp['anomaly_type']=='趋势拐点') & (allp['base_value'].fillna(0)==0))]

# 馆场景年同比暂停（2027-01-01前）：同比命中且 wd 含"馆"的，剔出真异动，另标注
def is_guan(wd):
    return isinstance(wd,str) and '馆' in wd
allp['_yoy'] = allp['anomaly_type'].astype(str).str.startswith('同比')
guan_yoy = allp['_yoy'] & allp['wd'].apply(is_guan)

# real_anomaly 标记：季节性=True 的周环比 -> 周期性可解释(非真异动)；馆场景同比 -> 暂停(不计真异动)
# 真异动主清单门槛：业务可读粒度(整体/单维度) 或 该行自身单量 pay_pv 足够大(>=50)
# scene/货 场景行的 abs_scale 是全站DAU(误导)，故主清单只认单量绝对量：用 pay_pv 分片的 abs_scale 或粒度
PAY_MIN = 50
def legible(tag):
    return tag == '整体' or str(tag).startswith('单维度')

def classify(r):
    if r['_yoy'] and is_guan(r['wd']):
        return '馆场景年同比暂停'
    if r['seasonal'] == True or str(r['seasonal']).lower()=='true':
        return '季节性可解释'
    # 主清单：业务可读粒度，或 pay_pv 指标且单量>=PAY_MIN
    if legible(r['tag_01']):
        return '真异动·主清单'
    if r['metric']=='pay_pv' and pd.notna(r['abs_scale']) and float(r['abs_scale'])>=PAY_MIN:
        return '真异动·主清单'
    return '真异动·细粒度候选'
allp['verdict'] = allp.apply(classify, axis=1)
allp = allp.drop(columns=['_yoy'])
allp['round'] = 1

# 排序：主清单优先，再按 |change_pct| 降序
allp['_absc'] = allp['change_pct'].abs()
order = {'真异动·主清单':0,'真异动·细粒度候选':1,'季节性可解释':2,'馆场景年同比暂停':3}
allp['_o'] = allp['verdict'].map(order).fillna(4)
allp = allp.sort_values(['_o','_absc'], ascending=[True,False]).drop(columns=['_absc','_o'])

out_cols = COLS + ['verdict','round']
allp = allp[out_cols]
outp = f'{AR}/anomaly_2026-07-17.csv'
allp.to_csv(outp, index=False, encoding='utf-8-sig')
print(f'[OK] 合并 {len(allp)} 条 -> {outp}')
print('verdict 分布:')
print(allp['verdict'].value_counts().to_string())
print('\nmetric 分布(仅真异动):')
print(allp[allp.verdict=='真异动']['metric'].value_counts().to_string())
print('\nanomaly_type 分布(仅真异动):')
print(allp[allp.verdict=='真异动']['anomaly_type'].value_counts().to_string())

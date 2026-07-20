#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qa_check.py — 结论生成前的质量闸口

检查 tidy 长表 + 异动清单的硬/软问题，passed=False 即阻断流水线进入结论生成。
硬失败(hard_failures，必停)：
  - 必需列缺失 / 全空
  - 维度解析失败率过高(交叉行端列空 > 5%)
  - 北极星与漏斗链不自洽(整体行 dau_pay_rate 与四环节连乘偏差过大)
软警告(soft_warnings，记录不阻断)：
  - matched_dau_uv NULL 率偏高(> 2%)
  - 主指标当日缺失率 > 30%
  - 异动清单为空 / 日期覆盖不足

用法：
  python qa_check.py --tidy tidy.csv --anomaly anomaly.csv --analyze-dt 2026-07-07 \
      --metric dau_pay_rate --out quality_check.json
"""
import argparse, json, sys
from datetime import datetime, timedelta
import pandas as pd

REQUIRED = ['tag_01','wd','exp_uv','detail_uv','order_uv','pay_pv','matched_dau_uv','dt']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tidy', required=True)
    ap.add_argument('--anomaly', default=None)
    ap.add_argument('--analyze-dt', required=True)
    ap.add_argument('--metric', default='dau_pay_rate', help='本次结论所用主指标')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    hard, soft, info = [], [], {}
    df = pd.read_csv(args.tidy)
    df['dt'] = df['dt'].astype(str).str.slice(0, 10)

    miss = [c for c in REQUIRED if c not in df.columns]
    if miss:
        hard.append(f'缺必需列: {miss}')
    info['rows'] = len(df)
    info['dates'] = sorted(df['dt'].unique().tolist())

    cur = df[df.dt == args.analyze_dt]

    # 维度解析健康度（只统计确实含「端」维度的交叉族——scene组合_业务/来源/资产分层等
    #   本就不含端，duan 空是设计使然，不能计入解析失败率）
    if 'duan' in df.columns:
        cross = df[df['tag_01'].astype(str).str.contains('维度交叉')
                   & df['tag_01'].astype(str).str.contains('端')]
        if len(cross):
            null_rate = cross['duan'].isna().mean()
            info['cross_duan_null_rate'] = round(float(null_rate), 4)
            info['cross_duan_scope'] = '仅含端维度的交叉族'
            if null_rate > 0.05:
                hard.append(f'交叉行端列解析失败率 {null_rate:.1%} > 5%，wd 拆分逻辑可能漏枚举值')

    # matched_dau_uv NULL 率（正常 ~3300 行里 6~8 行，>2% 告警）
    if 'matched_dau_uv' in df.columns and len(cur):
        null_rate = cur['matched_dau_uv'].isna().mean()
        info['matched_dau_uv_null_rate'] = round(float(null_rate), 4)
        if null_rate > 0.02:
            soft.append(f'matched_dau_uv 当日 NULL 率 {null_rate:.1%} > 2%，DAU 分母完整性闸门异常')

    # 北极星与漏斗链自洽性（整体行：dau_pay_rate ≈ 曝光渗透×商详到达×下单率×支付率）
    whole = cur[cur['tag_01'] == '整体']
    if len(whole):
        r = whole.iloc[0]
        try:
            chain = (r['exp_penetration'] * r['detail_reach'] * r['order_rate'] * r['pay_rate'])
            star = r['dau_pay_rate']
            if pd.notna(chain) and pd.notna(star) and star > 0:
                dev = abs(chain - star) / star
                info['整体_北极星_链乘偏差'] = round(float(dev), 4)
                if dev > 0.05:
                    hard.append(f'整体行北极星({star:.5f})与漏斗四环节连乘({chain:.5f})偏差 {dev:.1%} > 5%，'
                                '口径可能不自洽')
        except (KeyError, TypeError):
            soft.append('缺漏斗环节列，跳过北极星链乘自洽性校验')

    # 主指标缺失率
    if args.metric in df.columns and len(cur):
        mr = cur[args.metric].isna().mean()
        info[f'{args.metric}_missing_rate'] = round(float(mr), 4)
        if mr > 0.30:
            soft.append(f'{args.metric} 当日缺失率 {mr:.1%} > 30%')

    # 环比/趋势的日期覆盖
    d = datetime.strptime(args.analyze_dt, '%Y-%m-%d')
    for off, label in [(1,'t-1'), (7,'上周同日')]:
        bd = (d - timedelta(days=off)).strftime('%Y-%m-%d')
        if bd not in info['dates']:
            soft.append(f'缺基准日 {bd}({label})，无法做该环比')
    if len(info['dates']) < 3:
        soft.append('日期 < 3 天，趋势拐点判断不可靠')

    # 异动清单
    if args.anomaly:
        try:
            a = pd.read_csv(args.anomaly)
            info['anomaly_count'] = len(a)
            if len(a) == 0:
                soft.append('异动清单为空，确认阈值是否过严或当日确实平稳')
        except Exception as e:
            soft.append(f'异动清单读取失败: {e}')

    passed = len(hard) == 0
    out = {'passed': passed, 'analyze_dt': args.analyze_dt, 'metric': args.metric,
           'hard_failures': hard, 'soft_warnings': soft, 'info': info,
           'checked_at': datetime.now().isoformat(timespec='seconds')}
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()

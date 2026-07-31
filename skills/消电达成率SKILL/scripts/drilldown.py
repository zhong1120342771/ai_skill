# -*- coding: utf-8 -*-
"""
未达标指标归因用的漏斗拆解 + 维度下钻工具（读同一份明细 CSV）。

漏斗四环节（提袋率的乘法链路）：
  曝光渗透率 exp_uv/uv_all  →  商详到达率 detail_uv/exp_uv
  →  下单率 order_uv/detail_uv  →  支付效率 pay_pv/order_uv
  其中 提袋率 = pay_pv/exp_uv = 前四环节连乘；商详转化率 = pay_pv/detail_uv。
把某未达标指标沿这条链拆开，看是哪一环拖平的（首月 vs 末月）。

用法（命令行给一个 JSON 任务文件，或直接改 __main__ 里的调用）：
  python drilldown.py --csv 明细.csv --tasks tasks.json --first 1 --last 6

tasks.json 结构示例见 references/attribution_playbook.md。
本脚本更多是"可调用函数库 + CLI 薄封装"，归因分析时按需组合 funnel_decomp / drill。
"""
import csv, json, argparse
from collections import defaultdict

_AGG = None
_FIRST = 1
_LAST = 6


def parse_month(dt):
    sep = '/' if '/' in dt else '-'
    p = dt.split(sep)
    return int(p[0]), int(p[1])


def build_agg(csv_path, cols, year=2026):
    agg = defaultdict(lambda: defaultdict(float))
    with open(csv_path, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            y, mo = parse_month(row['dt'])
            if y != year:
                continue
            k = (row['tag_01'], row['wd'], mo)
            for c in cols:
                if c in row:
                    try:
                        agg[k][c] += float(row[c] or 0)
                    except ValueError:
                        pass
    return agg


def g(tag, wd, mo, c):
    return _AGG[(tag, wd, mo)][c]


def r(tag, wd, mo, num, den):
    d = g(tag, wd, mo, den)
    return g(tag, wd, mo, num) / d if d else None


def pct(v):
    return '%.3f%%' % (v * 100) if v is not None else 'NA'


def num(v):
    return '%.2f' % v if v is not None else 'NA'


def chg(v1, v2):
    return '%+.1f%%' % ((v2 - v1) / v1 * 100) if (v1 and v2) else 'NA'


def funnel_decomp(label, tag, wd):
    print('\n===== %s | 漏斗环节拆解 (%d月 vs %d月) =====' % (label, _FIRST, _LAST))
    stages = [
        ('曝光渗透率 exp_uv/uv_all', 'exp_uv', 'uv_all', pct),
        ('商详到达率 detail_uv/exp_uv', 'detail_uv', 'exp_uv', pct),
        ('下单率 order_uv/detail_uv', 'order_uv', 'detail_uv', pct),
        ('支付效率 pay_pv/order_uv', 'pay_pv', 'order_uv', num),
        ('[=商详转化率 pay_pv/detail_uv]', 'pay_pv', 'detail_uv', pct),
        ('[=提袋率 pay_pv/exp_uv]', 'pay_pv', 'exp_uv', pct),
    ]
    for nm, a, b, f in stages:
        v1 = r(tag, wd, _FIRST, a, b)
        v2 = r(tag, wd, _LAST, a, b)
        print('  %-32s 首月=%-10s 末月=%-10s 变化=%s' % (nm, f(v1), f(v2), chg(v1, v2)))


def drill(label, tag, members, num_c, den_c, fmt=pct):
    """members: 完整 wd 名列表。逐个看 num_c/den_c 首月 vs 末月。"""
    print('\n----- %s | 维度下钻 -----' % label)
    print('  %-22s %-12s %-12s %-10s' % ('子维度', '首月', '末月', '变化'))
    for wd in members:
        v1 = r(tag, wd, _FIRST, num_c, den_c)
        v2 = r(tag, wd, _LAST, num_c, den_c)
        print('  %-22s %-12s %-12s %s' % (wd, fmt(v1), fmt(v2), chg(v1, v2)))


def growth(label, tag, members, col):
    """看某个绝对量列（如 exp_uv 曝光UV）首月→末月增长率，用于业务/品类曝光对比。"""
    print('\n----- %s | %s 增长 -----' % (label, col))
    for wd in members:
        v1 = g(tag, wd, _FIRST, col)
        v2 = g(tag, wd, _LAST, col)
        print('  %-22s 首月=%.0f 末月=%.0f 变化=%s' % (wd, v1, v2, chg(v1, v2)))


def main():
    global _AGG, _FIRST, _LAST
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--tasks', help='JSON 任务清单；不给则只建 agg 供交互调用')
    ap.add_argument('--first', type=int, default=1)
    ap.add_argument('--last', type=int, default=6)
    args = ap.parse_args()
    _FIRST, _LAST = args.first, args.last

    default_cols = ['exp_pv', 'exp_uv', 'detail_pv', 'detail_uv',
                    'order_pv', 'order_uv', 'pay_pv', 'uv_all', 'matched_dau_uv']
    _AGG = build_agg(args.csv, default_cols)

    if not args.tasks:
        print('agg 已构建。请在交互环境 import 本模块调用 funnel_decomp/drill/growth。')
        return

    tasks = json.load(open(args.tasks, encoding='utf-8'))
    for t in tasks:
        kind = t['kind']
        if kind == 'funnel':
            funnel_decomp(t['label'], t['tag'], t['wd'])
        elif kind == 'drill':
            drill(t['label'], t['tag'], t['members'], t['num'], t['den'],
                  pct if t.get('fmt', 'pct') == 'pct' else num)
        elif kind == 'growth':
            growth(t['label'], t['tag'], t['members'], t['col'])


if __name__ == '__main__':
    main()

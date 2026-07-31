# -*- coding: utf-8 -*-
"""
为每个指标画 H1 逐月趋势图。达标绿、未达标红，虚线为目标线（首月×(1+目标)）。

用法：
  python make_charts.py --result result.json --out-dir ./charts
产出 chart_01.png .. chart_NN.png，序号与 result.json 中 rows 顺序一致。
"""
import json, os, argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager


def set_cn_font():
    for fp in ['/System/Library/Fonts/PingFang.ttc',
               '/System/Library/Fonts/STHeiti Medium.ttc']:
        if os.path.exists(fp):
            font_manager.fontManager.addfont(fp)
            plt.rcParams['font.family'] = font_manager.FontProperties(fname=fp).get_name()
            break
    plt.rcParams['axes.unicode_minus'] = False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--result', default='result.json')
    ap.add_argument('--out-dir', default='.')
    ap.add_argument('--dpi', type=int, default=130)
    args = ap.parse_args()
    set_cn_font()
    os.makedirs(args.out_dir, exist_ok=True)

    data = json.load(open(args.result, encoding='utf-8'))
    rows = data['rows'] if isinstance(data, dict) else data
    months = data.get('months', list(range(1, 7))) if isinstance(data, dict) else list(range(1, 7))
    mlabels = ['%d月' % m for m in months]

    for i, r in enumerate(rows):
        vals = r['vals']
        isp = r.get('is_percent', True)
        ys = [(v * 100 if isp else v) if v is not None else None for v in vals]
        fig, ax = plt.subplots(figsize=(7, 4))
        color = '#27ae60' if r['meet'] else '#c0392b'
        ax.plot(mlabels, ys, marker='o', color=color, linewidth=2, markersize=6)
        for x, y in enumerate(ys):
            if y is None:
                continue
            lbl = ('%.2f%%' % y) if isp else ('%.1f' % y)
            ax.annotate(lbl, (x, y), textcoords='offset points', xytext=(0, 8),
                        ha='center', fontsize=8, color='#333')
        if ys[0] is not None:
            tline = ys[0] * (1 + r['target'])
            ax.axhline(tline, ls='--', color='#888', lw=1)
            ax.annotate('目标线 %s' % (('%.2f%%' % tline) if isp else ('%.1f' % tline)),
                        (len(mlabels) - 1, tline), textcoords='offset points',
                        xytext=(0, 4), ha='right', fontsize=8, color='#888')
        act = ('%+.1f%%' % (r['actual'] * 100)) if r['actual'] is not None else 'NA'
        status = '达标' if r['meet'] else '未达标'
        ax.set_title('%s  H1逐月趋势\n实际提升(末vs首) %s / 目标 +%.1f%%  → %s'
                     % (r['name'], act, r['target'] * 100, status), fontsize=11)
        ax.set_ylabel('比率(%)' if isp else '数值')
        ax.grid(axis='y', ls=':', alpha=0.5)
        ax.margins(y=0.18)
        fig.tight_layout()
        fn = os.path.join(args.out_dir, 'chart_%02d.png' % (i + 1))
        fig.savefig(fn, dpi=args.dpi)
        plt.close(fig)
        print('saved', fn)
    print('done, %d charts' % len(rows))


if __name__ == '__main__':
    main()

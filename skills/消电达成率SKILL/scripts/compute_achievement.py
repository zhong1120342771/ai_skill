# -*- coding: utf-8 -*-
"""
消电达成率计算：读明细 CSV + 指标配置 JSON，按月聚合分子/分母，算达成率。

达成率口径（团队既定，勿改）：
  实际提升 = (末月比率 - 首月比率) / 首月比率      # 相对提升，不是绝对差
  达标     = 实际提升 >= 目标提升(target)
  比率     = 月内先对分子/分母各自加总，再相除（不是先算日比率再平均）

用法：
  python compute_achievement.py \
    --csv /path/to/明细.csv \
    --metrics metrics_config.json \
    --out result.json \
    [--start-month 1] [--end-month 6]

明细 CSV 必备列：tag_01, wd, dt, 以及各指标用到的分子/分母列
  （典型：exp_pv,exp_uv,detail_pv,detail_uv,order_pv,order_uv,pay_pv,uv_all）
dt 支持 'YYYY/M/D' 或 'YYYY-MM-DD' 两种格式，自动识别。
"""
import csv, json, argparse, os
from collections import defaultdict


def parse_month(dt):
    """返回 (year, month)。兼容 2026/1/5 和 2026-01-05。"""
    sep = '/' if '/' in dt else '-'
    p = dt.split(sep)
    return int(p[0]), int(p[1])


def load_agg(csv_path, num_den_cols, start_m, end_m, year):
    """聚合 (tag_01, wd, month) -> {col: sum}。只保留指定年份、月份窗口。"""
    agg = defaultdict(lambda: defaultdict(float))
    with open(csv_path, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            y, mo = parse_month(row['dt'])
            if y != year or mo < start_m or mo > end_m:
                continue
            k = (row['tag_01'], row['wd'], mo)
            for c in num_den_cols:
                if c in row:
                    try:
                        agg[k][c] += float(row[c] or 0)
                    except ValueError:
                        pass
    return agg


def ratio(agg, tag, wd, mo, num, den):
    k = (tag, wd, mo)
    d = agg[k][den]
    return (agg[k][num] / d) if d else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--metrics', required=True, help='指标配置 JSON')
    ap.add_argument('--out', default='result.json')
    ap.add_argument('--start-month', type=int, default=1)
    ap.add_argument('--end-month', type=int, default=6)
    ap.add_argument('--year', type=int, default=2026)
    args = ap.parse_args()

    cfg = json.load(open(args.metrics, encoding='utf-8'))
    metrics = cfg['metrics'] if isinstance(cfg, dict) else cfg

    cols = set()
    for m in metrics:
        cols.add(m['num'])
        cols.add(m['den'])

    agg = load_agg(args.csv, cols, args.start_month, args.end_month, args.year)
    months = list(range(args.start_month, args.end_month + 1))

    rows = []
    for m in metrics:
        vals = [ratio(agg, m['tag'], m['wd'], mo, m['num'], m['den']) for mo in months]
        first, last = vals[0], vals[-1]
        actual = (last - first) / first if (first and last) else None
        meet = (actual is not None and actual >= m['target'])
        rows.append(dict(
            name=m['name'], tag=m['tag'], wd=m['wd'],
            num=m['num'], den=m['den'],
            vals=vals, target=m['target'],
            is_percent=m.get('is_percent', True),
            actual=actual, meet=meet,
            lead=m.get('lead', {}),   # 方向/负责人/目标值提升/当前值/期望值 等表格前置列
        ))

    json.dump(dict(months=months, rows=rows), open(args.out, 'w'),
              ensure_ascii=False, indent=2)

    # 控制台速览
    def fmt(v, isp):
        if v is None:
            return 'NA'
        return ('%.3f%%' % (v * 100)) if isp else ('%.2f' % v)

    hdr = '指标 | ' + ' | '.join('%d月' % mo for mo in months) + ' | 实际提升 | 目标 | 达标'
    print(hdr)
    print('-' * len(hdr))
    for r in rows:
        vs = ' | '.join(fmt(v, r['is_percent']) for v in r['vals'])
        act = ('%+.1f%%' % (r['actual'] * 100)) if r['actual'] is not None else 'NA'
        print('%s | %s | %s | +%.1f%% | %s' % (
            r['name'], vs, act, r['target'] * 100,
            '达标' if r['meet'] else '未达标'))
    print('\n达标: %d/%d' % (sum(1 for r in rows if r['meet']), len(rows)))
    print('结果写入', args.out)


if __name__ == '__main__':
    main()

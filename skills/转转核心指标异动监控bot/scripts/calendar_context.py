#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
calendar_context.py — 日历与季节性上下文（异动判定的"背景板"）

给某个分析日贴上日历标签，帮异动步与结论步区分：
  这波涨跌是「真异动」，还是「日历可解释」（周末、法定节假日、调休补班）。

核心用途（异动归因前先问一句）：
  - 环比 vs t-1 跌了 → 是不是 t-1 本身是周末高基数，今天回落属正常节奏？
  - 环比 vs 上周同日 —— 本脚本给出「上周同日」和「上月同日」的对齐建议，避免拿工作日比节假日。

无外部节假日库依赖：法定节假日/调休以常量维护（真源见
references/日历与季节性.md，改一处同步两处）。覆盖 2025-01 ~ 2026-12，逐年补。
注意：本脚本**不含大促窗口/峰日**——那类节点属外部行业惯例、非用户输入，已按全局规则
「不拿行业通用标准当用户输入」剔除。若需大促背景，须由用户明确给定或从实测数据得出。

用法：
  python calendar_context.py --dt 2026-07-08                 # 打印该日日历上下文
  python calendar_context.py --dt 2026-07-08 --json          # 机器可读 JSON（供结论步引用）
  python calendar_context.py --dt 2026-07-08 --compare 2026-07-01  # 顺带判定两日可比性
"""
import argparse, json, sys
from datetime import date, datetime, timedelta

WEEKDAY_CN = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

# 法定节假日（放假日）：真源 references/日历与季节性.md。逐年补。
HOLIDAYS = {
    # 2025
    '2025-01-01': '元旦',
    **{f'2025-01-{d:02d}': '春节' for d in range(28, 32)},
    **{f'2025-02-{d:02d}': '春节' for d in range(1, 5)},
    **{f'2025-04-{d:02d}': '清明' for d in (4, 5, 6)},
    **{f'2025-05-{d:02d}': '劳动节' for d in range(1, 6)},
    **{f'2025-05-31': '端午', '2025-06-01': '端午', '2025-06-02': '端午'},
    **{f'2025-10-{d:02d}': '国庆中秋' for d in range(1, 9)},
    # 2026
    '2026-01-01': '元旦',
    **{f'2026-02-{d:02d}': '春节' for d in range(16, 23)},   # 除夕2/16~初六2/22（预估，以国务院公布为准）
    **{f'2026-04-{d:02d}': '清明' for d in (4, 5, 6)},
    **{f'2026-05-{d:02d}': '劳动节' for d in range(1, 6)},
    '2026-06-19': '端午', '2026-06-20': '端午', '2026-06-21': '端午',
    **{f'2026-09-{d:02d}': '中秋' for d in (25, 26, 27)},
    **{f'2026-10-{d:02d}': '国庆' for d in range(1, 8)},
}

# 调休补班（周末上班日）：这些"周末"其实是工作日节奏，别当周末低基数。
MAKEUP_WORKDAYS = {
    '2025-01-26', '2025-02-08', '2025-04-27', '2025-09-28', '2025-10-11',
    '2026-02-15', '2026-09-19',  # 预估，以官方公布为准
}

# 大促/营销窗口与峰日：已剔除。
# 618/双11/双12/年货节等时间节点属电商行业惯例、非用户明确输入，按全局规则
# 「不拿行业通用标准当用户输入」不再硬编码。同比对齐因此统一走星期对齐(-364天，
# 纯日历计算无臆测)。若确需大促背景，由用户显式给定窗口或从实测数据取峰，不在此默认生成。

# 低基数业务同比抑制（用户输入，2026-07-20）：
# 兴趣 / 二奢 两个业务 2025 年的转化率与单量基数低，同比(去年同期)极易越阈值、误报异常。
# 规则：这两个业务的【转化率(北极星/漏斗各环节率)】与【单量(pay_pv)】，
#       当【同比基准日 < YOY_LOW_BASE_CUTOFF(2026-01-01)】时，一律不做同比、不参与异常判定。
# 到分析日的去年同期落到 2026-01-01 及以后（即分析日 >= 2026-12-31）后自动恢复同比。
# 环比/横向/趋势不受此规则影响；消费电子等其他业务不受影响。
YOY_LOW_BASE_CUTOFF = '2026-01-01'
YOY_LOW_BASE_BIZ = ('二奢', '兴趣')


def yoy_low_base_suppressed(name, yoy_base_dt):
    """判断某业务/品类的同比是否因 25 年低基数被抑制。
    name（业务名/品类名/场景名，如 '二奢'、'二奢包袋'、'兴趣骑行@首页feeds'）含 '二奢'/'兴趣'，
    且同比基准日 yoy_base_dt < YOY_LOW_BASE_CUTOFF(2026-01-01) → 返回 True。
    True 表示：该行转化率/单量的同比应跳过（不计算、不计入异常）。"""
    if not name or yoy_base_dt is None:
        return False
    if str(yoy_base_dt) >= YOY_LOW_BASE_CUTOFF:
        return False
    return any(b in str(name) for b in YOY_LOW_BASE_BIZ)


def d(s):
    return datetime.strptime(s, '%Y-%m-%d').date()


def day_type(day):
    """返回 (type, label)：法定节假日 / 调休补班 / 周末 / 工作日。"""
    s = day.isoformat()
    if s in HOLIDAYS:
        return 'holiday', f'法定节假日·{HOLIDAYS[s]}'
    if s in MAKEUP_WORKDAYS:
        return 'makeup_workday', '调休补班(周末上班)'
    if day.weekday() >= 5:
        return 'weekend', '周末'
    return 'workday', '工作日'


def yoy_baseline(day):
    """给分析日推荐【同比(去年同期)】对齐基准（双口径同比，无大促特例）：
      - 同比周(week_aligned_dt)：分析日 -364 天(=52 周)，保持星期几一致，消解周内节奏差。主口径。
      - 同比日(date_aligned_dt)：去年同一日历日(如 2026-07-13 → 2025-07-13)。
    大促峰值日的"日期对齐"特例已剔除（大促节点非用户输入，见文件头说明）——同比统一星期对齐。
    aligned_dt/align_mode 保留旧字段名(=星期对齐主口径)，向后兼容旧调用。
    peak_name 恒为 None（保留字段防下游 KeyError）。
    返回 dict：{aligned_dt, align_mode, peak_name, weekday_aligned, prev_week_dt,
               week_aligned_dt, date_aligned_dt, dual_yoy}
      prev_week_dt = 同比周基准日再往前 7 天(去年的"上周同日"位)，供周环比的去年同期校验用。
      dual_yoy = 同比周≠同比日时 True(两列都要取)。"""
    # 日期对齐：去年同一 月-日（闰年 2/29 回退到 2/28）
    try:
        date_aligned = day.replace(year=day.year - 1)
    except ValueError:
        date_aligned = day.replace(year=day.year - 1, day=28)
    week_aligned = day - timedelta(days=364)
    aligned = week_aligned               # 主口径统一=星期对齐
    mode = '星期对齐(-364天)'
    dual = week_aligned != date_aligned
    return {'aligned_dt': aligned.isoformat(), 'align_mode': mode,
            'peak_name': None, 'weekday_aligned': WEEKDAY_CN[aligned.weekday()],
            'prev_week_dt': (week_aligned - timedelta(days=7)).isoformat(),
            'week_aligned_dt': week_aligned.isoformat(),   # 同比周
            'date_aligned_dt': date_aligned.isoformat(),   # 同比日
            'dual_yoy': dual}


def context(day):
    dtype, dlabel = day_type(day)
    ctx = {
        'dt': day.isoformat(),
        'weekday': WEEKDAY_CN[day.weekday()],
        'day_type': dtype,
        'day_type_label': dlabel,
        'is_rest_day': dtype in ('holiday', 'weekend'),
        'yoy_baseline': yoy_baseline(day),
    }
    return ctx


def comparability(a, b):
    """判定两日环比是否"同质可比"（同为工作日 or 同为休息日）。"""
    ca, cb = context(a), context(b)
    reasons = []
    ok = True
    if ca['is_rest_day'] != cb['is_rest_day']:
        ok = False
        reasons.append(f'一为{"休息日" if ca["is_rest_day"] else "工作日"}、'
                       f'另一为{"休息日" if cb["is_rest_day"] else "工作日"}，作息节奏不同，环比会被日历效应污染')
    if ca['day_type'] == 'makeup_workday' or cb['day_type'] == 'makeup_workday':
        reasons.append('含调休补班日：日期虽是周末但按工作日跑量，勿按周末低基数解读')
    if ok and not reasons:
        reasons.append('两日同质（作息一致），环比可直接比')
    return {'comparable': ok, 'reasons': reasons, 'a': ca, 'b': cb}


def suggest_baselines(day):
    """给分析日推荐对齐基准：上周同日 + 上月同日，并各自标注同质性。"""
    out = []
    for delta, name in [(7, '上周同日'), (14, '两周前同日')]:
        base = day - timedelta(days=delta)
        cmp = comparability(day, base)
        out.append({'baseline': name, 'dt': base.isoformat(),
                    'comparable': cmp['comparable'], 'reasons': cmp['reasons']})
    # 上月同日（日历日对齐）
    m, y = day.month, day.year
    pm_y, pm = (y - 1, 12) if m == 1 else (y, m - 1)
    try:
        last_month = day.replace(year=pm_y, month=pm)
        cmp = comparability(day, last_month)
        out.append({'baseline': '上月同日', 'dt': last_month.isoformat(),
                    'comparable': cmp['comparable'], 'reasons': cmp['reasons']})
    except ValueError:
        pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dt', required=True, help='分析日 YYYY-MM-DD')
    ap.add_argument('--compare', default=None, help='另一日，判定与 --dt 的环比可比性')
    ap.add_argument('--json', action='store_true', help='输出 JSON')
    args = ap.parse_args()

    day = d(args.dt)
    ctx = context(day)
    ctx['baseline_suggestions'] = suggest_baselines(day)
    if args.compare:
        ctx['comparison'] = comparability(day, d(args.compare))

    if args.json:
        print(json.dumps(ctx, ensure_ascii=False, indent=2))
        return

    print(f'[日历] {ctx["dt"]} {ctx["weekday"]} · {ctx["day_type_label"]}'
          f'{" · 休息日" if ctx["is_rest_day"] else ""}')
    yb = ctx['yoy_baseline']
    if yb['dual_yoy']:
        print(f'[同比基准·双口径] 同比周={yb["week_aligned_dt"]}(星期对齐-364) ｜ '
              f'同比日={yb["date_aligned_dt"]}(去年同一日历日) → 两口径并列呈现')
    else:
        print(f'[同比基准] 去年同期={yb["aligned_dt"]} {yb["weekday_aligned"]}｜'
              f'对齐方式={yb["align_mode"]} → 同比 = 分析日 vs 该日')
    print('[对齐基准建议]')
    for b in ctx['baseline_suggestions']:
        mark = '✓可比' if b['comparable'] else '⚠不同质'
        print(f'   {b["baseline"]}={b["dt"]} {mark}: {"；".join(b["reasons"])}')
    if args.compare:
        cmp = ctx['comparison']
        mark = '✓ 同质可比' if cmp['comparable'] else '⚠ 不同质，环比慎读'
        print(f'[可比性] {args.dt} vs {args.compare} → {mark}')
        for r in cmp['reasons']:
            print(f'   - {r}')


if __name__ == '__main__':
    main()

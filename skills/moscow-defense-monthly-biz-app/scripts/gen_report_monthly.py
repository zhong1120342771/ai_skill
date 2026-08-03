#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
莫斯科保卫战月报 —— 月度面板计算 + XML 生成器

核心职责：
1. 从 01_panel.csv（月度全维度面板）计算 月环比(MoM) + 同比(YoY)
2. 生成 KPI 表（指标/月度目标/本月均值/月环比/月同比）、整体漏斗横表、4 维度 7 列表（单元格双拼环比｜同比）、维度构成表的 XML
3. 供 Step 4 洞察结论生成 agent 直接调用（import）或独立跑

约定：
- 面板每行 = (tag_01, wd, 月份) 的月均绝对值 + 各率字符串
- 环比/同比一律在 Python 端算，SQL 不含窗口
- 单元格默认展示「绝对值（月环比%）」；同比通过 build_kpi_table / build_funnel_table 的 yoy 参数体现
"""

import re
from datetime import date

# ====== 月份工具 ======

def prev_month(ym):
    """'2026-06' -> '2026-05'"""
    y, m = int(ym[:4]), int(ym[5:7])
    m -= 1
    if m == 0:
        y, m = y - 1, 12
    return f"{y:04d}-{m:02d}"


def yoy_month(ym):
    """'2026-06' -> '2025-06'"""
    return f"{int(ym[:4]) - 1:04d}-{ym[5:7]}"


def month_cn(ym):
    """'2026-06' -> '2026年6月'"""
    return f"{int(ym[:4])}年{int(ym[5:7])}月"


# ====== 数值解析 ======

def to_float(cell):
    """'1.129%' / '4500000' / '-' -> float 小数(率类除100) 或 None。率类返回小数，绝对值原样。"""
    s = str(cell).strip()
    if not s or s in ('-', 'nan', 'None') or 'null' in s.lower():
        return None
    is_pct = s.endswith('%')
    s2 = s.rstrip('%').replace(',', '')
    try:
        v = float(s2)
    except ValueError:
        return None
    return v / 100.0 if is_pct else v


def chg(cur, base):
    """变化率：(cur-base)/base，返回百分数值（如 +6.51 表示 +6.51%）；base 缺失返回 None"""
    if cur is None or base is None or base == 0:
        return None
    return (cur - base) / base * 100.0


def fmt_abs(abs_str):
    """绝对值字符串标准化：纯数字→整数千分位；率(带%)/'-'原样。"""
    if abs_str is None:
        return '-'
    a = str(abs_str).strip()
    if a in ('-', '', 'nan', 'None') or a.endswith('%'):
        return a if a not in ('', 'nan', 'None') else '-'
    try:
        v = float(a.replace(',', ''))
    except ValueError:
        return a
    return f'{int(round(v)):,}'


def fmt_cell(abs_str, chg_val):
    """'1.129%' + 6.51 -> '1.129%（+6.51%）'；chg 缺失 -> '绝对值'；绝对值缺失 -> '-'"""
    if abs_str is None or str(abs_str).strip() in ('-', '', 'nan', 'None'):
        return '-'
    a = fmt_abs(abs_str)
    if chg_val is None:
        return a
    sign = '+' if chg_val >= 0 else ''
    return f'{a}（{sign}{chg_val:.2f}%）'


def fmt_cell_dual(abs_str, mom, yoy):
    """双拼：'1.129%' + mom + yoy -> '1.129%（环+6.51%｜同+3.20%）'。
    缺失的对比用 - 占位；绝对值缺失整体返回 '-'。"""
    if abs_str is None or str(abs_str).strip() in ('-', '', 'nan', 'None'):
        return '-'
    a = fmt_abs(abs_str)
    def _p(v):
        return f'{v:+.2f}%' if v is not None else '-'
    return f'{a}（环{_p(mom)}｜同{_p(yoy)}）'


# ====== 面板索引 ======

# 面板列名（与 01_panel_monthly.sql 输出对齐）
ABS_COLS = ['dau_日均', '单量', '商详uv', '曝光uv', '下单uv', '曝光pv']
RATE_COLS = ['dau-净支付pv转化率', '商详转化率', '商详渗透率', '曝光渗透率',
             '商详到达率', '下单率', '支付率', '提袋率']


def index_panel(rows):
    """rows: list[dict]（csv.DictReader）。返回 {(tag_01, wd, 月份): row_dict}"""
    idx = {}
    for r in rows:
        key = (r['tag_01'].strip(), r['wd'].strip(), str(r['月份']).strip())
        idx[key] = r
    return idx


def metric_with_changes(idx, tag, wd, month, col, is_rate):
    """取某维度项某指标的 (本月绝对值str, 月环比, 同比)"""
    pm, ym = prev_month(month), yoy_month(month)
    cur_row = idx.get((tag, wd, month))
    pm_row = idx.get((tag, wd, pm))
    ym_row = idx.get((tag, wd, ym))
    if cur_row is None:
        return ('-', None, None)
    cur_abs = cur_row.get(col, '-')
    cur_v = to_float(cur_abs)
    pm_v = to_float(pm_row.get(col)) if pm_row else None
    ym_v = to_float(ym_row.get(col)) if ym_row else None
    return (cur_abs, chg(cur_v, pm_v), chg(cur_v, ym_v))


# ====== KPI 表（4 列：指标 / 本月均值 / 月环比 / 月同比） ======
# App 端不设 KPI 目标，只报实际月均值 + 月环比 + 月同比（与 app 周报口径一致，去掉「月度目标」列）

KPI_METRICS = {
    'dau-净支付pv转化率': ('净支付转化率', True),
    'dau_日均':          ('DAU（日均）', False),
    '单量':              ('净支付单量（月均）', False),
}


def build_kpi_table(idx, month):
    """KPI 表 XML（4 列：指标/本月均值/月环比/月同比）。数据源：整体行。App 端不设目标。"""
    header = ['指标', '本月均值', '月环比', '月同比']
    hcells = ''.join(f'<th background-color="light-gray"><p>{h}</p></th>' for h in header)
    rows_xml = []
    for col, (label, is_rate) in KPI_METRICS.items():
        cur_abs, mom, yoy = metric_with_changes(idx, '整体', '整体', month, col, is_rate)
        mom_str = f'{mom:+.2f}%' if mom is not None else '-'
        yoy_str = f'{yoy:+.2f}%' if yoy is not None else '-'
        cur_disp = cur_abs if is_rate else fmt_abs(cur_abs)
        cells = ''.join(f'<td><p>{c}</p></td>' for c in
                        [label, cur_disp, mom_str, yoy_str])
        rows_xml.append(f'<tr>{cells}</tr>')
    return f'<table><thead><tr>{hcells}</tr></thead><tbody>{"".join(rows_xml)}</tbody></table>'


# ====== 整体漏斗横表（12 环节，单元格「绝对值（月环比%）」） ======

FUNNEL_ORDER = [
    ('DAU', 'dau_日均', False),
    ('曝光UV', '曝光uv', False),
    ('曝光渗透率', '曝光渗透率', True),
    ('商详UV', '商详uv', False),
    ('商详到达率', '商详到达率', True),
    ('商详渗透率', '商详渗透率', True),
    ('下单UV', '下单uv', False),
    ('下单率', '下单率', True),
    ('净支付PV', '单量', False),
    ('支付率', '支付率', True),
    ('商详转化率', '商详转化率', True),
    ('净支付转化率', 'dau-净支付pv转化率', True),
]


def build_funnel_table(idx, month):
    header = ''.join(f'<th background-color="light-gray"><p>{lab}</p></th>' for lab, _, _ in FUNNEL_ORDER)
    cells = []
    for _, col, is_rate in FUNNEL_ORDER:
        cur_abs, mom, _ = metric_with_changes(idx, '整体', '整体', month, col, is_rate)
        cells.append(f'<td><p>{fmt_cell(cur_abs, mom)}</p></td>')
    return f'<table><thead><tr>{header}</tr></thead><tbody><tr>{"".join(cells)}</tr></tbody></table>'


# ====== 4 维度 7 列表 ======

# 维度 -> tag_01。App 端专属表无「端」维度，四维拆解：品类/场景/用户来源/用户分层
DIM_TAG = {
    '品类': '拆分品类',
    '场景': '拆分场景',
    '用户来源': '拆分用户来源',
    '用户分层': '拆分用户资产分层',
}

DIM_TABLE_COLS = [
    ('净支付转化率', 'dau-净支付pv转化率', True),
    ('商详渗透率', '商详渗透率', True),
    ('商详转化率', '商详转化率', True),
    ('曝光渗透率', '曝光渗透率', True),
    ('商详到达率', '商详到达率', True),
    ('下单率', '下单率', True),
    ('支付率', '支付率', True),
]


def _z_rank(wd):
    """从 wd 里抽 Z 后面的数字用于排序，如 'Z3-高价值' -> 3；无 Z 序号返回大数排后面"""
    m = re.search(r'[Zz]\s*(\d+)', wd)
    return int(m.group(1)) if m else 999


def _cat_rank(wd):
    """品类项按 wd 前缀数字排序：'1-手机'->1 / '2_5类目'->2 / '3-N聚合'->3 ...
    固定顺序：1-手机/2_5类目/3-N聚合/4-平板/5-笔记本/6-摄影摄像矩阵/7-电脑办公。
    无前缀数字返回大数排后面。"""
    m = re.match(r'\s*(\d+)', wd)
    return int(m.group(1)) if m else 999


# 各维度永久排除的 wd（不在报告任何表/图中出现）
DIM_EXCLUDE = {
    '拆分场景': {'找靓机-不区分场景'},
}


def _dim_items(idx, tag, month):
    """返回该维度本月出现的所有 wd。用户资产分层按 Z0-Z5 排序，品类按 wd 前缀数字排序
    （1-手机/2_5类目/3-N聚合/4-平板/5-笔记本/6-摄影摄像矩阵/7-电脑办公），其余按面板出现顺序。
    DIM_EXCLUDE 里列出的 wd 永久过滤（如场景的「找靓机-不区分场景」）。"""
    excl = DIM_EXCLUDE.get(tag, set())
    seen = []
    for (t, wd, m) in idx:
        if t == tag and m == month and wd not in seen and wd != '整体' and wd not in excl:
            seen.append(wd)
    if tag == '拆分用户资产分层':
        seen.sort(key=lambda wd: (_z_rank(wd), wd))
    elif tag == '拆分品类':
        seen.sort(key=lambda wd: (_cat_rank(wd), wd))
    return seen


def build_dim_table(idx, dim_name, month):
    tag = DIM_TAG[dim_name]
    header = ['维度项'] + [lab for lab, _, _ in DIM_TABLE_COLS]
    hcells = ''.join(f'<th background-color="light-gray"><p>{h}</p></th>' for h in header)
    rows_xml = []
    for wd in _dim_items(idx, tag, month):
        cells = f'<td><p>{wd}</p></td>'
        for _, col, is_rate in DIM_TABLE_COLS:
            cur_abs, mom, yoy = metric_with_changes(idx, tag, wd, month, col, is_rate)
            cells += f'<td><p>{fmt_cell_dual(cur_abs, mom, yoy)}</p></td>'
        rows_xml.append(f'<tr>{cells}</tr>')
    return f'<table><thead><tr>{hcells}</tr></thead><tbody>{"".join(rows_xml)}</tbody></table>'


# ====== 维度构成表（6 列：占比 + 月环比） ======

def build_struct_table(idx, dim_name, month, use_exposure=False):
    """
    端/用户来源：DAU 月均/占比/月环比 + 单量 月均/占比/月环比
    场景(use_exposure=True)：曝光UV 月均/渗透率/月环比 + 单量 月均/占比/月环比
    """
    tag = DIM_TAG[dim_name]
    pm = prev_month(month)
    items = _dim_items(idx, tag, month)
    # 整体分母
    o = idx.get(('整体', '整体', month), {})
    o_dau = to_float(o.get('dau_日均'))
    o_pay = to_float(o.get('单量'))

    flow_label = '曝光UV' if use_exposure else 'DAU'
    ratio_label = '曝光UV渗透率' if use_exposure else 'DAU占比'
    header = [dim_name, f'{flow_label}（月均）', ratio_label, f'{flow_label}月环比',
              '单量（月均）', '单量占比', '单量月环比']
    hcells = ''.join(f'<th background-color="light-gray"><p>{h}</p></th>' for h in header)
    rows_xml = []
    for wd in items:
        cur = idx.get((tag, wd, month), {})
        prev = idx.get((tag, wd, pm), {})
        flow_col = '曝光uv' if use_exposure else 'dau_日均'
        flow_v = to_float(cur.get(flow_col))
        flow_prev = to_float(prev.get(flow_col))
        pay_v = to_float(cur.get('单量'))
        pay_prev = to_float(prev.get('单量'))
        # 占比 / 渗透率：场景用「曝光UV/整体DAU」（渗透率口径，可>100%）；端/来源用「DAU/整体DAU」
        ratio = (flow_v / o_dau * 100) if (flow_v and o_dau) else None
        pay_ratio = (pay_v / o_pay * 100) if (pay_v and o_pay) else None
        flow_mom = chg(flow_v, flow_prev)
        pay_mom = chg(pay_v, pay_prev)
        cells = ''.join(f'<td><p>{c}</p></td>' for c in [
            wd,
            f'{int(round(flow_v)):,}' if flow_v is not None else '-',
            f'{ratio:.2f}%' if ratio is not None else '-',
            f'{flow_mom:+.2f}%' if flow_mom is not None else '-',
            f'{int(round(pay_v)):,}' if pay_v is not None else '-',
            f'{pay_ratio:.2f}%' if pay_ratio is not None else '-',
            f'{pay_mom:+.2f}%' if pay_mom is not None else '-',
        ])
        rows_xml.append(f'<tr>{cells}</tr>')
    return f'<table><thead><tr>{hcells}</tr></thead><tbody>{"".join(rows_xml)}</tbody></table>'


if __name__ == '__main__':
    import sys, csv
    if len(sys.argv) < 3:
        print('usage: gen_report_monthly.py <panel_csv> <month YYYY-MM>')
        sys.exit(1)
    panel_csv, month = sys.argv[1], sys.argv[2]
    with open(panel_csv, encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    idx = index_panel(rows)
    print('=== KPI ==='); print(build_kpi_table(idx, month)[:400])
    print('=== FUNNEL ==='); print(build_funnel_table(idx, month)[:400])
    for d in DIM_TAG:
        print(f'=== DIM {d} 项数:', len(_dim_items(idx, DIM_TAG[d], month)))

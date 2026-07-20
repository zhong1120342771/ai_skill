#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
莫斯科保卫战周报 XML 生成器

输入：整体漏斗数据 + 维度拆解数据
输出：符合规范的飞书文档 XML
"""

import re

# ====== 数据解析 ======

def parse_val(raw):
    """从 "0.903% (环比：-6.07%)" 提取 (绝对值, 环比变化量)"""
    raw = str(raw).strip()
    if not raw or raw == '-' or 'null' in raw.lower():
        return ('-', 0)
    m = re.match(r'^([\d.]+%?)\s*\(\s*环比\s*[:：]\s*([+\-]?[\d.]+)%?\s*\)', raw)
    if m:
        return (m.group(1), float(m.group(2)))
    m2 = re.match(r'^([\d.]+%?)', raw)
    if m2:
        return (m2.group(1), 0)
    return (raw, 0)


def fmt_cell(abs_val, chg):
    """格式化单元格：绝对值（+X%）"""
    if abs_val == '-' or abs_val == '':
        return '-'
    sign = '+' if chg >= 0 else ''
    return f'{abs_val}（{sign}{chg:.2f}%）'


# ====== 指标定义 ======

# 原始数据列顺序（与 Excel 维度拆解 sheet 对齐）
METRIC_KEYS = [
    "净支付转化率", "dau", "曝光uv", "商详uv", "净支付pv",
    "商详渗透率", "商详转化率", "提袋率",
    "曝光渗透率", "商详到达率", "下单率", "支付率",
]

# 维度表展示指标及对应索引
TABLE_METRIC_INDICES = [0, 5, 6, 8, 9, 10, 11]
TABLE_HEADER = ['维度项', '净支付转化率', '商详渗透率', '商详转化率', '曝光渗透率', '商详到达率', '下单率', '支付率']

# 章节顺序（仅 App 端：无「端」维度，用四维替代）
SECTION_ORDER = ["品类", "场景", "用户来源", "用户资产分层"]

# 漏斗横向表环节顺序
FUNNEL_ORDER = [
    ("DAU", "dau"),
    ("曝光UV", "曝光uv"),
    ("曝光渗透率", "曝光渗透率"),
    ("商详UV", "商详uv"),
    ("商详到达率", "商详到达率"),
    ("商详渗透率", "商详渗透率"),
    ("下单UV", "下单uv"),
    ("下单率", "下单率"),
    ("净支付PV", "净支付pv"),
    ("支付率", "支付率"),
    ("商详转化率", "商详转化率"),
    ("净支付转化率", "净支付转化率"),
]


# ====== 行解析 ======

def parse_row(row):
    """将原始行数据解析为 {name, 指标_abs, 指标_chg} 字典"""
    item = {"name": row[0]}
    for i, key in enumerate(METRIC_KEYS):
        abs_val, chg = parse_val(row[i + 1])
        item[f"{key}_abs"] = abs_val
        item[f"{key}_chg"] = chg
    return item


# ====== XML 生成 ======

def build_funnel_table(overall):
    """生成横向漏斗总览表"""
    header_cells = ''.join(
        f'<th vertical-align="top"><p>{label}</p></th>'
        for label, _ in FUNNEL_ORDER
    )
    data_cells = ''.join(
        f'<td vertical-align="top"><p>{fmt_cell(overall[key][0], overall[key][1])}</p></td>'
        for _, key in FUNNEL_ORDER
    )
    return f'<table><thead><tr>{header_cells}</tr></thead><tbody><tr>{data_cells}</tr></tbody></table>'


def build_dim_table(items):
    """生成维度拆解数据表"""
    hcells = ''.join(f'<th vertical-align="top"><p>{h}</p></th>' for h in TABLE_HEADER)
    rows = []
    for item in items:
        cells = f'<td vertical-align="top"><p>{item["name"]}</p></td>'
        for idx in TABLE_METRIC_INDICES:
            key = METRIC_KEYS[idx]
            cells += f'<td vertical-align="top"><p>{fmt_cell(item[f"{key}_abs"], item[f"{key}_chg"])}</p></td>'
        rows.append(f'<tr>{cells}</tr>')
    return f'<table><thead><tr>{hcells}</tr></thead><tbody>{"".join(rows)}</tbody></table>'


def generate_xml(overall, raw_rows, analyses):
    """
    生成完整周报 XML。

    overall: dict[str, (abs_val, chg)] — 整体漏斗数据
    raw_rows: dict[str, list[list[str]]] — 维度拆解原始行
    analyses: dict[str, str] — 各维度分析话术
    """
    all_dims = {name: [parse_row(r) for r in rows] for name, rows in raw_rows.items()}

    parts = []

    # 漏斗口径
    nzh_abs, nzh_chg = overall["净支付转化率"]
    sxl_abs, sxl_chg = overall["商详转化率"]
    xdl_abs, xdl_chg = overall["下单率"]
    parts.append('<p><b>漏斗口径</b></p>')
    parts.append(
        f'<p>本周净支付转化率环比 {nzh_chg:+.2f}%（绝对值 {nzh_abs}），'
        f'主要下降环节为「商详转化」环节（环比 {sxl_chg:+.2f}%），'
        f'「下单」子环节的下降较为明显（{xdl_chg:+.2f}%）。</p>'
    )

    # 漏斗总览表
    parts.append('<p><b>整体漏斗各环节数据</b></p>')
    parts.append(build_funnel_table(overall))

    # 维度章节（仅 App 端顺序：品类、场景、用户来源、用户资产分层）
    for i, dim_name in enumerate(SECTION_ORDER):
        if dim_name not in all_dims:
            continue
        label = f'{i + 1}、{dim_name}'
        parts.append(f'<h5>{label}</h5>')
        parts.append(f'<p>{analyses[dim_name]}</p>')
        parts.append(build_dim_table(all_dims[dim_name]))

    return '\n'.join(parts)


# ====== 使用示例 ======

if __name__ == '__main__':
    # 示例数据（实际使用时从 Excel 读取替换）
    overall = {}
    raw_rows = {}
    analyses = {}

    xml = generate_xml(overall, raw_rows, analyses)
    with open('fishu_report.xml', 'w') as f:
        f.write(xml)
    print(f'Generated {len(xml)} chars')

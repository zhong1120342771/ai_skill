#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_anomaly_table.py — 把报告 §三「异常判定总表」渲染成彩色表图(v5-0711)

从 final_report/核心指标异动_${dt}.md 里解析 §三 的**两张** markdown 表：
  表1 · 转化效率（大盘/分用户来源=净支付pv转化率；业务/场景=提袋率；带单量）
  表2 · 流量（大盘/分用户来源=活跃DAU；业务/场景=曝光UV）
各渲染成一张彩色表图，用于飞书文档 §三 内嵌 + P2P 推送直接呈现。

规则（v5-0711）：
- 任一表头含「当日/周环比」的列，自动拆成「当日」「周环比」两列，周环比按符号上色。
- 周环比为负标绿、为正标红（红涨绿跌，用户指定口径）。
- 指标名写进单元格（如「dau-净支付pv转化率 1.31%」），表头不再单列北极星注解（v5 改点2.1）。
- 比率必带绝对量（沿用报告表内容，不改数字）。
中文字体必须显式设置，否则方块乱码。

用法：
  python render_anomaly_table.py --md final_report/核心指标异动_2026-07-09.md \
      --dt 2026-07-09 --outdir visualizations/2026-07-09
  → 产出 anomaly_table_eff.png（转化效率）+ anomaly_table_flow.png（流量）
"""
import argparse, os, re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

GREEN = '#1a9850'   # 周环比为负
RED = '#d6604d'     # 周环比为正
INK = '#222222'
HEADER_BG = '#3b4a5a'
HEADER_FG = '#ffffff'
ZEBRA = '#f2f5f8'
GRID = '#d9dee4'

PCT_RE = re.compile(r'([+-]?\d+(?:\.\d+)?)\s*(?:%|pp)')
# 当日/周环比 | 当日/周环比/同比 | 当日/周环比/同比周/同比日（v9 双口径同比）
MOM_COL_RE = re.compile(r'当日\s*/\s*周环比')
YOY_COL_RE = re.compile(r'当日\s*/\s*周环比\s*/\s*同比')
YOY2_COL_RE = re.compile(r'当日\s*/\s*周环比\s*/\s*同比周\s*/\s*同比日')

# 各列角色 → (相对宽度, 折行显示宽度或None)
WIDE_COLS = {'细拆/根因', '细拆/特征', '细拆', '细拆特征'}
MID_WIDE_COLS = {'拖累环节', '拖累/走弱点', '走弱点', '拖累/走弱', '拖累'}


def _wlen(s):
    """按显示宽度算长度：中文/全角算2，其余算1。"""
    return sum(2 if ord(c) > 0x2E7F else 1 for c in str(s))


def wrap_cell(text, max_w):
    """把长单元格文本按显示宽度折行；优先在 ｜/、/空格 处断，再按宽度硬折。"""
    text = str(text)
    if not text or _wlen(text) <= max_w:
        return text
    segs = re.split(r'(?<=[｜、\s])', text)  # 保留分隔符在行尾
    lines, cur = [], ''
    for seg in segs:
        if _wlen(cur) + _wlen(seg) <= max_w or not cur:
            cur += seg
        else:
            lines.append(cur); cur = seg
        while _wlen(cur) > max_w:  # 单段仍超宽再硬折
            cut, acc = 0, 0
            for ch in cur:
                acc += 2 if ord(ch) > 0x2E7F else 1
                cut += 1
                if acc >= max_w:
                    break
            lines.append(cur[:cut]); cur = cur[cut:]
    if cur:
        lines.append(cur)
    return '\n'.join(lines)


def find_tables(md_text):
    """定位 §三 章节后的所有 pipe 表，返回 [(caption, header, body), ...]。
    caption 取每张表前最近的一行非空文字（若是 **表1 …** 之类的小标题）。"""
    lines = md_text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if '异常判定总表' in ln and ln.lstrip().startswith('#'):
            start = i
            break
    if start is None:
        raise RuntimeError('未找到「异常判定总表」章节')
    # 收集本章节（到下一个 ## 标题为止）内的所有表
    seg = []
    for ln in lines[start + 1:]:
        if ln.lstrip().startswith('## '):
            break
        seg.append(ln)
    tables, cur_rows, caption, last_text = [], [], None, None
    for ln in seg:
        s = ln.strip()
        if s.startswith('|'):
            cells = [c.strip() for c in s.strip('|').split('|')]
            if not cur_rows:
                caption = last_text  # 表前最近的一行文字作小标题
            cur_rows.append(cells)
        else:
            if cur_rows:
                tables.append((caption, cur_rows)); cur_rows = []
            if s and not s.startswith('>') and not s.startswith('<!--'):
                last_text = s
    if cur_rows:
        tables.append((caption, cur_rows))
    out = []
    for cap, rows in tables:
        body = [r for r in rows[1:] if not set(''.join(r)) <= set('-: ')]
        if body:
            out.append((cap, rows[0], body))
    if not out:
        raise RuntimeError('§三 未解析到任何表')
    return out


def split_val_segs(cell, n):
    """把 '指标名 1.316% / -5.58% / +2.1%' 按 '/' 拆成 n 段，不足补 None。
    n=2 → (当日, 周环比)；n=3 → (当日, 周环比, 同比)。"""
    cell = str(cell)
    parts = [p.strip() for p in cell.split('/')]
    parts += [None] * (n - len(parts))
    return tuple(parts[:n])


def mom_color(mom_text):
    """按周环比符号取色：负→绿，正→红，取不到符号→墨色。"""
    if not mom_text:
        return INK
    m = PCT_RE.search(str(mom_text))
    if not m:
        return INK
    v = float(m.group(1))
    if v < 0:
        return GREEN
    if v > 0:
        return RED
    return INK


def build_columns(header, body):
    """通用重排：表头含「当日/周环比/同比」的列拆成 当日+周环比+同比 三列；
    含「当日/周环比」拆成 当日+周环比 两列。周环比/同比列按符号上色。其余列原样。
    返回 (new_header, new_rows, colors)。"""
    # 记录每列拆几段：4=当日/周环比/同比周/同比日, 3=当日/周环比/同比, 2=当日/周环比, 0=不拆
    nseg = {}
    for i, h in enumerate(header):
        if YOY2_COL_RE.search(h):
            nseg[i] = 4
        elif YOY_COL_RE.search(h):
            nseg[i] = 3
        elif MOM_COL_RE.search(h):
            nseg[i] = 2
    new_header = []
    for i, h in enumerate(header):
        if nseg.get(i):
            if nseg[i] == 4:
                base = YOY2_COL_RE.sub('', h)
            elif nseg[i] == 3:
                base = YOY_COL_RE.sub('', h)
            else:
                base = MOM_COL_RE.sub('', h)
            base = re.sub(r'[（(][）)]?$', '', base.strip()).strip()  # 去掉尾部空括号
            new_header.append((base + ' 当日').strip())
            new_header.append('周环比')
            if nseg[i] >= 3:
                new_header.append('同比周')
            if nseg[i] == 4:
                new_header.append('同比日')
        else:
            new_header.append(h)

    def col(r, i):
        return r[i] if i < len(r) else ''

    new_rows, colors = [], []
    for r in body:
        row, rowcolor = [], []
        for i, h in enumerate(header):
            raw = col(r, i)
            if nseg.get(i):
                segs = split_val_segs(raw, nseg[i])
                row.append(segs[0]); rowcolor.append(INK)                 # 当日
                row.append(segs[1] or '—'); rowcolor.append(mom_color(segs[1]))  # 周环比
                if nseg[i] >= 3:
                    row.append(segs[2] or '—'); rowcolor.append(mom_color(segs[2]))  # 同比周
                if nseg[i] == 4:
                    row.append(segs[3] or '—'); rowcolor.append(mom_color(segs[3]))  # 同比日
            else:
                # 细拆/拖累类列折行
                if h in WIDE_COLS:
                    row.append(wrap_cell(raw, 24))
                elif h in MID_WIDE_COLS:
                    row.append(wrap_cell(raw, 12))
                else:
                    row.append(wrap_cell(raw, 16) if _wlen(raw) > 16 else raw)
                rowcolor.append(INK)
        new_rows.append(row); colors.append(rowcolor)
    return new_header, new_rows, colors


def _col_width(name):
    """按列名给相对宽度权重。"""
    n = name.replace(' 当日', '').strip()
    if n in WIDE_COLS:
        return 0.24
    if n in MID_WIDE_COLS:
        return 0.13
    if n in ('周环比', '同比', '同比周', '同比日'):
        return 0.07
    if n == '层级':
        return 0.05
    if n == '对象':
        return 0.10
    if n == '今日判定':
        return 0.10
    return 0.14  # 指标当日列（含指标名+值）


def render(caption, header, rows, colors, dt, out):
    line_counts = [max(1, max(str(c).count('\n') + 1 for c in row)) for row in rows]
    widths = [_col_width(h) for h in header]
    widths = [w / sum(widths) for w in widths]
    fig_w = max(13.0, 1.05 * sum(_col_width(h) for h in header) * 13)
    fig_w = min(fig_w, 16.5)
    fig_h = 1.5 + 0.42 * sum(line_counts)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis('off')
    cap = re.sub(r'\*+', '', caption or '').strip('# ').strip()
    title = f'{dt} · {cap}' if cap else f'{dt} · 核心指标异常判定总表'
    ax.set_title(title, fontsize=15, fontweight='bold', color=INK, pad=16)

    tbl = ax.table(cellText=rows, colLabels=header, cellLoc='left',
                   colWidths=widths, loc='center')
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10.5)
    tbl.scale(1, 1.9)

    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor(GRID)
        cell.set_linewidth(0.6)
        if r == 0:
            cell.set_facecolor(HEADER_BG)
            cell.set_text_props(color=HEADER_FG, fontweight='bold', fontsize=10)
            cell.set_height(cell.get_height() * 1.5)
        else:
            cell.set_facecolor(ZEBRA if r % 2 == 0 else '#ffffff')
            txtcolor = colors[r - 1][c] if c < len(colors[r - 1]) else INK
            weight = 'bold' if txtcolor in (GREEN, RED) else 'normal'
            cell.set_text_props(color=txtcolor, fontweight=weight,
                                verticalalignment='center')
            cell.set_height(cell.get_height() * line_counts[r - 1])
            cell.PAD = 0.03
    fig.text(0.012, 0.02,
             '周环比/同比上色：为负标绿（回落）、为正标红（上涨）。比率均附绝对量。'
             '同比对齐：大促峰值日=去年同一日历日，其余=去年星期对齐日。',
             fontsize=9, color='#666666', ha='left')
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(out, dpi=150, bbox_inches='tight'); plt.close(fig)
    return out


def _slug(caption, idx):
    """按小标题决定输出文件后缀：转化效率→eff，流量→flow，否则序号。"""
    cap = caption or ''
    if '效率' in cap or '转化' in cap:
        return 'eff'
    if '流量' in cap:
        return 'flow'
    return f't{idx + 1}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--md', required=True)
    ap.add_argument('--dt', required=True)
    ap.add_argument('--outdir', default=None, help='输出目录，产出 anomaly_table_<eff|flow>.png')
    ap.add_argument('--out', default=None, help='(兼容旧调用)只出第一张表到该路径')
    args = ap.parse_args()

    md = open(args.md, encoding='utf-8').read()
    tables = find_tables(md)
    outs = []
    if args.out and not args.outdir:  # 旧式单图调用：只渲第一张
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        cap, header, body = tables[0]
        nh, nr, colors = build_columns(header, body)
        render(cap, nh, nr, colors, args.dt, args.out)
        outs.append(args.out)
    else:
        outdir = args.outdir or 'visualizations'
        os.makedirs(outdir, exist_ok=True)
        for idx, (cap, header, body) in enumerate(tables):
            nh, nr, colors = build_columns(header, body)
            out = os.path.join(outdir, f'anomaly_table_{_slug(cap, idx)}.png')
            render(cap, nh, nr, colors, args.dt, out)
            outs.append(out)
    for p in outs:
        print(f'[OK] 判定总表图 → {p}')


if __name__ == '__main__':
    main()


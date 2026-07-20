#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_category_exposure_doc.py — 每日「分品类曝光明细」飞书文档一键生成

随核心指标异动日报每天新建一份当天文档，产出：
  1) 取数：APP端整体基准(单维度-拆分端/转转APP) + 各业务品类(2维度交叉-端_业务/品类,转转APP_品类%)
     近 ~18 个月曝光序列(dt/wd/exp_uv/matched_dau_uv)，含乐器/台球杆(2026-07-15 拆分)。
  2) 汇总表：曝光UV + 曝光渗透率(=品类曝光UV/APP端活跃DAU) 各配 日环比/周环比/同比周/同比日。
  3) 趋势图：复用 render_category_exposure_charts.py，每品类一张 2x2 四宫格。
  4) 建飞书 docx(标题【${dt}】分品类曝光明细) + 按品类插图，返回 doc_url。

口径与全局规则：
  - 曝光渗透率＝品类曝光UV÷当日APP端活跃DAU(matched_dau_uv of 转转APP)。
  - 同比周＝去年星期对齐日(-364天)；同比日＝去年同一日历日(-1年同月同日)。
  - 兴趣业务只出 乐器/台球杆/骑行/潮玩/球拍 五品类(INTEREST_KEEP，与 render 脚本同源)，
    其余兴趣品类(错挂的包袋/腕表/鞋服/饰品/兴趣N-其他)剔除。
  - 名称含「其他」的品类剔除。
  - 凭证只走环境变量(XINGHE_*)，不硬编码不打印。

用法：
  python3 build_category_exposure_doc.py --dt 2026-07-14
      [--src <已有曝光序列csv>]     # 缺省则实时取数落 data_storage/
      [--outdir <图目录>]           # 缺省 visualizations/${dt}/cat_exposure
      [--url-out <把doc_url写到该文件>]  # 供流水线拿 url 喂 feishu_publish --extra-link
      [--no-doc]                    # 只取数+出图+算表，不建飞书文档(调试)
退出码：0 成功(doc_url 已产出) / 2 建文档失败 / 3 取数失败
"""
import argparse, os, sys, json, subprocess, re, time, urllib.request
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path.home() / '.claude'
SKILL = BASE / 'skills' / '转转核心指标异动监控bot'
XINGHE = BASE / 'skills' / 'xinghe-data' / 'scripts'
TABLE = 'hdp_zhuanzhuan_tmp_global.tmp_dws_zz_core_dataagent_zmt_v2_di'
LARK = 'lark-cli'

BIZ_ORDER = ['消费电子', '二奢', '兴趣']
PREFIX = '转转APP_品类'
INTEREST_KEEP = {'乐器', '台球杆', '骑行', '潮玩', '球拍'}  # 与 render_category_exposure_charts.py 同源
PLACEHOLDER = '__CAT_EXPOSURE_BODY__'


def fetch_series(dt, out_csv):
    """实时取近 ~18 个月(去年同期起)曝光序列：APP端整体基准 + 各品类。落 out_csv。"""
    sys.path.insert(0, str(XINGHE))
    from xinghe_client import XingheExplorer
    start = (datetime.strptime(dt, '%Y-%m-%d') - timedelta(days=560)).strftime('%Y-%m-%d')
    sql = f"""
select dt, wd, exp_uv, matched_dau_uv
from {TABLE}
where dt between '{start}' and '{dt}'
  and (
    (tag_01='单维度-拆分端' and wd='转转APP')
    or (tag_01='2维度交叉-端_业务/品类' and wd like '转转APP_品类%')
  )
"""
    c = XingheExplorer()
    eid = c.run_sql(sql, sql_engine=5)
    r = c.wait_and_get_result(eid, max_wait=1800)
    urllib.request.urlretrieve(r['filename_csv'], out_csv)
    return out_csv


def parse_biz_cat(wd):
    """转转APP_品类<业务><品类> -> (业务, 品类)；基准 wd=转转APP 单独处理，不进这里。"""
    rest = wd[len(PREFIX):] if wd.startswith(PREFIX) else wd
    for b in BIZ_ORDER + ['其他']:
        if rest.startswith(b):
            return b, rest[len(b):]
    return '其他', rest


def pct(cur, base):
    """涨跌幅字符串，正标红负标绿由文档渲染负责，这里只出 ±X.XX%。base 缺失/0 → —。"""
    if cur is None or base in (None, 0) or (isinstance(base, float) and base != base):
        return '—'
    return '%+.2f%%' % ((cur / base - 1) * 100)


def build_rows(df, dt):
    """返回 (rows, base_dau, dates)。rows = [(业务, 品类, 曝光UV, uv日环比, uv周环比, uv同比周, uv同比日,
    渗透率, 渗率日环比, 渗率周环比, 渗率同比周, 渗率同比日), ...]，第一行是 APP端整体(基准)，业务=None。"""
    import pandas as pd
    df = df.copy()
    df['dt'] = pd.to_datetime(df['dt'])
    d0 = pd.Timestamp(dt)
    d_day = d0 - timedelta(days=1)      # 日环比基准 t-1
    d_wk = d0 - timedelta(days=7)       # 周环比基准 上周同日
    d_yw = d0 - timedelta(days=364)     # 同比周 去年星期对齐
    d_yd = d0.replace(year=d0.year - 1)  # 同比日 去年同一日历日
    dates = dict(dt=d0, day=d_day, wk=d_wk, yw=d_yw, yd=d_yd)

    def val(wd, day):
        s = df[(df.wd == wd) & (df.dt == day)]['exp_uv']
        return float(s.iloc[0]) if len(s) else None

    # APP端活跃DAU(分母)取当日基准行 matched_dau_uv
    bser = df[(df.wd == '转转APP') & (df.dt == d0)]['matched_dau_uv']
    base_dau = float(bser.iloc[0]) if len(bser) else None

    def pen(uv):  # 曝光渗透率
        return (uv / base_dau * 100) if (uv is not None and base_dau) else None

    def row_for(wd):
        uv = {k: val(wd, v) for k, v in dates.items()}
        p = {k: pen(uv[k]) for k in uv}  # 注意渗透率分母应各自当日DAU；见下修正
        return uv, p

    # 渗透率分母须用各基准日自己的APP活跃DAU，重取
    def base_dau_at(day):
        s = df[(df.wd == '转转APP') & (df.dt == day)]['matched_dau_uv']
        return float(s.iloc[0]) if len(s) else None
    dau_by = {k: base_dau_at(v) for k, v in dates.items()}

    def make(wd):
        uv = {k: val(wd, v) for k, v in dates.items()}
        p = {k: (uv[k] / dau_by[k] * 100 if (uv[k] is not None and dau_by[k]) else None)
             for k in uv}
        return uv, p

    rows = []
    # 基准行
    uv, p = make('转转APP')
    rows.append((None, 'APP端整体（基准）', uv, p))
    # 品类行：按业务序 → 品类名，剔除"其他"和兴趣非白名单
    cats = []
    for wd in df['wd'].unique():
        if wd == '转转APP' or not wd.startswith(PREFIX):
            continue
        b, cat = parse_biz_cat(wd)
        if '其他' in cat or b == '其他':
            continue
        if b == '兴趣' and cat not in INTEREST_KEEP:
            continue
        if b not in BIZ_ORDER:
            continue
        cats.append((BIZ_ORDER.index(b), b, cat, wd))
    cats.sort()
    for _, b, cat, wd in cats:
        uv, p = make(wd)
        rows.append((b, cat, uv, p))
    return rows, dates


def color_pct(cur, base):
    """涨跌幅 XML span：正值标红、负值标绿(用户 2026-07-15 定)。缺失 → —。"""
    if cur is None or base in (None, 0) or (isinstance(base, float) and base != base):
        return '—'
    v = (cur / base - 1) * 100
    col = 'red' if v > 0 else ('green' if v < 0 else 'gray')
    return '<span text-color="%s">%+.2f%%</span>' % (col, v)


def fmt_uv(v):
    return format(int(round(v)), ',d') if v is not None else '—'


def fmt_pen(v):
    return '%.2f%%' % v if v is not None else '—'


def build_table_xml(rows, dates):
    """12 列汇总表：业务线|品类|曝光UV|UV日环比|UV周环比|UV同比周|UV同比日|曝光渗透率|渗率日环比|渗率周环比|渗率同比周|渗率同比日。
    第一行 APP端整体(基准,业务线+品类合并两列)。品类按业务 rowspan 合并业务线列。"""
    heads = ['业务线', '品类', '曝光UV', '曝光UV日环比', '曝光UV周环比', '曝光UV同比周', '曝光UV同比日',
             '曝光渗透率', '渗透率日环比', '渗透率周环比', '渗透率同比周', '渗透率同比日']
    xml = ['<table>', '<colgroup>' + '<col/>' * 12 + '</colgroup>', '<thead><tr>']
    for h in heads:
        xml.append('<th vertical-align="top"><p>%s</p></th>' % h)
    xml.append('</tr></thead><tbody>')

    def cells(uv, p):
        return (
            '<td vertical-align="top"><p>%s</p></td>' % fmt_uv(uv['dt']) +
            '<td vertical-align="top"><p>%s</p></td>' % color_pct(uv['dt'], uv['day']) +
            '<td vertical-align="top"><p>%s</p></td>' % color_pct(uv['dt'], uv['wk']) +
            '<td vertical-align="top"><p>%s</p></td>' % color_pct(uv['dt'], uv['yw']) +
            '<td vertical-align="top"><p>%s</p></td>' % color_pct(uv['dt'], uv['yd']) +
            '<td vertical-align="top"><p>%s</p></td>' % fmt_pen(p['dt']) +
            '<td vertical-align="top"><p>%s</p></td>' % color_pct(p['dt'], p['day']) +
            '<td vertical-align="top"><p>%s</p></td>' % color_pct(p['dt'], p['wk']) +
            '<td vertical-align="top"><p>%s</p></td>' % color_pct(p['dt'], p['yw']) +
            '<td vertical-align="top"><p>%s</p></td>' % color_pct(p['dt'], p['yd'])
        )

    # 基准行：业务线+品类两列合并
    _, _, uv0, p0 = rows[0]
    xml.append('<tr><td colspan="2" vertical-align="top"><p><b>APP端整体（基准）</b></p></td>' + cells(uv0, p0) + '</tr>')
    # 品类行，按业务分组，业务列 rowspan
    body = rows[1:]
    from itertools import groupby
    for biz, grp in groupby(body, key=lambda r: r[0]):
        grp = list(grp)
        for i, (b, cat, uv, p) in enumerate(grp):
            cell = '<tr>'
            if i == 0:
                cell += '<td rowspan="%d" vertical-align="top"><p><b>%s</b></p></td>' % (len(grp), biz)
            cell += '<td vertical-align="top"><p>%s</p></td>' % cat + cells(uv, p) + '</tr>'
            xml.append(cell)
    xml.append('</tbody></table>')
    return ''.join(xml)


def biz_cat_seq(rows):
    """出图顺序 = 汇总表品类顺序(去基准)，返回 [(seq, 业务, 品类, h2标题), ...]，seq 与 render 脚本一致(1起)。
    h2标题形如「1.4 智能手表」，作插图锚点(比纯品类名更唯一，避免'智能手表'撞到表格文字)。"""
    biz_idx = {b: i for i, b in enumerate(['消费电子', '二奢', '兴趣'], 1)}
    out, per_biz = [], {}
    for i, (b, cat, _, _) in enumerate(rows[1:], 1):
        per_biz[b] = per_biz.get(b, 0) + 1
        h2 = '%d.%d %s' % (biz_idx.get(b, 9), per_biz[b], cat)
        out.append((i, b, cat, h2))
    return out


def build_doc_xml(dt, rows, dates):
    """整篇 docx XML：标题 + 口径 callout + 汇总表 + 业务线(h1)/品类(h2)目录。
    图片不在此插入(XML 无法内嵌本地图)，用 media-insert 按品类锚点句后插。这里为每品类留一个 h2 锚点。"""
    d0 = dates['dt']
    yw = dates['yw'].strftime('%Y-%m-%d'); yd = dates['yd'].strftime('%Y-%m-%d')
    day = dates['day'].strftime('%Y-%m-%d'); wk = dates['wk'].strftime('%Y-%m-%d')
    callout = (
        '<callout emoji="📌"><p>口径：仅统计转转APP端，曝光渗透率＝品类曝光UV÷当日APP端活跃DAU。'
        '环比含日环比（vs %s）与周环比（vs 上周同日 %s）；同比周＝去年星期对齐日 %s，'
        '同比日＝去年同一日历日 %s。环比/同比数值正值标红、负值标绿。</p></callout>'
        % (day, wk, yw, yd)
    )
    parts = ['<title>【%s】分品类曝光明细</title>' % dt, callout,
             '<h2>全品类曝光汇总</h2>', build_table_xml(rows, dates)]
    # 业务线目录(h1) + 品类子目录(h2)，h2 标题即插图锚点(见 biz_cat_seq)
    seq = biz_cat_seq(rows)
    from itertools import groupby
    biz_idx = {b: i for i, b in enumerate(['消费电子', '二奢', '兴趣'], 1)}
    cn = {1: '一', 2: '二', 3: '三'}
    for biz, grp in groupby(seq, key=lambda r: r[1]):
        parts.append('<h1>%s、%s</h1>' % (cn.get(biz_idx.get(biz, 9), str(biz_idx.get(biz, 9))), biz))
        for s, b, cat, h2 in grp:
            parts.append('<h2>%s</h2>' % h2)
    return ''.join(parts)


def render_charts(dt, src, outdir):
    """复用 render_category_exposure_charts.py 出每品类 2x2 图。返回 outdir。"""
    os.makedirs(outdir, exist_ok=True)
    cp = subprocess.run(
        [sys.executable, str(SKILL / 'scripts' / 'render_category_exposure_charts.py'),
         '--dt', dt, '--src', src, '--outdir', outdir],
        capture_output=True, text=True)
    print(cp.stdout.strip())
    if cp.returncode != 0:
        print('[warn] 出图失败:', cp.stderr[:400], file=sys.stderr)
    return outdir


def create_doc(xml, dt):
    """建 docx，返回 (doc_token, doc_url)。XML 走 --content @file(cwd相对)。"""
    tmp = BASE / ('_cat_exposure_%s.xml' % dt)
    tmp.write_text(xml, encoding='utf-8')
    try:
        cp = subprocess.run(
            [LARK, 'docs', '+create', '--doc-format', 'xml',
             '--title', '【%s】分品类曝光明细' % dt,
             '--content', '@%s' % tmp.name, '--as', 'user'],
            cwd=str(BASE), capture_output=True, text=True)
        m = re.search(r'\{.*\}', cp.stdout, re.DOTALL)
        js = json.loads(m.group(0)) if m else {}
        if not js.get('ok'):
            raise RuntimeError('docs +create 失败: %s' % (cp.stdout[:400] + cp.stderr[:200]))
        data = js.get('data', {}).get('document') or js.get('data', {})
        token = data.get('document_id') or data.get('doc_token') or data.get('token')
        url = data.get('url') or 'https://zhuanspirit.feishu.cn/docx/%s' % token
        return token, url
    finally:
        if tmp.exists():
            tmp.unlink()


def insert_charts(doc_token, rows, dt, chart_dir):
    """按品类把 cat_%02d_业务_品类.png 插到该品类 h2 标题句(锚点)之后。"""
    seq = biz_cat_seq(rows)
    for s, b, cat, h2 in seq:
        png = Path(chart_dir) / ('cat_%02d_%s_%s.png' % (s, b, cat))
        if not png.exists():
            print('[warn] 图缺失跳过:', png.name, file=sys.stderr); continue
        try:
            rel = png.resolve().relative_to(BASE.resolve()); file_arg, cwd = str(rel), str(BASE)
        except ValueError:
            file_arg, cwd = png.name, str(png.parent)
        anchor = h2  # h2 全标题(如「1.4 智能手表」)，正文唯一，比纯品类名更稳
        cp = subprocess.run(
            [LARK, 'docs', '+media-insert', '--doc', doc_token, '--file', file_arg,
             '--selection-with-ellipsis', anchor, '--as', 'user'],
            cwd=cwd, capture_output=True, text=True)
        ok = cp.returncode == 0 and '"type": "image"' in cp.stdout
        if not ok:  # 锚点没匹配，兜底追文末
            subprocess.run([LARK, 'docs', '+media-insert', '--doc', doc_token,
                            '--file', file_arg, '--as', 'user'], cwd=cwd,
                           capture_output=True, text=True)
        print('[img] %s @「%s」-> %s' % (png.name, anchor, 'ok' if ok else 'FAIL(退文末)'))
        time.sleep(0.4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dt', required=True, help='分析日 t-1，如 2026-07-15')
    ap.add_argument('--src', default=None, help='已有曝光序列csv(dt/wd/exp_uv/matched_dau_uv)；缺省实时取数')
    ap.add_argument('--outdir', default=None, help='趋势图目录；缺省 visualizations/${dt}/cat_exposure')
    ap.add_argument('--url-out', default=None, help='把 doc_url 写到该文件(供 feishu_publish --extra-link)')
    ap.add_argument('--no-doc', action='store_true', help='只取数+出图+算表，不建飞书文档')
    args = ap.parse_args()

    import pandas as pd
    dt = args.dt
    src = args.src or str(BASE / 'data_storage' / ('category_app_exposure_%s.csv' % dt))
    if not args.src or not os.path.exists(src):
        print('[fetch] 实时取曝光序列 →', src)
        try:
            fetch_series(dt, src)
        except Exception as e:
            print('[err] 取数失败:', e, file=sys.stderr); return 3
    df = pd.read_csv(src)
    if not (df['wd'] == '转转APP').any() or df[df.dt == dt].empty:
        print('[err] 源数据缺 %s 当日或基准行' % dt, file=sys.stderr); return 3

    rows, dates = build_rows(df, dt)
    outdir = args.outdir or str(BASE / 'visualizations' / dt / 'cat_exposure')
    render_charts(dt, src, outdir)

    if args.no_doc:
        print('[done] --no-doc：跳过建文档。汇总表行数 %d(含基准)' % len(rows))
        return 0

    xml = build_doc_xml(dt, rows, dates)
    try:
        token, url = create_doc(xml, dt)
    except RuntimeError as e:
        print('[err]', e, file=sys.stderr); return 2
    insert_charts(token, rows, dt, outdir)
    print('[done] 分品类曝光明细文档:', url)
    if args.url_out:
        Path(args.url_out).write_text(url, encoding='utf-8')
        print('[url-out]', args.url_out)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print('[build_category_exposure_doc] internal error:', e, file=sys.stderr); sys.exit(4)



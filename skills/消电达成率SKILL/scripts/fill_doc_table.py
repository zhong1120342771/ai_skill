# -*- coding: utf-8 -*-
"""
把 result.json + 趋势图写进飞书文档的达成率表格（整表重建，block_replace）。

飞书插图机制（本脚本已封装，勿手改顺序）：
  1) media-insert 把本地 png 传成临时块，拿 file_token / height
  2) 把 <img src="file_token"> 拼进目标单元格 XML
  3) block_replace 整张表 → 飞书把图 copy 成新 token 落到单元格
  4) block_delete 删掉步骤 1 的临时块（否则文末留一堆游离图）

用法：
  python fill_doc_table.py \
    --doc <doc_token> \
    --table-block <整张表的 block_id> \
    --result result.json \
    --charts-dir ./charts \
    [--chart-width 320]

前置：lark-cli 已登录（lark-cli auth status 有 open_id）。
表头顺序固定见 HEAD；前置业务列取自 result.json 每行的 lead 字典。
"""
import json, subprocess, argparse, os


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    return r.stdout + r.stderr


def parse_json(s):
    """从 media-insert 输出里抠出第一段平衡花括号 JSON。"""
    i = s.find('{')
    depth = 0
    end = i
    for k in range(i, len(s)):
        if s[k] == '{':
            depth += 1
        elif s[k] == '}':
            depth -= 1
            if depth == 0:
                end = k + 1
                break
    return json.loads(s[i:end])


def esc(t):
    return str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def fmt(v, isp):
    if v is None:
        return 'NA'
    return ('%.3f%%' % (v * 100)) if isp else ('%.2f' % v)


HEAD = ['方向', '负责人', '目标指标', '目标值提升', '当前值', '期望值',
        '末月实际值', '最高月值(月份)', '实际提升（首月-末月）', '各月指标变化趋势图', '达成情况']
COLW = [102, 125, 233, 118, 80, 80, 90, 100, 100, 100, 100]
# lead 字典键顺序，对应前 6 列
LEAD_KEYS = ['direction', 'owner', 'name', 'target_text', 'current', 'expected']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--doc', required=True)
    ap.add_argument('--table-block', required=True)
    ap.add_argument('--result', default='result.json')
    ap.add_argument('--charts-dir', default='.')
    ap.add_argument('--chart-width', type=int, default=320)
    args = ap.parse_args()

    data = json.load(open(args.result, encoding='utf-8'))
    rows = data['rows'] if isinstance(data, dict) else data
    months = data.get('months', list(range(1, 7))) if isinstance(data, dict) else list(range(1, 7))
    mlabels = ['%d月' % m for m in months]

    # 1. 上传所有图，拿 token
    imgs = []
    temps = []
    for i in range(len(rows)):
        fn = os.path.join(args.charts_dir, 'chart_%02d.png' % (i + 1))
        out = run(['lark-cli', 'docs', '+media-insert', '--doc', args.doc,
                   '--file', fn, '--width', str(args.chart_width)])
        m = parse_json(out)
        dd = m.get('data', m)
        imgs.append((dd['file_token'], dd['height']))
        temps.append(dd['block_id'])
        print('uploaded chart_%02d -> %s' % (i + 1, dd['file_token']))

    # 2. 拼表 XML
    colgroup = '<colgroup>' + ''.join('<col width="%d"/>' % w for w in COLW) + '</colgroup>'
    thead = '<thead><tr>' + ''.join(
        '<th vertical-align="top"><p>%s</p></th>' % esc(h) for h in HEAD) + '</tr></thead>'

    body = []
    for i, r in enumerate(rows):
        vals = r['vals']
        isp = r.get('is_percent', True)
        m_last = fmt(vals[-1], isp)
        hi = max(range(len(vals)), key=lambda k: vals[k] if vals[k] is not None else -1e18)
        hival = '%s(%s)' % (fmt(vals[hi], isp), mlabels[hi])
        actual = ('%+.1f%%' % (r['actual'] * 100)) if r['actual'] is not None else 'NA'
        tok, h = imgs[i]
        img = '<img src="%s" width="%d" height="%d" name="chart_%02d.png"/>' % (
            tok, args.chart_width, h, i + 1)
        status = ('<span text-color="green">✅ 达标</span>' if r['meet']
                  else '<span text-color="red">❌ 未达标</span>')
        lead = r.get('lead', {})
        cells = []
        for key in LEAD_KEYS:
            cells.append('<td vertical-align="top"><p>%s</p></td>' % esc(lead.get(key, '')))
        cells.append('<td vertical-align="top"><p>%s</p></td>' % m_last)
        cells.append('<td vertical-align="top"><p>%s</p></td>' % hival)
        cells.append('<td vertical-align="top"><p>%s</p></td>' % actual)
        cells.append('<td>%s</td>' % img)
        cells.append('<td vertical-align="top"><p>%s</p></td>' % status)
        body.append('<tr>' + ''.join(cells) + '</tr>')

    tbl = '<table>' + colgroup + thead + '<tbody>' + ''.join(body) + '</tbody></table>'
    print('table built, len=', len(tbl))

    # 3. block_replace 整表
    out = run(['lark-cli', 'docs', '+update', '--api-version', 'v2', '--doc', args.doc,
               '--command', 'block_replace', '--block-id', args.table_block, '--content', tbl])
    ok = '"success"' in out or '"result": "success"' in out
    print('REPLACE:', 'success' if ok else out[:400])

    # 4. 删临时块
    run(['lark-cli', 'docs', '+update', '--api-version', 'v2', '--doc', args.doc,
         '--command', 'block_delete', '--block-id', ','.join(temps)])
    print('temp blocks deleted:', len(temps))
    print('DONE')


if __name__ == '__main__':
    main()

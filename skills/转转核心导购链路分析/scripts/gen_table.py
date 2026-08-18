# -*- coding: utf-8 -*-
import csv, html

rows=list(csv.reader(open('/tmp/full5_chain.csv')))
hdr=rows[0]
body=rows[1:]

def fmt(v):
    s=str(v)
    # 纯整数绝对值加千分位；百分比/文字/小计名保持原样
    if s.isdigit():
        return f'{int(s):,}'
    return s

def cell(txt, tag='td'):
    return f'<{tag}><p>{html.escape(fmt(txt))}</p></{tag}>'

# 标题
h='<h3>表5 5来源×分业务 完整链路：曝光→点击→商详→收银台→支付（dt=2026-08-11，App端）</h3>'
note=('<p>说明：曝光/点击取自埋点（explosureGoods 的 goodsList、zpmclick 的 infoId，token 去重，'
      '页面识别 actiontype+region 见附录 SQL）；商详/收银台/支付取自 dm 交易表场景归因（商详按 first_from，'
      '收银台/支付按 ori_firstfrom）。购物车 dm 表无 first_from，其商详/收银台/支付走时序链路（曝光时间戳后发生的交易）。'
      '足迹"点击→商详">100% 系点击(埋点)与商详(dm场景归因)两套数据源交叉所致，非计算错误。</p>')

# colgroup: 2列名 + 5绝对值 + 5转化率 = 12列
cols=''.join('<col width="70"/>' for _ in range(2)) + ''.join('<col width="78"/>' for _ in range(5)) + ''.join('<col width="78"/>' for _ in range(5))
thead='<thead><tr>'+''.join(cell(h_,'th') for h_ in hdr)+'</tr></thead>'

trs=[]
for r in body:
    if r[1]=='小计':
        continue
    tds=''.join(cell(v) for v in r)
    trs.append(f'<tr>{tds}</tr>')
tbody='<tbody>'+''.join(trs)+'</tbody>'

table=f'<table><colgroup>{cols}</colgroup>{thead}{tbody}</table>'
content=h+note+table
open('/tmp/table5.html','w').write(content)
print('len',len(content),'rows',len(body))

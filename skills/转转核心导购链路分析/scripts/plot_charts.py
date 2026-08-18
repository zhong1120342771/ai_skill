# -*- coding: utf-8 -*-
# 分业务×5来源 曝光→点击 / 曝光→支付 对比柱状图
# 5来源 = 搜索(搜索结果页) / feed(首页推荐流) / 收藏(我的收藏列表) / 购物车(加购列表) / 足迹(浏览足迹列表)
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import numpy as np

plt.rcParams['font.sans-serif']=['Arial Unicode MS']
plt.rcParams['axes.unicode_minus']=False

rows=list(csv.reader(open('/tmp/full5_chain.csv')))
body=[r for r in rows[1:] if r[1]!='小计']
CATES=['消费电子','兴趣','二奢','其他']
SRCS=['搜索','feed','收藏','购物车','足迹']
d={(r[0],r[1]):r for r in body}

def pctval(s):
    s=s.strip()
    if s.endswith('%'):
        return float(s.rstrip('%'))
    return 0.0

# 来源配色（与场景语义呼应，稳定色板）
COLORS={'搜索':'#4C72B0','feed':'#DD8452','收藏':'#55A868','购物车':'#C44E52','足迹':'#8172B3'}

def draw(col_idx, title, fname, caption_note):
    fig,ax=plt.subplots(figsize=(10,4.6))
    n_cat=len(CATES); n_src=len(SRCS)
    x=np.arange(n_cat)
    w=0.16
    for i,s in enumerate(SRCS):
        vals=[pctval(d[(s,ct)][col_idx]) if (s,ct) in d else 0 for ct in CATES]
        bars=ax.bar(x+(i-2)*w, vals, w, label=s, color=COLORS[s])
        for b,v in zip(bars,vals):
            if v>0:
                ax.text(b.get_x()+b.get_width()/2, v, f'{v:.1f}', ha='center', va='bottom', fontsize=7)
    ax.set_xticks(x); ax.set_xticklabels(CATES, fontsize=11)
    ax.set_ylabel('转化率 (%)', fontsize=10)
    ax.set_title(title, fontsize=13, pad=10)
    ax.legend(ncol=5, fontsize=9, loc='upper right', frameon=False)
    ax.grid(axis='y', ls='--', alpha=0.4)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    top=ax.get_ylim()[1]
    ax.set_ylim(0, top*1.12)
    fig.tight_layout()
    fig.savefig(fname, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('saved', fname, caption_note)

# 曝光→点击列=7, 曝光→支付列=11
draw(7, '分业务×5来源 曝光→点击转化率（dt=2026-08-11，App端）', '/tmp/t5_expo_click.png', 'expo_click')
draw(11, '分业务×5来源 曝光→支付转化率（dt=2026-08-11，App端）', '/tmp/t5_expo_pay.png', 'expo_pay')

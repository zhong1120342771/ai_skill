# -*- coding: utf-8 -*-
import matplotlib, sys
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

for fp in ['/System/Library/Fonts/PingFang.ttc', '/System/Library/Fonts/STHeiti Medium.ttc']:
    try: font_manager.fontManager.addfont(fp)
    except Exception: pass
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
C_MAIN='#2E5BFF'; C_ACC='#FF7A45'; C_GRN='#22C55E'

# 电子/兴趣/二奢 = 强+极强合并
DATA = {
  'overall': {
    'tag':'整体', 'suffix':'v5o',
    '消费电子': dict(total=1407474, matched=1237332, dianzi=838237+338100, xingqu=40532+2952, ershe=15908+1603),
    '二奢':     dict(total=180727,  matched=150073,  dianzi=122636+11459, xingqu=2757+443,  ershe=9811+2967),
    '兴趣':     dict(total=33,      matched=32,      dianzi=20+0,         xingqu=9+1,       ershe=2+0),
  },
  'app': {
    'tag':'仅APP端', 'suffix':'v5a',
    '消费电子': dict(total=1356702, matched=1237126, dianzi=838087+338051, xingqu=40527+2949, ershe=15907+1605),
    '二奢':     dict(total=180727,  matched=150082,  dianzi=122648+11457, xingqu=2758+443,  ershe=9810+2966),
    '兴趣':     dict(total=33,      matched=32,      dianzi=20+0,         xingqu=9+1,       ershe=2+0),
  },
}
lists = ['消费电子','二奢','兴趣']

def draw(key):
    D = DATA[key]; tag = D['tag']; sf = D['suffix']
    # 图1: 匹配率
    fig, ax = plt.subplots(figsize=(8.8,5.2))
    rates = [D[l]['matched']/D[l]['total']*100 for l in lists]
    labels = [f'{l}名单' for l in lists]
    bars = ax.bar(labels, rates, color=[C_MAIN,C_ACC,C_GRN], width=0.55)
    for r,l in zip(bars, lists):
        ax.text(r.get_x()+r.get_width()/2, r.get_height()+1.2,
                f'{r.get_height():.1f}%\n(n={D[l]["total"]:,})', ha='center', fontsize=9.5)
    ax.set_ylabel('命中平台首标签意向占业务名单 (%)', fontsize=11)
    ax.set_title(f'业务重点名单 → 命中平台首次意向标签的比例（{tag}，dt=2026-07-27）',
                 fontsize=12.5, fontweight='bold', pad=14)
    ax.set_ylim(0,105); ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    plt.tight_layout(); plt.savefig(f'{sf}_chart1_match.png', dpi=150, bbox_inches='tight'); plt.close()
    # 图2: 流向
    fig, ax = plt.subplots(figsize=(9.5,5.6))
    cats=['电子','兴趣','二奢']; colors=[C_MAIN,C_GRN,C_ACC]
    for gi,l in enumerate(lists):
        d=D[l]; m=d['matched']
        vals=[d['dianzi']/m*100, d['xingqu']/m*100, d['ershe']/m*100]
        base=0
        for ci,v in enumerate(vals):
            ax.barh(gi, v, left=base, color=colors[ci], edgecolor='white',
                    label=cats[ci] if gi==0 else None)
            if v>4:
                ax.text(base+v/2, gi, f'{cats[ci]}\n{v:.1f}%', ha='center', va='center',
                        fontsize=9.5, color='white', fontweight='bold')
            base+=v
    ax.set_yticks(range(len(lists))); ax.set_yticklabels([f'{l}名单' for l in lists], fontsize=11)
    ax.set_xlim(0,100); ax.set_xlabel('占匹配用户比例 (%)，首标签口径下互斥拆分', fontsize=11)
    ax.set_title(f'业务名单用户的平台首次意向 → 流向哪个业务（{tag}，dt=2026-07-27）',
                 fontsize=12.5, fontweight='bold', pad=14)
    ax.legend(frameon=False, fontsize=10, ncol=3, loc='lower center', bbox_to_anchor=(0.5,-0.20))
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    plt.tight_layout(); plt.savefig(f'{sf}_chart2_flow.png', dpi=150, bbox_inches='tight'); plt.close()

draw('overall'); draw('app')
print('charts done')

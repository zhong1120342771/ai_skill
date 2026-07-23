# -*- coding: utf-8 -*-
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
for f in ["PingFang SC","Heiti SC","Songti SC","Arial Unicode MS","STHeiti"]:
    try: fm.findfont(f,fallback_to_default=False); plt.rcParams["font.sans-serif"]=[f]; break
    except Exception: pass
plt.rcParams["axes.unicode_minus"]=False
mo=["1月","2月","3月","4月","5月","6月"]
N=[None]*6
# 动销率(%) 按城市, 无数据的月为 None
zz=[4.72,5.27,7.76,7.62,7.50,8.05]
dg=[None,None,None,4.64,4.29,6.86]
cd=[None,None,None,None,3.28,4.35]
tot=[4.72,5.27,7.76,6.64,5.15,6.34]
fig,ax=plt.subplots(figsize=(9,5.2))
def plot(y,label,color,ls="-"):
    xs=[i for i,v in enumerate(y) if v is not None]
    ys=[v for v in y if v is not None]
    ax.plot(xs,ys,ls,marker="o",label=label,color=color,linewidth=2,markersize=6)
    for x,v in zip(xs,ys): ax.annotate(f"{v:.2f}",(x,v),textcoords="offset points",xytext=(0,8),ha="center",fontsize=8,color=color)
plot(tot,"整体","#95A5A6","--")
plot(zz,"郑州","#2E86C1")
plot(cd,"成都","#48C9B0")
plot(dg,"东莞","#E67E22")
ax.set_xticks(range(6)); ax.set_xticklabels(mo)
ax.set_ylabel("pro店同售动销率（%）"); ax.set_ylim(2,9.5)
ax.set_title("pro店同售动销率按城市（全城市；各城仅在有数月出线）\n郑州全程最高 4.72%→8.05%；东莞 4月起 4.64%→6.86%；成都 5月起 3.28%→4.35%(新店库存刚铺,最低)",fontsize=11)
ax.legend(loc="lower right",frameon=False,ncol=2)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.grid(axis="y",alpha=0.3)
plt.tight_layout()
out="/Users/zhongmengting/.claude/visualizations/yiti_h1_review/fig14_pro_dongxiao_by_city.png"
plt.savefig(out,dpi=150); print("saved",out)

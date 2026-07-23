# -*- coding: utf-8 -*-
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import numpy as np
for f in ["PingFang SC","Heiti SC","Songti SC","Arial Unicode MS","STHeiti"]:
    try: fm.findfont(f,fallback_to_default=False); plt.rcParams["font.sans-serif"]=[f]; break
    except Exception: pass
plt.rcParams["axes.unicode_minus"]=False

fig,axes=plt.subplots(1,2,figsize=(11,5),sharey=False)
groups=["1月","6月"]
x=np.arange(2); w=0.36

# 左: 双城  (2025:197/284  2026用正文口径232/423)
ax=axes[0]
y25=[197,284]; y26=[232,423]
b1=ax.bar(x-w/2,y25,w,label="2025",color="#B0B0B0")
b2=ax.bar(x+w/2,y26,w,label="2026",color="#C0392B")
for b,v in list(zip(b1,y25))+list(zip(b2,y26)):
    ax.text(b.get_x()+b.get_width()/2,v+6,str(v),ha="center",va="bottom",fontsize=9,fontweight="bold")
ax.set_title("试点双城（郑州&成都）\nH1增幅：25年+44.0% → 26年+82.5%；6月同比+48.7%",fontsize=10)
ax.set_xticks(x); ax.set_xticklabels(groups); ax.set_ylabel("同城订单量日均（单/日）")
ax.set_ylim(0,480); ax.legend(frameon=False,loc="upper left")
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

# 右: 全一体化 (2025:744/1016  2026:918/1501)
ax=axes[1]
y25=[744,1016]; y26=[918,1501]
b1=ax.bar(x-w/2,y25,w,label="2025",color="#B0B0B0")
b2=ax.bar(x+w/2,y26,w,label="2026",color="#C0392B")
for b,v in list(zip(b1,y25))+list(zip(b2,y26)):
    ax.text(b.get_x()+b.get_width()/2,v+18,str(v),ha="center",va="bottom",fontsize=9,fontweight="bold")
ax.set_title("全一体化城市（除重庆&西安）\nH1增幅：25年+36.6% → 26年+63.4%；6月同比+47.8%",fontsize=10)
ax.set_xticks(x); ax.set_xticklabels(groups); ax.set_ylabel("同城订单量日均（单/日）")
ax.set_ylim(0,1680); ax.legend(frameon=False,loc="upper left")
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

fig.suptitle("同城订单量日均 2025 vs 2026 同比：今年增幅约为去年两倍，6月绝对量高出去年同月约一半",fontsize=12,y=1.02)
plt.tight_layout()
out="/Users/zhongmengting/.claude/visualizations/yiti_h1_review/fig15_tongcheng_volume_yoy.png"
plt.savefig(out,dpi=150,bbox_inches="tight"); print("saved",out)

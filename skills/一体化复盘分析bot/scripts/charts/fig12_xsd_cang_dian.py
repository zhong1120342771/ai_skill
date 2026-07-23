# -*- coding: utf-8 -*-
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import csv
for f in ["PingFang SC","Heiti SC","Songti SC","Arial Unicode MS","STHeiti"]:
    try: fm.findfont(f,fallback_to_default=False); plt.rcParams["font.sans-serif"]=[f]; break
    except Exception: pass
plt.rcParams["axes.unicode_minus"]=False
rows=list(csv.DictReader(open("/tmp/xsd0723_daily.csv",encoding="utf-8")))
mo=[r["month"] for r in rows]
cang=[int(r["仓库"]) for r in rows]
dian=[int(r["小店"])+int(r["pro"]) for r in rows]
qt=[int(r["其他"]) for r in rows]
tot=[int(r["整体"]) for r in rows]
fig,ax=plt.subplots(figsize=(9,5.2))
b1=ax.bar(mo,cang,label="仓库订单",color="#2E86C1",width=0.6)
b2=ax.bar(mo,dian,bottom=cang,label="门店订单(小店+pro)",color="#48C9B0",width=0.6)
b3=ax.bar(mo,qt,bottom=[a+b for a,b in zip(cang,dian)],label="其他",color="#95A5A6",width=0.6)
def lbl(bars,vals,offs,c="white"):
    for r,v,o in zip(bars,vals,offs):
        if v>=8: ax.text(r.get_x()+r.get_width()/2,o+v/2,str(v),ha="center",va="center",fontsize=9,color=c,fontweight="bold")
lbl(b1,cang,[0]*6)
for i,(m,t) in enumerate(zip(mo,tot)):
    ax.text(i,t+8,str(t),ha="center",va="bottom",fontsize=10,fontweight="bold",color="#222")
ax.set_ylabel("小时达订单量日均（单/日）"); ax.set_ylim(0,430)
ax.set_title("小时达订单量日均按仓/店拆解（全城市；三档合计=整体 20→386）\n仓库 15→352(约23倍,6月占91%)；门店 4→31；其他≈0→3可忽略",fontsize=11)
ax.legend(loc="upper left",frameon=False)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
plt.tight_layout()
out="/Users/zhongmengting/.claude/visualizations/yiti_h1_review/fig12_xsd_cang_dian.png"
plt.savefig(out,dpi=150); print("saved",out)

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
xd=[int(r["小店"]) for r in rows]
pro=[int(r["pro"]) for r in rows]
men=[a+b for a,b in zip(xd,pro)]
fig,ax=plt.subplots(figsize=(9,5.2))
b1=ax.bar(mo,xd,label="小店",color="#5DADE2",width=0.6)
b2=ax.bar(mo,pro,bottom=xd,label="pro店",color="#E67E22",width=0.6)
def lbl(bars,vals,offs):
    for r,v,o in zip(bars,vals,offs):
        if v>0: ax.text(r.get_x()+r.get_width()/2,o+v/2,str(v),ha="center",va="center",fontsize=9,color="white",fontweight="bold")
lbl(b1,xd,[0]*6); lbl(b2,pro,xd)
for i,t in enumerate(men):
    ax.text(i,t+0.6,str(t),ha="center",va="bottom",fontsize=10,fontweight="bold",color="#222")
ax.set_ylabel("门店小时达订单量日均（单/日）"); ax.set_ylim(0,38)
ax.set_title("小时达门店订单拆 pro店/小店（全城市；门店合计 4→31）\n小店 4→15（4月峰值21后回落）；pro 0→16（持续爬升，6月已≈小店）",fontsize=11)
ax.legend(loc="upper left",frameon=False)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
plt.tight_layout()
out="/Users/zhongmengting/.claude/visualizations/yiti_h1_review/fig13_xsd_mendian_pro_xiaodian.png"
plt.savefig(out,dpi=150); print("saved",out)

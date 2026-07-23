# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import csv

# CJK font
for f in ["PingFang SC","Heiti SC","Songti SC","Arial Unicode MS","STHeiti"]:
    try:
        fm.findfont(f,fallback_to_default=False); plt.rcParams["font.sans-serif"]=[f]; break
    except Exception: pass
plt.rcParams["axes.unicode_minus"]=False

rows=list(csv.DictReader(open("/tmp/pro_city_daily.csv",encoding="utf-8")))
months=[r["month"] for r in rows]
zz=[int(r["郑州"]) for r in rows]
cd=[int(r["成都"]) for r in rows]
dg=[int(r["东莞"]) for r in rows]
tot=[int(r["整体"]) for r in rows]

fig,ax=plt.subplots(figsize=(9,5.2))
c_zz,c_cd,c_dg="#2E86C1","#48C9B0","#E67E22"
b1=ax.bar(months,zz,label="郑州",color=c_zz,width=0.6)
b2=ax.bar(months,cd,bottom=zz,label="成都",color=c_cd,width=0.6)
b3=ax.bar(months,dg,bottom=[a+b for a,b in zip(zz,cd)],label="东莞",color=c_dg,width=0.6)

# per-segment labels (skip zeros)
def lbl(bars,vals,offs):
    for rect,v,o in zip(bars,vals,offs):
        if v>0:
            ax.text(rect.get_x()+rect.get_width()/2, o+v/2, str(v),
                    ha="center",va="center",fontsize=9,color="white",fontweight="bold")
lbl(b1,zz,[0]*6); lbl(b2,cd,zz); lbl(b3,dg,[a+b for a,b in zip(zz,cd)])
# total on top
for i,(m,t) in enumerate(zip(months,tot)):
    ax.text(i,t+8,str(t),ha="center",va="bottom",fontsize=10,fontweight="bold",color="#222")

ax.set_ylabel("pro店同售单量日均（单/日）")
ax.set_ylim(0,540)
ax.set_title("pro店同售单量日均按城市拆解（全城市；三城合计=整体 96→480）\n郑州基本盘 96→189；东莞4月上线冲到174；成都5月起量到117；6月三城约 39%/36%/24%",fontsize=11)
ax.legend(loc="upper left",frameon=False)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
plt.tight_layout()
out="/Users/zhongmengting/.claude/visualizations/yiti_h1_review/fig9_pro_volume_by_city.png"
plt.savefig(out,dpi=150); print("saved",out)

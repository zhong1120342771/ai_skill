# -*- coding: utf-8 -*-
"""fig8 小店同售单量日均：全口径(柱) + 一体化覆盖城市(线)。配色与 fig4/5/6 统一。"""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

CJK=["PingFang SC","Heiti SC","Arial Unicode MS","SimHei","STHeiti"]
av={f.name for f in font_manager.fontManager.ttflist}
chosen=next((f for f in CJK if f in av),None)
if chosen is None:
    for p in ["/System/Library/Fonts/PingFang.ttc","/Library/Fonts/Arial Unicode.ttf"]:
        if os.path.exists(p):
            font_manager.fontManager.addfont(p); chosen=font_manager.FontProperties(fname=p).get_name(); break
plt.rcParams["font.sans-serif"]=([chosen] if chosen else [])+CJK
plt.rcParams["axes.unicode_minus"]=False
plt.rcParams["figure.dpi"]=160

D=os.path.expanduser("~/.claude/data_storage")
OUT=os.path.expanduser("~/.claude/visualizations/yiti_h1_review")
CUT=pd.Timestamp("2026-06-30")
MONTHS=["2026-01","2026-02","2026-03","2026-04","2026-05","2026-06"]; LAB=["1月","2月","3月","4月","5月","6月"]
C_BAR="#2E86C1"; C_PILOT="#C0392B"

def da(df,dcol,val,gc=None):
    df=df.copy(); df[dcol]=pd.to_datetime(df[dcol]); df=df[df[dcol]<=CUT]
    df["month"]=df[dcol].dt.to_period("M").astype(str)
    g=df.groupby(["month"]+(gc or [])).agg(total=(val,"sum"),nd=(dcol,"nunique")).reset_index()
    g["日均"]=g["total"]/g["nd"]; return g

# 全口径小店
ts=pd.read_csv(os.path.join(D,"yiti_tongshou_2026-07-21.csv")); ts.columns=["dt","city","type","kc","pay"]
allg=da(ts[ts["type"]=="小店"],"dt","pay").set_index("month")["日均"].reindex(MONTHS)
# 一体化覆盖城市(蓉郑)小店
tc=pd.read_csv(os.path.join(D,"yiti_tongshou_yiti_city_2026-07-21.csv")); tc.columns=["dt","grp","type","kc","pay"]
cov=da(tc[tc["grp"]=="一体化覆盖城市（小店）"],"dt","pay").set_index("month")["日均"].reindex(MONTHS)

fig,ax=plt.subplots(figsize=(10,6))
ax.bar(LAB,allg.values,color=C_BAR,label="全口径小店同售单量(单/日)")
for i,v in enumerate(allg.values):
    ax.annotate(f"{v:.0f}",(i,v),textcoords="offset points",xytext=(0,4),ha="center",fontsize=9,fontweight="bold",color="#1B4F72")
ax.set_ylabel("全口径小店同售单量（单/日）"); ax.set_ylim(0,allg.max()*1.2)
ax2=ax.twinx()
ax2.plot(LAB,cov.values,color=C_PILOT,marker="o",lw=2.4,label="一体化覆盖城市(郑州&成都)(单/日)")
for i,v in enumerate(cov.values):
    ax2.annotate(f"{v:.0f}",(i,v),textcoords="offset points",xytext=(0,8),ha="center",fontsize=9,fontweight="bold",color=C_PILOT)
ax2.set_ylabel("覆盖城市小店同售单量（单/日）",color=C_PILOT); ax2.tick_params(axis="y",labelcolor=C_PILOT); ax2.set_ylim(0,cov.max()*1.8)
ax.set_title("小店同售单量日均：全口径 vs 一体化覆盖城市\n全口径 1249→1403（+12.3%）；覆盖城市(郑州&成都) 149→295（+98.0%），增量集中在试点",fontsize=12.5,fontweight="bold")
l1,la1=ax.get_legend_handles_labels(); l2,la2=ax2.get_legend_handles_labels(); ax.legend(l1+l2,la1+la2,loc="upper right",fontsize=9)
ax.grid(axis="y",alpha=.3)
plt.tight_layout(); plt.savefig(os.path.join(OUT,"fig8_xiaodian_volume.png")); plt.close()
print("fig8 done. font:",chosen,"| 全口径",[round(x) for x in allg.values],"| 覆盖",[round(x) for x in cov.values])

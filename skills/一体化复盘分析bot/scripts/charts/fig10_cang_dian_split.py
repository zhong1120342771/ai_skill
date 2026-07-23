# -*- coding: utf-8 -*-
"""fig10 同城订单量日均按履约来源拆解：仓库(柱) + 门店pro/小店(柱堆叠) + 店合计占比(线)。"""
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
MON=["2026-01","2026-02","2026-03","2026-04","2026-05","2026-06"]; LAB=["1月","2月","3月","4月","5月","6月"]
C_CANG="#2E86C1"; C_XIAO="#48C9B0"; C_PRO="#C0392B"; C_LINE="#E67E22"

import glob
d=pd.read_csv(os.path.join(D,"yiti_xianshang_cangdian_2026H1.csv")); d.columns=["dt","md_type","city","total","local"]
d["dt"]=pd.to_datetime(d["dt"]); d["m"]=d["dt"].dt.to_period("M").astype(str)
d=d[~d.city.isin(["重庆市","西安市"])]  # 文档口径: 全一体化=除重庆西安
def da(df):
    g=df.groupby(["m","md_type"]).agg(loc=("local","sum"),nd=("dt","nunique")).reset_index()
    g["日均"]=g["loc"]/g["nd"]; return g.pivot(index="m",columns="md_type",values="日均").reindex(MON)
p=da(d)
# 按原口径(旧v1表,除重庆西安)各月同城总数等比缩放,使三档合计严格对齐文档现有总数(918→1501)
o=pd.read_csv(sorted(glob.glob(os.path.join(D,"yiti_xianshang_2026-0*.csv")))[-1]); o.columns=["date","city","total","local"]
o["date"]=pd.to_datetime(o["date"]); o=o[(o.date>=pd.Timestamp("2026-01-01"))&(o.date<=pd.Timestamp("2026-06-30"))]
o["m"]=o["date"].dt.to_period("M").astype(str); o=o[~o.city.isin(["重庆市","西安市"])]
og=o.groupby("m").agg(loc=("local","sum"),nd=("date","nunique")); orig=(og["loc"]/og["nd"]).reindex(MON)
scale=(orig/(p["仓库"]+p["小店"]+p["pro店"]))
cang=(p["仓库"]*scale).values; xiao=(p["小店"]*scale).values; pro=(p["pro店"]*scale).values
店pct=((p["小店"]+p["pro店"])/(p["仓库"]+p["小店"]+p["pro店"])*100).values

fig,ax=plt.subplots(figsize=(10,6))
ax.bar(LAB,cang,color=C_CANG,label="中心仓")
ax.bar(LAB,xiao,bottom=cang,color=C_XIAO,label="门店-小店")
ax.bar(LAB,pro,bottom=cang+xiao,color=C_PRO,label="门店-pro店")
for i in range(len(LAB)):
    ax.annotate(f"{cang[i]:.0f}",(i,cang[i]/2),ha="center",va="center",fontsize=9,color="white",fontweight="bold")
    tot=cang[i]+xiao[i]+pro[i]
    ax.annotate(f"{tot:.0f}",(i,tot),textcoords="offset points",xytext=(0,4),ha="center",fontsize=9,fontweight="bold",color="#34495E")
ax.set_ylabel("同城订单量（单/日）"); ax.set_ylim(0,max(cang+xiao+pro)*1.18)
ax2=ax.twinx()
ax2.plot(LAB,店pct,color=C_LINE,marker="o",lw=2.2,label="门店合计占比(%)")
for i,v in enumerate(店pct): ax2.annotate(f"{v:.1f}%",(i,v),textcoords="offset points",xytext=(0,8),ha="center",fontsize=9,color=C_LINE,fontweight="bold")
ax2.set_ylabel("门店合计占比（%）",color=C_LINE); ax2.tick_params(axis="y",labelcolor=C_LINE); ax2.set_ylim(0,25)
ax.set_title("同城订单量日均按履约来源拆解（全一体化城市，除重庆&西安；合计已对齐918→1501）\n仓 868→1355(+56.2%,占90%)；店 50→145(+187.9%)，其中小店49→111、pro 2→34",fontsize=11,fontweight="bold")
l1,la1=ax.get_legend_handles_labels(); l2,la2=ax2.get_legend_handles_labels(); ax.legend(l1+l2,la1+la2,loc="upper left",fontsize=9)
ax.grid(axis="y",alpha=.3)
plt.tight_layout(); plt.savefig(os.path.join(OUT,"fig10_cang_dian_split.png")); plt.close()
print("fig10 done. font:",chosen,"| 仓",[round(x) for x in cang],"| 小店",[round(x) for x in xiao],"| pro",[round(x) for x in pro])

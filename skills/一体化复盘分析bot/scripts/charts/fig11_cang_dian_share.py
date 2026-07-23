# -*- coding: utf-8 -*-
"""fig11 仓/店各自的同城订单占比(该来源同城单/该来源总单)月度趋势。全一体化城市,除重庆西安。"""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter

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

d=pd.read_csv(os.path.join(D,"yiti_xianshang_cangdian_2026H1.csv")); d.columns=["dt","md_type","city","total","local"]
d["dt"]=pd.to_datetime(d["dt"]); d["m"]=d["dt"].dt.to_period("M").astype(str)
d=d[~d.city.isin(["重庆市","西安市"])]
g=d.groupby(["m","md_type"]).agg(loc=("local","sum"),tot=("total","sum")).reset_index()
def sh(types):
    x=g[g.md_type.isin(types)].groupby("m").agg(loc=("loc","sum"),tot=("tot","sum"))
    return (x["loc"]/x["tot"]*100).reindex(MON)
cang=sh(["仓库"]); dian=sh(["小店","pro店"]); xiao=sh(["小店"]); pro=sh(["pro店"])

fig,ax=plt.subplots(figsize=(10,6))
series=[("中心仓","#2E86C1","o",cang),("门店合计","#E67E22","D",dian),("门店-小店","#48C9B0","s",xiao),("门店-pro店","#C0392B","^",pro)]
for lbl,col,mk,s in series:
    ax.plot(LAB,s.values,color=col,marker=mk,lw=2.2,markersize=7,label=lbl)
    ax.annotate(f"{s.iloc[-1]:.2f}%",(len(LAB)-1,s.iloc[-1]),textcoords="offset points",xytext=(6,0),fontsize=9,color=col,fontweight="bold")
    ax.annotate(f"{s.iloc[0]:.2f}%",(0,s.iloc[0]),textcoords="offset points",xytext=(-6,-2),ha="right",fontsize=8.5,color=col)
ax.set_ylabel("该来源同城订单占比（同城单/该来源总单，%）")
ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_:f"{v:.0f}%"))
ax.set_ylim(0,10)
ax.set_title("仓/店各自的同城订单占比月度趋势（全一体化城市，除重庆&西安）\n门店占比弹性远高于仓：门店 3.89%→8.25%(+4.36pp)、pro 1.69%→7.58%(+5.88pp)；仅 +0.92pp",fontsize=11,fontweight="bold")
ax.legend(loc="upper left",fontsize=9,ncol=2); ax.grid(axis="y",alpha=.3)
plt.tight_layout(); plt.savefig(os.path.join(OUT,"fig11_cang_dian_share.png")); plt.close()
print("fig11 done. font:",chosen,"| 仓",[round(x,2) for x in cang],"| 店",[round(x,2) for x in dian],"| pro",[round(x,2) for x in pro])

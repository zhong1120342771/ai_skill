# -*- coding: utf-8 -*-
"""重画 fig3/4/5/6 —— 绝对值指标改用日均（当月有数据天数）。fig1/2/7 是比率不变。"""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

CJK = ["PingFang SC","Heiti SC","Arial Unicode MS","SimHei","STHeiti"]
av = {f.name for f in font_manager.fontManager.ttflist}
chosen = next((f for f in CJK if f in av), None)
if chosen is None:
    for p in ["/System/Library/Fonts/PingFang.ttc","/Library/Fonts/Arial Unicode.ttf"]:
        if os.path.exists(p):
            font_manager.fontManager.addfont(p); chosen = font_manager.FontProperties(fname=p).get_name(); break
plt.rcParams["font.sans-serif"] = ([chosen] if chosen else []) + CJK
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 160

D = os.path.expanduser("~/.claude/data_storage")
OUT = os.path.expanduser("~/.claude/visualizations/yiti_h1_review")
CUT = pd.Timestamp("2026-06-30")
MONTHS = ["2026-01","2026-02","2026-03","2026-04","2026-05","2026-06"]
LAB = ["1月","2月","3月","4月","5月","6月"]

def da(df,dcol,valcol,gc=None):
    df=df.copy(); df[dcol]=pd.to_datetime(df[dcol]); df=df[df[dcol]<=CUT]
    df["month"]=df[dcol].dt.to_period("M").astype(str)
    g=df.groupby(["month"]+(gc or [])).agg(total=(valcol,"sum"),nd=(dcol,"nunique")).reset_index()
    g["日均"]=g["total"]/g["nd"]; return g

C_PILOT="#C0392B"; C_OTHER="#7FB3D5"; C_BAR="#2E86C1"; C_LINE="#E67E22"

def bars_labels(ax, xs, ys, color, fmt="{:.0f}"):
    for x,y in zip(xs,ys):
        ax.annotate(fmt.format(y),(x,y),textcoords="offset points",xytext=(0,4),
                    ha="center",fontsize=9,fontweight="bold",color=color)

# ---------- fig3 同城订单量 日均（试点 + 其他一体化 堆叠）----------
xs=pd.read_csv(os.path.join(D,"yiti_xianshang_2026-07-21.csv")); xs.columns=["date","city","total","local"]
def grp(c): return "对照(重庆&西安)" if c in["重庆市","西安市"] else("试点(郑州&成都)" if c in["成都市","郑州市"] else "其他一体化")
xs["grp"]=xs["city"].apply(grp)
g=da(xs,"date","local",["grp"]).pivot(index="month",columns="grp",values="日均").reindex(MONTHS)
fig,ax=plt.subplots(figsize=(10,6))
p1=ax.bar(LAB,g["试点(郑州&成都)"],color=C_PILOT,label="试点城市(郑州&成都)")
p2=ax.bar(LAB,g["其他一体化"],bottom=g["试点(郑州&成都)"],color=C_OTHER,label="其他一体化城市")
for i,(a,b) in enumerate(zip(g["试点(郑州&成都)"],g["其他一体化"])):
    ax.annotate(f"{a:.0f}",(i,a/2),ha="center",va="center",fontsize=9,color="white",fontweight="bold")
    ax.annotate(f"{a+b:.0f}",(i,a+b),textcoords="offset points",xytext=(0,4),ha="center",fontsize=9,fontweight="bold",color="#34495E")
ax.set_title("同城订单量日均趋势（试点 232→423，全一体化 918→1501 单/日）",fontsize=13,fontweight="bold")
ax.set_ylabel("同城订单量（单/日，当月有数据天数日均）"); ax.legend(); ax.grid(axis="y",alpha=.3)
plt.tight_layout(); plt.savefig(os.path.join(OUT,"fig3_tongcheng_volume.png")); plt.close()

# ---------- fig4 小时达 日均 ----------
xsd=pd.read_csv(os.path.join(D,"yiti_xiaoshida_2026-07-21.csv")); xsd.columns=["dt","city","type","orders"]
x=da(xsd,"dt","orders").set_index("month")["日均"].reindex(MONTHS)
fig,ax=plt.subplots(figsize=(10,6))
ax.bar(LAB,x.values,color=C_BAR)
bars_labels(ax,range(len(LAB)),x.values,"#1B4F72","{:.0f}")
ax.set_title("小时达订单量日均趋势（20→386 单/日，约 20 倍）",fontsize=13,fontweight="bold")
ax.set_ylabel("小时达订单量（单/日）"); ax.grid(axis="y",alpha=.3)
plt.tight_layout(); plt.savefig(os.path.join(OUT,"fig4_xiaoshida_trend.png")); plt.close()

# ---------- fig5 线索量日均(柱) + 转化率(线，比率不变) ----------
xl=pd.read_csv(os.path.join(D,"yiti_xiansuo_2026-07-21.csv")); xl.columns=["date","src","tag","xs","pay"]
lg=da(xl,"date","xs").set_index("month")["日均"].reindex(MONTHS)
# 转化率 = 月支付uv总 / 月线索uv总（比率，与日均无关）
tot=xl.copy(); tot["date"]=pd.to_datetime(tot["date"]); tot=tot[tot["date"]<=CUT]
tot["month"]=tot["date"].dt.to_period("M").astype(str)
conv=(tot.groupby("month")["pay"].sum()/tot.groupby("month")["xs"].sum()*100).reindex(MONTHS)
fig,ax=plt.subplots(figsize=(10,6))
ax.bar(LAB,lg.values,color=C_BAR,label="线索量(单/日)")
bars_labels(ax,range(len(LAB)),lg.values,"#1B4F72","{:.0f}")
ax.set_ylabel("线索量（UV/日）"); ax.set_title("线索量日均放量 vs 转化率稀释（35→299 单/日；转化率 6.13%→2.96%）",fontsize=12.5,fontweight="bold")
ax2=ax.twinx(); ax2.plot(LAB,conv.values,color=C_LINE,marker="o",lw=2.2,label="转化率(%)")
for i,v in enumerate(conv.values): ax2.annotate(f"{v:.2f}%",(i,v),textcoords="offset points",xytext=(0,8),ha="center",fontsize=9,color=C_LINE,fontweight="bold")
ax2.set_ylabel("线索转化率（%）",color=C_LINE); ax2.tick_params(axis="y",labelcolor=C_LINE)
ax.grid(axis="y",alpha=.3)
l1,la1=ax.get_legend_handles_labels(); l2,la2=ax2.get_legend_handles_labels(); ax.legend(l1+l2,la1+la2,loc="upper left")
plt.tight_layout(); plt.savefig(os.path.join(OUT,"fig5_xiansuo_trend.png")); plt.close()

# ---------- fig6 pro店同售单量日均(柱) + 动销率(线，比率不变) ----------
ts=pd.read_csv(os.path.join(D,"yiti_tongshou_2026-07-21.csv")); ts.columns=["dt","city","type","kc","pay"]
pro=ts[ts["type"]=="pro店"]
pg=da(pro,"dt","pay").set_index("month")["日均"].reindex(MONTHS)
pt=pro.copy(); pt["dt"]=pd.to_datetime(pt["dt"]); pt=pt[pt["dt"]<=CUT]; pt["month"]=pt["dt"].dt.to_period("M").astype(str)
dr=(pt.groupby("month")["pay"].sum()/pt.groupby("month")["kc"].sum()*100).reindex(MONTHS)
fig,ax=plt.subplots(figsize=(10,6))
ax.bar(LAB,pg.values,color=C_BAR,label="pro店同售单量(单/日)")
bars_labels(ax,range(len(LAB)),pg.values,"#1B4F72","{:.0f}")
ax.set_ylabel("pro店同售单量（单/日）"); ax.set_title("pro店同售单量日均 + 动销率（96→480 单/日 +398.8%；动销率 4.72%→6.34%）",fontsize=12,fontweight="bold")
ax2=ax.twinx(); ax2.plot(LAB,dr.values,color=C_LINE,marker="s",lw=2.2,label="动销率(%)")
for i,v in enumerate(dr.values): ax2.annotate(f"{v:.2f}%",(i,v),textcoords="offset points",xytext=(0,8),ha="center",fontsize=9,color=C_LINE,fontweight="bold")
ax2.set_ylabel("同售动销率（%）",color=C_LINE); ax2.tick_params(axis="y",labelcolor=C_LINE)
ax.axvline(3,color="#BDC3C7",ls="--",lw=1); ax.annotate("4-5月二期加速",(3.05,pg.max()*0.9),color="#7F8C8D",fontsize=10)
ax.grid(axis="y",alpha=.3)
l1,la1=ax.get_legend_handles_labels(); l2,la2=ax2.get_legend_handles_labels(); ax.legend(l1+l2,la1+la2,loc="upper left")
plt.tight_layout(); plt.savefig(os.path.join(OUT,"fig6_pro_tongshou_trend.png")); plt.close()

print("regenerated fig3/4/5/6 as daily-average. font:",chosen)

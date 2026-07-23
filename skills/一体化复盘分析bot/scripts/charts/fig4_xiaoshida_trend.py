# -*- coding: utf-8 -*-
"""fig4 小时达订单量日均总趋势(全城市)。数据源与fig12同(xsd_h1_split)，保证1月=23、约17倍一致。"""
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

OUT=os.path.expanduser("~/.claude/visualizations/yiti_h1_review")
MON=["2026-01","2026-02","2026-03","2026-04","2026-05","2026-06"]; LAB=["1月","2月","3月","4月","5月","6月"]
C_BAR="#2E86C1"

# 整体: 当月总pv / 当月活跃天数(单一月度nd)
m=pd.read_csv("/Users/zhongmengting/Downloads/xsd_h1_month.csv").set_index("m").reindex(MON)
tot=(m["tot_pv"]/m["nd_month"]).values

fig,ax=plt.subplots(figsize=(10,6))
ax.bar(LAB,tot,color=C_BAR)
for i,v in enumerate(tot):
    ax.annotate(f"{v:.0f}",(i,v),textcoords="offset points",xytext=(0,4),ha="center",fontsize=10,fontweight="bold",color="#34495E")
ax.set_ylabel("小时达订单量（单/日）"); ax.set_ylim(0,max(tot)*1.15)
ax.set_title("小时达订单量日均趋势（全城市）\n1 月中旬起量，20→386 单/日，约 20 倍",fontsize=11,fontweight="bold")
ax.grid(axis="y",alpha=.3)
plt.tight_layout(); plt.savefig(os.path.join(OUT,"fig4_xiaoshida_trend.png")); plt.close()
print("fig4 done. font:",chosen,"| 合计",[round(x) for x in tot])

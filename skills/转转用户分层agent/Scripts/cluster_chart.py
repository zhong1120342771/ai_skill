#!/usr/bin/env python3
"""价敏叠加分群 气泡图：x=付费率lift, y=GMV lift, 气泡大小=人数, 颜色=价敏倾向。
用法: python cluster_chart.py <cluster_csv> <out_png>
"""
import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

csv, out = sys.argv[1], sys.argv[2]
plt.rcParams["font.sans-serif"]=["Arial Unicode MS","PingFang SC","Heiti SC","STHeiti"]
plt.rcParams["axes.unicode_minus"]=False
df=pd.read_csv(csv)

fig,ax=plt.subplots(figsize=(12,7.5))
# 颜色按价敏分位均值:低=偏贵=蓝,高=偏便宜=橙
c=df["近90价敏分位均值"].fillna(0.5)
sizes=(df["人数"]/df["人数"].max()*2600)+180
sc=ax.scatter(df["付费率lift"],df["GMVlift"],s=sizes,c=c,cmap="coolwarm_r",
              alpha=0.72,edgecolors="#333",linewidths=1.1,vmin=0.2,vmax=0.85)
for _,r in df.iterrows():
    ax.annotate(f"{r['人群']}\n{r['人数']:,}人({r['占比']*100:.1f}%)",
                (r["付费率lift"],r["GMVlift"]),ha="center",va="center",fontsize=8,color="#111")
ax.axhline(1,ls="--",c="#999",alpha=0.6); ax.axvline(1,ls="--",c="#999",alpha=0.6)
ax.text(1.02,ax.get_ylim()[1]*0.98,"GMV=大盘均值",fontsize=8,color="#999",va="top")
ax.set_xlabel("未来365天付费率 / 全样本基线（lift，>1 更易再付费）",fontsize=11)
ax.set_ylabel("未来365天人均GMV / 全样本基线（lift，>1 更值钱）",fontsize=11)
ax.set_title("价敏×单维叠加分群：各运营人群的付费率与GMV价值（气泡=人数，蓝=偏买贵，橙=偏买便宜）",fontsize=12.5,pad=12)
ax.grid(ls="--",alpha=0.25); ax.set_axisbelow(True)
cb=plt.colorbar(sc,ax=ax,pad=0.01); cb.set_label("近90天同类价格分位均值（低=价敏偏便宜）",fontsize=9)
plt.tight_layout(); plt.savefig(out,dpi=150,bbox_inches="tight")
print(f"[chart] -> {out}")

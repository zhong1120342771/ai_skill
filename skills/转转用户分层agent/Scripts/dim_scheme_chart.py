#!/usr/bin/env python3
"""单维度分层人数分布图：R/F/M/L/A 主维各层人数堆叠横条。
用法: python dim_scheme_chart.py <scheme_csv> <out_png>
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
main_dims=["R 最近支付间隔","F 支付频次","M 支付金额","L 生命周期","A 活跃度(复合0-6)"]
d=df[df.维度.isin(main_dims)].copy()

fig,ax=plt.subplots(figsize=(13,6))
dims=main_dims[::-1]
y=np.arange(len(dims))
cmap=plt.cm.RdYlGn  # 高层绿低层红
for yi,dim in enumerate(dims):
    sub=d[d.维度==dim].reset_index(drop=True)
    left=0
    k=len(sub)
    for i,row in sub.iterrows():
        frac=row["占比"]
        color=cmap(1-i/(k-1)) if k>1 else cmap(0.5)
        ax.barh(yi,frac,left=left,color=color,edgecolor="white",height=0.62)
        if frac>0.02:
            ax.text(left+frac/2,yi,f"{row['层级'].split(' ')[0].split('(')[0]}\n{row['人数']:,}\n{frac*100:.1f}%",
                    ha="center",va="center",fontsize=7.5,color="#222")
        left+=frac
ax.set_yticks(y); ax.set_yticklabels(dims,fontsize=11)
ax.set_xlim(0,1); ax.set_xlabel("占全样本比例（样本100万，dt=2025-07-27）")
ax.set_title("五大维度单维分层人数分布（切点均来自实测分位，高层绿→低层红）",fontsize=13,pad=12)
ax.set_axisbelow(True); ax.grid(axis="x",ls="--",alpha=0.3)
plt.tight_layout(); plt.savefig(out,dpi=150,bbox_inches="tight")
print(f"[chart] -> {out}")

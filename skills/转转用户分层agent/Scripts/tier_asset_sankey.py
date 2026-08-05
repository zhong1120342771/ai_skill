#!/usr/bin/env python3
"""价值层L1-L5 → 资产层z0-z5 流向桑基图（matplotlib 纯静态 PNG，无 plotly 依赖）。
用法: python tier_asset_sankey.py <flow_csv> <out_png> <rho> <tau>
"""
import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.path import Path

flow_csv, out_png = sys.argv[1], sys.argv[2]
rho = float(sys.argv[3]); tau = float(sys.argv[4])
plt.rcParams["font.sans-serif"] = ["Arial Unicode MS","PingFang SC","Heiti SC","STHeiti"]
plt.rcParams["axes.unicode_minus"] = False

flow = pd.read_csv(flow_csv, index_col=0)
L = list(flow.index)          # L5..L1
Z = list(flow.columns)        # z5..z0
M = flow.to_numpy().astype(float)
total = M.sum()

# 左右节点纵向排布（按总量分配高度，留 gap）
def node_layout(sizes, gap_frac=0.02):
    gap = total*gap_frac
    heights = sizes.copy()
    y, tops = 0.0, []
    for h in heights:
        tops.append(y); y += h + gap
    span = y - gap
    return tops, span

left_sizes = M.sum(axis=1)
right_sizes = M.sum(axis=0)
lt, lspan = node_layout(left_sizes)
rt, rspan = node_layout(right_sizes)
span = max(lspan, rspan)

fig, ax = plt.subplots(figsize=(11,7))
x_left, x_right, node_w = 0.10, 0.90, 0.022
cmapL = plt.cm.viridis(np.linspace(0.15,0.9,len(L)))

# 记录各节点已用偏移
loff = [0.0]*len(L); roff=[0.0]*len(Z)
lpos = {l:(lt[i], left_sizes[i]) for i,l in enumerate(L)}
rpos = {z:(rt[j], right_sizes[j]) for j,z in enumerate(Z)}

for i,l in enumerate(L):
    for j,z in enumerate(Z):
        v = M[i,j]
        if v <= 0: continue
        y0 = lt[i] + loff[i]; y1 = lt[i] + loff[i] + v; loff[i]+=v
        y2 = rt[j] + roff[j]; y3 = rt[j] + roff[j] + v; roff[j]+=v
        # 归一到 0-1
        def ny(y): return 1 - y/span*0.9 - 0.05
        ya0,ya1,yb0,yb1 = ny(y0),ny(y1),ny(y2),ny(y3)
        xa, xb = x_left+node_w, x_right
        xm = (xa+xb)/2
        verts=[(xa,ya0),(xm,ya0),(xm,yb0),(xb,yb0),(xb,yb1),(xm,yb1),(xm,ya1),(xa,ya1),(xa,ya0)]
        codes=[Path.MOVETO,Path.CURVE4,Path.CURVE4,Path.CURVE4,Path.LINETO,Path.CURVE4,Path.CURVE4,Path.CURVE4,Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(verts,codes),facecolor=cmapL[i],alpha=0.45,edgecolor="none"))

# 画节点块 + 标签
for i,l in enumerate(L):
    y0=lt[i]; h=left_sizes[i]
    def ny(y): return 1 - y/span*0.9 - 0.05
    ax.add_patch(Rectangle((x_left,ny(y0+h)),node_w,(h/span*0.9),facecolor=cmapL[i],edgecolor="k",lw=0.5))
    ax.text(x_left-0.01, ny(y0+h/2), f"{l}\n{int(left_sizes[i]):,} ({left_sizes[i]/total:.1%})",
            ha="right",va="center",fontsize=10,fontweight="bold")
for j,z in enumerate(Z):
    y0=rt[j]; h=right_sizes[j]
    def ny(y): return 1 - y/span*0.9 - 0.05
    ax.add_patch(Rectangle((x_right,ny(y0+h)),node_w,(h/span*0.9),facecolor="#888",edgecolor="k",lw=0.5))
    ax.text(x_right+node_w+0.01, ny(y0+h/2), f"{z}\n{int(right_sizes[j]):,}",
            ha="left",va="center",fontsize=10,fontweight="bold")

ax.text(x_left, 1.02, "RFMLAP 价值层", ha="left", fontsize=12, fontweight="bold")
ax.text(x_right+node_w, 1.02, "资产分层(数分体系)", ha="right", fontsize=12, fontweight="bold")
ax.set_title(f"价值层 → 资产层 用户流向  (Spearman ρ={rho:.2f}, Kendall τ-b={tau:.2f}，强正相关)",
             fontsize=13, pad=24)
ax.set_xlim(0,1.05); ax.set_ylim(0,1.06); ax.axis("off")
plt.tight_layout()
plt.savefig(out_png, dpi=150, bbox_inches="tight")
print(f"[sankey] -> {out_png}")

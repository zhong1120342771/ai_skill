#!/usr/bin/env python3
"""两套体系预测力对比图：左右两个子图(7d/365d)各叠RFMLAP与资产层ROC。
用法: python sys_compare_chart.py <roc_csv> <json> <out_png>
"""
import sys, json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

roc_csv, jf, out = sys.argv[1], sys.argv[2], sys.argv[3]
plt.rcParams["font.sans-serif"]=["Arial Unicode MS","PingFang SC","Heiti SC","STHeiti"]
plt.rcParams["axes.unicode_minus"]=False
roc=pd.read_csv(roc_csv); res=json.load(open(jf,encoding="utf-8"))
fig,axes=plt.subplots(1,2,figsize=(14,5.8))
cmap={"RFMLAP价值层":"#1f77b4","资产分层z0-z5":"#d62728"}
for ax,win in zip(axes,["7d","365d"]):
    for sysname,color in cmap.items():
        r=roc[(roc.window==win)&(roc.system==sysname)].sort_values("fpr")
        auc=res[sysname][win]["AUC"]
        ax.plot(r.fpr,r.tpr,color=color,lw=2.2,label=f"{sysname}  AUC={auc:.4f}")
    ax.plot([0,1],[0,1],"--",color="#999",lw=1)
    ax.set_xlabel("假正率 FPR"); ax.set_ylabel("真正率 TPR")
    ax.set_title(f"{win} 净支付：两套分层体系 ROC 对比", fontsize=12)
    ax.legend(loc="lower right",fontsize=10); ax.grid(ls="--",alpha=0.4)
    ax.set_xlim(0,1); ax.set_ylim(0,1)
fig.suptitle("RFMLAP价值层 vs 资产分层(z0-z5) 预测力对比（同一批用户 D=2025-07-27，100万）",fontsize=13,y=1.02)
plt.tight_layout()
plt.savefig(out,dpi=150,bbox_inches="tight")
print(f"[chart] -> {out}")

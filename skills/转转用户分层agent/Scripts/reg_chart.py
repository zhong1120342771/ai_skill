#!/usr/bin/env python3
"""回归验证图：左 McFadden伪R²(付费概率,三套预测变量×两窗口)，右 分层校准(预测vs实际人均GMV365)。
用法: python reg_chart.py <reg_json> <calib_csv> <out_png>
"""
import sys, json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

jf, calib_csv, out = sys.argv[1], sys.argv[2], sys.argv[3]
plt.rcParams["font.sans-serif"]=["Arial Unicode MS","PingFang SC","Heiti SC","STHeiti"]
plt.rcParams["axes.unicode_minus"]=False
res=json.load(open(jf,encoding="utf-8")); calib=pd.read_csv(calib_csv)
fig,axes=plt.subplots(1,2,figsize=(14,5.8))

# 左：McFadden伪R² 分组柱(付费概率)
ax=axes[0]
mf=res["Logistic_McFaddenR2"]
wins=list(mf.keys())  # 7日/365日
sets=list(mf[wins[0]].keys())
x=np.arange(len(wins)); w=0.26
colors=["#1f77b4","#2ca02c","#d62728"]
for i,s in enumerate(sets):
    vals=[mf[win][s] for win in wins]
    b=ax.bar(x+(i-1)*w, vals, w, label=s, color=colors[i])
    for xi,v in zip(x+(i-1)*w,vals): ax.text(xi,v+0.002,f"{v:.3f}",ha="center",fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([w.replace("是否付费","") for w in wins])
ax.set_ylabel("McFadden 伪R²"); ax.set_title("付费概率可解释度：三套预测变量×两窗口\n(伪R²越高=越能解释'会不会付费')",fontsize=11)
ax.legend(fontsize=9); ax.grid(axis="y",ls="--",alpha=0.4)

# 右：分层校准 预测vs实际 人均GMV365
ax=axes[1]
order=["L5","L4","L3","L2","L1"]
c=calib.set_index("层级").reindex(order)
x=np.arange(len(order)); w=0.38
ax.bar(x-w/2, c["实际人均GMV365"], w, label="实际人均GMV", color="#1f77b4")
ax.bar(x+w/2, c["预测人均GMV365"], w, label="OLS预测人均GMV", color="#ff7f0e")
for xi,v in zip(x-w/2,c["实际人均GMV365"]): ax.text(xi,v+150,f"{v:,.0f}",ha="center",fontsize=8)
for xi,v in zip(x+w/2,c["预测人均GMV365"]): ax.text(xi,v+150,f"{v:,.0f}",ha="center",fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(order); ax.set_ylabel("未来365日人均GMV (元)")
ax.set_title("分层校准：OLS预测 vs 实际人均GMV\n(线性模型压不住L5长尾,头部严重低估)",fontsize=11)
ax.legend(fontsize=10); ax.grid(axis="y",ls="--",alpha=0.4)

plt.tight_layout(); plt.savefig(out,dpi=150,bbox_inches="tight")
print(f"[chart] -> {out}")

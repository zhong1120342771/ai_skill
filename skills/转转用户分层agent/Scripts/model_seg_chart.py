#!/usr/bin/env python3
"""模型分层图：左 五特征标准化系数(驱动力)，中 模型层校准(预测概率vs实际付费率)，右 模型层×规则层交叉热力。
用法: python model_seg_chart.py <model_json> <calib_csv> <out_png>
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
fig,axes=plt.subplots(1,3,figsize=(17,5.2))

# 左：标准化系数
ax=axes[0]
coef=res["标准化系数(特征贡献,越大越重要)"]
ks=list(coef.keys()); vs=[coef[k] for k in ks]
cols=["#2ca02c" if v>=0 else "#d62728" for v in vs]
ax.barh(ks[::-1],[coef[k] for k in ks[::-1]],color=cols[::-1])
for i,k in enumerate(ks[::-1]): ax.text(coef[k],i,f" {coef[k]:.3f}",va="center",fontsize=10)
ax.axvline(0,color="#333",lw=0.8)
ax.set_title("五特征标准化系数(付费驱动力)\nA活跃最强,R间隔为负",fontsize=11)
ax.set_xlabel("logistic 标准化系数")

# 中：校准 预测概率 vs 实际付费率
ax=axes[1]
order=["M5","M4","M3","M2","M1"]
c=calib.set_index("模型层").reindex(order)
x=np.arange(len(order)); w=0.38
pcol="预测付费概率均值"; acol=[c for c in calib.columns if c.startswith("实际") and "付费率" in c][0]
ax.bar(x-w/2,c[pcol],w,label="预测付费概率",color="#ff7f0e")
ax.bar(x+w/2,c[acol],w,label="实际付费率",color="#1f77b4")
for xi,v in zip(x-w/2,c[pcol]): ax.text(xi,v+0.01,f"{v:.2f}",ha="center",fontsize=8)
for xi,v in zip(x+w/2,c[acol]): ax.text(xi,v+0.01,f"{v:.2f}",ha="center",fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(order); ax.set_ylabel("概率/付费率")
a_test=res["测试集AUC"]["模型分层(五特征logistic)"]
ax.set_title(f"模型层校准:预测概率≈实际付费率(测试集)\n模型AUC={a_test}",fontsize=11)
ax.legend(fontsize=9); ax.grid(axis="y",ls="--",alpha=0.4)

# 右：模型层×规则层交叉热力
ax=axes[2]
cross=pd.DataFrame(res["模型层vs规则层交叉"]).reindex(index=["M5","M4","M3","M2","M1"],columns=["L5","L4","L3","L2","L1"])
crossp=cross.div(cross.sum(axis=1),axis=0)
im=ax.imshow(crossp.values,cmap="Blues",aspect="auto",vmin=0,vmax=1)
ax.set_xticks(range(5)); ax.set_xticklabels(["L5","L4","L3","L2","L1"])
ax.set_yticks(range(5)); ax.set_yticklabels(["M5","M4","M3","M2","M1"])
ax.set_xlabel("规则分层"); ax.set_ylabel("模型分层")
for i in range(5):
    for j in range(5):
        v=crossp.values[i,j]
        if v>0.005: ax.text(j,i,f"{v*100:.0f}%",ha="center",va="center",fontsize=8,color="white" if v>0.5 else "#333")
ax.set_title("模型层×规则层交叉(行归一)\n对角为主,模型按活跃度再排序",fontsize=11)
fig.colorbar(im,ax=ax,fraction=0.046)

plt.tight_layout(); plt.savefig(out,dpi=150,bbox_inches="tight")
print(f"[chart] -> {out}")

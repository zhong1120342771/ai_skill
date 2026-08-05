#!/usr/bin/env python3
"""两窗口精确度对比图：左 ROC 曲线(带AUC)，右 各层转化率lift对比。
用法: python window_acc_chart.py <roc_csv> <acc_json> <out_png>
"""
import sys, json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

roc_csv, acc_json, out = sys.argv[1], sys.argv[2], sys.argv[3]
plt.rcParams["font.sans-serif"] = ["Arial Unicode MS","PingFang SC","Heiti SC","STHeiti"]
plt.rcParams["axes.unicode_minus"] = False

roc = pd.read_csv(roc_csv)
acc = json.load(open(acc_json, encoding="utf-8"))
fig, axes = plt.subplots(1, 2, figsize=(14,5.8))

# 左：ROC
ax = axes[0]
for win,color in [("7d","#1f77b4"),("365d","#d62728")]:
    r = roc[roc.window==win].sort_values("fpr")
    auc = acc[win]["AUC"]
    ax.plot(r.fpr, r.tpr, color=color, lw=2.2, label=f"{win}  AUC={auc:.4f}")
ax.plot([0,1],[0,1],"--",color="#999",lw=1)
ax.set_xlabel("假正率 FPR"); ax.set_ylabel("真正率 TPR")
ax.set_title("ROC 曲线：分层打分对两窗口净支付的判别力\n(同一批用户 D=2025-07-27，AUC基率无关可公平比)", fontsize=12)
ax.legend(loc="lower right", fontsize=11); ax.grid(ls="--", alpha=0.4)
ax.set_xlim(0,1); ax.set_ylim(0,1)

# 右：各层转化率(双窗口)+ 相对lift
ax = axes[1]
order = ["L5","L4","L3","L2","L1"]
r7 = [acc["7d"]["各层转化率"][t]*100 for t in order]
r365 = [acc["365d"]["各层转化率"][t]*100 for t in order]
x = np.arange(len(order)); w=0.38
ax.bar(x-w/2, r7, w, label=f"7日 (base {acc['7d']['base_rate']*100:.2f}%)", color="#1f77b4")
ax.bar(x+w/2, r365, w, label=f"365日 (base {acc['365d']['base_rate']*100:.2f}%)", color="#d62728")
for xi,v in zip(x,r7): ax.text(xi-w/2, v+0.6, f"{v:.1f}", ha="center", fontsize=8)
for xi,v in zip(x,r365): ax.text(xi+w/2, v+0.6, f"{v:.1f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(order); ax.set_ylabel("净支付转化率 (%)")
lift7=acc["7d"]["L5_lift(倍)"]; lift365=acc["365d"]["L5_lift(倍)"]
ax.set_title(f"各层净支付转化率：7日 vs 365日\nL5相对全量lift：7日 {lift7}× / 365日 {lift365}×", fontsize=12)
ax.legend(fontsize=10); ax.grid(axis="y", ls="--", alpha=0.4)

plt.tight_layout()
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"[chart] -> {out}")

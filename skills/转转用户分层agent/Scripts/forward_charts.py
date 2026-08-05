#!/usr/bin/env python3
"""分层×7日转化 与 分层×一年LTV 两张图。
用法: python forward_charts.py <tier_7d_csv> <tier_1y_csv> <out_png>
"""
import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

c7, c1, out = sys.argv[1], sys.argv[2], sys.argv[3]
plt.rcParams["font.sans-serif"] = ["Arial Unicode MS","PingFang SC","Heiti SC","STHeiti"]
plt.rcParams["axes.unicode_minus"] = False

d7 = pd.read_csv(c7); d1 = pd.read_csv(c1)
d7 = d7[d7["层级"]!="全量"]; d1 = d1[d1["层级"]!="全量"]
order = ["L5","L4","L3","L2","L1"]
d7 = d7.set_index("层级").reindex(order); d1 = d1.set_index("层级").reindex(order)

fig, axes = plt.subplots(1, 2, figsize=(14,5.5))
x = np.arange(len(order)); colors = plt.cm.viridis(np.linspace(0.15,0.9,len(order)))

# 左：7日净支付转化率
ax = axes[0]
conv7 = d7["活跃后7日内净支付转化率"].to_numpy()*100
b = ax.bar(x, conv7, color=colors, edgecolor="k", lw=0.5)
for xi,v in zip(x,conv7): ax.text(xi, v+0.15, f"{v:.2f}%", ha="center", fontsize=10, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(order); ax.set_ylabel("活跃后7日内净支付转化率 (%)")
ax.set_title("分层 × 活跃后7日内净支付转化率 (D=2026-07-27)", fontsize=12)
ax.grid(axis="y", ls="--", alpha=0.4)

# 右：一年LTV(人均GMV) + 一年转化率(折线)
ax = axes[1]
ltv = d1["人均GMV(LTV,元)"].to_numpy()
b = ax.bar(x, ltv, color=colors, edgecolor="k", lw=0.5)
for xi,v in zip(x,ltv): ax.text(xi, v+ltv.max()*0.02, f"{v:,.0f}", ha="center", fontsize=10, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(order); ax.set_ylabel("未来一年人均GMV / LTV (元)")
ax.set_title("分层 × 未来一年LTV与净支付转化率 (D=2025-07-27)", fontsize=12)
ax.grid(axis="y", ls="--", alpha=0.4)
ax2 = ax.twinx()
conv1 = d1["未来一年净支付转化率"].to_numpy()*100
ax2.plot(x, conv1, "o-", color="#d62728", lw=2, label="一年净支付转化率")
for xi,v in zip(x,conv1): ax2.text(xi, v+1.5, f"{v:.1f}%", ha="center", fontsize=9, color="#d62728")
ax2.set_ylabel("未来一年净支付转化率 (%)", color="#d62728")
ax2.tick_params(axis="y", labelcolor="#d62728")

plt.tight_layout()
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"[charts] -> {out}")

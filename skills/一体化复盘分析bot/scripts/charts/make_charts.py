# -*- coding: utf-8 -*-
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter

# ---------- 中文字体 ----------
CJK_CANDIDATES = ["PingFang SC", "Heiti SC", "Arial Unicode MS", "SimHei", "STHeiti"]
available = {f.name for f in font_manager.fontManager.ttflist}
chosen = next((f for f in CJK_CANDIDATES if f in available), None)
if chosen is None:
    # 尝试按路径直接注册 PingFang
    for p in ["/System/Library/Fonts/PingFang.ttc",
              "/System/Library/Fonts/STHeiti Medium.ttc",
              "/Library/Fonts/Arial Unicode.ttf"]:
        if os.path.exists(p):
            font_manager.fontManager.addfont(p)
            chosen = font_manager.FontProperties(fname=p).get_name()
            break
plt.rcParams["font.sans-serif"] = [chosen] + CJK_CANDIDATES if chosen else CJK_CANDIDATES
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 160
print("Using font:", chosen)

DATA = os.path.expanduser("~/.claude/data_storage/h1_review")
OUT = os.path.expanduser("~/.claude/visualizations/yiti_h1_review")

# ---------- 配色 ----------
C_PILOT = "#C0392B"   # 试点 深红
C_CTRL  = "#7F8C8D"   # 对照 灰
C_OTHER = "#2E86C1"   # 其他一体化 蓝
C_BAR   = "#5DADE2"
C_BAR2  = "#48C9B0"
C_LINE  = "#E67E22"

def mlabel(m):  # 2026-06 -> 6月
    return f"{int(m.split('-')[1])}月"

def pct_fmt(x, _):
    return f"{x:.0f}%"

def annotate_last(ax, xs, ys, txt, color, dy=6, ha="center"):
    ax.annotate(txt, (xs, ys), textcoords="offset points", xytext=(0, dy),
                ha=ha, fontsize=10, fontweight="bold", color=color)

# ============================================================
# fig1 同城订单占比月度趋势
# ============================================================
df = pd.read_csv(os.path.join(DATA, "q1_tongcheng_monthly.csv"))
df["grp"] = df["grp"].replace({"试点城市(蓉郑)":"试点城市(郑州&成都)","对照城市(渝西)":"对照城市(重庆&西安)"})
df["m"] = df["month"].map(mlabel)
order = ["2026-01","2026-02","2026-03","2026-04","2026-05","2026-06"]
labels = [mlabel(m) for m in order]

fig, ax = plt.subplots(figsize=(10, 6))
series = [
    ("试点城市(郑州&成都)", C_PILOT, "o", 2.6),
    ("对照城市(重庆&西安)", C_CTRL, "s", 1.8),
    ("其他一体化城市", C_OTHER, "^", 1.8),
]
for grp, col, mk, lw in series:
    sub = df[df["grp"] == grp].set_index("month").reindex(order)
    ax.plot(labels, sub["同城占比_pct"], marker=mk, color=col, lw=lw,
            markersize=7, label=grp)
    v0, v1 = sub["同城占比_pct"].iloc[0], sub["同城占比_pct"].iloc[-1]
    annotate_last(ax, labels[-1], v1, f"{v1:.2f}%", col,
                  dy=8 if grp != "对照城市(重庆&西安)" else -16)
    if grp == "试点城市(郑州&成都)":
        annotate_last(ax, labels[0], v0, f"{v0:.2f}%", col, dy=-16)
        ax.annotate(f"爬坡 +{v1-v0:.2f}pp", (labels[3], 26.5), color=C_PILOT,
                    fontsize=11, fontweight="bold")
    if grp == "对照城市(重庆&西安)":
        annotate_last(ax, labels[0], v0, f"{v0:.2f}%", col, dy=8)

# 标注春节/618
ax.axvline(labels[1], color="#BDC3C7", ls="--", lw=1)
ax.text(labels[1], 14, "春节", color="#95A5A6", fontsize=9, ha="center")
ax.axvline(labels[5], color="#BDC3C7", ls="--", lw=1)
ax.text(labels[5], 14, "618", color="#95A5A6", fontsize=9, ha="center")

ax.set_title("同城订单占比月度趋势（试点 vs 对照 vs 其他一体化）\n本地需求被激发 · 试点显著爬坡", fontsize=14, fontweight="bold")
ax.set_ylabel("同城订单占比"); ax.set_xlabel("2026 年")
ax.yaxis.set_major_formatter(FuncFormatter(pct_fmt))
ax.set_ylim(0, 32)
ax.legend(loc="center left", frameon=False)
ax.grid(axis="y", ls=":", alpha=0.4)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig1_tongcheng_share_trend.png"), bbox_inches="tight")
plt.close(fig)

# ============================================================
# fig2 试点城市同城占比 2025 vs 2026 同比
# ============================================================
yoy = pd.read_csv(os.path.join(DATA, "q1_tongcheng_yoy.csv"),
                  dtype={"month": str})
yoy["grp"] = yoy["grp"].replace({"试点城市(蓉郑)":"试点城市(郑州&成都)","对照城市(渝西)":"对照城市(重庆&西安)"})
pilot = yoy[yoy["grp"] == "试点城市(郑州&成都)"].copy()
pilot["mnum"] = pilot["month"].astype(int)
xlab = [f"{i}月" for i in range(1, 7)]

fig, ax = plt.subplots(figsize=(10, 6))
for yr, col, mk in [(2025, C_CTRL, "s"), (2026, C_PILOT, "o")]:
    sub = pilot[pilot["year"] == yr].sort_values("mnum")
    ax.plot(xlab, sub["同城占比_pct"], marker=mk, color=col, lw=2.4,
            markersize=8, label=f"{yr} 年")
    v0, v1 = sub["同城占比_pct"].iloc[0], sub["同城占比_pct"].iloc[-1]
    annotate_last(ax, xlab[-1], v1, f"{v1:.2f}%", col, dy=8)
    annotate_last(ax, xlab[0], v0, f"{v0:.2f}%", col, dy=-16)

ax.set_title("试点城市(郑州&成都) 同城订单占比：2025 vs 2026 同比\n2025 平坦 · 2026 才爬坡（项目效应，非季节）", fontsize=14, fontweight="bold")
ax.set_ylabel("同城订单占比"); ax.set_xlabel("月份")
ax.yaxis.set_major_formatter(FuncFormatter(pct_fmt))
ax.set_ylim(15, 31)
ax.legend(loc="upper left", frameon=False)
ax.grid(axis="y", ls=":", alpha=0.4)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig2_tongcheng_yoy.png"), bbox_inches="tight")
plt.close(fig)

# ============================================================
# fig3 同城订单量绝对值（试点 + 其他一体化叠加）
# ============================================================
fig, ax = plt.subplots(figsize=(10, 6))
pilot_v = df[df["grp"] == "试点城市(郑州&成都)"].set_index("month").reindex(order)["同城订单量"]
other_v = df[df["grp"] == "其他一体化城市"].set_index("month").reindex(order)["同城订单量"]
x = np.arange(len(order))
ax.bar(x, pilot_v.values, color=C_PILOT, label="试点城市(郑州&成都)", zorder=3)
ax.bar(x, other_v.values, bottom=pilot_v.values, color=C_OTHER, alpha=0.55,
       label="其他一体化城市", zorder=2)
ax.set_xticks(x); ax.set_xticklabels(labels)
for xi, v in zip(x, pilot_v.values):
    ax.text(xi, v/2, f"{int(v):,}", ha="center", va="center", color="white",
            fontsize=9, fontweight="bold")
p0, p1 = pilot_v.iloc[0], pilot_v.iloc[-1]
ax.annotate(f"试点 {int(p0):,} → {int(p1):,}  (+{(p1/p0-1)*100:.0f}%)",
            (x[2], max((pilot_v+other_v).values)*0.95), color=C_PILOT,
            fontsize=11, fontweight="bold")
ax.set_title("同城订单量（绝对值）月度\n试点城市量级增长", fontsize=14, fontweight="bold")
ax.set_ylabel("同城订单量"); ax.set_xlabel("2026 年")
ax.get_yaxis().set_major_formatter(FuncFormatter(lambda v, _: f"{int(v/1000)}k"))
ax.legend(loc="upper left", frameon=False)
ax.grid(axis="y", ls=":", alpha=0.4)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig3_tongcheng_volume.png"), bbox_inches="tight")
plt.close(fig)

# ============================================================
# fig4 小时达订单量月度
# ============================================================
xsd = pd.read_csv(os.path.join(DATA, "q1_xiaoshida_monthly.csv"))
xsd["m"] = xsd["month"].map(mlabel)
fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.bar(xsd["m"], xsd["小时达订单量"], color=C_BAR, zorder=3)
for b, v in zip(bars, xsd["小时达订单量"]):
    ax.text(b.get_x()+b.get_width()/2, v, f"{int(v):,}", ha="center",
            va="bottom", fontsize=10, fontweight="bold", color="#1B4F72")
v0, v1 = xsd["小时达订单量"].iloc[0], xsd["小时达订单量"].iloc[-1]
ax.annotate(f"{int(v0):,} → {int(v1):,}  (×{v1/v0:.0f})", (0.5, v1*0.9),
            color=C_BAR, fontsize=12, fontweight="bold")
ax.set_title("小时达订单量月度趋势\n一期新能力：从 0 到规模化", fontsize=14, fontweight="bold")
ax.set_ylabel("小时达订单量"); ax.set_xlabel("2026 年")
ax.grid(axis="y", ls=":", alpha=0.4)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig4_xiaoshida_trend.png"), bbox_inches="tight")
plt.close(fig)

# ============================================================
# fig5 线索量 + 转化率 组合图
# ============================================================
xs = pd.read_csv(os.path.join(DATA, "q2_xiansuo_monthly.csv"))
xs["m"] = xs["month"].map(mlabel)
fig, ax1 = plt.subplots(figsize=(10, 6))
bars = ax1.bar(xs["m"], xs["线索量"], color=C_BAR, alpha=0.85, zorder=2, label="线索量")
for b, v in zip(bars, xs["线索量"]):
    ax1.text(b.get_x()+b.get_width()/2, v, f"{int(v):,}", ha="center",
             va="bottom", fontsize=9, color="#1B4F72")
ax1.set_ylabel("线索量", color="#1B4F72"); ax1.set_xlabel("2026 年")
ax1.set_ylim(0, xs["线索量"].max()*1.2)

ax2 = ax1.twinx()
ax2.plot(xs["m"], xs["转化率_pct"], marker="o", color=C_LINE, lw=2.6,
         markersize=8, label="转化率", zorder=3)
for xi, v in zip(range(len(xs)), xs["转化率_pct"]):
    ax2.annotate(f"{v:.2f}%", (xi, v), textcoords="offset points",
                 xytext=(0, 8), ha="center", fontsize=9, fontweight="bold", color=C_LINE)
ax2.set_ylabel("转化率", color=C_LINE)
ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax2.set_ylim(0, 8)
c0, c1 = xs["转化率_pct"].iloc[1], xs["转化率_pct"].iloc[-1]
ax2.annotate(f"转化率被稀释 {c0:.2f}%→{c1:.2f}%", (2.3, 7.2), color=C_LINE,
             fontsize=10, fontweight="bold")

l1, lab1 = ax1.get_legend_handles_labels()
l2, lab2 = ax2.get_legend_handles_labels()
ax1.legend(l1+l2, lab1+lab2, loc="upper left", frameon=False)
ax1.set_title("线索量 vs 转化率月度\n线索放量、转化率被稀释", fontsize=14, fontweight="bold")
ax1.grid(axis="y", ls=":", alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig5_xiansuo_trend.png"), bbox_inches="tight")
plt.close(fig)

# ============================================================
# fig6 pro店 同售单量 + 动销率 组合图
# ============================================================
ts = pd.read_csv(os.path.join(DATA, "q3_tongshou_pro_xiaodian_monthly.csv"))
pro = ts[ts["type"] == "pro店"].copy()
pro["m"] = pro["month"].map(mlabel)
fig, ax1 = plt.subplots(figsize=(10, 6))
bars = ax1.bar(pro["m"], pro["同售单量"], color=C_BAR2, alpha=0.9, zorder=2, label="同售单量")
for b, v in zip(bars, pro["同售单量"]):
    ax1.text(b.get_x()+b.get_width()/2, v, f"{int(v):,}", ha="center",
             va="bottom", fontsize=9, color="#0E6655")
ax1.set_ylabel("同售单量", color="#0E6655"); ax1.set_xlabel("2026 年")
ax1.set_ylim(0, pro["同售单量"].max()*1.25)

ax2 = ax1.twinx()
ax2.plot(pro["m"], pro["动销率_pct"], marker="o", color=C_PILOT, lw=2.6,
         markersize=8, label="动销率", zorder=3)
for xi, v in zip(range(len(pro)), pro["动销率_pct"]):
    ax2.annotate(f"{v:.2f}%", (xi, v), textcoords="offset points",
                 xytext=(0, 9), ha="center", fontsize=9, fontweight="bold", color=C_PILOT)
ax2.set_ylabel("动销率", color=C_PILOT)
ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax2.set_ylim(0, 10)
# 4-5月加速点标注
ax1.axvspan(2.5, 4.5, color="#F9E79F", alpha=0.3, zorder=0)
ax1.annotate("4-5月加速\n(二期新仓店)", (3.5, pro["同售单量"].max()*1.12),
             color="#B7950B", fontsize=10, fontweight="bold", ha="center")
d0, d1 = pro["动销率_pct"].iloc[0], pro["动销率_pct"].iloc[-1]
q0, q1 = pro["同售单量"].iloc[0], pro["同售单量"].iloc[-1]

l1, lab1 = ax1.get_legend_handles_labels()
l2, lab2 = ax2.get_legend_handles_labels()
ax1.legend(l1+l2, lab1+lab2, loc="upper left", frameon=False)
ax1.set_title(f"pro店 同售单量 & 动销率月度\n单量 {int(q0):,}→{int(q1):,} · 动销率 {d0:.2f}%→{d1:.2f}%", fontsize=14, fontweight="bold")
ax1.grid(axis="y", ls=":", alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig6_pro_tongshou_trend.png"), bbox_inches="tight")
plt.close(fig)

# ============================================================
# fig7 小店同售动销率 DiD 三档城市
# ============================================================
city = pd.read_csv(os.path.join(DATA, "q2_xiaodian_tongshou_by_city.csv"))
city["m"] = city["month"].map(mlabel)
fig, ax = plt.subplots(figsize=(10, 6))
cseries = [
    ("一体化覆盖城市（小店）", C_PILOT, "o"),
    ("对照城市（重庆&西安）", C_CTRL, "s"),
    ("其他城市", C_OTHER, "^"),
]
for grp, col, mk in cseries:
    sub = city[city["grp"] == grp].set_index("month").reindex(order)
    ax.plot(labels, sub["动销率_pct"], marker=mk, color=col, lw=2.2,
            markersize=7, label=grp)
    v0, v1 = sub["动销率_pct"].iloc[0], sub["动销率_pct"].iloc[-1]
    annotate_last(ax, labels[-1], v1, f"{v1:.2f}%", col, dy=8)
    if grp in ("一体化覆盖城市（小店）", "对照城市（重庆&西安）"):
        annotate_last(ax, labels[0], v0, f"{v0:.2f}%", col,
                      dy=-16 if grp.startswith("对照") else 8)

# DiD 净效应
cov = city[city["grp"] == "一体化覆盖城市（小店）"].set_index("month").reindex(order)["动销率_pct"]
ctl = city[city["grp"] == "对照城市（重庆&西安）"].set_index("month").reindex(order)["动销率_pct"]
did = (cov.iloc[-1]-cov.iloc[0]) - (ctl.iloc[-1]-ctl.iloc[0])
ax.annotate(f"DiD 净效应 +{did:.2f}pp\n(覆盖 {cov.iloc[0]:.2f}→{cov.iloc[-1]:.2f} vs 对照 {ctl.iloc[0]:.2f}→{ctl.iloc[-1]:.2f})",
            (labels[1], 6.0), color=C_PILOT, fontsize=10.5, fontweight="bold")
ax.set_title("小店同售动销率月度：城市三档对比（DiD）\n一体化覆盖跑赢对照", fontsize=14, fontweight="bold")
ax.set_ylabel("动销率"); ax.set_xlabel("2026 年")
ax.set_ylim(3, 6.5)
ax.set_yticks([3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5])
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.1f}%"))
ax.legend(loc="lower right", frameon=False)
ax.grid(axis="y", ls=":", alpha=0.4)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig7_xiaodian_tongshou_did.png"), bbox_inches="tight")
plt.close(fig)

print("DONE")

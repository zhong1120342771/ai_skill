"""case 影响评估 — 绘图脚本模板
生成 3 张标准图：①DiD转化率对照 ②多口径成单损失区间 ③用户体验暴露漏斗。
用法：改数据源与 loss/methods 数值（从 case_impact_analysis.py 输出取）后运行。
图存到 visualizations/<case名>/，中文字体 Arial Unicode MS。
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from pathlib import Path

matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang HK', 'STHeiti']
matplotlib.rcParams['axes.unicode_minus'] = False

OUT = Path.home() / '.claude' / 'visualizations' / 'model_filter_case'
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_excel(Path.home() / 'Downloads' / '机型筛选case评估.xlsx')
df['日期'] = pd.to_datetime(df['日期'])
BS, BE = pd.Timestamp('2026-05-27'), pd.Timestamp('2026-07-11')

def per(d):
    if d < BS: return '故障前'
    if d <= BE: return '故障窗'
    return '修复后'
df['期'] = df['日期'].apply(per)

def r(d, pg, cat, end):
    s = d[(d.页面 == pg) & (d.品类类目 == cat) & (d.端 == end)]
    c = s['点击机型筛选的用户'].sum(); o = s['订单量'].sum()
    return (o / c) if c else 0

BLUE, ORANGE, GRAY, RED, GREEN = '#2E5C8A', '#E8833A', '#9AA5B1', '#C0392B', '#27AE60'

# ---------- 图1: G1004 前/中 人均单量 对照 (DiD视觉) ----------
fig, ax = plt.subplots(figsize=(9, 5.2))
groups = ['故障前', '故障窗']
and_other = [r(df[df.期 == g], 'G1004', '手机外的其他类目', 'android') for g in groups]
ios_other = [r(df[df.期 == g], 'G1004', '手机外的其他类目', 'iOS') for g in groups]
and_phone = [r(df[df.期 == g], 'G1004', '手机', 'android') for g in groups]
x = range(len(groups)); w = 0.2
ax.bar([i - 1.5*w for i in x], and_other, w, label='Android·手机外(受影响)', color=RED)
ax.bar([i - 0.5*w for i in x], and_phone, w, label='Android·手机(干净对照)', color=BLUE)
ax.bar([i + 0.5*w for i in x], ios_other, w, label='iOS·手机外(跨端对照)', color=ORANGE)
for i in x:
    ax.text(i-1.5*w, and_other[i]+0.0004, f'{and_other[i]:.4f}', ha='center', fontsize=8)
    ax.text(i-0.5*w, and_phone[i]+0.0004, f'{and_phone[i]:.4f}', ha='center', fontsize=8)
    ax.text(i+0.5*w, ios_other[i]+0.0004, f'{ios_other[i]:.4f}', ha='center', fontsize=8)
ax.set_xticks(list(x)); ax.set_xticklabels(groups)
ax.set_ylabel('人均单量 (订单/点击型号用户)')
ax.set_title('G1004 型号点击用户人均单量：受影响组 vs 两组对照\n受影响组故障窗不降反升 → 无可测量成单损失', fontsize=12)
ax.legend(fontsize=9); ax.grid(axis='y', alpha=0.3)
plt.tight_layout(); plt.savefig(OUT / '01_did_conversion.png', dpi=150); plt.close()

# ---------- 图2: 成单损失反事实区间 ----------
fig, ax = plt.subplots(figsize=(9, 4.8))
methods = ['G1004\n跨端DiD', 'G1004\n时间DiD(iOS)', 'G1004\n时间DiD(手机)', 'G1003\n跨端(小样本)']
loss = [-249.6, -290.8, -46.9, 37.5]
colors = [GREEN if v <= 0 else ORANGE for v in loss]
bars = ax.bar(methods, loss, color=colors, width=0.6)
for b, v in zip(bars, loss):
    ax.text(b.get_x()+b.get_width()/2, v + (6 if v >= 0 else -14),
            f'{v:+.0f}单', ha='center', fontsize=10, fontweight='bold')
ax.axhline(0, color='black', lw=1)
ax.set_ylabel('反事实成单损失估计 (单 / 整个45天窗口)')
ax.set_title('多口径反事实成单损失：负值=实际≥预期(无损失)\nG1004三法一致无损失；G1003名义+37单但对照仅34单不可靠', fontsize=12)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout(); plt.savefig(OUT / '02_order_loss_range.png', dpi=150); plt.close()

# ---------- 图3: 用户体验暴露漏斗 ----------
fig, ax = plt.subplots(figsize=(9, 5))
labels = ['候选点击上界\n(案例权威去重UV)', '手机外类目折算\n(受损风险UV)', '实际看到空结果\n(不可精确统计)']
vals = [97753, 50453, None]
ypos = [2, 1, 0]
ax.barh(2, 97753, color=GRAY, height=0.55)
ax.barh(1, 50453, color=ORANGE, height=0.55)
ax.barh(0, 50453, color='none', edgecolor=RED, height=0.55, hatch='///', linewidth=1.5)
ax.text(97753+900, 2, '97,753 UV / 654,727 PV', va='center', fontsize=10, fontweight='bold')
ax.text(50453+900, 1, '≈50,453 UV / ≈337,921 PV (手机外占51.6%)', va='center', fontsize=10)
ax.text(1500, 0, '≤ 上方，受"地址是否命中同城"进一步收窄，无日志不可测', va='center', fontsize=9, color=RED)
ax.set_yticks(ypos); ax.set_yticklabels(labels, fontsize=9)
ax.set_xlim(0, 130000)
ax.set_xlabel('去重设备 UV')
ax.set_title('用户体验受损暴露量：候选上界 → 手机外折算 → 实际不可测\n故障持续45.7天，日均约2,125 UV点击型号', fontsize=12)
ax.grid(axis='x', alpha=0.3)
plt.tight_layout(); plt.savefig(OUT / '03_ux_funnel.png', dpi=150); plt.close()

print('done:', list(OUT.glob('*.png')))

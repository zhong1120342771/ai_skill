# -*- coding: utf-8 -*-
"""
九宫格下线 D+12 可视化 (含 618 大促当天)

业务背景:
- xcx-九宫格 渠道 2026-06-10 下线
- D+5 (6.10-6.15) 已做 DiD 分析，留下 "618 当天承接能力未知" 待解
- 本脚本基于 D+12 (6.10-6.21) 数据，含 618 当天 6.18

输入:
- /Users/zhongmengting/.claude/data_storage/jgg_offline_0622/raw_belong02.xlsx  (2026-05/06)
- /Users/zhongmengting/.claude/data_storage/jgg_offline_0622/xprog_2025_dapan.xlsx (2025-06 同期, 拆分端=转转小程序口径=小程序大盘)
- /Users/zhongmengting/.claude/data_storage/jgg_offline_0622/did_summary_d12.csv (若存在，优先使用)

口径:
- 小程序大盘 = 转转小程序 + xcx-九宫格 (下线后实际近似 = 转转小程序)
- 2025 同期对照: 拆分端=转转小程序 (彼时 wd=转转小程序 就是大盘汇总, 经核对与 yoy_daily_compare.csv 一致)

输出:
- /Users/zhongmengting/.claude/visualizations/jgg_offline_0622/yoy_dau_d12.png
- /Users/zhongmengting/.claude/visualizations/jgg_offline_0622/yoy_net_payment_d12.png
- /Users/zhongmengting/.claude/visualizations/jgg_offline_0622/d618_funnel_compare.png
- /Users/zhongmengting/.claude/visualizations/jgg_offline_0622/d5_vs_d12_correction.png
"""

import os
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti TC', 'Arial Unicode MS',
                                   'STHeiti', 'Hiragino Sans GB', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 150

DATA_DIR = '/Users/zhongmengting/.claude/data_storage/jgg_offline_0622'
OUT_DIR = '/Users/zhongmengting/.claude/visualizations/jgg_offline_0622'
RAW_26 = os.path.join(DATA_DIR, 'raw_belong02.xlsx')
RAW_25 = os.path.join(DATA_DIR, 'xprog_2025_dapan.xlsx')
DID_SUMMARY_D12 = os.path.join(DATA_DIR, 'did_summary_d12.csv')

os.makedirs(OUT_DIR, exist_ok=True)

# -------- 颜色 / 样式 --------
COLOR_25 = '#5B9BD5'    # 浅蓝色 - 2025 同期对照
COLOR_26 = '#C0504D'    # 深红色 - 2026 实际
COLOR_JGG_LINE = '#D62728'   # 红色虚线 - 九宫格下线日 6.10
COLOR_618_LINE = '#FF7F0E'   # 橙色虚线 - 618 大促 6.18

# -------- 1. 加载 & 聚合 --------

def load_dapan_26():
    """2026 小程序大盘 = 转转小程序 + xcx-九宫格 按 dt 聚合."""
    df = pd.read_excel(RAW_26)
    df = df[df['wd'].isin(['转转小程序', 'xcx-九宫格'])].copy()
    df['dt'] = df['dt'].astype(str)
    num_cols = ['exp_pv', 'exp_uv', 'detail_pv', 'detail_uv',
                'order_pv', 'order_uv', 'pay_pv', 'uv_all']
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    agg = df.groupby('dt', as_index=False)[num_cols].sum()
    agg['date'] = pd.to_datetime(agg['dt'])
    return agg.sort_values('date').reset_index(drop=True)


def load_dapan_25():
    """2025 小程序大盘 - 拆分端口径下 wd=转转小程序 即为大盘."""
    df = pd.read_excel(RAW_25)
    df['dt'] = df['dt'].astype(str)
    num_cols = ['exp_pv', 'exp_uv', 'detail_pv', 'detail_uv',
                'order_pv', 'order_uv', 'pay_pv', 'uv_all']
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df['date'] = pd.to_datetime(df['dt'])
    return df[['date', 'dt'] + num_cols].sort_values('date').reset_index(drop=True)


df26 = load_dapan_26()
df25 = load_dapan_25()

df26_win = df26[(df26['date'] >= '2026-06-01') & (df26['date'] <= '2026-06-21')].copy()
df25_win = df25[(df25['date'] >= '2025-06-01') & (df25['date'] <= '2025-06-21')].copy()
# 25 年的日期搬到 26 年位置，便于同图比较
df25_win['date_for_plot'] = df25_win['date'] + pd.DateOffset(years=1)


# -------- 2. 图 1/2: 25 vs 26 折线 --------

def plot_yoy_line(metric_col, title, ylabel, fname):
    fig, ax = plt.subplots(figsize=(12, 5.6))

    ax.plot(df25_win['date_for_plot'], df25_win[metric_col],
            marker='o', markersize=5.5, linewidth=2.0,
            color=COLOR_25, label='2025 同期')
    ax.plot(df26_win['date'], df26_win[metric_col],
            marker='^', markersize=6.5, linewidth=2.0,
            color=COLOR_26, label='2026 实际')

    jgg_date = pd.Timestamp('2026-06-10')
    d618 = pd.Timestamp('2026-06-18')
    ax.axvline(jgg_date, color=COLOR_JGG_LINE, linestyle='--',
               linewidth=1.8, alpha=0.85, zorder=0)
    ax.axvline(d618, color=COLOR_618_LINE, linestyle='--',
               linewidth=1.8, alpha=0.85, zorder=0)

    ymin, ymax = ax.get_ylim()
    y_text_top = ymin + (ymax - ymin) * 0.965
    y_text_bot = ymin + (ymax - ymin) * 0.905
    ax.text(jgg_date + pd.Timedelta(hours=4), y_text_top,
            '6/10 九宫格下线',
            color=COLOR_JGG_LINE, fontsize=10.5, fontweight='bold',
            ha='left', va='top')
    ax.text(d618 + pd.Timedelta(hours=4), y_text_bot,
            '6/18 618 大促',
            color=COLOR_618_LINE, fontsize=10.5, fontweight='bold',
            ha='left', va='top')

    ax.set_title(title, fontsize=14, fontweight='bold', pad=12)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_xlabel('日期 (6.1 - 6.21)', fontsize=11)
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0)
    ax.grid(True, linestyle=':', alpha=0.4)
    ax.legend(loc='lower left', frameon=True, framealpha=0.92, fontsize=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x):,}'))

    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, fname)
    plt.savefig(out_path, bbox_inches='tight')
    plt.close(fig)
    return out_path


print('==> 1. yoy_dau_d12.png')
p1 = plot_yoy_line('uv_all', 'DAU 25 vs 26 同期对比 (小程序大盘)', 'DAU', 'yoy_dau_d12.png')
print('  ', p1)

print('==> 2. yoy_net_payment_d12.png')
p2 = plot_yoy_line('pay_pv', '净支付 PV 25 vs 26 同期对比 (小程序大盘)',
                   '净支付 PV', 'yoy_net_payment_d12.png')
print('  ', p2)


# -------- 3. 图 3: 618 当天双年漏斗对比柱状图 --------

print('==> 3. d618_funnel_compare.png')

# 取 6.18 单日值
row25 = df25_win[df25_win['date'] == pd.Timestamp('2025-06-18')].iloc[0]
row26 = df26_win[df26_win['date'] == pd.Timestamp('2026-06-18')].iloc[0]

funnel_metrics = [
    ('曝光 UV', 'exp_uv'),
    ('商详 UV', 'detail_uv'),
    ('下单 UV', 'order_uv'),
    ('净支付 PV', 'pay_pv'),
]

labels = [m[0] for m in funnel_metrics]
vals25 = [float(row25[m[1]]) for m in funnel_metrics]
vals26 = [float(row26[m[1]]) for m in funnel_metrics]
yoy_pct = [(v26 - v25) / v25 * 100 for v25, v26 in zip(vals25, vals26)]

fig, ax = plt.subplots(figsize=(11, 6.2))
x = np.arange(len(labels))
w = 0.36

b1 = ax.bar(x - w / 2, vals25, w, color=COLOR_25, label='2025-06-18', edgecolor='white', linewidth=0.5)
b2 = ax.bar(x + w / 2, vals26, w, color=COLOR_26, label='2026-06-18', edgecolor='white', linewidth=0.5)

ax.set_yscale('log')
ax.set_ylabel('数量 (对数轴)', fontsize=11)
ax.set_title('618 大促当天 25 vs 26 漏斗对比 (小程序大盘)',
             fontsize=14, fontweight='bold', pad=12)
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=11)
ax.legend(loc='upper right', frameon=True, framealpha=0.92, fontsize=10)
ax.grid(True, axis='y', linestyle=':', alpha=0.4, which='both')

# 柱顶数字 (绝对值)
for bar, v in zip(b1, vals25):
    ax.text(bar.get_x() + bar.get_width() / 2, v * 1.05, f'{int(v):,}',
            ha='center', va='bottom', fontsize=9, color=COLOR_25, fontweight='bold')
for bar, v in zip(b2, vals26):
    ax.text(bar.get_x() + bar.get_width() / 2, v * 1.05, f'{int(v):,}',
            ha='center', va='bottom', fontsize=9, color=COLOR_26, fontweight='bold')

# YoY 百分比放在中间高一点位置
for xi, (v25, v26, pct) in enumerate(zip(vals25, vals26, yoy_pct)):
    top = max(v25, v26)
    color = '#2E7D32' if pct >= 0 else '#C62828'
    sign = '+' if pct >= 0 else ''
    ax.text(xi, top * 1.55, f'YoY {sign}{pct:.1f}%',
            ha='center', va='bottom',
            fontsize=11, fontweight='bold', color=color,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                      edgecolor=color, linewidth=1))

# 扩大上方空间
ymin, ymax = ax.get_ylim()
ax.set_ylim(ymin, ymax * 4)

plt.tight_layout()
p3 = os.path.join(OUT_DIR, 'd618_funnel_compare.png')
plt.savefig(p3, bbox_inches='tight')
plt.close(fig)
print('  ', p3)


# -------- 4. 图 4: D+5 vs D+12 真实损失对比柱状图 --------

print('==> 4. d5_vs_d12_correction.png')


def compute_did_d12_from_raw():
    """从 raw 数据自行计算 D+12 DiD 真实净效应."""
    abs_metrics = ['uv_all', 'detail_uv', 'pay_pv']

    def period_means(df):
        df = df.copy()
        df['mmdd'] = df['date'].dt.strftime('%m-%d')
        pre = df[(df['mmdd'] >= '06-01') & (df['mmdd'] <= '06-09')][abs_metrics].mean()
        post = df[(df['mmdd'] >= '06-10') & (df['mmdd'] <= '06-21')][abs_metrics].mean()
        return pre, post

    pre25, post25 = period_means(df25_win)
    pre26, post26 = period_means(df26_win)

    out = {}
    for m in abs_metrics:
        rate25 = (post25[m] - pre25[m]) / pre25[m]
        cf26 = pre26[m] * (1 + rate25)
        real_gap_pct = (post26[m] - cf26) / cf26 * 100
        out[m] = real_gap_pct

    # 净支付转化率: 用 pay_pv / uv_all 计算每天比率, 再求期段均值
    def rate_period_means(df):
        df = df.copy()
        df['mmdd'] = df['date'].dt.strftime('%m-%d')
        df['rate'] = df['pay_pv'] / df['uv_all']
        pre = df[(df['mmdd'] >= '06-01') & (df['mmdd'] <= '06-09')]['rate'].mean()
        post = df[(df['mmdd'] >= '06-10') & (df['mmdd'] <= '06-21')]['rate'].mean()
        return pre, post

    r25_pre, r25_post = rate_period_means(df25_win)
    r26_pre, r26_post = rate_period_means(df26_win)
    rate25_change_pct = (r25_post - r25_pre) / r25_pre * 100
    rate26_change_pct = (r26_post - r26_pre) / r26_pre * 100
    out['pay_rate_pp'] = rate26_change_pct - rate25_change_pct

    return out


# 优先用 did_summary_d12.csv (并行 agent 产出的 D+12 标准结果)
d12_vals = None
d5_vals_from_csv = None
if os.path.exists(DID_SUMMARY_D12):
    try:
        sm = pd.read_csv(DID_SUMMARY_D12)
        idx_col = sm.columns[0]

        def get_row(metric_keys):
            mask = sm[idx_col].astype(str).str.contains('|'.join(metric_keys), na=False)
            return sm[mask].iloc[0]

        # 绝对量指标用 D+12_相对缺口 (小数 -> %)
        # 转化率用 DiD净效应_D+12 的变化率差 -> pp (×100)
        r_dau = get_row(['DAU\\(uv_all\\)', '^DAU'])
        r_xq = get_row(['商详uv'])
        r_pay = get_row(['^净支付pv$', '净支付pv,'])
        # 净支付转化率行
        r_rate = get_row(['净支付转化率', 'dau_pay_rate'])

        d12_vals = {
            'uv_all': float(r_dau['D+12_相对缺口']) * 100,
            'detail_uv': float(r_xq['D+12_相对缺口']) * 100,
            'pay_pv': float(r_pay['D+12_相对缺口']) * 100,
            # 转化率: 用 DiD 净效应 (26 变化率 - 25 变化率) 作为相对变化 pp
            'pay_rate_pp': float(r_rate['DiD净效应_D+12(26-25)']) * 100,
        }

        # 顺便也从 CSV 校验 D+5 值
        d5_vals_from_csv = {
            'uv_all': float(r_dau['D+5_相对缺口']) * 100,
            'detail_uv': float(r_xq['D+5_相对缺口']) * 100,
            'pay_pv': float(r_pay['D+5_相对缺口']) * 100,
            'pay_rate_pp': float(r_rate['DiD净效应_D+5(26-25)']) * 100,
        }
        print('   [从 did_summary_d12.csv 读取 D+12 真实效应]')
        print(f'   CSV D+5: {d5_vals_from_csv}')
        print(f'   CSV D+12: {d12_vals}')
    except Exception as e:
        print(f'   读取 did_summary_d12.csv 失败 ({e}), 改用自行重算')
        d12_vals = None

if d12_vals is None or d12_vals.get('pay_rate_pp') is None:
    print('   [自行重算 D+12 真实效应]')
    d12_vals = compute_did_d12_from_raw()

# D+5 历史已知值 (任务给定, 来自 0615 D+5 DiD 报告)
d5_vals = {
    'uv_all': -35.7,       # DAU 反事实相对缺口 %
    'detail_uv': -24.8,    # 商详UV 反事实相对缺口 %
    'pay_pv': -12.5,       # 净支付PV 反事实相对缺口 %
    'pay_rate_pp': 35.6,   # 净支付转化率 真实变化 (pp)
}
# 注: CSV 中 D+5 数值与任务给定值非常接近(差异在 1pp 内, 来自细节口径差),
# 此处遵循任务指令使用 0615 报告中的官方 D+5 数字, 保持与原沟通一致.


metric_order = [
    ('DAU', 'uv_all', '%'),
    ('商详 UV', 'detail_uv', '%'),
    ('净支付 PV', 'pay_pv', '%'),
    ('净支付转化率', 'pay_rate_pp', 'pp'),
]

labels = [m[0] for m in metric_order]
d5_plot = [d5_vals[m[1]] for m in metric_order]
d12_plot = [d12_vals[m[1]] for m in metric_order]

fig, ax = plt.subplots(figsize=(11, 6.5))
x = np.arange(len(labels))
w = 0.36

c_d5 = '#7E57C2'   # D+5 紫色
c_d12 = '#26A69A'  # D+12 青绿色

bars_d5 = ax.bar(x - w / 2, d5_plot, w, color=c_d5, label='D+5 真实净效应 (6.10-6.15)',
                 edgecolor='white', linewidth=0.5)
bars_d12 = ax.bar(x + w / 2, d12_plot, w, color=c_d12, label='D+12 真实净效应 (6.10-6.21)',
                  edgecolor='white', linewidth=0.5)

ax.axhline(0, color='#444444', linewidth=1)
ax.set_ylabel('真实净效应 (%, 净支付转化率为 pp)', fontsize=11)
ax.set_title('九宫格下线影响: D+5 vs D+12 真实损失对比 (小程序大盘)',
             fontsize=14, fontweight='bold', pad=12)
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=11)
ax.legend(loc='lower right', frameon=True, framealpha=0.92, fontsize=10)
ax.grid(True, axis='y', linestyle=':', alpha=0.4)

# 柱顶数字
def lab(v, suffix):
    sign = '+' if v > 0 else ''
    return f'{sign}{v:.1f}{suffix}'

# 先扩大上下空间, 再写注释, 避免与柱顶数字重叠
ymin_data = min(min(d5_plot), min(d12_plot), 0)
ymax_data = max(max(d5_plot), max(d12_plot), 0)
span = ymax_data - ymin_data
pad = span * 0.28
ax.set_ylim(ymin_data - pad, ymax_data + pad)

# 柱顶数字 (紧贴柱)
def put_bar_label(bar, v, unit, color):
    h = bar.get_height()
    if h >= 0:
        ax.text(bar.get_x() + bar.get_width() / 2, h + span * 0.015,
                lab(v, unit), ha='center', va='bottom',
                fontsize=10, fontweight='bold', color=color)
    else:
        ax.text(bar.get_x() + bar.get_width() / 2, h - span * 0.015,
                lab(v, unit), ha='center', va='top',
                fontsize=10, fontweight='bold', color=color)

for bar, v, (_, key, unit) in zip(bars_d5, d5_plot, metric_order):
    put_bar_label(bar, v, unit, c_d5)
for bar, v, (_, key, unit) in zip(bars_d12, d12_plot, metric_order):
    put_bar_label(bar, v, unit, c_d12)

# 收窄/扩大注释 - 放到柱组外侧, 留足距离
for xi, (v5, v12, (lbl, _, unit)) in enumerate(zip(d5_plot, d12_plot, metric_order)):
    narrow = abs(v12) < abs(v5)
    delta = v12 - v5
    sign = '+' if delta > 0 else ''
    if unit == '%':
        tag = '损失收窄' if narrow else '损失扩大'
    else:
        tag = '转化率扩大' if delta > 0 else '转化率收窄'
        narrow = delta > 0   # 转化率正向变化算 "好"
    color = '#2E7D32' if narrow else '#C62828'
    annot = f'{tag} ({sign}{delta:.1f}{unit})'

    ymax_here = max(v5, v12, 0)
    ymin_here = min(v5, v12, 0)
    if abs(ymax_here) >= abs(ymin_here):
        y_pos = ymax_here + span * 0.14
        va = 'bottom'
    else:
        y_pos = ymin_here - span * 0.16
        va = 'top'
    ax.text(xi, y_pos, annot, ha='center', va=va,
            fontsize=10, fontweight='bold', color=color,
            bbox=dict(boxstyle='round,pad=0.35', facecolor='white',
                      edgecolor=color, linewidth=1.2))

plt.tight_layout()
p4 = os.path.join(OUT_DIR, 'd5_vs_d12_correction.png')
plt.savefig(p4, bbox_inches='tight')
plt.close(fig)
print('  ', p4)


# -------- 总结 --------
print('\n=== 完成 ===')
for p in [p1, p2, p3, p4]:
    print(p)

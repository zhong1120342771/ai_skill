"""
九宫格下线影响分析 - D+12 扩窗复盘 (含 6.18 当天承接能力)

输入:
  - /Users/zhongmengting/.claude/data_storage/jgg_offline_0622/raw_belong02.xlsx
      2026 数据，含 wd 维度 (转转小程序 / xcx-九宫格 / 转转APP / 找靓机)，
      时间 2026-05-01 ~ 2026-06-21
  - /Users/zhongmengting/.claude/data_storage/jgg_yoy/2025_daily.xlsx
      2025 同期小程序大盘日级指标 (DAU/净支付pv/商详uv/转化率族)，
      时间 2025-06-01 ~ 2025-06-15 (注意: 25 年只到 6.15，6.16~6.21 缺失)

输出:
  - /Users/zhongmengting/.claude/data_storage/jgg_offline_0622/daily_metrics_d12.csv
  - /Users/zhongmengting/.claude/data_storage/jgg_offline_0622/did_summary_d12.csv
  - /Users/zhongmengting/.claude/data_storage/jgg_offline_0622/d618_compare.csv
  - /Users/zhongmengting/.claude/data_storage/jgg_offline_0622/d5_vs_d12.csv

口径:
  - 小程序大盘 = 转转小程序 + xcx-九宫格 (下线前) / ≈ 转转小程序 (下线后)
  - 非九宫格小程序 = 转转小程序
  - 九宫格 = xcx-九宫格
  - 所有率值用区间 sum 重算 (sum(numerator)/sum(denominator))，不用日均率
  - 注意之前看板里的 "xcx-非九宫格" 对应本次的 "转转小程序"
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ----------- 路径 -----------
PATH_26_RAW = '/Users/zhongmengting/.claude/data_storage/jgg_offline_0622/raw_belong02.xlsx'
PATH_25_DAILY = '/Users/zhongmengting/.claude/data_storage/jgg_yoy/2025_daily.xlsx'

OUT_DIR = Path('/Users/zhongmengting/.claude/data_storage/jgg_offline_0622')
OUT_DAILY = OUT_DIR / 'daily_metrics_d12.csv'
OUT_DID = OUT_DIR / 'did_summary_d12.csv'
OUT_618 = OUT_DIR / 'd618_compare.csv'
OUT_D5_D12 = OUT_DIR / 'd5_vs_d12.csv'

OFFLINE_DAY = '2026-06-10'

# ----------- 1. 加载 26 原始数据 -----------
df26 = pd.read_excel(PATH_26_RAW)
df26 = df26[df26['tag_01'] == '拆分端'].copy()
df26['dt'] = pd.to_datetime(df26['dt'].astype(str))

# 仅保留小程序两个子端
df26_xcx = df26[df26['wd'].isin(['转转小程序', 'xcx-九宫格'])].copy()

# ----------- 2. 按 wd 分组日级数据 -----------
metric_cols = ['exp_pv', 'exp_uv', 'detail_pv', 'detail_uv',
               'order_pv', 'order_uv', 'pay_pv', 'uv_all']

# 子端逐日
daily_per_wd = df26_xcx[['dt', 'wd'] + metric_cols].copy()

# 大盘 = 转转小程序 + xcx-九宫格 (按 dt 聚合)
daily_dapan = (df26_xcx.groupby('dt')[metric_cols].sum().reset_index())
daily_dapan['wd'] = '小程序大盘'

# 转转小程序单独 (非九宫格)
daily_fjgg = df26_xcx[df26_xcx['wd'] == '转转小程序'].copy().reset_index(drop=True)

# 九宫格单独
daily_jgg = df26_xcx[df26_xcx['wd'] == 'xcx-九宫格'].copy().reset_index(drop=True)

# 衍生率 (区间 sum 法的 daily 版本：单日就是当日值，sum=当日)
def add_rates(df):
    df = df.copy()
    df['dau_pay_rate'] = df['pay_pv'] / df['uv_all'].replace(0, np.nan)
    df['dau_sx_rate'] = df['detail_uv'] / df['uv_all'].replace(0, np.nan)
    df['sx_pay_rate'] = df['pay_pv'] / df['detail_uv'].replace(0, np.nan)
    df['exp_per_uv'] = df['exp_pv'] / df['exp_uv'].replace(0, np.nan)  # 人均曝光pv
    df['exp_penetration'] = df['exp_uv'] / df['uv_all'].replace(0, np.nan)
    df['sx_to_order_rate'] = df['order_uv'] / df['detail_uv'].replace(0, np.nan)
    return df

daily_per_wd = add_rates(daily_per_wd)
daily_dapan = add_rates(daily_dapan)
daily_fjgg = add_rates(daily_fjgg)
daily_jgg = add_rates(daily_jgg)

# 合并为长表 (wd 维度 + 大盘)
daily_all = pd.concat([
    daily_per_wd[['dt', 'wd'] + metric_cols + ['dau_pay_rate', 'dau_sx_rate', 'sx_pay_rate', 'exp_per_uv', 'exp_penetration', 'sx_to_order_rate']],
    daily_dapan[['dt', 'wd'] + metric_cols + ['dau_pay_rate', 'dau_sx_rate', 'sx_pay_rate', 'exp_per_uv', 'exp_penetration', 'sx_to_order_rate']],
], ignore_index=True)
daily_all = daily_all.sort_values(['wd', 'dt']).reset_index(drop=True)

# ----------- 3. 加载 25 同期大盘日级 (有缺) -----------
df25 = pd.read_excel(PATH_25_DAILY)
df25 = df25[df25['日期(day)'].astype(str).str.match(r'^\d{8}$')].copy()
df25['dt'] = pd.to_datetime(df25['日期(day)'].astype(str), format='%Y%m%d')
df25 = df25.sort_values('dt').reset_index(drop=True)

# 重命名以匹配
df25 = df25.rename(columns={
    'DAU': 'uv_all',
    '净支付pv': 'pay_pv',
    '净支付pv转化率': 'dau_pay_rate',
    '商详uv': 'detail_uv',
    '商详渗透率': 'dau_sx_rate',
    '商详转化率': 'sx_pay_rate',
    '曝光渗透率': 'exp_penetration',
    '商详到达率': 'detail_arrival_rate',
    '下单率': 'sx_to_order_rate',
    '支付率': 'order_to_pay_rate',
    '提袋率': 'pickup_rate',
    '人均曝光pv': 'exp_per_uv',
})

# 25 年大盘也加 wd 标签便于合并
df25['wd'] = '小程序大盘_25'

# YoY 对齐到 26 同日 (相同 month-day)
df25['dt_md'] = df25['dt'].dt.strftime('%m-%d')
daily_dapan['dt_md'] = daily_dapan['dt'].dt.strftime('%m-%d')

yoy = daily_dapan.merge(
    df25[['dt_md', 'uv_all', 'pay_pv', 'dau_pay_rate', 'detail_uv',
          'dau_sx_rate', 'sx_pay_rate', 'exp_per_uv', 'exp_penetration']]
       .rename(columns=lambda c: f'{c}_25' if c != 'dt_md' else c),
    on='dt_md', how='left'
)

# 计算同日 YoY (26 vs 25) 只对 6 月匹配上的
for c in ['uv_all', 'pay_pv', 'dau_pay_rate', 'detail_uv', 'dau_sx_rate', 'sx_pay_rate', 'exp_per_uv', 'exp_penetration']:
    yoy[f'{c}_yoy'] = (yoy[c] - yoy[f'{c}_25']) / yoy[f'{c}_25']

# ----------- 输出 daily_all 长表 + yoy 宽表 (拼到一起) -----------
# 先输出宽长表：left = daily_all 全量
daily_all_out = daily_all.copy()
# 把 yoy 块附在大盘的对应日期上，新列 YoY_*
yoy_keep = yoy[['dt', 'wd'] + [f'{c}_25' for c in ['uv_all', 'pay_pv', 'dau_pay_rate', 'detail_uv', 'dau_sx_rate', 'sx_pay_rate', 'exp_per_uv', 'exp_penetration']]
              + [f'{c}_yoy' for c in ['uv_all', 'pay_pv', 'dau_pay_rate', 'detail_uv', 'dau_sx_rate', 'sx_pay_rate', 'exp_per_uv', 'exp_penetration']]].copy()
daily_all_out = daily_all_out.merge(yoy_keep, on=['dt', 'wd'], how='left')

daily_all_out['dt'] = daily_all_out['dt'].dt.strftime('%Y-%m-%d')
daily_all_out.to_csv(OUT_DAILY, index=False, encoding='utf-8-sig')
print(f'[saved] {OUT_DAILY}  shape={daily_all_out.shape}')

# ----------- 4. D+12 DiD 汇总 (小程序大盘口径) -----------
# 前期 2026-06-01 ~ 2026-06-09 (9d)
# D+12  2026-06-10 ~ 2026-06-21 (12d)
# 25 年 6.10-6.21 数据缺 6.16-6.21，只能用 6.10-6.15 (6d) 代表 25 后期
# 同时也跑一版「同窗口对齐」: 25 前 6.1-6.9 vs 25 后 6.10-6.15 (6d)，
# 反事实节奏用「日均变化率」推 12 天 (假设节奏延续)

PRE_START = pd.Timestamp('2026-06-01')
PRE_END = pd.Timestamp('2026-06-09')
POST_START = pd.Timestamp('2026-06-10')
POST_END_D12 = pd.Timestamp('2026-06-21')
POST_END_D5 = pd.Timestamp('2026-06-15')

PRE_START_25 = pd.Timestamp('2025-06-01')
PRE_END_25 = pd.Timestamp('2025-06-09')
POST_START_25 = pd.Timestamp('2025-06-10')
POST_END_25_AVAIL = pd.Timestamp('2025-06-15')  # 仅有这部分

def agg_window_count(df, start, end, cols):
    """以 sum 聚合区间内 cols 列"""
    sub = df[(df['dt'] >= start) & (df['dt'] <= end)]
    out = {c: sub[c].sum() for c in cols}
    out['__days__'] = sub['dt'].nunique()
    return out, sub

def safe_div(a, b):
    return a / b if b else np.nan

def compute_rates_from_sums(s):
    return {
        'dau_pay_rate': safe_div(s['pay_pv'], s['uv_all']),
        'dau_sx_rate': safe_div(s['detail_uv'], s['uv_all']),
        'sx_pay_rate': safe_div(s['pay_pv'], s['detail_uv']),
        'exp_per_uv': safe_div(s['exp_pv'], s['exp_uv']),
        'exp_penetration': safe_div(s['exp_uv'], s['uv_all']),
        'sx_to_order_rate': safe_div(s['order_uv'], s['detail_uv']),
    }

base_cols = ['exp_pv', 'exp_uv', 'detail_pv', 'detail_uv', 'order_pv', 'order_uv', 'pay_pv', 'uv_all']

# 26 大盘
pre26_sum, _ = agg_window_count(daily_dapan, PRE_START, PRE_END, base_cols)
post26_sum_d12, _ = agg_window_count(daily_dapan, POST_START, POST_END_D12, base_cols)
post26_sum_d5, _ = agg_window_count(daily_dapan, POST_START, POST_END_D5, base_cols)

# 26 大盘日均
def to_daily_avg(s):
    d = s['__days__']
    return {c: s[c] / d for c in base_cols if c != '__days__'} | {'__days__': d}

pre26_avg = to_daily_avg(pre26_sum)
post26_avg_d12 = to_daily_avg(post26_sum_d12)
post26_avg_d5 = to_daily_avg(post26_sum_d5)

# 25 大盘：日均 (从 2025_daily.xlsx 直接日级求均值)
df25_base = df25[df25['wd'] == '小程序大盘_25'].copy()
pre25_rows = df25_base[(df25_base['dt'] >= PRE_START_25) & (df25_base['dt'] <= PRE_END_25)]
post25_rows = df25_base[(df25_base['dt'] >= POST_START_25) & (df25_base['dt'] <= POST_END_25_AVAIL)]

# 25 数据列：uv_all, pay_pv, detail_uv (绝对量) + 各率值
# 25 没有 exp_pv/exp_uv 绝对量 (只有 exp_penetration, exp_per_uv 率)
# 注意 25 数据没有 detail_pv, order_pv, order_uv -> 这些指标 DiD 仅在 26 内部对比可用
pre25_avg = {
    'uv_all': pre25_rows['uv_all'].mean(),
    'pay_pv': pre25_rows['pay_pv'].mean(),
    'detail_uv': pre25_rows['detail_uv'].mean(),
    'dau_pay_rate': pre25_rows['dau_pay_rate'].mean(),
    'dau_sx_rate': pre25_rows['dau_sx_rate'].mean(),
    'sx_pay_rate': pre25_rows['sx_pay_rate'].mean(),
    'exp_per_uv': pre25_rows['exp_per_uv'].mean(),
    'exp_penetration': pre25_rows['exp_penetration'].mean(),
    '__days__': len(pre25_rows),
}
post25_avg = {
    'uv_all': post25_rows['uv_all'].mean(),
    'pay_pv': post25_rows['pay_pv'].mean(),
    'detail_uv': post25_rows['detail_uv'].mean(),
    'dau_pay_rate': post25_rows['dau_pay_rate'].mean(),
    'dau_sx_rate': post25_rows['dau_sx_rate'].mean(),
    'sx_pay_rate': post25_rows['sx_pay_rate'].mean(),
    'exp_per_uv': post25_rows['exp_per_uv'].mean(),
    'exp_penetration': post25_rows['exp_penetration'].mean(),
    '__days__': len(post25_rows),
}

# 同窗口对齐 25 post (与 26 6.10-6.15 比) - 这里 post25_avg 已经是 6.10-6.15
# 26 后期对应数据：
post26_avg_d5_rates = compute_rates_from_sums(post26_sum_d5)
post26_avg_d12_rates = compute_rates_from_sums(post26_sum_d12)
pre26_avg_rates = compute_rates_from_sums(pre26_sum)

# 25 同窗口 (6.1-6.9 vs 6.10-6.15) 变化率作为反事实节奏
def chg_rate(pre, post, key):
    if pre.get(key) is None or post.get(key) is None or pre[key] in (0, None) or pd.isna(pre[key]):
        return np.nan
    return (post[key] - pre[key]) / pre[key]

# 指标列表 - DiD 用
did_metrics = [
    ('DAU(uv_all)', 'uv_all'),
    ('净支付pv', 'pay_pv'),
    ('商详uv', 'detail_uv'),
    ('净支付转化率(dau_pay_rate)', 'dau_pay_rate'),
    ('商详渗透率(dau_sx_rate)', 'dau_sx_rate'),
    ('商详转化率(sx_pay_rate)', 'sx_pay_rate'),
    ('曝光渗透率(exp_penetration)', 'exp_penetration'),
    ('人均曝光pv(exp_per_uv)', 'exp_per_uv'),
]

# 26 后期 D+12 sum 重算的率值
post26_d12_metrics_dict = {**post26_avg_d12, **post26_avg_d12_rates}
pre26_metrics_dict = {**pre26_avg, **pre26_avg_rates}
post26_d5_metrics_dict = {**post26_avg_d5, **post26_avg_d5_rates}

# 输出 DiD 汇总表
did_rows = []
for mname, mkey in did_metrics:
    p25 = pre25_avg.get(mkey, np.nan)
    q25 = post25_avg.get(mkey, np.nan)
    chg25 = (q25 - p25) / p25 if (p25 and not pd.isna(p25)) else np.nan

    # 26 D+12 (后期日均 sum/days)
    p26 = pre26_metrics_dict.get(mkey, np.nan)
    q26_d12 = post26_d12_metrics_dict.get(mkey, np.nan)
    q26_d5 = post26_d5_metrics_dict.get(mkey, np.nan)
    chg26_d12 = (q26_d12 - p26) / p26 if (p26 and not pd.isna(p26)) else np.nan
    chg26_d5 = (q26_d5 - p26) / p26 if (p26 and not pd.isna(p26)) else np.nan

    did_d12 = chg26_d12 - chg25
    did_d5 = chg26_d5 - chg25

    did_rows.append({
        '指标': mname,
        '25前(6.1-6.9日均)': p25,
        '25后(6.10-6.15日均,仅6d)': q25,
        '25变化率': chg25,
        '26前(6.1-6.9日均)': p26,
        '26后D+5(6.10-6.15日均)': q26_d5,
        '26变化率_D+5': chg26_d5,
        '26后D+12(6.10-6.21日均)': q26_d12,
        '26变化率_D+12': chg26_d12,
        'DiD净效应_D+5(26-25)': did_d5,
        'DiD净效应_D+12(26-25)': did_d12,
    })

did_df = pd.DataFrame(did_rows)
did_df.to_csv(OUT_DID, index=False, encoding='utf-8-sig')
print(f'[saved] {OUT_DID}  shape={did_df.shape}')

# ----------- 5. 反事实计算 (用 25 变化率推 26 应有值) -----------
# 把 25 同窗口变化率作为反事实节奏，套到 26 前期得到 26 后期反事实
cf_rows = []
for mname, mkey in did_metrics:
    p25 = pre25_avg.get(mkey, np.nan)
    q25 = post25_avg.get(mkey, np.nan)
    p26 = pre26_metrics_dict.get(mkey, np.nan)
    q26_d12 = post26_d12_metrics_dict.get(mkey, np.nan)
    q26_d5 = post26_d5_metrics_dict.get(mkey, np.nan)

    chg25 = (q25 - p25) / p25 if (p25 and not pd.isna(p25)) else np.nan
    cf26 = p26 * (1 + chg25) if not pd.isna(chg25) else np.nan

    gap_d12 = q26_d12 - cf26
    gap_d5 = q26_d5 - cf26
    rel_gap_d12 = gap_d12 / cf26 if cf26 else np.nan
    rel_gap_d5 = gap_d5 / cf26 if cf26 else np.nan

    cf_rows.append({
        '指标': mname,
        '25变化率(反事实节奏)': chg25,
        '26前': p26,
        '反事实26后(p26*(1+chg25))': cf26,
        '实际D+5': q26_d5,
        'D+5_缺口': gap_d5,
        'D+5_相对缺口': rel_gap_d5,
        '实际D+12': q26_d12,
        'D+12_缺口': gap_d12,
        'D+12_相对缺口': rel_gap_d12,
    })
cf_df = pd.DataFrame(cf_rows)
# 追加到 did_summary（合并保存）
did_full = did_df.merge(cf_df.drop(columns=['25变化率(反事实节奏)', '26前', '实际D+5', '实际D+12']), on='指标', how='left')
did_full.to_csv(OUT_DID, index=False, encoding='utf-8-sig')
print(f'[saved+merge counter-factual] {OUT_DID}')

# ----------- 6. 6.18 当天承接能力 -----------
d_618_26 = pd.Timestamp('2026-06-18')
d_609_26 = pd.Timestamp('2026-06-09')  # 下线前最后正常日
d_615_25 = pd.Timestamp('2025-06-15')  # 25 最后可对照日

def get_day(df, day, prefix=''):
    row = df[df['dt'] == day]
    if row.empty:
        return None
    r = row.iloc[0]
    return {f'{prefix}{c}': r[c] for c in r.index if c not in ('dt', 'wd', 'dt_md')}

# 26 6.18 大盘
r26_618_dapan = get_day(daily_dapan, d_618_26)
r26_609_dapan = get_day(daily_dapan, d_609_26)
# 26 6.18 拆分小程序 (转转小程序)
r26_618_fjgg = get_day(daily_fjgg, d_618_26)
r26_609_fjgg = get_day(daily_fjgg, d_609_26)
# 26 6.18 九宫格
r26_618_jgg = get_day(daily_jgg, d_618_26)
r26_609_jgg = get_day(daily_jgg, d_609_26)

# 25 6.15 (最后可比基准)
r25_615 = df25_base[df25_base['dt'] == d_615_25].iloc[0] if not df25_base[df25_base['dt'] == d_615_25].empty else None
# 25 6.9
r25_609 = df25_base[df25_base['dt'] == pd.Timestamp('2025-06-09')].iloc[0] if not df25_base[df25_base['dt'] == pd.Timestamp('2025-06-09')].empty else None

# 同窗口 25 大促预热区间 (6.10-6.15) 日均，作为 25 视角"618 前临门" 表征
r25_post_avg = {
    'uv_all': post25_rows['uv_all'].mean(),
    'pay_pv': post25_rows['pay_pv'].mean(),
    'detail_uv': post25_rows['detail_uv'].mean(),
    'dau_pay_rate': post25_rows['dau_pay_rate'].mean(),
    'dau_sx_rate': post25_rows['dau_sx_rate'].mean(),
    'sx_pay_rate': post25_rows['sx_pay_rate'].mean(),
    'exp_per_uv': post25_rows['exp_per_uv'].mean(),
    'exp_penetration': post25_rows['exp_penetration'].mean(),
}

# Build the table:
rows_618 = []
# 指标
for mname, mkey in [('DAU(uv_all)', 'uv_all'), ('净支付pv', 'pay_pv'),
                    ('商详uv', 'detail_uv'), ('净支付转化率', 'dau_pay_rate'),
                    ('商详渗透率', 'dau_sx_rate'), ('商详转化率', 'sx_pay_rate'),
                    ('人均曝光pv', 'exp_per_uv'), ('曝光渗透率', 'exp_penetration'),
                    ('曝光uv', 'exp_uv')]:
    v_dapan_618 = r26_618_dapan.get(mkey) if r26_618_dapan else np.nan
    v_dapan_609 = r26_609_dapan.get(mkey) if r26_609_dapan else np.nan
    v_fjgg_618 = r26_618_fjgg.get(mkey) if r26_618_fjgg else np.nan
    v_jgg_618 = r26_618_jgg.get(mkey) if r26_618_jgg else np.nan
    v_25_615 = r25_615[mkey] if (r25_615 is not None and mkey in r25_615) else np.nan
    v_25_post_avg = r25_post_avg.get(mkey, np.nan)

    # YoY 6.18 vs 25 同期 (6.15 替代)
    yoy_618_vs_615_25 = (v_dapan_618 - v_25_615) / v_25_615 if (v_25_615 and not pd.isna(v_25_615)) else np.nan
    # 6.18 vs 25 6.10-6.15 日均
    yoy_618_vs_25postavg = (v_dapan_618 - v_25_post_avg) / v_25_post_avg if (v_25_post_avg and not pd.isna(v_25_post_avg)) else np.nan
    # 6.18 vs 26.6.9 (下线前最后日)
    vs_609 = (v_dapan_618 - v_dapan_609) / v_dapan_609 if (v_dapan_609 and not pd.isna(v_dapan_609)) else np.nan
    # 非九宫格 6.18 vs 25 6.15
    yoy_fjgg_618_vs_615_25 = (v_fjgg_618 - v_25_615) / v_25_615 if (v_25_615 and not pd.isna(v_25_615)) else np.nan

    rows_618.append({
        '指标': mname,
        '26.6.18_大盘': v_dapan_618,
        '26.6.18_转转小程序': v_fjgg_618,
        '26.6.18_九宫格': v_jgg_618,
        '26.6.9_大盘(下线前最后)': v_dapan_609,
        '25.6.15_大盘(25末日)': v_25_615,
        '25.6.10-15_日均': v_25_post_avg,
        '大盘6.18_vs_25.6.15': yoy_618_vs_615_25,
        '大盘6.18_vs_25末窗均': yoy_618_vs_25postavg,
        '大盘6.18_vs_26.6.9': vs_609,
        '转转小程序6.18_vs_25.6.15': yoy_fjgg_618_vs_615_25,
    })

rows_618_df = pd.DataFrame(rows_618)
rows_618_df.to_csv(OUT_618, index=False, encoding='utf-8-sig')
print(f'[saved] {OUT_618}  shape={rows_618_df.shape}')

# ----------- 7. D+5 vs D+12 对比 -----------
# 损失是否随时间收窄 (相对反事实)
d5_d12_rows = []
for mname, mkey in did_metrics:
    p25 = pre25_avg.get(mkey, np.nan)
    q25 = post25_avg.get(mkey, np.nan)
    p26 = pre26_metrics_dict.get(mkey, np.nan)
    q26_d12 = post26_d12_metrics_dict.get(mkey, np.nan)
    q26_d5 = post26_d5_metrics_dict.get(mkey, np.nan)
    chg25 = (q25 - p25) / p25 if (p25 and not pd.isna(p25)) else np.nan
    cf26 = p26 * (1 + chg25) if not pd.isna(chg25) else np.nan

    gap_d5 = q26_d5 - cf26
    gap_d12 = q26_d12 - cf26
    rel_gap_d5 = gap_d5 / cf26 if cf26 else np.nan
    rel_gap_d12 = gap_d12 / cf26 if cf26 else np.nan

    # 收窄程度
    delta = rel_gap_d12 - rel_gap_d5
    direction = '收窄' if (not pd.isna(delta) and delta > 0) else ('扩大' if (not pd.isna(delta) and delta < 0) else 'NA')

    d5_d12_rows.append({
        '指标': mname,
        '26_D+5日均': q26_d5,
        '26_D+12日均': q26_d12,
        '反事实D+5(等同D+12,基于25变化率推)': cf26,
        'D+5相对缺口': rel_gap_d5,
        'D+12相对缺口': rel_gap_d12,
        'D+12-D+5_缺口差(pp)': delta,
        '方向': direction,
    })

d5_d12_df = pd.DataFrame(d5_d12_rows)
d5_d12_df.to_csv(OUT_D5_D12, index=False, encoding='utf-8-sig')
print(f'[saved] {OUT_D5_D12}  shape={d5_d12_df.shape}')

# ----------- 8. 控制台打印关键数值 (供人工对账) -----------
pd.set_option('display.unicode.east_asian_width', True)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 280)
pd.set_option('display.float_format', lambda x: f'{x:.4f}' if abs(x) < 1 else f'{x:,.2f}')

print('\n========== DiD D+12 汇总 ==========')
print(did_full.to_string(index=False))
print('\n========== 6.18 当天承接能力 ==========')
print(rows_618_df.to_string(index=False))
print('\n========== D+5 vs D+12 缺口对比 ==========')
print(d5_d12_df.to_string(index=False))

# 关键摘要 print
print('\n========== 关键摘要 ==========')
for mname, mkey in did_metrics:
    p26 = pre26_metrics_dict.get(mkey, np.nan)
    q26_d12 = post26_d12_metrics_dict.get(mkey, np.nan)
    p25 = pre25_avg.get(mkey, np.nan)
    q25 = post25_avg.get(mkey, np.nan)
    chg25 = (q25 - p25) / p25 if (p25 and not pd.isna(p25)) else np.nan
    chg26 = (q26_d12 - p26) / p26 if (p26 and not pd.isna(p26)) else np.nan
    did = chg26 - chg25 if not (pd.isna(chg26) or pd.isna(chg25)) else np.nan
    print(f'{mname:30s}  25变化率={chg25*100 if not pd.isna(chg25) else np.nan:+.2f}%  '
          f'26变化率D+12={chg26*100 if not pd.isna(chg26) else np.nan:+.2f}%  '
          f'DiD净效应={did*100 if not pd.isna(did) else np.nan:+.2f}pp')

print('\n[done]')

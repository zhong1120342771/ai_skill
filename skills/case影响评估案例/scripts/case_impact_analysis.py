"""case 影响评估 — 分析脚本模板
三期切分 + 多口径双重差分(DiD)估单量损失 + 用户体验受损量折算。

用法：改顶部 CONFIG 常量后运行。明细数据默认结构为
  日期 | 页面 | 品类类目 | 端 | 点击用户列 | 订单列
若字段名不同，改 COL_* 映射即可。
"""
import pandas as pd
from pathlib import Path

# ==================== CONFIG（每个 case 改这里）====================
DATA_FILE   = Path.home() / 'Downloads' / '机型筛选case评估.xlsx'   # 明细数据
BUG_START   = pd.Timestamp('2026-05-27')       # 故障窗起（含）
BUG_END     = pd.Timestamp('2026-07-11')       # 故障窗止（含）
WINDOW_DAYS = 45.7                              # 故障持续天数（复盘口径，用于日均）

# 明细列名映射
COL_DATE, COL_PAGE, COL_CAT, COL_PLAT = '日期', '页面', '品类类目', '端'
COL_CLICK, COL_ORDER = '点击机型筛选的用户', '订单量'

# 受影响 / 对照 维度取值
AFFECTED_CAT   = '手机外的其他类目'   # 受影响品类
CONTROL_CAT    = '手机'              # 同端干净对照品类
AFFECTED_PLAT  = 'android'           # 受影响端
CONTROL_PLAT   = 'iOS'               # 跨端对照端
MAIN_PAGE      = 'G1004'             # 主力页（占受影响点击 majority）

# 用户体验候选上界（来自事故复盘的去重口径，非本明细）
CAND_PV, CAND_UV = 654727, 97753
# ================================================================

df = pd.read_excel(DATA_FILE)
df[COL_DATE] = pd.to_datetime(df[COL_DATE])

def period(d):
    if d < BUG_START: return '故障前'
    if d <= BUG_END:  return '故障窗'
    return '修复后'
df['期'] = df[COL_DATE].apply(period)

def rate(d, page, cat, plat):
    """人均单量 = 订单 / 点击用户"""
    s = d[(d[COL_PAGE]==page)&(d[COL_CAT]==cat)&(d[COL_PLAT]==plat)]
    c, o = s[COL_CLICK].sum(), s[COL_ORDER].sum()
    return c, o, (o/c if c else 0)

bug = df[df['期']=='故障窗']
pre = df[df['期']=='故障前']

print("="*66)
print("三期 × 页面 × 品类 × 端  人均单量")
print("="*66)
g = df.groupby(['期',COL_PAGE,COL_CAT,COL_PLAT]).apply(
    lambda s: pd.Series({'点击':s[COL_CLICK].sum(),'单':s[COL_ORDER].sum()}), include_groups=False
).reset_index()
g['人均'] = (g['单']/g['点击']).round(4)
print(g.to_string(index=False))

print("\n"+"="*66)
print(f"{MAIN_PAGE} 双重差分（多口径）")
print("="*66)
c_af,o_af,r_af = rate(bug, MAIN_PAGE, AFFECTED_CAT, AFFECTED_PLAT)
_,_,r_ctrl_cat = rate(bug, MAIN_PAGE, AFFECTED_CAT, CONTROL_PLAT)   # 跨端对照品类
_,_,r_aff_ctrlcat = rate(bug, MAIN_PAGE, CONTROL_CAT, AFFECTED_PLAT) # 受影响端干净品类
_,_,r_ctrl_ctrlcat = rate(bug, MAIN_PAGE, CONTROL_CAT, CONTROL_PLAT) # 对照端干净品类

# 口径A 跨端DiD：用干净品类测两端结构比，套到受影响品类
plat_ratio = r_aff_ctrlcat / r_ctrl_ctrlcat if r_ctrl_ctrlcat else 0
cf_A = r_ctrl_cat * plat_ratio
lossA = (cf_A - r_af) * c_af
print(f"[跨端DiD] 端结构比={plat_ratio:.4f} 预期={cf_A:.4f} 实际={r_af:.4f} 损失={lossA:+.1f}单")

# 口径B 时间DiD（对照端同品类为趋势）
_,_,rp_af = rate(pre, MAIN_PAGE, AFFECTED_CAT, AFFECTED_PLAT)
_,_,rp_ctrl_cat = rate(pre, MAIN_PAGE, AFFECTED_CAT, CONTROL_PLAT)
cf_B = rp_af * (r_ctrl_cat/rp_ctrl_cat) if rp_ctrl_cat else 0
lossB = (cf_B - r_af) * c_af
print(f"[时间DiD·对照端] 预期={cf_B:.4f} 实际={r_af:.4f} 损失={lossB:+.1f}单")

# 口径C 时间DiD（受影响端干净品类为趋势）
_,_,rp_aff_ctrlcat = rate(pre, MAIN_PAGE, CONTROL_CAT, AFFECTED_PLAT)
cf_C = rp_af * (r_aff_ctrlcat/rp_aff_ctrlcat) if rp_aff_ctrlcat else 0
lossC = (cf_C - r_af) * c_af
print(f"[时间DiD·干净品类] 预期={cf_C:.4f} 实际={r_af:.4f} 损失={lossC:+.1f}单")
print(f"\n{MAIN_PAGE} 受影响组: 点击{c_af} 单{o_af} 实际人均{r_af:.4f}")

print("\n"+"="*66)
print("用户体验受损量（剔除不受影响品类）")
print("="*66)
a = bug[bug[COL_PLAT]==AFFECTED_PLAT]
click_aff = a[a[COL_CAT]==AFFECTED_CAT][COL_CLICK].sum()
click_ctrl = a[a[COL_CAT]==CONTROL_CAT][COL_CLICK].sum()
share = click_aff/(click_aff+click_ctrl)
uv_ex, pv_ex = CAND_UV*share, CAND_PV*share
print(f"受影响端点击结构: {AFFECTED_CAT}占比 {share*100:.1f}%")
print(f"候选上界(含所有品类): {CAND_UV:,} UV / {CAND_PV:,} PV")
print(f"剔除{CONTROL_CAT}后受损上界: {uv_ex:,.0f} UV / {pv_ex:,.0f} PV")
print(f"日均: {uv_ex/WINDOW_DAYS:,.0f} UV / {pv_ex/WINDOW_DAYS:,.0f} PV  (窗口{WINDOW_DAYS}天)")

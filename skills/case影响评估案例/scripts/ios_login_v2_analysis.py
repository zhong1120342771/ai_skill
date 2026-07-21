"""iOS 一键登录 bug 影响 · v2 口径重算
调整原因：点击登陆埋点研发侧验证有问题，重新取数（点击登陆 UV 口径收窄）。
登录成功 UV 不变；点击登陆 UV 及其 cohort 的成单/GMV 随口径变化。

数据：
  A. 点击登陆和成功登陆_v2.csv : dt × 设备类型 × {点击登陆,登录成功} → 用户量
  B. 点击登陆用户的成单和gmv_v2.csv : dt × 设备类型 → 点击登陆uv,支付用户数,单量,GMV

方法：
  体验影响 = iOS 登录成功缺口（同端 android 逐日趋势反事实 DiD）
  单量影响 = iOS 点击登陆-cohort 单量/GMV 的跨端 DiD + 时间 DiD
"""
import csv
from datetime import datetime
from pathlib import Path

DL = Path.home() / 'Downloads'
F_LOGIN = DL / '点击登陆和成功登陆_v2.csv'
F_ORDER = DL / '点击登陆用户的成单和gmv_v2.csv'

BASE = [datetime(2026,6,28), datetime(2026,7,5)]   # 灰度前基线（含）
WIN  = [datetime(2026,7,6),  datetime(2026,7,14)]  # 灰度窗（含），9天
WIN_DAYS = 9

def kd(s): return datetime.strptime(s, '%Y/%m/%d')
def inb(d): return BASE[0] <= d <= BASE[1]
def inw(d): return WIN[0]  <= d <= WIN[1]

# ---------- 读登录数据 ----------
login = {}  # (dt, plat) -> {点击登陆, 登录成功}
with open(F_LOGIN, encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        d = kd(r['dt']); p = r['设备类型']
        login.setdefault((d,p), {})[r['tag']] = int(r['用户量'])

# ---------- 读成单数据 ----------
order = {}  # (dt, plat) -> dict
with open(F_ORDER, encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        d = kd(r['dt']); p = r['设备类型']
        order[(d,p)] = {'click': int(r['点击登陆uv']), 'payuv': int(r['支付用户数']),
                        'ord': int(r['单量']), 'gmv': float(r['GMV'])}

def avg(vals): return sum(vals)/len(vals)
def series(dct, key, plat, phase):
    sel = inb if phase=='base' else inw
    return [dct[(d,p)][key] for (d,p) in dct if p==plat and sel(d)]

print("="*70)
print("一、登录成功 UV（体验）——基线 vs 灰度窗 日均")
print("="*70)
for plat in ['iOS','android']:
    b = avg([login[(d,p)]['登录成功'] for (d,p) in login if p==plat and inb(d)])
    w = avg([login[(d,p)]['登录成功'] for (d,p) in login if p==plat and inw(d)])
    print(f"{plat:8} 登录成功 基线日均={b:,.0f}  灰度窗日均={w:,.0f}  变化={w/b-1:+.1%}")

# 体验 DiD：iOS 登录成功缺口，反事实 = iOS基线日均 × (android当日/android基线日均)
print("\n"+"-"*70)
print("iOS 登录成功缺口（DiD，android 逐日趋势反事实）")
print("-"*70)
ios_succ_base = avg([login[(d,p)]['登录成功'] for (d,p) in login if p=='iOS' and inb(d)])
and_succ_base = avg([login[(d,p)]['登录成功'] for (d,p) in login if p=='android' and inb(d)])
win_days = sorted({d for (d,p) in login if inw(d)})
gap_total = 0; peak=(None,0)
print(f"{'日期':<10}{'iOS实际':>10}{'反事实':>10}{'缺口':>10}")
for d in win_days:
    ios_a = login[(d,'iOS')]['登录成功']
    and_a = login[(d,'android')]['登录成功']
    cf = ios_succ_base * (and_a/and_succ_base)
    gap = cf - ios_a
    gap_total += gap
    if gap>peak[1]: peak=(d,gap)
    print(f"{d.strftime('%m-%d'):<10}{ios_a:>10,.0f}{cf:>10,.0f}{gap:>+10,.0f}")
print(f"{'累计':<10}{'':>10}{'':>10}{gap_total:>+10,.0f}")
print(f"日均缺口 = {gap_total/WIN_DAYS:,.0f} 人·天   峰值 {peak[0].strftime('%m-%d')} = {peak[1]:+,.0f}")

print("\n"+"="*70)
print("二、点击登陆 UV（口径已收窄）——基线 vs 灰度窗 日均")
print("="*70)
for plat in ['iOS','android']:
    b = avg(series(order,'click',plat,'base'))
    w = avg(series(order,'click',plat,'win'))
    print(f"{plat:8} 点击登陆UV 基线日均={b:,.0f}  灰度窗日均={w:,.0f}  变化={w/b-1:+.1%}")

print("\n"+"="*70)
print("三、单量影响 —— 点击登陆 cohort 的成单，跨端 & 时间 DiD")
print("="*70)
for metric,label,unit in [('ord','单量','单'),('gmv','GMV','元')]:
    ios_b = avg(series(order,metric,'iOS','base'))
    ios_w = avg(series(order,metric,'iOS','win'))
    and_b = avg(series(order,metric,'android','base'))
    and_w = avg(series(order,metric,'android','win'))
    ratio_base = ios_b/and_b
    print(f"\n[{label}] 基线 iOS/android 结构比 = {ratio_base:.4f}")
    print(f"  iOS  基线日均={ios_b:,.0f}  灰度窗日均={ios_w:,.0f} ({ios_w/ios_b-1:+.1%})")
    print(f"  安卓 基线日均={and_b:,.0f}  灰度窗日均={and_w:,.0f} ({and_w/and_b-1:+.1%})")

    # 跨端 DiD 逐日
    print(f"  {'日期':<8}{'iOS实际':>12}{'反事实(跨端)':>14}{'缺口':>12}")
    tot_x = 0
    for d in win_days:
        ia = order[(d,'iOS')][metric]; aa = order[(d,'android')][metric]
        cf = aa*ratio_base; gap = cf-ia; tot_x += gap
        print(f"  {d.strftime('%m-%d'):<8}{ia:>12,.0f}{cf:>14,.0f}{gap:>+12,.0f}")
    print(f"  跨端DiD 累计缺口 = {tot_x:+,.0f} {unit}  (正=损失, 负=无损失/超出)")

    # 时间 DiD：iOS基线 × android窗/android基线
    cf_time = ios_b * (and_w/and_b)
    loss_time_daily = cf_time - ios_w
    print(f"  时间DiD 预期日均={cf_time:,.0f}  实际日均={ios_w:,.0f}  日均缺口={loss_time_daily:+,.0f}  累计≈{loss_time_daily*WIN_DAYS:+,.0f} {unit}")

    # 人均转化
    ios_click_b = avg(series(order,'click','iOS','base')); ios_click_w = avg(series(order,'click','iOS','win'))
    and_click_b = avg(series(order,'click','android','base')); and_click_w = avg(series(order,'click','android','win'))
    print(f"  人均{label}(/点击登陆uv): iOS {ios_b/ios_click_b:.5f}->{ios_w/ios_click_w:.5f}  安卓 {and_b/and_click_b:.5f}->{and_w/and_click_w:.5f}")

print("\n"+"="*70)
print("四、旧口径「登录成功率」在新口径下的问题")
print("="*70)
for d in [datetime(2026,7,5),datetime(2026,7,10),datetime(2026,7,13)]:
    c = login[(d,'iOS')]['点击登陆']; s = login[(d,'iOS')]['登录成功']
    print(f"iOS {d.strftime('%m-%d')}: 点击登陆={c:,}  登录成功={s:,}  成功/点击={s/c:.2f}  (>1，旧成功率口径失效)")

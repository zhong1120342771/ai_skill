"""iOS 一键登录 bug · v2 口径 3 张标准图"""
import csv
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'Arial Unicode MS'
matplotlib.rcParams['axes.unicode_minus'] = False

DL = Path.home() / 'Downloads'
OUT = Path.home() / '.claude' / 'visualizations' / 'ios_login_v2'
OUT.mkdir(parents=True, exist_ok=True)

def kd(s): return datetime.strptime(s, '%Y/%m/%d')
BASE=[datetime(2026,6,28),datetime(2026,7,5)]; WIN=[datetime(2026,7,6),datetime(2026,7,14)]
def inb(d): return BASE[0]<=d<=BASE[1]
def inw(d): return WIN[0]<=d<=WIN[1]

login={}
with open(DL/'点击登陆和成功登陆_v2.csv',encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        login.setdefault((kd(r['dt']),r['设备类型']),{})[r['tag']]=int(r['用户量'])
order={}
with open(DL/'点击登陆用户的成单和gmv_v2.csv',encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        order[(kd(r['dt']),r['设备类型'])]={'click':int(r['点击登陆uv']),'ord':int(r['单量']),'gmv':float(r['GMV'])}

def avg(v): return sum(v)/len(v)
win_days=sorted({d for (d,p) in login if inw(d)})
lbl=[d.strftime('%m-%d') for d in win_days]

BLUE='#2E5BFF'; ORANGE='#FF8A3D'; GREEN='#2FBF71'; GREY='#9AA0A6'; RED='#E5484D'

# ---------- 图1：iOS vs android 关键指标 基线 vs 灰度窗 对照 ----------
fig,axes=plt.subplots(1,2,figsize=(13,5))
# 左：登录成功日均（体验）
ios_s_b=avg([login[(d,'iOS')]['登录成功'] for d in login if 0] or [login[(d,p)]['登录成功'] for (d,p) in login if p=='iOS' and inb(d)])
ios_s_w=avg([login[(d,p)]['登录成功'] for (d,p) in login if p=='iOS' and inw(d)])
and_s_b=avg([login[(d,p)]['登录成功'] for (d,p) in login if p=='android' and inb(d)])
and_s_w=avg([login[(d,p)]['登录成功'] for (d,p) in login if p=='android' and inw(d)])
ax=axes[0]
x=[0,1]; w=0.35
ax.bar([i-w/2 for i in x],[ios_s_b/1e4,ios_s_w/1e4],w,label='iOS',color=BLUE)
ax.bar([i+w/2 for i in x],[and_s_b/1e4,and_s_w/1e4],w,label='安卓(对照)',color=GREY)
ax.set_xticks(x); ax.set_xticklabels(['灰度前基线','灰度窗']); ax.set_ylabel('登录成功 UV 日均（万人·天）')
ax.set_title(f'登录成功：iOS {ios_s_w/ios_s_b-1:+.0%} vs 安卓 {and_s_w/and_s_b-1:+.0%}',fontsize=11)
for i,(a,b) in enumerate([(ios_s_b,ios_s_w),(and_s_b,and_s_w)]): pass
for i,v in zip([0,1],[ios_s_b,ios_s_w]): ax.text(i-w/2,v/1e4,f'{v/1e4:.1f}',ha='center',va='bottom',fontsize=9,color=BLUE)
for i,v in zip([0,1],[and_s_b,and_s_w]): ax.text(i+w/2,v/1e4,f'{v/1e4:.1f}',ha='center',va='bottom',fontsize=9,color=GREY)
ax.legend()
# 右：点击登陆 cohort 人均单量（成单转化）
def click(p,ph): return avg([order[(d,q)]['click'] for (d,q) in order if q==p and (inb(d) if ph=='b' else inw(d))])
def od(p,ph): return avg([order[(d,q)]['ord'] for (d,q) in order if q==p and (inb(d) if ph=='b' else inw(d))])
ios_c_b=od('iOS','b')/click('iOS','b'); ios_c_w=od('iOS','w')/click('iOS','w')
and_c_b=od('android','b')/click('android','b'); and_c_w=od('android','w')/click('android','w')
ax=axes[1]
ax.bar([i-w/2 for i in x],[ios_c_b*1000,ios_c_w*1000],w,label='iOS',color=ORANGE)
ax.bar([i+w/2 for i in x],[and_c_b*1000,and_c_w*1000],w,label='安卓(对照)',color=GREY)
ax.set_xticks(x); ax.set_xticklabels(['灰度前基线','灰度窗']); ax.set_ylabel('点击登陆用户 人均单量（单/千人）')
ax.set_title('点击登陆用户成单转化：iOS 未下降反升',fontsize=11)
for i,v in zip([0,1],[ios_c_b,ios_c_w]): ax.text(i-w/2,v*1000,f'{v*1000:.1f}',ha='center',va='bottom',fontsize=9,color=ORANGE)
for i,v in zip([0,1],[and_c_b,and_c_w]): ax.text(i+w/2,v*1000,f'{v*1000:.1f}',ha='center',va='bottom',fontsize=9,color=GREY)
ax.legend()
fig.suptitle('图1 · iOS 一键登录 bug：登录体验受损，但点击登陆用户成单转化未降（安卓对照）',fontsize=12,fontweight='bold')
fig.tight_layout(); fig.savefig(OUT/'fig1_did_compare.png',dpi=140,bbox_inches='tight'); plt.close()

# ---------- 图2：单量损失区间（跨端+时间DiD，逐日缺口）----------
ratio=od('iOS','b')/od('android','b')
gap_x=[order[(d,'android')]['ord']*ratio-order[(d,'iOS')]['ord'] for d in win_days]
cf_time=od('iOS','b')*(od('android','w')/od('android','b'))
gap_t=[cf_time-order[(d,'iOS')]['ord'] for d in win_days]
fig,ax=plt.subplots(figsize=(11,5))
X=range(len(win_days)); w=0.38
def col(v): return GREEN if v<=0 else ORANGE
ax.bar([i-w/2 for i in X],gap_x,w,label='跨端 DiD 缺口',color=[col(v) for v in gap_x])
ax.bar([i+w/2 for i in X],gap_t,w,label='时间 DiD 缺口',color=[col(v) for v in gap_t],alpha=0.55)
ax.axhline(0,color='#333',lw=1)
ax.set_xticks(list(X)); ax.set_xticklabels(lbl); ax.set_ylabel('单量缺口（反事实 − iOS实际，单）')
ax.set_title(f'图2 · 点击登陆用户成单损失：两口径 DiD 全为负 → 无可测净损失\n累计 跨端 {sum(gap_x):+,.0f} 单 / 时间 {sum(gap_t):+,.0f} 单（负=实际≥预期）',fontsize=11,fontweight='bold')
for i,v in zip(X,gap_x): ax.text(i-w/2,v,f'{v:+.0f}',ha='center',va='top' if v<0 else 'bottom',fontsize=8,color=GREEN)
ax.text(0.98,0.06,'绿柱=iOS实际单量≥反事实 → 未测出损失',transform=ax.transAxes,fontsize=10,color=GREEN,va='bottom',ha='right')
ax.legend(loc='upper right'); fig.tight_layout(); fig.savefig(OUT/'fig2_order_loss_band.png',dpi=140,bbox_inches='tight'); plt.close()

# ---------- 图3：体验暴露 —— iOS 登录成功 实际 vs 反事实（缺口填充）----------
ios_b=avg([login[(d,p)]['登录成功'] for (d,p) in login if p=='iOS' and inb(d)])
and_b=avg([login[(d,p)]['登录成功'] for (d,p) in login if p=='android' and inb(d)])
actual=[login[(d,'iOS')]['登录成功'] for d in win_days]
cf=[ios_b*(login[(d,'android')]['登录成功']/and_b) for d in win_days]
fig,ax=plt.subplots(figsize=(11,5))
ax.plot(lbl,[c/1e4 for c in cf],'--',color=GREY,marker='o',label='反事实(无bug应有)')
ax.plot(lbl,[a/1e4 for a in actual],color=BLUE,marker='o',lw=2,label='iOS 实际登录成功')
ax.fill_between(range(len(lbl)),[a/1e4 for a in actual],[c/1e4 for c in cf],color=RED,alpha=0.18)
total=sum(c-a for c,a in zip(cf,actual))
ax.set_ylabel('登录成功 UV（万人·天）')
ax.set_title(f'图3 · iOS 登录成功缺口（体验受损规模）\n累计约 {total/1e4:.1f} 万人·天，日均约 {total/9/1e4:.2f} 万，峰值 07-11',fontsize=11,fontweight='bold')
ax.annotate(f'累计缺口≈{total/1e4:.1f}万人·天',xy=(5,actual[5]/1e4),xytext=(3.2,(actual[5]+30000)/1e4),
            color=RED,fontsize=11,arrowprops=dict(arrowstyle='->',color=RED))
ax.legend(); fig.tight_layout(); fig.savefig(OUT/'fig3_exposure.png',dpi=140,bbox_inches='tight'); plt.close()
print('OK ->',OUT)
for p in sorted(OUT.glob('*.png')): print(p.name)

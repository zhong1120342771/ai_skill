"""补充视角(系数法/上界法) 配图"""
import csv
from datetime import datetime
from pathlib import Path
import matplotlib, matplotlib.pyplot as plt
matplotlib.rcParams['font.family']='Arial Unicode MS'; matplotlib.rcParams['axes.unicode_minus']=False
DL=Path.home()/'Downloads'; OUT=Path.home()/'.claude'/'visualizations'/'ios_login_v2'; OUT.mkdir(parents=True,exist_ok=True)
def kd(s): return datetime.strptime(s,'%Y/%m/%d')
BASE=[datetime(2026,6,28),datetime(2026,7,5)]; WIN=[datetime(2026,7,6),datetime(2026,7,14)]
def inb(d): return BASE[0]<=d<=BASE[1]
def inw(d): return WIN[0]<=d<=WIN[1]
login={}
with open(DL/'点击登陆和成功登陆_v2.csv',encoding='utf-8-sig') as f:
    for r in csv.DictReader(f): login.setdefault((kd(r['dt']),r['设备类型']),{})[r['tag']]=int(r['用户量'])
def avg(v): return sum(v)/len(v)
ios_b=avg([login[(d,p)]['登录成功'] for (d,p) in login if p=='iOS' and inb(d)])
and_b=avg([login[(d,p)]['登录成功'] for (d,p) in login if p=='android' and inb(d)])
days=sorted({d for (d,p) in login if inw(d)}); lbl=[d.strftime('%m-%d') for d in days]
gap=[ios_b*(login[(d,'android')]['登录成功']/and_b)-login[(d,'iOS')]['登录成功'] for d in days]

BLUE='#2E5BFF'; ORANGE='#FF8A3D'; GREEN='#2FBF71'; GREY='#9AA0A6'
fig,axes=plt.subplots(1,2,figsize=(13,5))
ax=axes[0]
bars=ax.bar(lbl,[g/1e4 for g in gap],color=BLUE)
bars[gap.index(max(gap))].set_color(ORANGE)
ax.set_ylabel('受影响UV / 登录成功缺口（万人·天）')
ax.set_title(f'受影响UV逐日（登录成功缺口）\n累计约{sum(gap)/1e4:.1f}万人·天，日均约{sum(gap)/9/1e4:.2f}万，峰值07-11',fontsize=11)
for b,g in zip(bars,gap): ax.text(b.get_x()+b.get_width()/2,g/1e4,f'{g/1e4:.1f}',ha='center',va='bottom',fontsize=8)

ax=axes[1]
labels=['上界·点击登陆\n用户人均口径','上界·登录成功\n平均口径(doc1)','DiD实测\n净损失']
vals=[4578,6562,0]
cols=[ORANGE,'#C24E00',GREEN]
b=ax.bar(labels,vals,color=cols)
ax.set_ylabel('单量（单）')
ax.set_title('毛损失上界区间 vs DiD实测净损失',fontsize=11)
for bi,v in zip(b,vals):
    ax.text(bi.get_x()+bi.get_width()/2,v+80,('≈0（未测出损失）' if v==0 else f'{v:,}单'),ha='center',va='bottom',fontsize=9)
ax.set_ylim(0,7600)
ax.annotate('区间约 4,600~6,600 单\n实际实现远低于上界\n（重试/改期回补）',xy=(1,3300),fontsize=9,color='#555',ha='center')
fig.suptitle('图 · 补充视角(上界法)：受影响UV × 人均产出，与DiD实测夹出损失区间',fontsize=12,fontweight='bold')
fig.tight_layout(); fig.savefig(OUT/'fig4_upperbound.png',dpi=140,bbox_inches='tight'); plt.close()
print('OK', OUT/'fig4_upperbound.png')

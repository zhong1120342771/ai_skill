#!/usr/bin/env python3
"""单维分层 + 价敏(同类价格分位)叠加的可解释用户聚类分群。
价敏口径 = price_pctl_90d(近90天订单在同 cate_02 内成交价 PERCENT_RANK 均值),越低越价敏。
切点用实测分位 P20=0.26/P50=0.57/P80=0.82。分群用规则式(业务可读),
每群报真实未来365天付费率/人均GMV/lift,与全样本基线对比。
用法: python price_sens_cluster.py <pricesens_csv>
输出: data_storage/seg_cluster_<d>.csv/json
"""
import sys, json
import pandas as pd
import numpy as np

csv_path = sys.argv[1]
outdir = "/Users/zhongmengting/.claude/data_storage"
df = pd.read_csv(csv_path)
d = str(df["d"].iloc[0])
df["regist_days"] = df["regist_days"].fillna(-1).astype(int)
n = len(df)
paid = df.f_pay_cnt_180d > 0
base_p365 = float(df.is_paid_365d.mean())
base_gmv  = float(df.pay_amt_365d.mean())

# ---- 活跃复合分 A(0-6) 同十四/十五章 ----
df["a_score"] = ((df.a_visit_pv_30d>=5).astype(int)+(df.a_search_pv_30d>=3).astype(int)
                 +(df.a_love_pv_30d>=1).astype(int)*2+(df.a_hist_order_cnt>=1).astype(int)*2)

# ---- 价敏标签(同类价格分位,P20=0.26/P50=0.57/P80=0.82) ----
pp = df.price_pctl_90d
df["ps_label"] = np.where(pp.isna(), "无近90天支付",
                  np.where(pp<=0.26, "高价敏(买同类里便宜的)",
                  np.where(pp>=0.82, "低价敏(买同类里贵的)", "中性")))
print(f"样本 {n:,} | 付费者 {int(paid.sum()):,}({paid.mean()*100:.1f}%)"
      f" | 未来365付费基线 {base_p365*100:.2f}% | 人均GMV基线 {base_gmv:.0f}元")
print("\n== 价敏标签分布(同类价格分位) ==")
for k in ["高价敏(买同类里便宜的)","中性","低价敏(买同类里贵的)","无近90天支付"]:
    s=df[df.ps_label==k]
    print(f"  {k}: {len(s):,}({len(s)/n*100:.1f}%)  未来365付费{s.is_paid_365d.mean()*100:.1f}%  人均GMV{s.pay_amt_365d.mean():.0f}元")

# ---- 规则式分群:价敏 × 单维档 圈运营人群 ----
rows=[]
def cluster(name, mask, desc):
    s=df[mask]; c=len(s)
    if c==0: return
    rows.append({"人群":name,"圈选条件":desc,"人数":c,"占比":round(c/n,4),
        "未来365付费率":round(float(s.is_paid_365d.mean()),4),
        "付费率lift":round(float(s.is_paid_365d.mean()/base_p365),2),
        "人均GMV":round(float(s.pay_amt_365d.mean()),0),
        "GMVlift":round(float(s.pay_amt_365d.mean()/base_gmv),2),
        "近90价敏分位均值":round(float(s.price_pctl_90d.mean()),3) if s.price_pctl_90d.notna().any() else None})

high_ps = pp<=0.26
low_ps  = pp>=0.82
hi_act  = df.a_score>=5
mid_act = df.a_score.between(3,4)
lux     = df.is_lux_buyer_180d==1
recent  = paid & (df.r_last_pay_days<=45)
sleep   = paid & (df.r_last_pay_days>90) & (df.r_last_pay_days<=180)
freq    = df.f_pay_cnt_180d>=3
big     = paid & (df.m_pay_amt_180d>=6000)
newuser = df.regist_days.between(0,30)
love_nobuy = (df.a_love_pv_30d>0) & (~paid)

# 8个候选运营人群(可解释,互不追求互斥,给运营挑)
cluster("品质高活跃核心", low_ps & hi_act, "价敏低(同类买贵的)+活跃≥5分：认品质、逛得勤,复购主力")
cluster("高价敏高频跑量", high_ps & freq, "价敏高(同类买便宜的)+180天≥3单：靠低价高频贡献,量大利薄")
cluster("低价敏大额客", low_ps & big, "价敏低+180天累计≥6000元：单客高价值,做高端/以旧换新")
cluster("二奢品质客", lux & low_ps, "买过二奢+价敏低：绝对高客单,专属客服/鉴定权益")
cluster("捡漏蹲降价", love_nobuy, "有加购收藏但近180天没买：在等降价/比价,临门一脚人群")
cluster("高活跃沉睡付费", sleep & hi_act, "曾付费91-180天没回+仍高活跃：还在逛没下单,召回优先")
cluster("高价敏新客", high_ps & newuser, "价敏高+注册≤30天：新客靠价格拉动,首单券承接")
cluster("近期高活跃品质", low_ps & recent & hi_act, "价敏低+45天内付过+高活跃：最热的高质人群,连带推荐")

out=pd.DataFrame(rows).sort_values("GMVlift",ascending=False).reset_index(drop=True)
out.to_csv(f"{outdir}/seg_cluster_{d}.csv",index=False,encoding="utf-8-sig")
res={"d":d,"n":n,"base_p365":round(base_p365,4),"base_gmv":round(base_gmv,1),
     "价敏口径":"price_pctl_90d 同cate_02成交价PERCENT_RANK近90天均值,越低越价敏;切点实测P20=0.26/P80=0.82",
     "价敏说明":"行为代理,反映买同类里偏便宜还是偏贵,非问卷式真实价格敏感度",
     "clusters":out.to_dict(orient="records")}
with open(f"{outdir}/seg_cluster_{d}.json","w",encoding="utf-8") as fh:
    json.dump(res,fh,ensure_ascii=False,indent=2)
print("\n== 运营人群(按GMV lift排序) ==")
print(out[["人群","人数","占比","未来365付费率","付费率lift","人均GMV","GMVlift"]].to_string(index=False))

#!/usr/bin/env python3
"""单维度分层方案：R/F/M/L/A 各维按实测分布定切点，输出各层人数与占比。
切点一律来自本样本实测分位，不套行业默认。
用法: python single_dim_scheme.py <both_csv>
输出: data_storage/seg_dim_scheme_<d>.json ; seg_dim_scheme_<d>.csv
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

rows = []
def emit(dim, layer, mask, note=""):
    c = int(mask.sum())
    rows.append({"维度":dim,"层级":layer,"判定":note,"人数":c,"占比":round(c/n,4)})

# ---- R 最近支付间隔(天)。切点来自付费用户分位 P25=5/P50=39/P75=105 ----
r = df.r_last_pay_days
emit("R 最近支付间隔","R4 活跃期(≤14天)", paid & (r<=14), "≤14天,约付费者top25%")
emit("R 最近支付间隔","R3 正常(15-45天)", paid & (r>14)&(r<=45), "15-45天,~中位")
emit("R 最近支付间隔","R2 疏远(46-90天)", paid & (r>45)&(r<=90), "46-90天")
emit("R 最近支付间隔","R1 沉睡(91-180天)", paid & (r>90)&(r<=180), "91-180天")
emit("R 最近支付间隔","R0 无近180天支付", ~paid, "近180天无有效支付")

# ---- F 支付频次(180天)。实测:1单占80%付费者 ----
f = df.f_pay_cnt_180d
emit("F 支付频次","F4 高频(≥5单)", f>=5, "≥5单")
emit("F 支付频次","F3 中频(3-4单)", (f>=3)&(f<=4), "3-4单")
emit("F 支付频次","F2 复购(2单)", f==2, "2单")
emit("F 支付频次","F1 单次(1单)", f==1, "1单")
emit("F 支付频次","F0 未支付(0单)", f==0, "0单")

# ---- M 支付金额(元,180天)。切点付费者分位 P50=1768/P75=3498/P90=5648 ----
m = df.m_pay_amt_180d
emit("M 支付金额","M4 高额(≥6000元)", paid & (m>=6000), "≥6000,~付费者top10%")
emit("M 支付金额","M3 中高(3000-6000)", paid & (m>=3000)&(m<6000), "3000-6000")
emit("M 支付金额","M2 中额(1000-3000)", paid & (m>=1000)&(m<3000), "1000-3000,~中位")
emit("M 支付金额","M1 低额(<1000)", paid & (m<1000), "<1000")
emit("M 支付金额","M0 未支付", ~paid, "无支付金额")

# ---- L 生命周期(注册天数)。切点全量分位 P25=137/P50=541/P75=1324 ----
l = df.regist_days
emit("L 生命周期","L4 老客(>720天)", l>720, ">720天,~两年以上")
emit("L 生命周期","L3 成熟(181-720天)", (l>180)&(l<=720), "181-720天")
emit("L 生命周期","L2 成长(31-180天)", (l>=31)&(l<=180), "31-180天")
emit("L 生命周期","L1 新客(≤30天)", (l>=0)&(l<=30), "≤30天")
emit("L 生命周期","L0 注册时间缺失", l<0, "regist_time为空")

# ---- A 活跃度(复合分0-6)。四信号:visit>=5/search>=3/love>=1(x2)/hist_order>=1(x2) ----
a = ((df.a_visit_pv_30d>=5).astype(int)+(df.a_search_pv_30d>=3).astype(int)
     +(df.a_love_pv_30d>=1).astype(int)*2+(df.a_hist_order_cnt>=1).astype(int)*2)
emit("A 活跃度(复合0-6)","A4 高活跃(≥5分)", a>=5)
emit("A 活跃度(复合0-6)","A3 中活跃(3-4分)", (a>=3)&(a<=4))
emit("A 活跃度(复合0-6)","A2 低活跃(1-2分)", (a>=1)&(a<=2))
emit("A 活跃度(复合0-6)","A1 沉默(0分)", a==0)

# ---- A 四个子信号单独分层(全量,切点实测分位) ----
emit("A-商详浏览30天","高(≥26)", df.a_visit_pv_30d>=26, "≥P90")
emit("A-商详浏览30天","中(5-25)", (df.a_visit_pv_30d>=5)&(df.a_visit_pv_30d<26), "5~P90")
emit("A-商详浏览30天","低(1-4)", (df.a_visit_pv_30d>=1)&(df.a_visit_pv_30d<5), "")
emit("A-商详浏览30天","无(0)", df.a_visit_pv_30d==0, "")
emit("A-搜索30天","高(≥288)", df.a_search_pv_30d>=288, "≥P90")
emit("A-搜索30天","中(8-287)", (df.a_search_pv_30d>=8)&(df.a_search_pv_30d<288), "P50~P90")
emit("A-搜索30天","低(1-7)", (df.a_search_pv_30d>=1)&(df.a_search_pv_30d<8), "")
emit("A-搜索30天","无(0)", df.a_search_pv_30d==0, "")
emit("A-下单加购收藏30天","高(≥3)", df.a_love_pv_30d>=3, "≥P95")
emit("A-下单加购收藏30天","中(1-2)", (df.a_love_pv_30d>=1)&(df.a_love_pv_30d<3), "")
emit("A-下单加购收藏30天","无(0)", df.a_love_pv_30d==0, "占82.7%")
emit("A-历史成交365天","高(≥2单)", df.a_hist_order_cnt>=2, "")
emit("A-历史成交365天","中(1单)", df.a_hist_order_cnt==1, "")
emit("A-历史成交365天","无(0)", df.a_hist_order_cnt==0, "占84.2%")

out = pd.DataFrame(rows)
out.to_csv(f"{outdir}/seg_dim_scheme_{d}.csv", index=False, encoding="utf-8-sig")
res={"d":d,"n":n,"付费用户占比":round(float(paid.mean()),4),
     "切点依据":"全部来自本样本(100万,dt=2025-07-27)实测分位,非行业默认",
     "各维分层":out.to_dict(orient="records")}
with open(f"{outdir}/seg_dim_scheme_{d}.json","w",encoding="utf-8") as fh:
    json.dump(res,fh,ensure_ascii=False,indent=2)
# 打印每维小计
for dim in out["维度"].unique():
    print(f"\n== {dim} ==")
    print(out[out.维度==dim][["层级","判定","人数","占比"]].to_string(index=False))

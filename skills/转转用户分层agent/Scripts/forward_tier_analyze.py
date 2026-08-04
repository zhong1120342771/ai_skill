#!/usr/bin/env python3
"""分层×前瞻转化/LTV 后验分析。

用法: python forward_tier_analyze.py <csv> <outcome_kind>
  outcome_kind = 7d  -> 期望列 order_cnt_7d / is_paid_7d ，输出各层7日净支付转化率
  outcome_kind = 1y  -> 期望列 order_cnt_1y / is_paid_1y / pay_amt_1y，输出各层1年转化率+人均单量+人均GMV(LTV)

分层：截至抽样日的 5 维等权 RFLA(+M) 打分 → L1-L5（阈值同探索结论 L5≥16/L4≥12/L3≥6/L2≥4）。
输出: data_storage/seg_tier_<kind>_<d>.csv  各层转化率/LTV 表
"""
import sys, json
import pandas as pd
import numpy as np

csv_path, kind = sys.argv[1], sys.argv[2]
outdir = "/Users/zhongmengting/.claude/data_storage"
df = pd.read_csv(csv_path)
d = str(df["d"].iloc[0])
df["regist_days"] = df["regist_days"].fillna(-1).astype(int)
n = len(df)

# 5 维等权打分（与探索阶段 score_old 一致：R3+F4+M3+L3+A6，满分19）
r = np.select([df.r_last_pay_days<=30, df.r_last_pay_days<=90, df.r_last_pay_days<=180],[3,2,1],0)
f = np.select([df.f_pay_cnt_180d>=5, df.f_pay_cnt_180d>=3, df.f_pay_cnt_180d==2, df.f_pay_cnt_180d==1],[4,3,2,1],0)
m = np.select([df.m_pay_amt_180d>=10000, df.m_pay_amt_180d>=1000, df.m_pay_amt_180d>=100],[3,2,1],0)
l = np.select([(df.regist_days>=0)&(df.regist_days<=30),
               (df.regist_days>=31)&(df.regist_days<=180),
               (df.regist_days>180)&(df.f_pay_cnt_180d>=1)],[1,2,3],0)
a = ((df.a_visit_pv_30d>=5).astype(int) + (df.a_search_pv_30d>=3).astype(int)
     + (df.a_love_pv_30d>=1).astype(int)*2 + (df.a_hist_order_cnt>=1).astype(int)*2)
df["total_score"] = r+f+m+l+a
# 分层阈值（探索结论：5维等权按分位重设）
df["tier"] = np.select(
    [df.total_score>=16, df.total_score>=12, df.total_score>=6, df.total_score>=4],
    ["L5","L4","L3","L2"], "L1")

if kind == "7d":
    paid_col, cnt_col = "is_paid_7d", "order_cnt_7d"
    amt_col = None
    label = "活跃后7日内净支付"
else:
    paid_col, cnt_col, amt_col = "is_paid_1y", "order_cnt_1y", "pay_amt_1y"
    label = "未来一年净支付"

order = ["L5","L4","L3","L2","L1"]
rows = []
for t in order:
    g = df[df.tier==t]
    row = {"层级": t, "用户数": len(g), "占比": round(len(g)/n,4),
           f"{label}转化率": round(g[paid_col].mean(),4),
           "人均订单量": round(g[cnt_col].mean(),4)}
    if amt_col:
        row["人均GMV(LTV,元)"] = round(g[amt_col].mean(),2)
        paid = g[g[paid_col]==1]
        row["付费用户人均GMV(元)"] = round(paid[amt_col].mean(),2) if len(paid) else 0.0
    rows.append(row)
# 全量行
allrow = {"层级":"全量","用户数":n,"占比":1.0,
          f"{label}转化率":round(df[paid_col].mean(),4),
          "人均订单量":round(df[cnt_col].mean(),4)}
if amt_col:
    allrow["人均GMV(LTV,元)"]=round(df[amt_col].mean(),2)
    paidall=df[df[paid_col]==1]
    allrow["付费用户人均GMV(元)"]=round(paidall[amt_col].mean(),2) if len(paidall) else 0.0
rows.append(allrow)

out = pd.DataFrame(rows)
p = f"{outdir}/seg_tier_{kind}_{d}.csv"
out.to_csv(p, index=False, encoding="utf-8-sig")
print(f"[{kind}] d={d}, n={n}  -> {p}")
print(out.to_string(index=False))

# 单调性校验（L5→L1 转化率应递减）
conv = [df[df.tier==t][paid_col].mean() for t in order]
mono = all(conv[i] >= conv[i+1] for i in range(len(conv)-1))
print(f"\n[单调性] 转化率 L5→L1 逐层递减: {mono}  ({[round(c,4) for c in conv]})")

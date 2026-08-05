#!/usr/bin/env python3
"""对比分层体系对 7日 vs 365日 净支付转化的预测精确度。
指标：AUC(Mann-Whitney,基率无关,可跨窗口公平比) / KS / top层lift / 各分位命中。
用法: python window_accuracy_compare.py <both_csv>
输出:
  data_storage/seg_window_acc_<d>.json     AUC/KS/lift 对比
  data_storage/seg_window_roc_<d>.csv       两窗口 ROC 点(供画图)
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

# 连续排序分 total_score（同打层口径，作为预测打分）
r = np.select([df.r_last_pay_days<=30, df.r_last_pay_days<=90, df.r_last_pay_days<=180],[3,2,1],0)
f = np.select([df.f_pay_cnt_180d>=5, df.f_pay_cnt_180d>=3, df.f_pay_cnt_180d==2, df.f_pay_cnt_180d==1],[4,3,2,1],0)
m = np.select([df.m_pay_amt_180d>=10000, df.m_pay_amt_180d>=1000, df.m_pay_amt_180d>=100],[3,2,1],0)
l = np.select([(df.regist_days>=0)&(df.regist_days<=30),(df.regist_days>=31)&(df.regist_days<=180),(df.regist_days>180)&(df.f_pay_cnt_180d>=1)],[1,2,3],0)
a = ((df.a_visit_pv_30d>=5).astype(int)+(df.a_search_pv_30d>=3).astype(int)+(df.a_love_pv_30d>=1).astype(int)*2+(df.a_hist_order_cnt>=1).astype(int)*2)
score = (r+f+m+l+a).astype(float)
df["score"] = score
df["tier"] = np.select([score>=16,score>=12,score>=6,score>=4],["L5","L4","L3","L2"],"L1")

def auc_mannwhitney(s, y):
    # AUC = P(score_pos > score_neg)，用秩：U 统计量法，含并列 0.5 权重
    order = np.argsort(s, kind="mergesort")
    s_sorted = s[order]
    ranks = pd.Series(s).rank(method="average").to_numpy()
    n_pos = int(y.sum()); n_neg = len(y)-n_pos
    if n_pos==0 or n_neg==0: return float("nan")
    sum_ranks_pos = ranks[y==1].sum()
    auc = (sum_ranks_pos - n_pos*(n_pos+1)/2) / (n_pos*n_neg)
    return float(auc)

def ks_stat(s, y):
    # KS = max |CDF_pos - CDF_neg| 沿 score 降序累积
    dfk = pd.DataFrame({"s":s,"y":y}).sort_values("s", ascending=False)
    P = dfk.y.sum(); N = len(dfk)-P
    cum_p = (dfk.y.cumsum())/P
    cum_n = ((1-dfk.y).cumsum())/N
    return float((cum_p-cum_n).abs().max())

def roc_points(s, y, k=100):
    dfr = pd.DataFrame({"s":s,"y":y}).sort_values("s", ascending=False)
    P = dfr.y.sum(); N = len(dfr)-P
    tp = dfr.y.cumsum().to_numpy()
    fp = (1-dfr.y).cumsum().to_numpy()
    tpr = tp/P; fpr = fp/N
    idx = np.linspace(0, len(dfr)-1, k).astype(int)
    return fpr[idx], tpr[idx]

order_l = ["L5","L4","L3","L2","L1"]
res = {"d": d, "n": n}
roc_rows = []
for win, ycol, cntcol in [("7d","is_paid_7d","order_cnt_7d"), ("365d","is_paid_365d","order_cnt_365d")]:
    y = df[ycol].to_numpy().astype(int)
    base = y.mean()
    auc = auc_mannwhitney(score.to_numpy(), y)
    ks = ks_stat(score.to_numpy(), y)
    # top层(L5)与top10%(按score阈值≥6即L3+)lift
    l5 = df[df.tier=="L5"]; l5_rate = l5[ycol].mean()
    top_score = df[df.score>=12]  # L4+ ~ top5%
    lift_l5 = l5_rate/base if base>0 else float("nan")
    # 各层转化率
    tier_rate = {t: round(df[df.tier==t][ycol].mean(),4) for t in order_l}
    res[win] = {
        "base_rate": round(float(base),4),
        "AUC": round(auc,4),
        "KS": round(ks,4),
        "L5转化率": round(float(l5_rate),4),
        "L5_lift(倍)": round(float(lift_l5),2),
        "各层转化率": tier_rate,
    }
    fpr, tpr = roc_points(score.to_numpy(), y)
    for a_,b_ in zip(fpr,tpr):
        roc_rows.append({"window":win,"fpr":round(float(a_),4),"tpr":round(float(b_),4)})

res["结论"] = ("AUC 基率无关，可跨窗口公平比较排序能力；AUC 更高的窗口=分层把付费用户排到高分层的判别力更强。"
              f" 7d_AUC={res['7d']['AUC']} vs 365d_AUC={res['365d']['AUC']}")
res["更精确的窗口"] = "365d" if res["365d"]["AUC"]>res["7d"]["AUC"] else "7d"

pd.DataFrame(roc_rows).to_csv(f"{outdir}/seg_window_roc_{d}.csv", index=False, encoding="utf-8-sig")
with open(f"{outdir}/seg_window_acc_{d}.json","w",encoding="utf-8") as fh:
    json.dump(res, fh, ensure_ascii=False, indent=2)
print(json.dumps(res, ensure_ascii=False, indent=2))

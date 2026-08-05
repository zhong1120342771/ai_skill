#!/usr/bin/env python3
"""对比两套分层体系对净支付的预测力：RFMLAP价值层(total_score) vs 资产分层(z0-z5)。
同队列 seg_both，两套打分各自算 7d/365d 的 AUC/KS/L5(或z5)lift，同表比较。
用法: python asset_vs_rfmlap_compare.py <both_csv>
输出:
  data_storage/seg_sys_compare_<d>.json
  data_storage/seg_sys_roc_<d>.csv   4条ROC(2体系×2窗口)
"""
import sys, json
import pandas as pd
import numpy as np

csv_path = sys.argv[1]
outdir = "/Users/zhongmengting/.claude/data_storage"
df = pd.read_csv(csv_path)
d = str(df["d"].iloc[0])
df["regist_days"] = df["regist_days"].fillna(-1).astype(int)

# ---- RFMLAP 打分 ----
r = np.select([df.r_last_pay_days<=30, df.r_last_pay_days<=90, df.r_last_pay_days<=180],[3,2,1],0)
f = np.select([df.f_pay_cnt_180d>=5, df.f_pay_cnt_180d>=3, df.f_pay_cnt_180d==2, df.f_pay_cnt_180d==1],[4,3,2,1],0)
m = np.select([df.m_pay_amt_180d>=10000, df.m_pay_amt_180d>=1000, df.m_pay_amt_180d>=100],[3,2,1],0)
l = np.select([(df.regist_days>=0)&(df.regist_days<=30),(df.regist_days>=31)&(df.regist_days<=180),(df.regist_days>180)&(df.f_pay_cnt_180d>=1)],[1,2,3],0)
a = ((df.a_visit_pv_30d>=5).astype(int)+(df.a_search_pv_30d>=3).astype(int)+(df.a_love_pv_30d>=1).astype(int)*2+(df.a_hist_order_cnt>=1).astype(int)*2)
df["rfmlap_score"] = (r+f+m+l+a).astype(float)

# ---- 资产层打分：z0-z5 -> 0..5 序数 ----
df["asset_score"] = df["user_type"].astype(str).str.extract(r"z(\d)").astype(float)
# 缺资产层的行两套都参与时会不公平，做两套对比时统一只取有资产层的用户
df = df[df["asset_score"].notna()].copy()
n = len(df)

def auc_mw(s, y):
    ranks = pd.Series(s).rank(method="average").to_numpy()
    n_pos = int(y.sum()); n_neg = len(y)-n_pos
    if n_pos==0 or n_neg==0: return float("nan")
    return float((ranks[y==1].sum() - n_pos*(n_pos+1)/2)/(n_pos*n_neg))

def ks_stat(s, y):
    dfk = pd.DataFrame({"s":s,"y":y}).sort_values("s", ascending=False)
    P=dfk.y.sum(); N=len(dfk)-P
    return float(((dfk.y.cumsum())/P - ((1-dfk.y).cumsum())/N).abs().max())

def roc_points(s, y, k=120):
    dfr = pd.DataFrame({"s":s,"y":y}).sort_values("s", ascending=False)
    P=dfr.y.sum(); N=len(dfr)-P
    tpr=(dfr.y.cumsum()/P).to_numpy(); fpr=((1-dfr.y).cumsum()/N).to_numpy()
    idx=np.linspace(0,len(dfr)-1,k).astype(int)
    return fpr[idx], tpr[idx]

res = {"d": d, "n_with_asset": n,
       "note":"同队列同一批用户,两套体系各自打分对同一净支付outcome算AUC/KS;AUC基率无关可直接比谁排序判别力更强"}
roc_rows=[]
for sysname, scol in [("RFMLAP价值层","rfmlap_score"),("资产分层z0-z5","asset_score")]:
    res[sysname]={}
    for win,ycol in [("7d","is_paid_7d"),("365d","is_paid_365d")]:
        y=df[ycol].to_numpy().astype(int); base=y.mean()
        s=df[scol].to_numpy()
        auc=auc_mw(s,y); ks=ks_stat(s,y)
        # 头部层：RFMLAP取score>=16(L5),资产取z5
        if scol=="rfmlap_score": topmask = df.rfmlap_score>=16
        else: topmask = df.asset_score>=5
        top_rate=df[topmask][ycol].mean(); top_share=topmask.mean()
        res[sysname][win]={"base_rate":round(float(base),4),"AUC":round(auc,4),"KS":round(ks,4),
            "头部层":"L5" if scol=="rfmlap_score" else "z5",
            "头部层占比":round(float(top_share),4),"头部层转化率":round(float(top_rate),4),
            "头部层lift":round(float(top_rate/base),2) if base>0 else None}
        fpr,tpr=roc_points(s,y)
        for x_,t_ in zip(fpr,tpr):
            roc_rows.append({"system":sysname,"window":win,"fpr":round(float(x_),4),"tpr":round(float(t_),4)})

# 结论：谁AUC更高
concl={}
for win in ["7d","365d"]:
    ar=res["RFMLAP价值层"][win]["AUC"]; az=res["资产分层z0-z5"][win]["AUC"]
    concl[win]={"RFMLAP_AUC":ar,"资产层_AUC":az,"更强":"RFMLAP" if ar>az else "资产层","AUC差":round(ar-az,4)}
res["对比结论"]=concl

pd.DataFrame(roc_rows).to_csv(f"{outdir}/seg_sys_roc_{d}.csv", index=False, encoding="utf-8-sig")
with open(f"{outdir}/seg_sys_compare_{d}.json","w",encoding="utf-8") as fh:
    json.dump(res, fh, ensure_ascii=False, indent=2)
print(json.dumps(res, ensure_ascii=False, indent=2))

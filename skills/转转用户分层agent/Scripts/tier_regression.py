#!/usr/bin/env python3
"""分层预测力的回归验证：不只看排序(AUC)，看能解释多少变异(R²)与分层校准。
- OLS 回归预测 未来订单量 / 未来GMV(LTV)，看 R²（全体用户的可解释方差，非仅头部）。
- Logistic 回归预测 是否付费，看 McFadden 伪R²。
- 三套预测变量对比：①仅分层分total_score ②完整R/F/M/L/A五特征 ③资产层z0-z5。
- 分层校准：每层预测均值 vs 实际均值，看中间层是否也预测得准（回应"除最高层外无法预测"）。
纯 numpy 实现，无 sklearn。
用法: python tier_regression.py <both_csv>
输出: data_storage/seg_reg_<d>.json ; data_storage/seg_reg_calib_<d>.csv
"""
import sys, json
import pandas as pd
import numpy as np

csv_path = sys.argv[1]
outdir = "/Users/zhongmengting/.claude/data_storage"
df = pd.read_csv(csv_path)
d = str(df["d"].iloc[0])
df["regist_days"] = df["regist_days"].fillna(-1).astype(int)

# 特征
r = np.select([df.r_last_pay_days<=30, df.r_last_pay_days<=90, df.r_last_pay_days<=180],[3,2,1],0).astype(float)
f = np.select([df.f_pay_cnt_180d>=5, df.f_pay_cnt_180d>=3, df.f_pay_cnt_180d==2, df.f_pay_cnt_180d==1],[4,3,2,1],0).astype(float)
m = np.select([df.m_pay_amt_180d>=10000, df.m_pay_amt_180d>=1000, df.m_pay_amt_180d>=100],[3,2,1],0).astype(float)
l = np.select([(df.regist_days>=0)&(df.regist_days<=30),(df.regist_days>=31)&(df.regist_days<=180),(df.regist_days>180)&(df.f_pay_cnt_180d>=1)],[1,2,3],0).astype(float)
a = ((df.a_visit_pv_30d>=5).astype(int)+(df.a_search_pv_30d>=3).astype(int)+(df.a_love_pv_30d>=1).astype(int)*2+(df.a_hist_order_cnt>=1).astype(int)*2).astype(float)
score = r+f+m+l+a
df["score"]=score
df["tier"]=np.select([score>=16,score>=12,score>=6,score>=4],["L5","L4","L3","L2"],"L1")
asset = df["user_type"].astype(str).str.extract(r"z(\d)").astype(float)

def ols_r2(X, y):
    X1 = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
    yhat = X1 @ beta
    ss_res = ((y-yhat)**2).sum(); ss_tot = ((y-y.mean())**2).sum()
    return float(1-ss_res/ss_tot), beta, yhat

def logit_mcfadden(X, y, iters=30):
    X1 = np.column_stack([np.ones(len(X)), X]).astype(float)
    # 标准化以稳数值
    mu = X1[:,1:].mean(0); sd = X1[:,1:].std(0)+1e-9
    X1[:,1:] = (X1[:,1:]-mu)/sd
    beta = np.zeros(X1.shape[1])
    for _ in range(iters):
        eta = X1@beta; p = 1/(1+np.exp(-eta)); p=np.clip(p,1e-9,1-1e-9)
        W = p*(1-p)
        grad = X1.T @ (y-p)
        H = (X1.T*W)@X1 + 1e-6*np.eye(X1.shape[1])
        beta += np.linalg.solve(H, grad)
    eta=X1@beta; p=np.clip(1/(1+np.exp(-eta)),1e-9,1-1e-9)
    ll = (y*np.log(p)+(1-y)*np.log(1-p)).sum()
    p0=y.mean(); ll0=(y*np.log(p0)+(1-y)*np.log(1-p0)).sum()
    return float(1-ll/ll0), p

res={"d":d,"n":len(df),
     "note":"OLS看R²(全体可解释方差,非仅头部);Logistic看McFadden伪R²;对比仅分层分/五特征/资产层"}
feat_sets={
    "仅分层分(total_score)": score.to_numpy().reshape(-1,1),
    "五特征(R/F/M/L/A)": np.column_stack([r,f,m,l,a]),
    "资产层(z0-z5)": asset.fillna(asset.mean()).to_numpy().reshape(-1,1),
}
# 连续目标：订单量、GMV；二元目标：是否付费。两窗口
targets_cont={"未来7日订单量":"order_cnt_7d","未来7日GMV":"pay_amt_7d",
              "未来365日订单量":"order_cnt_365d","未来365日GMV":"pay_amt_365d"}
targets_bin={"未来7日是否付费":"is_paid_7d","未来365日是否付费":"is_paid_365d"}

res["OLS_R2"]={}
for tname,tcol in targets_cont.items():
    y=df[tcol].to_numpy().astype(float)
    res["OLS_R2"][tname]={fs: round(ols_r2(X,y)[0],4) for fs,X in feat_sets.items()}
res["Logistic_McFaddenR2"]={}
for tname,tcol in targets_bin.items():
    y=df[tcol].to_numpy().astype(float)
    res["Logistic_McFaddenR2"][tname]={fs: round(logit_mcfadden(X,y)[0],4) for fs,X in feat_sets.items()}

# 分层校准：五特征OLS预测未来365GMV,看每层预测vs实际(回应中间层能否预测)
y=df["pay_amt_365d"].to_numpy().astype(float)
_,_,yhat=ols_r2(np.column_stack([r,f,m,l,a]),y)
df["pred_gmv365"]=yhat
calib=[]
for t in ["L5","L4","L3","L2","L1"]:
    g=df[df.tier==t]
    calib.append({"层级":t,"用户数":len(g),
        "实际人均GMV365":round(float(g.pay_amt_365d.mean()),1),
        "预测人均GMV365":round(float(g.pred_gmv365.mean()),1),
        "实际付费率365":round(float(g.is_paid_365d.mean()),4)})
pd.DataFrame(calib).to_csv(f"{outdir}/seg_reg_calib_{d}.csv",index=False,encoding="utf-8-sig")
res["分层校准_365GMV"]=calib
res["结论"]=("回归验证补上AUC看不到的两点：R²=分层对全体用户(不只头部)结果变异的解释力；"
            "分层校准=各层预测均值与实际均值是否贴合,看中间层能否被预测。")

with open(f"{outdir}/seg_reg_{d}.json","w",encoding="utf-8") as fh:
    json.dump(res,fh,ensure_ascii=False,indent=2)
print(json.dumps(res,ensure_ascii=False,indent=2))

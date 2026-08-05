#!/usr/bin/env python3
"""模型分层：五特征 Logistic 拟合付费概率，按概率切模型层 M1-M5，对比规则分层。
- 训练/测试 7:3 拆分(哈希),测试集算 AUC，避免过拟合虚高。
- 输出：标准化系数(各特征贡献)、模型层各层付费校准、模型层 vs 规则层 AUC、交叉分布。
纯 numpy，无 sklearn。目标默认 未来365日是否付费(可换7d)。
用法: python model_segmentation.py <both_csv> [7d|365d]
输出: data_storage/seg_model_<d>.json ; seg_model_calib_<d>.csv ; seg_model_scored_<d>.csv(token+概率+层)
"""
import sys, json
import pandas as pd
import numpy as np

csv_path = sys.argv[1]
win = sys.argv[2] if len(sys.argv)>2 else "365d"
ycol = "is_paid_365d" if win=="365d" else "is_paid_7d"
outdir = "/Users/zhongmengting/.claude/data_storage"
df = pd.read_csv(csv_path)
d = str(df["d"].iloc[0])
df["regist_days"] = df["regist_days"].fillna(-1).astype(int)

# 五个原始特征分（与规则打分同口径的分档,但作为独立特征喂模型）
R = np.select([df.r_last_pay_days<=30, df.r_last_pay_days<=90, df.r_last_pay_days<=180],[3,2,1],0).astype(float)
F = np.select([df.f_pay_cnt_180d>=5, df.f_pay_cnt_180d>=3, df.f_pay_cnt_180d==2, df.f_pay_cnt_180d==1],[4,3,2,1],0).astype(float)
M = np.select([df.m_pay_amt_180d>=10000, df.m_pay_amt_180d>=1000, df.m_pay_amt_180d>=100],[3,2,1],0).astype(float)
L = np.select([(df.regist_days>=0)&(df.regist_days<=30),(df.regist_days>=31)&(df.regist_days<=180),(df.regist_days>180)&(df.f_pay_cnt_180d>=1)],[1,2,3],0).astype(float)
A = ((df.a_visit_pv_30d>=5).astype(int)+(df.a_search_pv_30d>=3).astype(int)+(df.a_love_pv_30d>=1).astype(int)*2+(df.a_hist_order_cnt>=1).astype(int)*2).astype(float)
Xraw = np.column_stack([R,F,M,L,A]); names=["R","F","M","L","A"]
y = df[ycol].to_numpy().astype(float)
rule_score = (R+F+M+L+A)
df["rule_tier"]=np.select([rule_score>=16,rule_score>=12,rule_score>=6,rule_score>=4],["L5","L4","L3","L2"],"L1")

# 训练/测试 7:3（哈希 token 稳定拆分）
h = (pd.util.hash_pandas_object(df["token"].astype(str), index=False).to_numpy() % 10)
train = h<7; test = ~train

# 标准化(用训练集统计)
mu=Xraw[train].mean(0); sd=Xraw[train].std(0)+1e-9
Xs=(Xraw-mu)/sd

def fit_logit(X,y,iters=40,ridge=1e-4):
    X1=np.column_stack([np.ones(len(X)),X])
    beta=np.zeros(X1.shape[1])
    for _ in range(iters):
        p=np.clip(1/(1+np.exp(-(X1@beta))),1e-9,1-1e-9)
        W=p*(1-p); g=X1.T@(y-p)-ridge*beta
        H=(X1.T*W)@X1+ridge*np.eye(X1.shape[1])
        beta+=np.linalg.solve(H,g)
    return beta

beta=fit_logit(Xs[train],y[train])
prob=np.clip(1/(1+np.exp(-(np.column_stack([np.ones(len(Xs)),Xs])@beta))),1e-9,1-1e-9)
df["pay_prob"]=prob

def auc_mw(s,yy):
    ranks=pd.Series(s).rank(method="average").to_numpy()
    npo=int(yy.sum()); nne=len(yy)-npo
    if npo==0 or nne==0: return float("nan")
    return float((ranks[yy==1].sum()-npo*(npo+1)/2)/(npo*nne))

auc_model_test=auc_mw(prob[test],y[test])
auc_rule_test =auc_mw(rule_score[test],y[test])

# 按预测概率切模型层 M1-M5：M5=top1%,M4=top5%,M3=top10%,M2=top20%,与规则层量级可比
q=np.quantile(prob,[0.80,0.90,0.95,0.99])
df["model_tier"]=np.select([prob>=q[3],prob>=q[2],prob>=q[1],prob>=q[0]],["M5","M4","M3","M2"],"M1")

# 各模型层付费校准(测试集)
calib=[]
dft=df[test]
for t in ["M5","M4","M3","M2","M1"]:
    g=dft[dft.model_tier==t]
    calib.append({"模型层":t,"用户数":int(len(g)),"占比":round(len(g)/len(dft),4),
        "预测付费概率均值":round(float(g.pay_prob.mean()),4),
        f"实际{win}付费率":round(float(g[ycol].mean()),4),
        f"实际{win}人均GMV":round(float((g.pay_amt_365d if win=='365d' else g.pay_amt_7d).mean()),1)})
pd.DataFrame(calib).to_csv(f"{outdir}/seg_model_calib_{d}.csv",index=False,encoding="utf-8-sig")

# 标准化系数(特征重要性)
coef={n:round(float(b),4) for n,b in zip(names,beta[1:])}

# 模型层 × 规则层 交叉分布
cross=pd.crosstab(df["model_tier"],df["rule_tier"]).reindex(index=["M5","M4","M3","M2","M1"],columns=["L5","L4","L3","L2","L1"],fill_value=0)

res={"d":d,"target":ycol,"n":len(df),"n_train":int(train.sum()),"n_test":int(test.sum()),
    "标准化系数(特征贡献,越大越重要)":coef,
    "系数解读":"正且大=该特征越高越易付费;对比可见哪个维度驱动力最强",
    "测试集AUC":{"模型分层(五特征logistic)":round(auc_model_test,4),"规则分层(total_score)":round(auc_rule_test,4),
                "提升":round(auc_model_test-auc_rule_test,4)},
    "模型层校准":calib,
    "模型层vs规则层交叉":cross.to_dict(),
    "结论":"模型分层=用五特征logistic预测付费概率再按概率分位切层;测试集AUC对比规则分层看提升;校准看各层预测概率与实际付费率是否贴合"}
with open(f"{outdir}/seg_model_{d}.json","w",encoding="utf-8") as fh:
    json.dump(res,fh,ensure_ascii=False,indent=2)
df[["token","user_type","pay_prob","model_tier","rule_tier"]].to_csv(f"{outdir}/seg_model_scored_{d}.csv",index=False,encoding="utf-8-sig")
print(json.dumps(res,ensure_ascii=False,indent=2))
print("\n[cross] 模型层×规则层:\n", cross.to_string())

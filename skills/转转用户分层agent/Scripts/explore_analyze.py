#!/usr/bin/env python3
"""探索性打标结果分析：分位线 + 五大价值层/九人群 前后对比。

用法: python explore_analyze.py <seg_explore_csv> <dt>
输出:
  data_storage/seg_explore_pctl_<dt>.csv     各指标分位线
  data_storage/seg_explore_compare_<dt>.json 前后对比结果
"""
import sys, json
import pandas as pd
import numpy as np

csv_path = sys.argv[1]
dt = sys.argv[2]
outdir = "/Users/zhongmengting/.claude/data_storage"

df = pd.read_csv(csv_path)
n = len(df)
regist_null = int(df["regist_days"].isna().sum())
# regist_days 缺失（regist_time 为空）：L 维无法判定，填 -1 作缺失标记，打分时归 l_score=0
df["regist_days"] = df["regist_days"].fillna(-1).astype(int)
print(f"[load] rows={n}, regist_days缺失={regist_null} ({regist_null/n:.2%})")

# 有支付用户子集（R/F/M 分位线只在有支付用户里看才有意义）
paid = df[df["f_pay_cnt_180d"] > 0].copy()
n_paid = len(paid)

# ---------- 1. 分位线 ----------
pctls = [50, 80, 90, 95, 99]
metrics_full = ["regist_days", "a_visit_pv_30d", "a_search_pv_30d",
                "a_love_pv_30d", "a_hist_order_cnt"]
metrics_paid = ["r_last_pay_days", "f_pay_cnt_180d", "m_pay_amt_180d",
                "price_pctl_90d", "p_coupon_rate", "p_promo_rate"]

rows = []
for m in metrics_full:
    col = df[df["regist_days"]>=0][m] if m=="regist_days" else df[m]
    r = {"metric": m, "scope": "全量样本", "mean": round(col.mean(), 2)}
    for p in pctls:
        r[f"P{p}"] = round(float(np.percentile(col, p)), 2)
    rows.append(r)
for m in metrics_paid:
    col = paid[m].dropna()   # price_pctl_90d 对无90天单用户为 NaN，需剔除
    r = {"metric": m, "scope": "有支付用户", "mean": round(float(col.mean()), 4)}
    for p in pctls:
        r[f"P{p}"] = round(float(np.percentile(col, p)), 4)
    rows.append(r)
pctl_df = pd.DataFrame(rows)
pctl_path = f"{outdir}/seg_explore_pctl_{dt}.csv"
pctl_df.to_csv(pctl_path, index=False, encoding="utf-8-sig")
print(f"[pctl] -> {pctl_path}")
print(pctl_df.to_string(index=False))

# ---------- 2. 打分函数（现有阈值 = 方案原版） ----------
def score_old(d):
    r = np.select([d.r_last_pay_days<=30, d.r_last_pay_days<=90, d.r_last_pay_days<=180],[3,2,1],0)
    f = np.select([d.f_pay_cnt_180d>=5, d.f_pay_cnt_180d>=3, d.f_pay_cnt_180d==2, d.f_pay_cnt_180d==1],[4,3,2,1],0)
    m = np.select([d.m_pay_amt_180d>=10000, d.m_pay_amt_180d>=1000, d.m_pay_amt_180d>=100],[3,2,1],0)
    l = np.select([(d.regist_days>=0)&(d.regist_days<=30),
                   (d.regist_days>=31)&(d.regist_days<=180),
                   (d.regist_days>180)&(d.f_pay_cnt_180d>=1)],[1,2,3],0)
    a = ((d.a_visit_pv_30d>=5).astype(int) + (d.a_search_pv_30d>=3).astype(int)
         + (d.a_love_pv_30d>=1).astype(int)*2 + (d.a_hist_order_cnt>=1).astype(int)*2)
    return r,f,m,l,a

# 现有阈值分层（不含 P，5 维等权累加 → 与更新后方案一致）
r,f,m,l,a = score_old(df)
df["r_score"],df["f_score"],df["m_score"],df["l_score"],df["a_score"]=r,f,m,l,a
df["total_score_5d"] = df.r_score+df.f_score+df.m_score+df.l_score+df.a_score
# 原方案分层阈值(基于6维加权28/20/13/7，此处5维等权需重新看分布)
print("\n[score] 5维等权 total_score 分布分位:")
for p in [50,80,90,95,99]:
    print(f"  P{p} = {np.percentile(df.total_score_5d,p):.1f}")
print(f"  max={df.total_score_5d.max()}, mean={df.total_score_5d.mean():.2f}")

result = {
    "dt": dt, "total_users": int(n), "paid_users": int(n_paid),
    "paid_ratio": round(n_paid/n, 4),
    "score_5d_dist": {f"P{p}": float(round(np.percentile(df.total_score_5d,p),1)) for p in [50,80,90,95,99]},
    "score_5d_max": int(df.total_score_5d.max()),
    "lux_buyer_cnt": int(df.is_lux_buyer_180d.sum()),
    "lux_buyer_ratio": round(float(df.is_lux_buyer_180d.mean()),5),
}

# ---------- 3. 九人群命中量（现有阈值口径） ----------
personas = {}
personas["高频金主"] = int(((df.l_score>=1)&(df.f_score==4)&(df.m_score>=2)).sum())
personas["价值回流"] = int(((df.r_score==0)&(df.a_hist_order_cnt>=3)).sum())
personas["新用户活跃"] = int(((df.regist_days<=30)&(df.a_score>=3)).sum())
personas["搜而不买"] = int(((df.a_search_pv_30d>=3)&(df.a_love_pv_30d==0)&(df.f_pay_cnt_180d==0)).sum())
personas["加购未付"] = int(((df.a_love_pv_30d>=1)&(df.f_pay_cnt_180d==0)).sum())
personas["沉睡老客"] = int(((df.a_hist_order_cnt>=1)&(df.r_score==0)).sum())
personas["高价值二奢"] = int(((df.m_score==3)&(df.is_lux_buyer_180d==1)).sum())
# 价敏改口径：同 cate_02 价格分位越低越价敏（买同类里便宜的）；price_pctl_90d<=0.3 且有90天单
personas["价格敏感"] = int(((df.price_pctl_90d.notna())&(df.price_pctl_90d<=0.3)).sum())
personas["分期依赖(数据源不支持)"] = None   # 本宽表 pay_type 近乎全 0，分期不可算，需换支付流水表
result["persona_counts_oldthr"] = personas
result["persona_ratio_oldthr"] = {k: (round(v/n,5) if v is not None else None) for k,v in personas.items()}
result["price_pctl_stat"] = {
    "有90天价格分位用户数": int(df.price_pctl_90d.notna().sum()),
    "均值": round(float(df.price_pctl_90d.mean()),4),
    "P20": round(float(np.nanpercentile(df.price_pctl_90d,20)),4),
    "P50": round(float(np.nanpercentile(df.price_pctl_90d,50)),4),
    "P80": round(float(np.nanpercentile(df.price_pctl_90d,80)),4),
}
result["data_caveats"] = [
    "业务线/品类打标改从商品表 dw_mysql_info_full_1d 取(cus_business_bu+business_line_id+cate_id映射)，订单INNER JOIN限定在消电/兴趣/二奢等圈定业务线内",
    "二奢口径改为 cate='二奢'(cus_business_bu='二奢' AND business_line_id IN(915051,915061))，替换旧的已停用 cate_first_name='奢侈品'",
    "价敏改口径：同 cate_02 内成交价 PERCENT_RANK 分位(近90天均值)，越低=越买同类里便宜的；替换失效的红包率口径",
    "love_pv_30d 口径已交叉校验：用户表'近30天下单/加购/收藏次数'与历史脚本 act_type='下单/收藏/加购'(三表union)口径一致，字段可用",
    "search_pv_30d 为搜索行为次数、visit_pv_30d 为b2c商详单日最大访问次数(非30天累计)，作活跃强度代理，量纲与历史UV口径不同已标注",
    "分期维度：本宽表近180天pay_type近乎全记0，分期占比不可算，人群'分期依赖'需换支付流水表",
    "regist_days缺失(regist_time为空)，L维对缺失用户判0",
]

# ---------- 4. 各维度：现有阈值 vs 分位线建议阈值 ----------
paid_pct = lambda col,p: round(float(np.percentile(paid[col],p)),2)
result["threshold_review"] = {
    "F_支付频次_180d": {
        "现有阈值": "≥5=4 / 3-4=3 / 2=2 / 1=1",
        "有支付分位": {"P50":paid_pct("f_pay_cnt_180d",50),"P80":paid_pct("f_pay_cnt_180d",80),"P90":paid_pct("f_pay_cnt_180d",90),"P95":paid_pct("f_pay_cnt_180d",95)},
        "判读": "P90=5，现≥5=满分仅覆盖top10%；≥3=3分与≥5=4分挤在尾部，建议按分位重设 4分线≈P95、3分线≈P90",
    },
    "M_支付金额_180d元": {
        "现有阈值": "≥10000=3 / ≥1000=2 / ≥100=1",
        "有支付分位": {"P50":paid_pct("m_pay_amt_180d",50),"P80":paid_pct("m_pay_amt_180d",80),"P90":paid_pct("m_pay_amt_180d",90),"P95":paid_pct("m_pay_amt_180d",95)},
        "判读": "P95=8564，现≥1万=满分几乎无人达到；≥100=1分门槛过低(P50已1778)。建议3分线≈P90(6298)、2分线≈P50(1778)、1分线≈P20",
    },
    "R_最近支付间隔_天": {
        "现有阈值": "≤30=3 / ≤90=2 / ≤180=1",
        "有支付分位": {"P50":paid_pct("r_last_pay_days",50),"P80":paid_pct("r_last_pay_days",80),"P90":paid_pct("r_last_pay_days",90)},
        "判读": "有支付用户R的P50=20天，现≤30=满分覆盖过半付费者，区分度尚可；180天窗口内分档合理，可保留",
    },
    "A_search_30d": {
        "现有阈值": "search≥3 记1分",
        "全量分位": {"P80":float(np.percentile(df.a_search_pv_30d,80)),"P90":float(np.percentile(df.a_search_pv_30d,90))},
        "判读": "search P80=84，现≥3门槛过低几乎人人满足，失去区分度，建议提高到≈P80或按活跃度分档",
    },
    "价敏_同类价格分位": {
        "新口径": "近90天订单在同 cate_02 内成交价 PERCENT_RANK 分位均值，越低越价敏",
        "有价格分位用户分位": {"P20":round(float(np.nanpercentile(df.price_pctl_90d,20)),3),"P50":round(float(np.nanpercentile(df.price_pctl_90d,50)),3),"P80":round(float(np.nanpercentile(df.price_pctl_90d,80)),3)},
        "判读": "替换旧红包率口径(区分度差)。价敏人群取分位≤0.3(买同类里最便宜的30%)，高溢价人群取≥0.7",
    },
}
result["value_tier_conflict"] = {
    "现有分层阈值(6维加权设计)": "L5≥28 / L4≥20 / L3≥13 / L2≥7",
    "实测5维等权total_score": {"max":int(df.total_score_5d.max()),"P95":float(np.percentile(df.total_score_5d,95)),"P99":float(np.percentile(df.total_score_5d,99))},
    "硬矛盾": "方案已去权重改5维等权，理论满分=R3+F4+M3+L3+A6=19，永远达不到L5≥28。实测max=19。价值层阈值必须按5维等权重设",
    "建议分层线(按total_score分位)": {"L5(top1%)":"≥16","L4(top5%)":"≥13","L3(top10%)":"≥9","L2(top20%)":"≥4","L1":"<4"},
}

json_path = f"{outdir}/seg_explore_compare_{dt}.json"
with open(json_path,"w",encoding="utf-8") as fh:
    json.dump(result, fh, ensure_ascii=False, indent=2)
print(f"\n[compare] -> {json_path}")
print(json.dumps(result, ensure_ascii=False, indent=2))

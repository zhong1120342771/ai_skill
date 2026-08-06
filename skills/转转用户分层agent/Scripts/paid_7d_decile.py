#!/usr/bin/env python3
"""当日付费用户 过去7天四信号 十分位频次分布。
四信号: 商详浏览visit / 搜索search / 下单加购收藏love / 历史成交deal。
按十分位(每10%一档)给分位切点 + 各档人数,并标注0值占比(埋点行为零膨胀严重)。
用法: python paid_7d_decile.py <signals_csv>
输出: data_storage/paid_7d_decile_<d>.csv/json
"""
import sys, json
import pandas as pd
import numpy as np

csv_path = sys.argv[1]
outdir = "/Users/zhongmengting/.claude/data_storage"
df = pd.read_csv(csv_path)
d = "2025-07-27"
n = len(df)
sigs = {"visit_7d":"商详浏览PV","search_7d":"搜索次数","love_7d":"下单/加购/收藏","deal_7d":"历史成交订单数"}

rows=[]
summary={}
for col,name in sigs.items():
    s = df[col].astype(float)
    zero = float((s==0).mean())
    # 十分位切点 P10..P100
    qs = {f"P{p}": float(np.percentile(s,p)) for p in range(10,101,10)}
    # 各十分位段人数(按值域分箱,用分位边界)
    edges = [np.percentile(s,p) for p in range(0,101,10)]
    summary[col] = {"信号":name,"均值":round(float(s.mean()),2),"最大":float(s.max()),
                    "0值占比":round(zero,4),"分位":{k:round(v,1) for k,v in qs.items()}}
    for i in range(10):
        lo,hi = edges[i],edges[i+1]
        if i<9:
            m = (s>=lo)&(s<hi) if lo<hi else (s==lo)
        else:
            m = (s>=lo)
        rows.append({"信号":name,"十分位段":f"D{i+1}(P{i*10}-P{(i+1)*10})",
                     "值域":f"[{lo:.0f},{hi:.0f}{')' if i<9 else ']'}","人数":int(m.sum()),
                     "占比":round(float(m.mean()),4)})

out=pd.DataFrame(rows)
out.to_csv(f"{outdir}/paid_7d_decile_{d}.csv",index=False,encoding="utf-8-sig")
with open(f"{outdir}/paid_7d_decile_{d}.json","w",encoding="utf-8") as fh:
    json.dump({"d":d,"n_paid_users":n,"窗口":"过去7天(D-6~D)","付费口径":"D当日净支付",
               "signals":summary},fh,ensure_ascii=False,indent=2)

print(f"当日付费用户数: {n:,} (D={d}, 过去7天窗口)")
print("\n== 四信号十分位切点 ==")
hdr="信号".ljust(12)+"0值%".rjust(7)+"均值".rjust(8)+ "".join(f"P{p}".rjust(7) for p in range(10,101,10))
print(hdr)
for col,name in sigs.items():
    v=summary[col]
    line=name.ljust(12)+f"{v['0值占比']*100:.1f}".rjust(7)+f"{v['均值']:.1f}".rjust(8)
    line+="".join(f"{v['分位'][f'P{p}']:.0f}".rjust(7) for p in range(10,101,10))
    print(line)
print("\n注: 0值占比高说明该信号大量付费用户过去7天为0(零膨胀),低分位切点多为0属正常。")

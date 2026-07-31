#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""群@回复服务的 token 花费统计。读 logs/group_auto_reply.cost.ndjson。
用法:
  python3 scripts/group_auto_reply_cost_report.py            # 全部汇总 + 按天
  python3 scripts/group_auto_reply_cost_report.py --today    # 只看今天
  python3 scripts/group_auto_reply_cost_report.py --by-chat  # 再按群拆
"""
import os, json, sys, time, collections

COSTLOG = os.path.expanduser("~/.claude/logs/group_auto_reply.cost.ndjson")

def load():
    if not os.path.exists(COSTLOG):
        print(f"还没有花费日志: {COSTLOG}\n(服务重启并有人@提问后才会产生)"); sys.exit(0)
    rows = []
    with open(COSTLOG) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: rows.append(json.loads(line))
            except: pass
    return rows

def fmt(usd):  # 美元 + 约人民币(汇率粗算7.2)
    return f"${usd:.4f} (约¥{usd*7.2:.2f})"

def main():
    rows = load()
    today = time.strftime("%F")
    if "--today" in sys.argv:
        rows = [r for r in rows if r.get("ts","").startswith(today)]
        print(f"=== 今天 {today} ===")

    if not rows:
        print("该时段无记录"); return

    n = len(rows)
    cost = sum(r.get("turn_cost_usd",0) for r in rows)
    tin  = sum(r.get("input_tokens",0) for r in rows)
    tout = sum(r.get("output_tokens",0) for r in rows)
    cread= sum(r.get("cache_read_input_tokens",0) for r in rows)
    print(f"总提问轮数: {n}")
    print(f"总花费:     {fmt(cost)}")
    print(f"单轮均价:   {fmt(cost/n)}")
    print(f"input tokens:  {tin:,}")
    print(f"output tokens: {tout:,}")
    print(f"cache 命中读取: {cread:,} (越大越省,复用了缓存)")

    # 按天
    if "--today" not in sys.argv:
        by_day = collections.defaultdict(lambda: [0,0.0])
        for r in rows:
            d = r.get("ts","")[:10]
            by_day[d][0]+=1; by_day[d][1]+=r.get("turn_cost_usd",0)
        print("\n=== 按天 ===")
        for d in sorted(by_day):
            c,u=by_day[d]; print(f"  {d}: {c} 轮  {fmt(u)}")

    if "--by-chat" in sys.argv:
        by_chat = collections.defaultdict(lambda: [0,0.0])
        for r in rows:
            k=r.get("chat_id","?")[:20]
            by_chat[k][0]+=1; by_chat[k][1]+=r.get("turn_cost_usd",0)
        print("\n=== 按群 ===")
        for k in sorted(by_chat, key=lambda x:-by_chat[x][1]):
            c,u=by_chat[k]; print(f"  {k}: {c} 轮  {fmt(u)}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
poll_and_route.py — 数据问答轮询bot 核心脚本

拉取飞书群最近消息，过滤出未回复的 @bot 消息，输出需要处理的消息列表。

用法：
  python3 poll_and_route.py [--chat-id <oc_xxx>] [--page-size 20] [--start <ISO8601>]

输出：JSON 数组，每项包含需要回答的消息的关键字段
"""
import sys, os, json, subprocess, argparse

BOT_NAME = "cai的飞书 CLI"
DEFAULT_CHAT_ID = "oc_f9d6d274f793f89b92c455b5691b0a00"


def fetch_messages(chat_id, page_size=20, start=None, page_token=None):
    cmd = ["lark-cli", "im", "+chat-messages-list",
           "--chat-id", chat_id, "--as", "user",
           "--page-size", str(page_size)]
    if start:
        cmd += ["--start", start]
    if page_token:
        cmd += ["--page-token", page_token]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[error] lark-cli 失败: {result.stderr[:200]}", file=sys.stderr)
        return [], None
    data = json.loads(result.stdout)
    msgs = data.get("data", {}).get("messages", [])
    next_token = data.get("data", {}).get("page_token")
    return msgs, next_token


def is_at_bot(msg):
    """消息是否 @bot"""
    mentions = msg.get("mentions", [])
    return any(m.get("name") == BOT_NAME for m in mentions)


def bot_already_replied(msg):
    """thread_replies 里是否已有 bot 的回复（判定已处理）"""
    replies = msg.get("thread_replies", [])
    for r in replies:
        sender = r.get("sender", {})
        if sender.get("name") == BOT_NAME:
            return True
        # 也检查 bot 发的「收到，处理中」
        content = r.get("content", "")
        if "收到，处理中" in content:
            return True
    return False


def classify_intent(content):
    """
    L1 快速意图分类（本地规则，0 token）：
    返回 'data_question' / 'existence_check' / 'chitchat' / 'incomplete_supplement'
    """
    text = content.lower()
    # 存在确认
    if any(kw in content for kw in ["你还在", "在不在", "在么", "还在吗"]):
        return "existence_check"
    # 不完整补充说明
    if any(kw in content for kw in ["之前给过", "口径之前", "你应该知道", "限制在"]):
        if "?" not in content and "？" not in content and len(content) < 50:
            return "incomplete_supplement"
    # 数据分析类关键词
    data_keywords = [
        "曝光", "渗透率", "ctr", "转化率", "支付", "dau", "模块", "栏目",
        "分析", "查一下", "看一下", "取数", "统计", "趋势", "环比", "同比",
        "ab实验", "实验组", "对照组", "品类", "二奢", "首页", "日报", "周报",
        "帮我", "sql", "跑数", "拉数", "数据",
    ]
    if any(kw in content for kw in data_keywords):
        return "data_question"
    return "chitchat"


def main():
    ap = argparse.ArgumentParser(description="飞书群消息轮询与路由")
    ap.add_argument("--chat-id", default=DEFAULT_CHAT_ID)
    ap.add_argument("--page-size", type=int, default=20)
    ap.add_argument("--start", default=None, help="向前追溯的起始时间 ISO8601")
    ap.add_argument("--page-token", default=None)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    msgs, next_token = fetch_messages(
        args.chat_id, args.page_size, args.start, args.page_token
    )

    if not msgs:
        print(json.dumps({"pending": [], "total": 0, "next_page_token": None}, ensure_ascii=False))
        return

    pending = []
    skipped = []

    for msg in msgs:
        pos = msg.get("message_position", "?")
        ts = msg.get("create_time", "")
        sender_name = msg.get("sender", {}).get("name", "")
        content = msg.get("content", "")
        thread_id = msg.get("thread_id", "")
        msg_id = msg.get("message_id", "")

        # L1 过滤
        if not is_at_bot(msg):
            skipped.append({"pos": pos, "reason": "no_at_bot"})
            continue
        if msg.get("msg_type") not in ("text", "post"):
            skipped.append({"pos": pos, "reason": "non_text"})
            continue
        if bot_already_replied(msg):
            skipped.append({"pos": pos, "reason": "already_replied"})
            continue

        # L1 意图分类
        intent = classify_intent(content)
        if intent == "incomplete_supplement":
            skipped.append({"pos": pos, "reason": "incomplete_supplement"})
            continue

        pending.append({
            "pos": pos,
            "message_id": msg_id,
            "thread_id": thread_id,
            "create_time": ts,
            "sender": sender_name,
            "content": content[:500],
            "intent": intent,
            "thread_replies_count": len(msg.get("thread_replies", [])),
        })

    result = {
        "pending": pending,
        "skipped_count": len(skipped),
        "total": len(msgs),
        "next_page_token": next_token,
    }
    if args.verbose:
        result["skipped"] = skipped

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一体化项目日报 Step 4 - 飞书 P2P 推送：
  1) 上传 3 张图（yiti_monthly.png / yiti_weekly.png / yiti_daily.png）拿 image_key
  2) 拼装 markdown 富文本（结论 + 文字总结 + 图1 + 图2 + 图3 + 表1）
  3) 对 LARK_YITI_RECEIVERS 中每个 open_id 各推一条 P2P
  4) 写 final_report/feishu_push_${dt}.json

用法：
  python feishu_publish.py --dt 2026-06-16
  python feishu_publish.py --dt 2026-06-16 --skip-image-upload   # 仅重推 IM
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import REPORT_DIR, FINAL_DIR, VIS_DIR_TPL, get_receivers, get_review_receiver, METRIC_LABELS, METRIC_FMT, METRICS_TPL, QC_TPL


def fmt_value(k, v):
    if v is None:
        return "—"
    if METRIC_FMT[k] == "rate":
        return f"{v*100:.2f}%"
    return f"{int(round(v)):,}"


def fmt_mom(v):
    if v is None:
        return "—"
    arrow = "↑" if v > 0 else ("↓" if v < 0 else "→")
    return f"{arrow}{abs(v)*100:.2f}%"


def upload_image(png_path: str) -> str:
    """cd ~/.claude && lark-cli im images create --file ./xxx.png --as bot
    返回 image_key。"""
    abs_claude = os.path.expanduser("~/.claude")
    rel = os.path.relpath(png_path, abs_claude)
    rel_arg = f"./{rel}"
    cmd = [
        "lark-cli", "im", "images", "create",
        "--data", '{"image_type":"message"}',
        "--file", rel_arg,
        "--as", "bot",
    ]
    print(f"[upload] {png_path}")
    proc = subprocess.run(cmd, cwd=abs_claude, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"upload failed: rc={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}")
    out = proc.stdout.strip()
    image_key = None
    try:
        j = json.loads(out)
        image_key = (j.get("data") or {}).get("image_key") or j.get("image_key")
    except Exception:
        import re
        m = re.search(r'image_key["\s:=]+["\']?(img_v3_[A-Za-z0-9_-]+)', out)
        if m:
            image_key = m.group(1)
    if not image_key:
        raise RuntimeError(f"no image_key in response: {out[:300]}")
    print(f"  image_key={image_key}")
    return image_key


def build_message(metrics: dict, qc: dict, img_monthly: str, img_weekly: str, img_daily: str,
                  include_warnings: bool = True) -> str:
    """include_warnings=False 时不拼「数据待复核」块（用于群推干净版；
    待复核内容改由 build_review_message 单独 P2P 推给负责人）。"""
    dt = metrics["dt"]
    ns = metrics["north_star"]
    ts_split = metrics.get("tongshou_split") or {}
    yiti_split = metrics.get("tongshou_xiaodian_yiti") or {}

    # 4 段结论
    line1 = (
        f"【同城订单&同城订单占比】"
        f"同城订单 {fmt_value('tongcheng_orders', ns['tongcheng_orders']['value'])}"
        f"（环比 {fmt_mom(ns['tongcheng_orders']['mom'])}）；"
        f"占比 {fmt_value('tongcheng_share', ns['tongcheng_share']['value'])}"
        f"（环比 {fmt_mom(ns['tongcheng_share']['mom'])}）"
    )
    line2 = (
        f"【线下线索量&线索量转化】"
        f"线下线索 {fmt_value('offline_leads', ns['offline_leads']['value'])}"
        f"（环比 {fmt_mom(ns['offline_leads']['mom'])}）；"
        f"线索转化 {fmt_value('lead_conv_total', ns['lead_conv_total']['value'])}"
        f"（环比 {fmt_mom(ns['lead_conv_total']['mom'])}）"
    )

    # 同售：三层结构（整体 / 小店&pro店 / 小店再按一体化城市拆）
    pro = ts_split.get("pro店")  or {}
    xd  = ts_split.get("小店")   or {}
    def _fmt_part(name: str, d: dict) -> str:
        if not d:
            return f"{name} 无数据"
        return (
            f"{name} 订单 {int(round(d.get('orders') or 0)):,}"
            f"（环比 {fmt_mom(d.get('orders_mom'))}）/"
            f"动销率 {(d.get('dongxiao_rate') or 0)*100:.2f}%"
            f"（环比 {fmt_mom(d.get('dongxiao_rate_mom'))}）"
        )

    # 第一层：整体
    seg_overall = (
        f"整体：同售订单 {fmt_value('tongshou_orders', ns['tongshou_orders']['value'])}"
        f"（环比 {fmt_mom(ns['tongshou_orders']['mom'])}）；"
        f"动销率 {fmt_value('tongshou_dongxiao_rate', ns['tongshou_dongxiao_rate']['value'])}"
        f"（环比 {fmt_mom(ns['tongshou_dongxiao_rate']['mom'])}）"
    )
    # 第二层：小店&pro店
    seg_store = (
        f"小店&pro店：{_fmt_part('pro店', pro)}；{_fmt_part('小店', xd)}"
    )
    # 第三层：一体化影响城市 vs 非一体化影响城市（仅小店同售）
    seg_lines = [f"【同售订单量&同售动销率】", seg_overall + "；", seg_store + "；"]
    if yiti_split:
        seg_city = (
            f"城市拆解（小店同售）："
            f"{_fmt_part('一体化覆盖城市(小店)', yiti_split.get('一体化覆盖城市（小店）') or {})}；"
            f"{_fmt_part('对照城市(重庆&西安)', yiti_split.get('对照城市（重庆&西安）') or {})}；"
            f"{_fmt_part('其他城市', yiti_split.get('其他城市') or {})}"
        )
        seg_lines.append(seg_city)
    # 用换行让三层在飞书消息里分行展示
    line3 = "\n".join(seg_lines)
    line4 = (
        f"【小时达订单量】"
        f"{fmt_value('xiaoshida_orders', ns['xiaoshida_orders']['value'])}"
        f"（环比 {fmt_mom(ns['xiaoshida_orders']['mom'])}）"
    )
    conclusion_lines = [f"- {line1}", f"- {line2}", f"- {line3}".replace("\n", "\n  "), f"- {line4}"]
    conclusion_block = "\n".join(conclusion_lines)

    warn_block = ""
    if include_warnings and (qc.get("warnings") or qc.get("soft_failures")):
        warn_lines = ["⚠ 数据待复核："]
        for w in qc.get("warnings", []):
            warn_lines.append(f"- {w}")
        for w in qc.get("soft_failures", []):
            warn_lines.append(f"- {w}")
        warn_block = "\n\n" + "\n".join(warn_lines)

    # 表 1
    table = ["| 指标 | t-1 绝对值 | 环比 | 7 日均值 | 月均 |", "|---|---|---|---|---|"]
    for k, lab in METRIC_LABELS.items():
        m = ns[k]
        table.append(
            f"| {lab} | {fmt_value(k, m['value'])} | {fmt_mom(m['mom'])} | "
            f"{fmt_value(k, m['wow_mean'])} | {fmt_value(k, m['month_mean'])} |"
        )
    table_md = "\n".join(table)

    md = f"""## 【{dt} 一体化数据日报】

**【结论】**

{conclusion_block}{warn_block}

---

**图1：2026 至今 月维度趋势（月均）**

![yiti_monthly]({img_monthly})

---

**图2：过去 8 周 周维度趋势（周均）**

![yiti_weekly]({img_weekly})

---

**图3：过去 30 日 日维度趋势**

![yiti_daily]({img_daily})

---

**表1：t-1（{dt}）7 项北极星指标汇总**

{table_md}
"""
    return md


def build_summary(ns: dict, qc: dict) -> str:
    """已废弃：保留占位以兼容历史调用。"""
    return ""


def build_review_message(metrics: dict, qc: dict) -> str:
    """待复核私推内容：仅含 warnings + soft_failures，给负责人单独 P2P。
    群消息已不含这部分（见 build_message include_warnings=False）。返回空串表示无待复核项。"""
    dt = metrics.get("dt")
    items = list(qc.get("warnings", [])) + list(qc.get("soft_failures", []))
    if not items:
        return ""
    lines = [f"## ⚠ 【{dt} 一体化日报 · 数据待复核】", "",
             "以下项偏离常态，已从群报告中剔除，请确认是否口径/数据异常：", ""]
    for w in items:
        lines.append(f"- {w}")
    return "\n".join(lines)


def send_one(receiver_id: str, markdown: str) -> dict:
    """receiver_id 同时支持群（oc_xxx，--chat-id）与用户（ou_xxx，--user-id）。"""
    if receiver_id.startswith("oc_"):
        target_flag, target_kind = "--chat-id", "chat"
    elif receiver_id.startswith("ou_"):
        target_flag, target_kind = "--user-id", "user"
    else:
        return {"receiver_id": receiver_id, "kind": "unknown", "status": "failed",
                "error": f"无法识别的 receiver_id 前缀（需 oc_/ou_）：{receiver_id}"}
    cmd = [
        "lark-cli", "im", "+messages-send",
        target_flag, receiver_id,
        "--markdown", markdown,
        "--as", "bot",
    ]
    print(f"[send] {target_kind}={receiver_id}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return {"receiver_id": receiver_id, "kind": target_kind, "status": "failed",
                "error": (proc.stderr or proc.stdout).strip()[:500]}
    out = proc.stdout.strip()
    msg_id = ""
    try:
        j = json.loads(out)
        msg_id = (j.get("data") or {}).get("message_id") or j.get("message_id") or ""
    except Exception:
        # 输出非 JSON，回退到正则提取 message_id
        import re
        m = re.search(r'message_id[\s:=]+["\']?(om_[A-Za-z0-9_-]+)', out)
        if m:
            msg_id = m.group(1)
    return {"receiver_id": receiver_id, "kind": target_kind, "status": "success",
            "message_id": msg_id, "raw": out[:300]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", default=None)
    ap.add_argument("--skip-image-upload", action="store_true",
                    help="复用上一次的 image_keys（从 final_report/feishu_push_${dt}.json 读取），仅重推 IM")
    args = ap.parse_args()
    dt = args.dt or (date.today() - timedelta(days=1)).isoformat()

    metrics_path = METRICS_TPL.format(dt=dt)
    qc_path      = QC_TPL.format(dt=dt)
    if not os.path.exists(metrics_path):
        print(f"[fatal] 缺 {metrics_path}", file=sys.stderr)
        return 3
    if not os.path.exists(qc_path):
        print(f"[fatal] 缺 {qc_path}", file=sys.stderr)
        return 3
    with open(metrics_path, encoding="utf-8") as f:
        metrics = json.load(f)
    with open(qc_path, encoding="utf-8") as f:
        qc = json.load(f)

    push_record_path = os.path.join(FINAL_DIR, f"feishu_push_{dt}.json")
    image_keys = {}
    if args.skip_image_upload and os.path.exists(push_record_path):
        with open(push_record_path, encoding="utf-8") as f:
            image_keys = json.load(f).get("image_keys") or {}
        print(f"[reuse] image_keys={image_keys}")
    else:
        vis_dir = VIS_DIR_TPL.format(dt=dt)
        m_png = os.path.join(vis_dir, "yiti_monthly.png")
        w_png = os.path.join(vis_dir, "yiti_weekly.png")
        d_png = os.path.join(vis_dir, "yiti_daily.png")
        for p in (m_png, w_png, d_png):
            if not os.path.exists(p):
                print(f"[fatal] 缺图：{p}", file=sys.stderr)
                return 3
        try:
            image_keys["monthly"] = upload_image(m_png)
            image_keys["weekly"]  = upload_image(w_png)
            image_keys["daily"]   = upload_image(d_png)
        except Exception as e:
            print(f"[fatal] 图片上传失败：{e}", file=sys.stderr)
            return 4

    if not all(k in image_keys for k in ("monthly", "weekly", "daily")):
        print(f"[fatal] image_keys 不全：{image_keys}", file=sys.stderr)
        return 4
    # 主报告：干净版，不含「数据待复核」。待复核改由下方单独私推负责人。
    md = build_message(metrics, qc, image_keys["monthly"], image_keys["weekly"], image_keys["daily"],
                       include_warnings=False)
    # 落本地一份，方便审查
    with open(os.path.join(FINAL_DIR, f"一体化日报_{dt}.md"), "w", encoding="utf-8") as f:
        f.write(md)

    receivers = get_receivers()
    print(f"[receivers] {receivers}")
    pushes = [send_one(rid, md) for rid in receivers]

    # 待复核内容：单独 P2P 推给负责人（不进群）
    review_md = build_review_message(metrics, qc)
    review_push = None
    if review_md:
        review_rid = get_review_receiver()
        print(f"[review] 待复核私推 → {review_rid}")
        review_push = send_one(review_rid, review_md)
    else:
        print("[review] 无待复核项，跳过私推")

    record = {"dt": dt, "im_push": pushes, "review_push": review_push, "image_keys": image_keys}
    with open(push_record_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    failed = [p for p in pushes if p["status"] != "success"]
    if review_push and review_push["status"] != "success":
        failed.append(review_push)
    print(f"[result] 主报告 success={len(pushes)-len([p for p in pushes if p['status']!='success'])}/{len(pushes)}"
          f"；待复核私推={'success' if (review_push and review_push['status']=='success') else ('none' if not review_push else 'FAILED')}")
    if failed:
        for p in failed:
            print(f"  FAILED: {p}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

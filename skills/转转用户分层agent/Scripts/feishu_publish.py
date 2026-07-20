#!/usr/bin/env python3
"""
用户分层流水线 Step 4 飞书发布（固化版）。

把 final_report/用户分层报告_${dt}.md 上传为飞书 docx，然后对
$LARK_SEG_RECEIVERS 里每个 open_id 各推一条纯文本 P2P。
最后产 final_report/feishu_doc_${dt}.json（schema 见 output-schemas.md §五）。

用法:
    LARK_SEG_RECEIVERS="ou_5e572adca6deef8ef21c3b18dfade573" \
        python scripts/feishu_publish.py --dt 2026-06-18

入参:
    --dt        YYYY-MM-DD，必填
    --root      数据根目录，默认 ~/.claude
    --skip-doc  跳过文档创建（只重推 IM，复用上次 feishu_doc_${dt}.json 中的 doc_url）

退出码:
    0 = 文档建好且至少 1 个收件人推送成功
    2 = 文档建好但所有 IM 推送失败
    3 = 文档创建失败
    4 = 内部异常
    5 = 收件人列表为空
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> tuple[int, str, str]:
    """执行命令，返回 (returncode, stdout, stderr)。"""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def lark_cli(*args: str) -> tuple[int, dict | None, str]:
    """调用 lark-cli，返回 (returncode, json_data_or_None, stderr)。"""
    cmd = ["/opt/homebrew/bin/lark-cli"] + list(args)
    rc, stdout, stderr = run(cmd)
    try:
        data = json.loads(stdout)
        return rc, data, stderr
    except Exception:
        return rc, None, stderr or stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dt", required=True)
    parser.add_argument("--root", default="~/.claude")
    parser.add_argument("--skip-doc", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).expanduser()
    dt = args.dt
    skill_dir = Path(__file__).resolve().parent.parent

    report_md = root / "final_report" / f"用户分层报告_{dt}.md"
    message_txt = root / "final_report" / f"seg_message_{dt}.txt"
    doc_result_file = root / "final_report" / f"feishu_doc_{dt}.json"
    doc_result_file.parent.mkdir(parents=True, exist_ok=True)

    # 收件人列表
    receivers_env = os.environ.get("LARK_SEG_RECEIVERS", "ou_5e572adca6deef8ef21c3b18dfade573")
    receivers = [r for r in receivers_env.split() if r.strip()]
    if not receivers:
        print("[feishu_publish] 收件人列表为空", file=sys.stderr)
        sys.exit(5)

    doc_url = None
    doc_token = None

    # ---- Step A: 创建飞书文档 ----
    if not args.skip_doc:
        if not report_md.exists():
            print(f"[feishu_publish] 报告文件不存在: {report_md}", file=sys.stderr)
            sys.exit(3)

        content = report_md.read_text(encoding="utf-8")
        title = f"转转用户分层报告 · {dt}"

        # 创建文档
        rc, data, err = lark_cli(
            "docs", "+create",
            "--api-version", "v2",
            "--title", title,
            "--content", content,
            "--doc-format", "md",
            "--as", "user"
        )
        if rc != 0 or not data or not data.get("ok"):
            print(f"[feishu_publish] 文档创建失败: {err or data}", file=sys.stderr)
            sys.exit(3)

        doc_token = data.get("data", {}).get("document", {}).get("document_id", "")
        doc_url = f"https://zhuanspirit.feishu.cn/docx/{doc_token}"
        print(f"[feishu_publish] 文档创建成功: {doc_url}")
    else:
        # --skip-doc：从上次产物中读取 doc_url
        if doc_result_file.exists():
            prev = json.loads(doc_result_file.read_text(encoding="utf-8"))
            doc_url = prev.get("doc_url", "")
            doc_token = prev.get("doc_token", "")
        if not doc_url:
            print("[feishu_publish] --skip-doc 但找不到上次的 doc_url", file=sys.stderr)
            sys.exit(3)

    # ---- Step B: 读取 IM 推文 ----
    if message_txt.exists():
        im_text = message_txt.read_text(encoding="utf-8").strip()
        # 回填 ${doc_url} 占位符
        im_text = im_text.replace("${doc_url}", doc_url or "")
    else:
        im_text = f"【{dt} 转转用户分层报告】\n{doc_url}"

    # ---- Step C: 推送 P2P ----
    im_results = []
    for open_id in receivers:
        rc, data, err = lark_cli(
            "im", "+messages-send",
            "--user-id", open_id,
            "--text", im_text,
            "--as", "bot"
        )
        ok = rc == 0 and data and data.get("ok")
        msg_id = (data or {}).get("data", {}).get("message_id", "")
        entry = {
            "open_id": open_id,
            "message_id": msg_id,
            "pushed_at": datetime.datetime.now().isoformat(),
            "status": "ok" if ok else "failed",
        }
        if not ok:
            entry["error"] = err or str(data)
            print(f"[feishu_publish] IM 推送失败 ({open_id}): {entry['error']}", file=sys.stderr)
        else:
            print(f"[feishu_publish] IM 推送成功 ({open_id}) msg_id={msg_id}")
        im_results.append(entry)

    # ---- Step D: 写产物 JSON ----
    result = {
        "dt": dt,
        "doc_url": doc_url,
        "doc_token": doc_token,
        "uploaded_at": datetime.datetime.now().isoformat(),
        "im_push": im_results,
    }
    doc_result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[feishu_publish] 产物写入: {doc_result_file}")

    # ---- 退出码 ----
    all_failed = all(r["status"] == "failed" for r in im_results)
    if all_failed:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()

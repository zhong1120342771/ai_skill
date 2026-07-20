#!/usr/bin/env python3
"""
Step 4 飞书发布(固化版)。

把 final_report/首页洞察_淑芬_${dt}.md 上传为飞书 docx,把 5 张图按章节插入,然后
对 $LARK_INSIGHT_RECEIVERS 里每个 open_id 各推一条纯文本 P2P;文字推送成功后,再把
核心汇总表配图 visualizations/${dt}/core_summary_table_淑芬.png 作为图片消息追加在末尾。
最后产 final_report/feishu_doc_淑芬_${dt}.json,schema 见 references/output-schemas.md §三。

用法:
    LARK_INSIGHT_RECEIVERS="ou_aaa ou_bbb" python scripts/feishu_publish.py --dt 2026-06-15

入参:
    --dt         YYYY-MM-DD
    --root       数据根目录,默认 ~/.claude
    --skip-doc   跳过文档创建(只重推 IM,复用上次产物里的 doc_url)
    --skip-push  只建文档+插图,不推 IM(把 P2P 推送留给 Step 5 机会计算器统一推一条)

退出码:
    0 = 成功(建文档且至少 1 个收件人推送成功;或 --skip-push 下文档建好)
    2 = 文档建好但所有 IM 推送失败
    3 = 文档创建失败
    4 = 内部异常
    5 = 收件人列表为空(--skip-push 时不触发此码)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

LARK = "lark-cli"
DOC_TITLE_FMT = "【{dt}】首页数据洞察日报"

CHART_TO_ANCHOR_HINTS = [
    ("module_ctr_rank_淑芬.png",              "11 模块利用效率排行"),
    ("module_exposure_vs_ctr_淑芬.png",       "曝光 vs UV-CTR 散点"),
    ("user_layer_heatmap_淑芬.png",           "用户分层差异"),
    ("daily_trend_淑芬.png",                  "结构迁移与挤压"),
    ("feed_depth_distribution_淑芬.png",      "feed 流深度分布"),
    # 四页对比图（默认四页产出；单页模式无这些图，锚点匹配不上会兜底追加，不报错）
    ("page_overall_compare_淑芬.png",         "四页整体对比"),
    ("page_module_ctr_matrix_淑芬.png",       "page × module UV-CTR 矩阵"),
    ("incremental_contribution_淑芬.png",     "扩页面增量贡献"),
    ("page_module_layer_heatmap_淑芬.png",    "page × module × 分层三维"),
]


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def parse_lark_json(stdout: str) -> dict | None:
    """lark-cli 偶尔在 JSON 之前打印 banner 行,容错抽取首个 {。"""
    m = re.search(r"\{.*\}", stdout, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _set_doc_title(token: str, dt: str) -> bool:
    """lark-cli 1.0.43 markdown 导入不落文档 meta 标题（<title>Untitled</title>），
    正文首个 H1 正确但文档名显示 Untitled。建文档后补一发 str_replace 把 <title> 刷成正确值。
    幂等：改不到（已正确/无 Untitled）只 warn 不抛，不阻断建文档主流程。"""
    want = DOC_TITLE_FMT.format(dt=dt)
    cmd = [LARK, "docs", "+update", "--api-version", "v2",
           "--doc", token, "--as", "user",
           "--command", "str_replace", "--doc-format", "xml",
           "--pattern", "<title>Untitled</title>",
           "--content", f"<title>{want}</title>"]
    cp = run(cmd)
    js = parse_lark_json(cp.stdout)
    ok = bool(js and js.get("ok") and (js.get("data", {}).get("result") == "success"
                                       or js.get("data", {}).get("document")))
    if not ok:
        print(f"[warn] 文档标题刷新失败(非阻断)：标题可能仍为 Untitled。rc={cp.returncode} stdout={cp.stdout[:300]}")
    return ok


def create_doc(md_path: Path, dt: str) -> tuple[str, str]:
    # lark-cli 1.0.43 的 --content @file 只接受相对路径(相对当前 cwd),不接受绝对路径
    cwd = md_path.parent
    rel = md_path.name
    cmd = [LARK, "docs", "+create", "--api-version", "v2",
           "--doc-format", "markdown",
           "--title", DOC_TITLE_FMT.format(dt=dt),
           "--content", f"@{rel}",
           "--as", "user"]
    cp = run(cmd, cwd=str(cwd))
    if cp.returncode != 0:
        raise RuntimeError(f"docs +create failed: rc={cp.returncode}\nstderr={cp.stderr}\nstdout={cp.stdout}")
    js = parse_lark_json(cp.stdout)
    if not js or not js.get("ok"):
        raise RuntimeError(f"docs +create unexpected response: {cp.stdout[:500]}")
    data = js.get("data", {}).get("document") or js.get("data", {})
    token = data.get("document_id") or data.get("doc_token") or data.get("token")
    url = data.get("url") or f"https://zhuanspirit.feishu.cn/docx/{token}"
    if not token:
        raise RuntimeError(f"docs +create no token: {js}")
    # markdown 导入后文档 meta 标题为 Untitled，补一发把 <title> 刷成正确标题
    _set_doc_title(token, dt)
    return token, url


def insert_image(doc_token: str, png_path: Path) -> dict:
    # lark-cli 1.0.43 的 --file 只接受相对当前 cwd 的相对路径,绝对路径会被 path
    # validation 静默拒绝(image_blocks 落空)。与 create_doc 一致,改用 cwd=图所在目录 + 文件名。
    cwd = png_path.parent
    rel = png_path.name
    cmd = [LARK, "docs", "+media-insert",
           "--doc", doc_token, "--file", rel, "--as", "user"]
    cp = run(cmd, cwd=str(cwd))
    if cp.returncode != 0:
        return {"ok": False, "error": cp.stderr or cp.stdout}
    js = parse_lark_json(cp.stdout) or {}
    return {"ok": True, "raw": js}


def push_text(open_id: str, text_file: Path) -> dict:
    # lark-cli 1.0.43 的两个限制:
    # 1) --file 必须是相对当前 cwd 的相对路径,绝对路径会被 validation 拒绝
    # 2) --file 推断成 msg-type=file,与 --msg-type=text 冲突
    # 解决:把文本读出来用 --text 内联,绕开 file path validation 与类型冲突
    try:
        text = text_file.read_text(encoding="utf-8")
    except OSError as e:
        return {"open_id": open_id, "status": "failed",
                "error": f"read text_file failed: {e}",
                "pushed_at": datetime.now().isoformat(timespec="seconds")}

    cmd = [LARK, "im", "+messages-send", "--as", "user",
           "--user-id", open_id,
           "--msg-type", "text",
           "--text", text]
    cp = run(cmd)
    if cp.returncode != 0:
        return {"open_id": open_id, "status": "failed",
                "error": (cp.stderr or cp.stdout)[:500],
                "pushed_at": datetime.now().isoformat(timespec="seconds")}
    js = parse_lark_json(cp.stdout) or {}
    data = js.get("data", {})
    return {
        "open_id": open_id,
        "chat_id": data.get("chat_id") or data.get("chatId"),
        "message_id": data.get("message_id") or data.get("messageId"),
        "pushed_at": datetime.now().isoformat(timespec="seconds"),
        "status": "ok" if js.get("ok") else "failed",
        "error": None if js.get("ok") else cp.stdout[:500],
    }


def push_image(open_id: str, png_path: Path) -> dict:
    """
    P2P 追加一条图片消息（核心汇总表配图，跟在文字消息后面）。
    lark-cli 1.0.43 坑：--image 只接受 cwd 相对路径 + ASCII 文件名，绝对路径/中文名/.. 都被拒；
    且 stdout 首行可能是 `uploading image:` 进度行，parse_lark_json 已容错。
    先把图 cp 成 ASCII 临时名放到图所在目录，再用 cwd + 相对名调用，用完删。
    """
    if not png_path.exists():
        return {"open_id": open_id, "status": "skipped",
                "error": f"summary png not found: {png_path}",
                "pushed_at": datetime.now().isoformat(timespec="seconds")}
    cwd = png_path.parent
    ascii_name = "core_summary_table.png"  # ASCII 名绕开中文路径拒绝
    ascii_path = cwd / ascii_name
    try:
        shutil.copyfile(png_path, ascii_path)
        cmd = [LARK, "im", "+messages-send", "--as", "user",
               "--user-id", open_id, "--image", ascii_name]
        cp = run(cmd, cwd=str(cwd))
    finally:
        try:
            if ascii_path.exists() and ascii_path != png_path:
                ascii_path.unlink()
        except OSError:
            pass
    if cp.returncode != 0:
        return {"open_id": open_id, "status": "failed",
                "error": (cp.stderr or cp.stdout)[:500],
                "pushed_at": datetime.now().isoformat(timespec="seconds")}
    js = parse_lark_json(cp.stdout) or {}
    data = js.get("data", {})
    return {
        "open_id": open_id,
        "message_id": data.get("message_id") or data.get("messageId"),
        "pushed_at": datetime.now().isoformat(timespec="seconds"),
        "status": "ok" if js.get("ok") else "failed",
        "error": None if js.get("ok") else cp.stdout[:500],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dt", required=True)
    ap.add_argument("--root", default=os.path.expanduser("~/.claude"))
    ap.add_argument("--skip-doc", action="store_true")
    ap.add_argument("--skip-push", action="store_true",
                    help="只建文档不推 IM,把 P2P 推送留给 Step 5 统一推一条")
    args = ap.parse_args()

    dt = args.dt
    root = Path(args.root)
    md_path = root / "final_report" / f"首页洞察_淑芬_{dt}.md"
    msg_path = root / "final_report" / f"feishu_message_淑芬_{dt}.txt"
    out_path = root / "final_report" / f"feishu_doc_淑芬_{dt}.json"
    chart_dir = root / "visualizations" / dt

    receivers = [r.strip() for r in os.environ.get("LARK_INSIGHT_RECEIVERS", "").split() if r.strip()]
    # --skip-push 只建文档,不需要收件人;其余模式收件人为空即报错
    if not receivers and not args.skip_push:
        print("[feishu_publish] LARK_INSIGHT_RECEIVERS is empty", file=sys.stderr)
        return 5

    if not md_path.exists():
        print(f"[feishu_publish] missing report: {md_path}", file=sys.stderr)
        return 3
    # 推送阶段才需要 P2P 文本;--skip-push 时允许 message 尚未由 Step 5 追加完成
    if not args.skip_push and not msg_path.exists():
        print(f"[feishu_publish] missing P2P text: {msg_path}", file=sys.stderr)
        return 3

    if args.skip_doc and out_path.exists():
        with open(out_path, encoding="utf-8") as f:
            prev = json.load(f)
        doc_token = prev.get("doc_token")
        doc_url = prev.get("doc_url")
        image_blocks = prev.get("image_blocks", {})
        block_anchors = prev.get("block_anchors", {})
        if not doc_token:
            print("[feishu_publish] --skip-doc but previous feishu_doc.json has no doc_token", file=sys.stderr)
            return 3
    else:
        try:
            doc_token, doc_url = create_doc(md_path, dt)
        except RuntimeError as e:
            err_path = root / "final_report" / f"feishu_error_淑芬_{dt}.log"
            err_path.parent.mkdir(parents=True, exist_ok=True)
            err_path.write_text(str(e), encoding="utf-8")
            print(f"[feishu_publish] doc create failed; see {err_path}", file=sys.stderr)
            return 3

        image_blocks = {}
        for fname, _hint in CHART_TO_ANCHOR_HINTS:
            png = chart_dir / fname
            if not png.exists():
                continue
            res = insert_image(doc_token, png)
            if res.get("ok"):
                raw = res["raw"].get("data", {})
                image_blocks[fname] = {
                    "block_id": raw.get("block_id"),
                    "file_token": raw.get("file_token"),
                }
            time.sleep(0.3)
        block_anchors = {}

    pushes = []
    image_pushes = []
    summary_png = chart_dir / "core_summary_table_淑芬.png"
    if args.skip_push:
        print("[feishu_publish] --skip-push: 文档已就绪,IM 推送留给 Step 5 统一推送")
    else:
        for oid in receivers:
            pushes.append(push_text(oid, msg_path))
            print(f"[done] feishu push -> open_id={oid} status={pushes[-1]['status']}")
            time.sleep(0.5)
            # 文字消息成功后,把核心汇总表 PNG 作为图片消息追加在末尾
            if pushes[-1]["status"] == "ok":
                img_res = push_image(oid, summary_png)
                image_pushes.append(img_res)
                print(f"[done] feishu summary-image -> open_id={oid} status={img_res['status']}")
                time.sleep(0.5)

    payload = {
        "dt": dt,
        "doc_url": doc_url,
        "doc_token": doc_token,
        "uploaded_at": datetime.now().isoformat(timespec="seconds"),
        "block_anchors": block_anchors,
        "image_blocks": image_blocks,
        "im_push": pushes,
        "im_image_push": image_pushes,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[done] {out_path}")

    if args.skip_push:
        return 0
    ok = sum(1 for p in pushes if p["status"] == "ok")
    return 0 if ok > 0 else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[feishu_publish] internal error: {e}", file=sys.stderr)
        sys.exit(4)

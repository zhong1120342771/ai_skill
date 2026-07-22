#!/usr/bin/env python3
"""
sync_data_map.py — 从飞书拉「转转数据地图」到本地缓存，diff 有变化就通知。

流程：
  1. lark-cli docs +fetch 拉最新文档（带 revision_id）
  2. 对比 .data_map_revision 里的旧 revision
  3. 无变化 → 静默退出（不通知，避免噪音）
  4. 有变化 → 写 markdown 缓存到 references/data-map-cache.md
              + 生成 diff 摘要
              + 飞书通知 + 更新 revision 文件
  5. 首次运行（本地无 revision）→ 直接写缓存但不通知

挂 cron：每天 08:57 触发
用法：
  python3 sync_data_map.py                  # 正常同步
  python3 sync_data_map.py --force          # 无视 revision 强制刷新
  python3 sync_data_map.py --no-notify      # 有变化也不发飞书
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
SKILL_DIR = SCRIPT_PATH.parent.parent           # 跑数 skill 根
REFERENCES_DIR = SKILL_DIR / "references"
CACHE_FILE = REFERENCES_DIR / "data-map-cache.md"
REV_FILE = SKILL_DIR / ".data_map_revision"

DATA_MAP_TOKEN = "KyzVdTWxtoQdpaxSPekctvJHneb"
DATA_MAP_URL = f"https://zhuanspirit.feishu.cn/docx/{DATA_MAP_TOKEN}"

LARK_CLI = str(Path.home() / ".npm-global/bin/lark-cli")
SELF_CHAT_ID = "oc_28e2d046dcd48abf32e14b28e32e58b3"  # 贺泽璇


def fetch_data_map() -> tuple[str, int]:
    """拉数据地图，返回 (markdown_content, revision_id)"""
    env = os.environ.copy()
    env["PATH"] = f"{Path.home()}/.npm-global/bin:{env.get('PATH','')}"
    result = subprocess.run(
        [LARK_CLI, "docs", "+fetch",
         "--api-version", "v2",
         "--doc", DATA_MAP_TOKEN,
         "--doc-format", "markdown",
         "--as", "user"],
        env=env, capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        raise RuntimeError(f"lark-cli fetch failed rc={result.returncode}: {result.stderr}")
    data = json.loads(result.stdout)
    if not data.get("ok"):
        raise RuntimeError(f"fetch not ok: {data}")
    doc = data["data"]["document"]
    return doc["content"], doc["revision_id"]


def load_old_revision() -> int:
    if not REV_FILE.exists():
        return -1
    try:
        return int(REV_FILE.read_text().strip())
    except Exception:
        return -1


def save_revision(rev: int) -> None:
    REV_FILE.write_text(str(rev))


def build_diff_summary(old_text: str, new_text: str, max_lines: int = 15) -> str:
    """两段文本 diff 出增删摘要，简短返回"""
    diff = list(difflib.unified_diff(
        old_text.splitlines(), new_text.splitlines(),
        lineterm="", n=0
    ))
    adds = [ln[1:].strip() for ln in diff if ln.startswith("+") and not ln.startswith("+++")]
    dels = [ln[1:].strip() for ln in diff if ln.startswith("-") and not ln.startswith("---")]
    adds = [a for a in adds if a]
    dels = [d for d in dels if d]

    lines = []
    if adds:
        lines.append(f"新增/改动 {len(adds)} 行：")
        for a in adds[:max_lines]:
            snippet = a[:100] + ("…" if len(a) > 100 else "")
            lines.append(f"  + {snippet}")
        if len(adds) > max_lines:
            lines.append(f"  … 还有 {len(adds) - max_lines} 处")
    if dels:
        lines.append(f"删除 {len(dels)} 行：")
        for d in dels[:5]:
            snippet = d[:100] + ("…" if len(d) > 100 else "")
            lines.append(f"  - {snippet}")
        if len(dels) > 5:
            lines.append(f"  … 还有 {len(dels) - 5} 处")
    return "\n".join(lines) if lines else "（无内容变化，仅元数据更新）"


def send_lark(text: str) -> None:
    if not Path(LARK_CLI).exists():
        print(f"⚠️  lark-cli not found: {LARK_CLI}", file=sys.stderr)
        return
    content = json.dumps({"text": text}, ensure_ascii=False)
    env = os.environ.copy()
    env["PATH"] = f"{Path.home()}/.npm-global/bin:{env.get('PATH','')}"
    try:
        result = subprocess.run(
            [LARK_CLI, "im", "+messages-send",
             "--as", "user",
             "--chat-id", SELF_CHAT_ID,
             "--msg-type", "text",
             "--content", content],
            env=env, capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"⚠️  lark send failed rc={result.returncode}: {result.stderr}", file=sys.stderr)
        else:
            print("✅ 飞书已发送", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  lark send exception: {e}", file=sys.stderr)


def wrap_cache(content: str, rev: int) -> str:
    """给缓存加个 header 标注同步时间和 revision"""
    header = f"""<!--
本文件由 sync_data_map.py 每天自动同步自飞书数据地图，不要手改。
飞书源：{DATA_MAP_URL}
最后同步：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
revision_id：{rev}

要改数据地图请去飞书文档改（业务方唯一维护源），改完等次日 08:57 自动同步；
急用可手动跑 `python3 $SKILL_DIR/scripts/sync_data_map.py`
-->

"""
    return header + content


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="无视 revision 强制刷新")
    ap.add_argument("--no-notify", action="store_true", help="不发飞书通知")
    args = ap.parse_args()

    REFERENCES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"拉飞书数据地图 {DATA_MAP_TOKEN} …", file=sys.stderr)

    try:
        new_content, new_rev = fetch_data_map()
    except Exception as e:
        err_msg = f"❌ 数据地图同步失败：{e}"
        print(err_msg, file=sys.stderr)
        if not args.no_notify:
            send_lark(f"⚠️ 数据地图同步失败\n{e}")
        return 1

    old_rev = load_old_revision()
    print(f"revision: 本地 {old_rev} → 飞书 {new_rev}", file=sys.stderr)

    if not args.force and old_rev == new_rev:
        print("✅ revision 未变，跳过", file=sys.stderr)
        return 0

    old_content = CACHE_FILE.read_text(encoding="utf-8") if CACHE_FILE.exists() else ""
    # 去掉 header 再比 diff
    if old_content.startswith("<!--"):
        try:
            old_content_body = old_content.split("-->", 1)[1].lstrip()
        except IndexError:
            old_content_body = old_content
    else:
        old_content_body = old_content

    is_first = old_rev == -1

    CACHE_FILE.write_text(wrap_cache(new_content, new_rev), encoding="utf-8")
    save_revision(new_rev)
    print(f"✅ 已写缓存: {CACHE_FILE}", file=sys.stderr)

    if is_first:
        print("首次同步，不发通知", file=sys.stderr)
        return 0

    diff_summary = build_diff_summary(old_content_body, new_content)
    notify_text = f"""📊 数据地图有更新（rev {old_rev} → {new_rev}）
{diff_summary}

飞书源：{DATA_MAP_URL}
本地缓存：{str(CACHE_FILE).replace(str(Path.home()), '~', 1)}"""
    print(f"\n{notify_text}", file=sys.stderr)
    if not args.no_notify:
        send_lark(notify_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

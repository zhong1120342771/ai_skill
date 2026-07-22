#!/usr/bin/env python3
"""
build_sql_index.py — 扫本地 SQL 库建可查询索引，含 LM 生成的一句话摘要。

流程：
  1. 扫本地 SQL 目录（继承 scan_new_sql.py 的路径 + 跳过规则）
  2. 抽特征：表、CTE、tag、paradigm、行数、mtime
  3. 对每份 SQL 生成 one_liner：
     - 已存在于旧索引 且 mtime 未变 → 直接复用
     - 新 / 变了 → 调 tokenhub anthropic API 生成
  4. 落 sql_index.json 到 skill 目录下（LM 检索时读它）

用法：
  python3 build_sql_index.py                  # 增量建索引（复用未变文件的摘要）
  python3 build_sql_index.py --force          # 强制全部重新生成摘要
  python3 build_sql_index.py --no-llm         # 只抽特征，不调 LM（可离线）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Optional


SCRIPT_PATH = Path(__file__).resolve()
SKILL_DIR = SCRIPT_PATH.parent.parent
INDEX_FILE = SKILL_DIR / "sql_index.json"

# 复用 scan_new_sql 的特征抽取
sys.path.insert(0, str(SCRIPT_PATH.parent))
from scan_new_sql import (  # noqa: E402
    extract_features, scan_dir, load_local_paths, DEFAULT_ROOTS,
)


# ==== tokenhub / anthropic 配置 ====
TOKENHUB_URL = "https://tokenhub.zhuanspirit.com/anthropic/v1/messages"
TOKENHUB_KEY = os.environ.get("TOKENHUB_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
HAIKU_MODEL = "zz-claude-haiku-4-5-20251001"


ONE_LINER_PROMPT = """你在给一份 Hive/Spark SQL 生成一句话中文摘要，用于案例检索。

品类 ID 参考（如 SQL 里含 cate_first_id 数字，按下表映射）：
- 105 = 骑行
- 114 = 二奢
- 115 = 潮玩
- 101 = 手机
- 119 = 平板
- 111 = 鞋服
- 1100002324 = 乐器

要求：
- 不超过 40 字，一句话
- 必须点明：分析对象（品类/业务/用户）+ 输出指标（订单/搜索词/漏斗/转化率）+ 关键维度（时间窗/新老客/坑位）
- 如 SQL 里出现 cate_first_id 数字，直接写映射后的中文品类名（如"骑行"），不要写"cate=105"
- 不要写"这是一条..."之类的废话，直接名词句
- 例子："骑行下单用户支付前搜索词的 PV/UV/召回商品数/意图分类"
- 例子："潮玩老客 SKU 分层（按购买频次）"

SQL 内容（前 1500 字符）：
```sql
{sql}
```

只输出摘要一句话，不要引号，不要"摘要："前缀。"""


def call_haiku(sql_text: str, timeout: int = 30) -> Optional[str]:
    """调 tokenhub haiku 生成一句话摘要"""
    if not TOKENHUB_KEY:
        print("⚠️  TOKENHUB_KEY / ANTHROPIC_AUTH_TOKEN 未设置，跳过 LM 摘要", file=sys.stderr)
        return None

    body = {
        "model": HAIKU_MODEL,
        "max_tokens": 100,
        "messages": [
            {"role": "user", "content": ONE_LINER_PROMPT.format(sql=sql_text[:1500])}
        ],
    }
    req = urllib.request.Request(
        TOKENHUB_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKENHUB_KEY}",
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        # anthropic messages 响应
        blocks = data.get("content", [])
        for b in blocks:
            if b.get("type") == "text":
                text = b.get("text", "").strip()
                # 去掉可能的引号/前缀
                text = text.strip('"\'"' + "'")
                text = re.sub(r"^(摘要[:：]|答[:：])", "", text).strip()
                # 单行
                text = text.splitlines()[0] if text else ""
                return text[:80]  # 硬截断防炸
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        print(f"⚠️  HTTP {e.code}: {body}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  call haiku failed: {e}", file=sys.stderr)
    return None


def load_old_index() -> dict[str, dict]:
    """把旧索引按 path 键化，方便增量复用"""
    if not INDEX_FILE.exists():
        return {}
    try:
        raw = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        return {item["path"]: item for item in raw.get("sqls", [])}
    except Exception as e:
        print(f"⚠️  旧索引读失败：{e}，重建", file=sys.stderr)
        return {}


def build_entry(sql, old_entry: Optional[dict], force: bool, no_llm: bool) -> dict:
    """构造一份 SQL 的索引条目"""
    home = str(Path.home())
    path_str = str(sql.path)
    rel_path = path_str.replace(home, "~", 1)

    entry = {
        "path": path_str,
        "rel_path": rel_path,
        "file_name": sql.path.name,
        "line_count": sql.line_count,
        "mtime": sql.mtime,
        "mtime_iso": datetime.fromtimestamp(sql.mtime).strftime("%Y-%m-%d"),
        "tables": sorted(sql.tables),
        "ctes": sorted(sql.ctes),
        "tags": sql.tags,
        "paradigms": sql.paradigms,
        "one_liner": "",
    }

    # 增量复用
    if old_entry and not force:
        if abs(old_entry.get("mtime", 0) - sql.mtime) < 1 and old_entry.get("one_liner"):
            entry["one_liner"] = old_entry["one_liner"]
            return entry

    # 需要重新生成摘要
    if no_llm:
        entry["one_liner"] = ""  # 稍后 fallback
        return entry

    try:
        sql_text = sql.path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"⚠️  读文件失败 {sql.path}: {e}", file=sys.stderr)
        return entry

    summary = call_haiku(sql_text)
    if summary:
        entry["one_liner"] = summary
        print(f"  📝 {sql.path.name} → {summary}", file=sys.stderr)
    return entry


def fallback_one_liner(entry: dict) -> str:
    """LM 不可用时的降级摘要：拼特征关键词"""
    parts = []
    if entry["tags"]:
        parts.append("、".join(entry["tags"][:3]))
    if entry["tables"]:
        # 只取主表名（去库名）
        main = [t.split(".")[-1] for t in entry["tables"][:2]]
        parts.append(" + ".join(main))
    parts.append(f"{entry['line_count']}行")
    return " | ".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="强制全部重新生成摘要")
    ap.add_argument("--no-llm", action="store_true", help="只抽特征，跳过 LM 摘要")
    ap.add_argument("--since", help="只扫此日期后修改的 SQL (仅影响新增部分)")
    ap.add_argument("--roots", help="覆盖默认扫描根，逗号分隔")
    args = ap.parse_args()

    since_ts = 0.0
    if args.since:
        since_ts = datetime.strptime(args.since, "%Y-%m-%d").timestamp()

    if args.roots:
        roots = [Path(p).expanduser() for p in args.roots.split(",")]
    else:
        roots = load_local_paths() + DEFAULT_ROOTS
    roots = list({p.resolve() for p in roots if p.exists()})

    print(f"扫描根：{[str(r) for r in roots]}", file=sys.stderr)

    candidates = []
    for r in roots:
        candidates.extend(scan_dir(r, since_ts))
    # 去重
    seen = set()
    uniq = []
    for c in candidates:
        if c.path in seen:
            continue
        seen.add(c.path)
        uniq.append(c)
    candidates = uniq

    print(f"候选 SQL：{len(candidates)} 个", file=sys.stderr)

    old_index = load_old_index()
    print(f"旧索引：{len(old_index)} 条", file=sys.stderr)

    entries = []
    new_or_changed = 0
    for i, sql in enumerate(candidates, 1):
        old_entry = old_index.get(str(sql.path))
        entry = build_entry(sql, old_entry, args.force, args.no_llm)
        if not entry["one_liner"]:
            entry["one_liner"] = fallback_one_liner(entry)
        else:
            if not old_entry or abs(old_entry.get("mtime", 0) - sql.mtime) >= 1:
                new_or_changed += 1
        entries.append(entry)
        # 温和限速，避免 rate limit
        if new_or_changed and new_or_changed % 20 == 0:
            time.sleep(1)

    index = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(entries),
        "new_or_changed": new_or_changed,
        "sqls": entries,
    }
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 索引落盘：{INDEX_FILE}", file=sys.stderr)
    print(f"   总数 {len(entries)}，其中新增/变化 {new_or_changed}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

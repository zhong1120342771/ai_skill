#!/usr/bin/env python3
"""
scan_new_sql.py — 扫本地 SQL 目录，找出可能需要新增/扩展到 templates/ 的候选 SQL。

流程：
  1. 扫本地 SQL 目录（默认 .local-sql-paths.local + 常见项目根）
  2. 抽每份 SQL 的骨架特征（主表、CTE 名、行数、是否含分桶/漏斗关键词）
  3. 跟 templates/ 里每份模板对比（表重合度 + CTE 名相似度）
  4. 分档输出 Markdown 报告到 ~/claude-output/sql_scan_YYYYMMDD.md
  5. 可选：调 lark-cli 把摘要发到你的飞书

用法：
  python3 scan_new_sql.py                                     # 全量扫，输出报告
  python3 scan_new_sql.py --since 2026-07-01                  # 只扫此日期后修改的 SQL
  python3 scan_new_sql.py --roots ~/AI/project                # 覆盖默认扫描根
  python3 scan_new_sql.py --no-write                          # 只打印不写文件
  python3 scan_new_sql.py --notify                            # 扫完发飞书给自己
  python3 scan_new_sql.py --since 2026-06-25 --notify         # 周报模式（cron 用）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Set, Tuple


SCRIPT_PATH = Path(__file__).resolve()
SKILL_DIR = SCRIPT_PATH.parent.parent          # 泡泡bot skill 根
TEMPLATES_DIR = SKILL_DIR / "templates"        # 模板库已内聚为 skill 子目录
OUTPUT_DIR = Path.home() / "claude-output"
LOCAL_PATHS_FILE = SKILL_DIR / ".local-sql-paths.local"

LARK_CLI = str(Path.home() / ".npm-global/bin/lark-cli")
SELF_CHAT_ID = "oc_28e2d046dcd48abf32e14b28e32e58b3"  # 贺泽璇自己

DEFAULT_ROOTS = [
    Path.home() / "AI" / "project",
    Path.home() / "Desktop" / "测试代码",
    Path.home() / "claude-output",
]

# 一次性调试文件的关键词（跳过）
SKIP_KEYWORDS = ["诊断", "debug", "验证", "check_", "compare_", "样例", "test_", "_bak"]

# 分片脚手架/日期切片文件（跳过）：_p1_ ~ _p9_ / _20YYMMDD 结尾 / dashboard_*
SKIP_PATTERNS = [
    re.compile(r"_p\d_"),
    re.compile(r"_20\d{6}(?:_20\d{6})?(?:_[a-z]+)?\.sql$", re.IGNORECASE),
    re.compile(r"^dashboard_", re.IGNORECASE),
]

# 骨架识别关键词（用于打标签）
TAG_PATTERNS = {
    "漏斗": [r"funnel", r"pv.*click", r"exposure.*visit", r"UNION ALL"],
    "分桶": [r"CASE\s+WHEN.*BETWEEN.*AND", r"percentile_approx", r"P\d+-P\d+"],
    "搜索": [r"dw_dwb_search_full_link", r"zzappsearch", r"orikeyword", r"rstmark"],
    "交叉": [r"cate_first_type.*=.*'其他'", r"cross join", r"新客.*老客"],
    "画像": [r"gender", r"user_layer", r"性别", r"新老客"],
    "订单来源": [r"first_from", r"sec_from", r"init_from"],
    "供给": [r"surplus", r"on_sale", r"has_surplus", r"info.*status"],
}

# 已在 riding-case-pattern.md 沉淀为「范式」的场景 —— 命中不建议再抽模板
PARADIGM_PATTERNS = {
    "范式A(TopN 点击率)": [r"top\d+.*click", r"page\s*=\s*0.*idx\s*BETWEEN", r"top16.*top6"],
    "范式B(10 档分位分桶)": [r"percentile_approx.*0\.1.*percentile_approx.*0\.9", r"P0-P10.*P10-P20"],
    "范式C(ROW_NUMBER TopN)": [r"ROW_NUMBER\(\)\s+OVER\s*\(\s*(?:PARTITION\s+BY\s+\w+\s+)?ORDER\s+BY.*DESC\s*\)\s+AS\s+rn"],
}

TABLE_RE = re.compile(r"\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_.]*)", re.IGNORECASE)
CTE_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s+AS\s*\(", re.IGNORECASE)


@dataclass
class SqlFeatures:
    path: Path
    mtime: float
    line_count: int
    tables: Set[str] = field(default_factory=set)
    ctes: Set[str] = field(default_factory=set)
    tags: List[str] = field(default_factory=list)
    paradigms: List[str] = field(default_factory=list)

    @property
    def rel_path(self) -> str:
        home = str(Path.home())
        s = str(self.path)
        return s.replace(home, "~", 1)


def load_local_paths() -> List[Path]:
    if not LOCAL_PATHS_FILE.exists():
        return []
    paths = []
    for line in LOCAL_PATHS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        p = Path(line).expanduser()
        if p.exists():
            paths.append(p)
    return paths


def should_skip(path: Path) -> bool:
    name = path.name
    for kw in SKIP_KEYWORDS:
        if kw in name:
            return True
    for pat in SKIP_PATTERNS:
        if pat.search(name):
            return True
    # tmp 库产物（用户经常把 CREATE TABLE tmp.xxx 的产物落回同名文件）
    if name.startswith("tmp_") or name.startswith("riding_"):
        return True
    return False


def strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    sql = re.sub(r"--.*", "", sql)
    return sql


def extract_features(path: Path) -> SqlFeatures:
    text = path.read_text(encoding="utf-8", errors="ignore")
    stripped = strip_comments(text)
    features = SqlFeatures(path=path, mtime=path.stat().st_mtime, line_count=text.count("\n") + 1)

    for m in TABLE_RE.findall(stripped):
        # 排除 CTE 名 —— 有小数点或含库名的算真实表
        if "." in m:
            features.tables.add(m.lower())
    for m in CTE_RE.findall(stripped):
        features.ctes.add(m.lower())
    for tag, patterns in TAG_PATTERNS.items():
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                features.tags.append(tag)
                break
    for para, patterns in PARADIGM_PATTERNS.items():
        for p in patterns:
            if re.search(p, text, re.IGNORECASE | re.DOTALL):
                features.paradigms.append(para)
                break
    return features


def scan_dir(root: Path, since_ts: float) -> List[SqlFeatures]:
    out = []
    if not root.exists():
        return out
    for p in root.rglob("*.sql"):
        try:
            if p.stat().st_mtime < since_ts:
                continue
        except OSError:
            continue
        if should_skip(p):
            continue
        try:
            f = extract_features(p)
        except Exception as e:
            print(f"⚠️  extract failed: {p} — {e}", file=sys.stderr)
            continue
        # 太短的骨架价值不大
        if f.line_count < 30:
            continue
        out.append(f)
    return out


def load_templates() -> List[SqlFeatures]:
    return [extract_features(p) for p in TEMPLATES_DIR.glob("*.sql")]


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def similarity(sql: SqlFeatures, tpl: SqlFeatures) -> Tuple[float, float]:
    """返回 (table_overlap, cte_overlap)"""
    return jaccard(sql.tables, tpl.tables), jaccard(sql.ctes, tpl.ctes)


def classify(sql: SqlFeatures, templates: List[SqlFeatures]) -> Tuple[str, str]:
    """返回 (分档, 说明)"""
    # 范式已覆盖优先判定：命中 paradigm 且未命中已有模板 → 归入 🔵 范式覆盖（不建议抽）
    best_tpl = None
    best_score = 0.0
    best_detail = ""
    for tpl in templates:
        t_ov, c_ov = similarity(sql, tpl)
        score = 0.7 * t_ov + 0.3 * c_ov
        if score > best_score:
            best_score = score
            best_tpl = tpl
            best_detail = f"表 {t_ov:.0%} / CTE {c_ov:.0%}"

    # 二次判定：单一维度极高也算已覆盖
    if best_tpl is not None:
        t_ov, c_ov = similarity(sql, best_tpl)
        if best_score >= 0.80 or c_ov >= 0.90 or (t_ov >= 0.90 and c_ov >= 0.60):
            return "🟢 已覆盖", f"匹配 {best_tpl.path.name}（{best_detail}）"

    # 已归入范式的场景，不建议再抽模板
    if sql.paradigms:
        paras = "、".join(sql.paradigms)
        return "🔵 范式覆盖", f"命中 {paras}（见 riding-case-pattern.md），按范式现写即可，不建议抽模板"

    if best_tpl is None:
        return "🟡 候选新增", "无匹配模板"
    t_ov, c_ov = similarity(sql, best_tpl)
    if best_score >= 0.50 or (t_ov >= 0.70 and c_ov >= 0.10):
        return "🟠 候选扩展", f"接近 {best_tpl.path.name}（{best_detail}），可能多了新维度"
    return "🟡 候选新增", f"最接近 {best_tpl.path.name}（{best_detail}），但差距大"


def build_report(candidates: List[SqlFeatures], templates: List[SqlFeatures]) -> str:
    lines = [
        f"# SQL 库扫描报告",
        "",
        f"- 扫描时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 候选 SQL 数：{len(candidates)}",
        f"- 现有模板数：{len(templates)}",
        "",
        "## 分档结果",
        "",
    ]
    buckets = {"🟡 候选新增": [], "🟠 候选扩展": [], "🔵 范式覆盖": [], "🟢 已覆盖": []}
    for sql in candidates:
        cat, detail = classify(sql, templates)
        buckets.setdefault(cat, []).append((sql, detail))

    for cat in ["🟡 候选新增", "🟠 候选扩展", "🔵 范式覆盖", "🟢 已覆盖"]:
        items = buckets[cat]
        lines.append(f"### {cat}（{len(items)} 个）")
        lines.append("")
        if not items:
            lines.append("_无_")
            lines.append("")
            continue
        for sql, detail in sorted(items, key=lambda x: -x[0].mtime):
            tags = "、".join(sql.tags) or "-"
            mtime = datetime.fromtimestamp(sql.mtime).strftime("%Y-%m-%d")
            lines.append(f"- **{sql.path.name}** ({sql.line_count} 行, {mtime}, 标签: {tags})")
            lines.append(f"  - 路径: `{sql.rel_path}`")
            lines.append(f"  - 判定: {detail}")
        lines.append("")

    lines.append("## 处理建议")
    lines.append("")
    lines.append("- 🟡 **候选新增**：认真评估，可能是新方向。检查骨架是否可参数化、是否值得抽")
    lines.append("- 🟠 **候选扩展**：跟已有模板重合但多了新东西，考虑给对应模板加参数/新增 CTE")
    lines.append("- 🔵 **范式覆盖**：命中已沉淀在 `riding-case-pattern.md` 的 SQL 范式（TopN 拆位/10 档分位/ROW_NUMBER TopN），按范式现写即可，不建议抽")
    lines.append("- 🟢 **已覆盖**：跟某模板高度重合，通常只是换品类/时间——跳过")
    lines.append("")
    lines.append("要抽入库，把候选路径发给助手，说 \"抽这个成模板\" 即可。")
    return "\n".join(lines)


def build_notify_summary(candidates: List[SqlFeatures], templates: List[SqlFeatures], report_path: Path) -> str:
    buckets = {"🟡 候选新增": [], "🟠 候选扩展": [], "🟢 已覆盖": []}
    for sql in candidates:
        cat, _ = classify(sql, templates)
        buckets.setdefault(cat, []).append(sql)

    new_items = sorted(buckets["🟡 候选新增"], key=lambda x: -x.mtime)[:3]
    ext_items = sorted(buckets["🟠 候选扩展"], key=lambda x: -x.mtime)[:2]

    lines = [
        f"📊 SQL 库扫描 {datetime.now().strftime('%Y-%m-%d')}",
        f"新增 {len(buckets['🟡 候选新增'])} / 扩展 {len(buckets['🟠 候选扩展'])} / 已覆盖 {len(buckets['🟢 已覆盖'])}",
    ]
    if new_items:
        lines.append("")
        lines.append("🟡 top 新增：")
        for s in new_items:
            tags = "、".join(s.tags) or "-"
            lines.append(f"  · {s.path.name}（{s.line_count}行 / {tags}）")
    if ext_items:
        lines.append("")
        lines.append("🟠 top 扩展：")
        for s in ext_items:
            tags = "、".join(s.tags) or "-"
            lines.append(f"  · {s.path.name}（{s.line_count}行 / {tags}）")
    lines.append("")
    lines.append(f"报告：{str(report_path).replace(str(Path.home()), '~', 1)}")
    return "\n".join(lines)


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="只扫此日期（YYYY-MM-DD）之后修改的 SQL")
    ap.add_argument("--roots", help="逗号分隔的扫描根目录，覆盖默认")
    ap.add_argument("--no-write", action="store_true", help="只打印不落盘")
    ap.add_argument("--notify", action="store_true", help="扫完给自己发飞书摘要")
    args = ap.parse_args()

    since_ts = 0.0
    if args.since:
        since_ts = datetime.strptime(args.since, "%Y-%m-%d").timestamp()

    if args.roots:
        roots = [Path(p).expanduser() for p in args.roots.split(",")]
    else:
        roots = load_local_paths() + DEFAULT_ROOTS
    roots = list({p.resolve() for p in roots if p.exists()})

    templates = load_templates()
    print(f"扫描根：{[str(r) for r in roots]}", file=sys.stderr)
    print(f"现有模板：{len(templates)} 个", file=sys.stderr)

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

    report = build_report(candidates, templates)
    print(report)

    report_path = None
    if not args.no_write:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = OUTPUT_DIR / f"sql_scan_{datetime.now().strftime('%Y%m%d')}.md"
        report_path.write_text(report, encoding="utf-8")
        print(f"\n报告已落盘: {report_path}", file=sys.stderr)

    if args.notify:
        summary = build_notify_summary(candidates, templates, report_path or Path("(未落盘)"))
        send_lark(summary)

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path


OUTPUT_DIR = Path.home() / "claude-output"
XINGHE_SUBMIT_FALLBACK = os.environ.get("XINGHE_SUBMIT", "xinghe-submit")

SCRIPT_PATH = Path(__file__).resolve()
SKILL_DIR = SCRIPT_PATH.parent.parent
CRED_FILE = SKILL_DIR / ".credentials.local"
BUILTIN_SUBMIT = SCRIPT_PATH.parent / "xinghe_submit.sh"
LOCAL_PATHS_FILE = SKILL_DIR / ".local-sql-paths.local"

DEFAULT_SEARCH_PATHS = [
    Path.home() / "claude-output",
    Path.home() / ".claude" / "projects",
]
SEARCHABLE_SUFFIXES = (".sql", ".tsv", ".jsonl", ".md", ".txt")
MAX_FILE_SIZE = 5 * 1024 * 1024

NO_CRED_HINT = (
    "未找到 StarRiver / One-Service 凭证，也无法回退到 PATH 里的 xinghe-submit。\n"
    "特别说明：需提前在 zeye 平台申请一个 accessKey，访问以下链接获取\n"
    "（如果没访问权限，请联系业成）:\n"
    "https://zeye.zhuanspirit.com/main/showPage?pageId=getOrCreateAiAccessKey\n"
    "申请到 accessKey 后，在 skill 目录下创建 .credentials.local:\n"
    f"  路径: {CRED_FILE}\n"
    "  内容:\n"
    "    OA_NAME=你的OA账号\n"
    "    ACCESS_KEY=你的accessKey\n"
    "（.credentials.local 已被 .gitignore 忽略，不会随 skill 包分发）\n"
    "\n"
    "agent 触发准入流程模板（agent-browser 只读辅助）：\n"
    "  agent-browser open 'https://zeye.zhuanspirit.com/main/showPage?pageId=getOrCreateAiAccessKey'\n"
    "  agent-browser snapshot -i   # 拿交互元素，引导用户在页面里完成申请"
)


def _which_in_path(executable: str, extra_path: str) -> str | None:
    """Look up `executable` against the runtime PATH we hand subprocess."""
    if os.sep in executable:
        return executable if Path(executable).is_file() and os.access(executable, os.X_OK) else None
    for directory in extra_path.split(os.pathsep):
        if not directory:
            continue
        candidate = Path(directory) / executable
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.as_posix()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="stariver_query.py",
        description="Run Hive/Spark SQL through local 58 StarRiver tooling.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run a SQL string or SQL file")
    run.add_argument("--sql", help="SQL text")
    run.add_argument("--sql-file", help="Path to SQL file")
    run.add_argument("--preview-rows", type=int, default=10)
    run.add_argument("--json", action="store_true", help="Emit machine-readable JSON summary")

    desc = sub.add_parser("describe", help="Describe a Hive table")
    desc.add_argument("table")
    desc.add_argument("--formatted", action="store_true", help="Use DESCRIBE FORMATTED")
    desc.add_argument("--columns", default="", help="Comma-separated column names or regex patterns to preview")
    desc.add_argument("--preview-rows", type=int, default=80)
    desc.add_argument("--json", action="store_true")

    sample = sub.add_parser("sample", help="Sample a Hive table")
    sample.add_argument("table")
    sample.add_argument("--columns", default="", help="Comma-separated explicit columns. Required by some masked tables.")
    sample.add_argument("--where", help="WHERE clause without the word WHERE")
    sample.add_argument("--limit", type=int, default=20)
    sample.add_argument("--preview-rows", type=int, default=20)
    sample.add_argument("--json", action="store_true")

    parts = sub.add_parser("partitions", help="Show table partitions")
    parts.add_argument("table")
    parts.add_argument("--limit", type=int, default=80, help="Preview line limit")
    parts.add_argument("--json", action="store_true")

    dbs = sub.add_parser("show-databases", help="Show databases")
    dbs.add_argument("--like", help="Optional LIKE pattern")
    dbs.add_argument("--json", action="store_true")

    tables = sub.add_parser("show-tables", help="Show tables in a database")
    tables.add_argument("database")
    tables.add_argument("--like", help="Optional LIKE pattern")
    tables.add_argument("--json", action="store_true")

    chk = sub.add_parser("check", help="Probe StarRiver connectivity (show databases)")
    chk.add_argument("--json", action="store_true")

    ssql = sub.add_parser("search-sql", help="Search local reference SQL by keyword (grep, legacy)")
    ssql.add_argument("keyword")
    ssql.add_argument("--limit", type=int, default=20, help="Max candidate snippets to return")
    ssql.add_argument("--json", action="store_true")

    # 语义检索：读 sql_index.json，按关键词/表/tag 打分返回卡片
    cases = sub.add_parser("search-cases", help="Search local SQL case library by semantic keywords (uses sql_index.json)")
    cases.add_argument("query", help="Natural language keywords, e.g. 'riding search funnel love cart'")
    cases.add_argument("--top", type=int, default=5, help="Top N results")
    cases.add_argument("--json", action="store_true")

    initp = sub.add_parser("init-paths", help="Manage local reference SQL search paths")
    initp.add_argument("--add", help="Append a path to .local-sql-paths.local")
    initp.add_argument("--list", action="store_true", help="List current search paths")
    initp.add_argument("--json", action="store_true")

    vl = sub.add_parser("verify-lifecycle", help="Verify SQL dt range against table lifecycle before submit")
    vl.add_argument("--sql", help="SQL text")
    vl.add_argument("--sql-file", help="Path to SQL file")
    vl.add_argument("--json", action="store_true")

    # 续拉子命令：按已知 task_id 拉远程任务结果（处理本地超时但远程成功的场景）
    fetch = sub.add_parser("fetch", help="Fetch result by task_id (use when run timed out locally)")
    fetch.add_argument("--task-id", required=True, help="StarRiver task id (execute_id)")
    fetch.add_argument("--preview-rows", type=int, default=10)
    fetch.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "run":
        sql = read_sql(args.sql, args.sql_file)
    elif args.command == "describe":
        sql = f"describe {'formatted ' if args.formatted else ''}{args.table}"
    elif args.command == "sample":
        columns = args.columns.strip() or (
            "order_id,buyer_id,seller_id,info_id,cate_first_id,cate_first_name,"
            "cate_second_id,cate_second_name,cate_third_id,cate_third_name,pay_time,pay_price,dt"
        )
        sql = f"select {columns} from {args.table}"
        if args.where:
            sql += f" where {args.where}"
        sql += f" limit {max(args.limit, 1)}"
    elif args.command == "partitions":
        sql = f"show partitions {args.table}"
    elif args.command == "show-databases":
        sql = "show databases"
        if args.like:
            sql += f" like {quote_sql_string(args.like)}"
    elif args.command == "show-tables":
        sql = f"show tables in {args.database}"
        if args.like:
            sql += f" like {quote_sql_string(args.like)}"
    elif args.command == "check":
        sql = "show databases"
    elif args.command == "search-sql":
        result = search_local_sql(args.keyword, limit=args.limit)
        if getattr(args, "json", False):
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_search_result(result)
        return 0 if result["ok"] else 1
    elif args.command == "search-cases":
        result = search_cases(args.query, top=args.top)
        if getattr(args, "json", False):
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_cases_result(result)
        return 0 if result["ok"] else 1
    elif args.command == "init-paths":
        if args.add:
            result = add_local_path(args.add)
        else:
            result = list_local_paths()
        if getattr(args, "json", False):
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_init_paths_result(result)
        return 0 if result["ok"] else 1
    elif args.command == "verify-lifecycle":
        sql = read_sql(args.sql, args.sql_file)
        result = verify_lifecycle(sql)
        if getattr(args, "json", False):
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_verify_lifecycle_result(result)
        return 0 if result["ok"] else 1
    elif args.command == "fetch":
        result = fetch_by_task_id(args.task_id, preview_rows=args.preview_rows)
        if getattr(args, "json", False):
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_fetch_result(result)
        return 0 if result["ok"] else 1
    else:
        raise AssertionError(args.command)

    result = run_with_xinghe_submit(sql, preview_rows=getattr(args, "preview_rows", 10))
    if args.command == "describe" and args.columns:
        result["column_filter"] = args.columns
        result["preview"] = filter_describe_preview(
            result.get("preview") or [],
            parse_column_filters(args.columns),
        )
    if args.command == "check" and not result["ok"]:
        result["hint"] = (
            "StarRiver 连通性探活失败。如未申请 accessKey，请读 "
            f"{SKILL_DIR}/references/apply-access-key.md 按引导申请；\n"
            "或直接访问 https://zeye.zhuanspirit.com/main/showPage?pageId=getOrCreateAiAccessKey "
            "（没权限联系业成）。"
        )
    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(result)
    return 0 if result["ok"] else 1


def read_sql(sql: str | None, sql_file: str | None) -> str:
    if sql and sql_file:
        raise SystemExit("Use only one of --sql or --sql-file")
    if sql_file:
        return Path(sql_file).read_text(encoding="utf-8").strip()
    if sql:
        return sql.strip()
    text = sys.stdin.read().strip()
    if not text:
        raise SystemExit("No SQL provided. Use --sql, --sql-file, or stdin.")
    return text


def quote_sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run_with_xinghe_submit(sql: str, preview_rows: int) -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    before = newest_result_files()

    env = os.environ.copy()
    env["PATH"] = f"{Path.home() / 'bin'}:{Path.home() / '.local/bin'}:{env.get('PATH', '')}"

    # 凭证决策（按 SKILL.md Step 0 准入约束）：
    # 1) skill 目录下有 .credentials.local → 用 skill 内置 xinghe_submit.sh（自包含，同事也能跑）
    # 2) 否则尝试回退 PATH 里的 xinghe-submit（作者本机 ~/bin/xinghe-submit 现状）
    # 3) 两者皆无 → 直接报准入失败（带 zeye 申请链接 + agent-browser 操作模板）
    #    不再让 subprocess 抛 FileNotFoundError 绕一圈，避免 agent 误以为是程序 bug。
    if CRED_FILE.is_file():
        command = [BUILTIN_SUBMIT.as_posix()]
        submit_source = f"skill builtin (cred: {CRED_FILE})"
    else:
        resolved = _which_in_path(XINGHE_SUBMIT_FALLBACK, env["PATH"])
        if resolved is None:
            return {
                "ok": False,
                "error": (
                    "准入未通过：未配置 .credentials.local，且 PATH 上找不到 "
                    f"{XINGHE_SUBMIT_FALLBACK!r} 回退。\n\n{NO_CRED_HINT}"
                ),
                "sql": sql,
            }
        command = [resolved]
        submit_source = (
            f"PATH xinghe-submit fallback (no .credentials.local at {CRED_FILE})"
        )

    try:
        completed = subprocess.run(
            command,
            input=sql,
            text=True,
            capture_output=True,
            timeout=int(os.environ.get("STARIVER_QUERY_TIMEOUT", "900")),
            env=env,
        )
    except FileNotFoundError:
        return {
            "ok": False,
            "error": (
                f"{command[0]} not found. submit_source={submit_source}\n{NO_CRED_HINT}"
            ),
            "sql": sql,
        }
    except subprocess.TimeoutExpired as exc:
        # 关键修复：超时不丢 task_id —— 从 stderr 解析出 task_id，让用户能续拉
        timeout_stderr = exc.stderr or ""
        task_id = parse_task_id(timeout_stderr)
        hint = ""
        if task_id:
            hint = (
                f"\n\n💡 远程任务可能还在跑（task_id={task_id}）。续拉结果：\n"
                f"   python3 {Path(__file__).name} fetch --task-id {task_id}\n"
                f"   （或调高超时：STARIVER_QUERY_TIMEOUT=1800 python3 {Path(__file__).name} run --sql-file <file>）"
            )
        return {
            "ok": False,
            "task_id": task_id,
            "error": (
                "StarRiver query timed out locally. The remote task may still be running."
                + hint
            ),
            "stdout": exc.stdout or "",
            "stderr": timeout_stderr,
            "sql": sql,
        }

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    parsed_result_path = parse_result_path(stdout)
    detected_result_path = detect_new_result_file(before)
    result_path = parsed_result_path or detected_result_path
    task_id = parse_task_id(stderr)  # 正常路径也暴露 task_id
    result_is_new = bool(result_path and result_path not in before)
    should_preview = completed.returncode == 0 and bool(result_path)
    preview = preview_file(result_path, preview_rows) if should_preview else []
    line_count = count_lines(result_path) if should_preview else None

    return {
        "ok": completed.returncode == 0,
        "exit_code": completed.returncode,
        "task_id": task_id,
        "result_path": str(result_path) if result_path else "",
        "result_is_new": result_is_new,
        "line_count": line_count,
        "preview": preview,
        "stdout_tail": tail_lines(stdout, 80),
        "stderr_tail": tail_lines(stderr, 80),
        "sql": sql,
    }


def newest_result_files() -> set[Path]:
    return set(OUTPUT_DIR.glob("sql_result_*.tsv"))


def parse_task_id(stderr: str) -> str | None:
    """从 submit.sh 的 stderr 解析星河 task_id（execute_id）。

    submit.sh 第 120 行打的格式：'✅ 任务已提交，ID: <task_id>'
    """
    match = re.search(r"任务已提交[，,].*?ID[:：]\s*(\d+)", stderr or "")
    if match:
        return match.group(1)
    # 兜底：直接抓 7+ 位数字（task_id 经验值）
    match = re.search(r"\bexecute_id[\"']?\s*[:：=]\s*(\d{7,})", stderr or "")
    if match:
        return match.group(1)
    return None


def fetch_by_task_id(task_id: str, preview_rows: int = 10) -> dict:
    """按已知 task_id 拉远程任务结果（本地超时但远程成功的场景）。

    流程：
    1. 调 OneService queryTaskProgress 看任务状态
    2. SUCCESS → 调 downloadTaskResult 拉结果，落盘 sql_result_<task_id>.tsv
    3. RUNNING → 提示用户等
    4. FAILED → 报错
    """
    import urllib.request
    import urllib.parse

    if not CRED_FILE.is_file():
        return {
            "ok": False,
            "error": f"未配置 {CRED_FILE}，无法调 OneService API。{NO_CRED_HINT}",
        }
    # 读凭证
    cred = {}
    for line in CRED_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cred[k.strip()] = v.strip()
    oa = cred.get("OA_NAME", "")
    ak = cred.get("ACCESS_KEY", "")
    if not oa or not ak:
        return {
            "ok": False,
            "error": f"{CRED_FILE} 缺 OA_NAME / ACCESS_KEY",
        }

    base = "https://oneservice.zhuanspirit.com/sqlTask"

    # 1) 查状态
    try:
        with urllib.request.urlopen(f"{base}/queryTaskProgress/{task_id}", timeout=30) as r:
            progress = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "task_id": task_id, "error": f"查任务状态失败: {e}"}

    data_list = progress.get("respData", {}).get("data", [])
    status = data_list[0].get("status", "") if data_list else ""
    if status not in ("SUCCESS",):
        return {
            "ok": False,
            "task_id": task_id,
            "status": status,
            "error": f"任务状态={status}（非 SUCCESS）。详情：{progress}",
        }

    # 2) 拉结果
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result_path = OUTPUT_DIR / f"sql_result_{task_id}.tsv"
    params = urllib.parse.urlencode({"oaName58": oa, "accessKey": ak})
    try:
        with urllib.request.urlopen(
            f"{base}/downloadTaskResult/{task_id}?{params}", timeout=60
        ) as r:
            body = r.read().decode("utf-8")
    except Exception as e:
        return {"ok": False, "task_id": task_id, "error": f"下载结果失败: {e}"}

    # OneService 小结果集返回 JSON 包 respData 数组；大结果集走另一接口（先不处理）
    try:
        parsed = json.loads(body)
        if isinstance(parsed, dict) and "respData" in parsed:
            lines = parsed["respData"]
            if isinstance(lines, list):
                result_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            else:
                # 大结果集走 queryTaskResult 拿下载链接（先报错让用户用 jq 处理）
                return {
                    "ok": False,
                    "task_id": task_id,
                    "error": "结果可能是大结果集，需要走 queryTaskResult 拿下载链接。原始响应已存。",
                    "raw_path": str(result_path) + ".raw.json",
                }
        else:
            # 不是 JSON，直接当 TSV 落盘
            result_path.write_text(body, encoding="utf-8")
    except json.JSONDecodeError:
        # 已经是 TSV 文本
        result_path.write_text(body, encoding="utf-8")

    preview = preview_file(result_path, preview_rows) if result_path.is_file() else []
    line_count = count_lines(result_path) if result_path.is_file() else None

    return {
        "ok": True,
        "task_id": task_id,
        "status": "SUCCESS",
        "result_path": str(result_path),
        "line_count": line_count,
        "preview": preview,
    }


def print_fetch_result(result: dict) -> None:
    if result.get("ok"):
        print(f"OK: 任务 {result.get('task_id')} 结果已拉回")
        print(f"result_path: {result.get('result_path')}")
        print(f"line_count: {result.get('line_count')}")
        if result.get("preview"):
            print("preview:")
            for line in result["preview"]:
                print(line)
    else:
        print(f"FAILED: {result.get('error', 'unknown')}")
        if result.get("task_id"):
            print(f"task_id: {result['task_id']}")
        if result.get("status"):
            print(f"status: {result['status']}")


def parse_result_path(stdout: str) -> Path | None:
    match = re.search(r"结果已保存:\s*(/[^ \n\r]+sql_result_\d+\.tsv)", stdout)
    if match:
        return Path(match.group(1))
    match = re.search(r"(sql_result_\d+\.tsv)", stdout)
    if match:
        return OUTPUT_DIR / match.group(1)
    return None


def detect_new_result_file(before: set[Path]) -> Path | None:
    after = newest_result_files()
    new_files = list(after - before)
    if not new_files:
        return None
    return max(new_files, key=lambda p: p.stat().st_mtime)


def parse_column_filters(raw: str) -> list[re.Pattern[str]]:
    patterns: list[re.Pattern[str]] = []
    for item in raw.split(","):
        value = item.strip()
        if not value:
            continue
        escaped = re.escape(value).replace(r"\*", ".*")
        patterns.append(re.compile(f"^{escaped}$", re.IGNORECASE))
    return patterns


def filter_describe_preview(rows: list[str], patterns: list[re.Pattern[str]]) -> list[str]:
    if not patterns or len(rows) <= 1:
        return rows
    header = rows[0]
    filtered = [header]
    for row in rows[1:]:
        if not row or row.startswith("#"):
            continue
        col_name = row.split("\t", 1)[0]
        if any(pattern.search(col_name) for pattern in patterns):
            filtered.append(row)
    return filtered


def preview_file(path: Path, limit: int) -> list[str]:
    if not path.exists():
        return []
    rows: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for index, line in enumerate(handle):
            if index >= limit:
                break
            rows.append(line.rstrip("\n"))
    return rows


def count_lines(path: Path | None) -> int | None:
    if path is None or not path.exists():
        return None
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def tail_lines(text: str, limit: int) -> list[str]:
    return text.splitlines()[-limit:]


def print_human(result: dict[str, object]) -> None:
    if result.get("ok"):
        print("OK: StarRiver query finished")
    else:
        print("FAILED: StarRiver query failed")
        if result.get("error"):
            print(f"error: {result['error']}")

    # task_id 在正常/失败/超时都打印（出问题时 fetch 续拉）
    if result.get("task_id"):
        print(f"task_id: {result['task_id']}")
    if result.get("result_path"):
        print(f"result_path: {result['result_path']}")
        print(f"result_is_new: {str(result.get('result_is_new')).lower()}")
    if result.get("line_count") is not None:
        print(f"line_count: {result['line_count']}")
    if result.get("column_filter"):
        print(f"column_filter: {result['column_filter']}")

    preview = result.get("preview") or []
    if preview:
        print("preview:")
        for line in preview:
            print(line)

    stderr_tail = result.get("stderr_tail") or []
    if stderr_tail:
        print("stderr_tail:")
        for line in stderr_tail:
            print(line)

    stdout_tail = result.get("stdout_tail") or []
    if stdout_tail and not preview:
        print("stdout_tail:")
        for line in stdout_tail:
            print(line)

    hint = result.get("hint")
    if hint:
        print("")
        print("hint:")
        print(hint)


def autoscan_vscode_history() -> list[Path]:
    """扫描 VSCode 历史，提取所有 .sql/.SQL 文件所在目录的公共上层根。
    返回去重后的目录列表，给 collect_search_paths() 使用。
    """
    vscode_history = Path.home() / "Library/Application Support/Code/User/History"
    if not vscode_history.is_dir():
        return []
    import urllib.parse, os
    dirs: set[Path] = set()
    for entries_json in vscode_history.glob("*/entries.json"):
        try:
            data = json.loads(entries_json.read_text(encoding="utf-8"))
        except Exception:
            continue
        resource = data.get("resource", "")
        if not resource.startswith("file://"):
            continue
        path = urllib.parse.unquote(resource.replace("file://", "", 1))
        if not path.lower().endswith((".sql",)):
            continue
        dirs.add(Path(os.path.dirname(path)))
    # 提取公共上层根：如果多个目录都在 ~/Desktop/测试代码 下，只保留 ~/Desktop/测试代码
    if not dirs:
        return []
    # 简单算法：按路径深度排序，深的被浅的覆盖
    sorted_dirs = sorted(dirs, key=lambda p: len(p.parts))
    roots: list[Path] = []
    for d in sorted_dirs:
        if not any(str(d).startswith(str(r) + "/") for r in roots):
            roots.append(d)
    # 进一步聚合：找深度 ≥ 4 的"业务根"（如 ~/Desktop/测试代码 而不是 ~/Desktop）
    # 实操：如果某根下的所有 SQL 文件路径前 N 段都一样，N 就是公共根深度
    return [r for r in roots if r.exists()]


def collect_search_paths(auto_scan_if_empty: bool = True) -> list[Path]:
    paths = list(DEFAULT_SEARCH_PATHS)
    user_paths: list[Path] = []
    if LOCAL_PATHS_FILE.is_file():
        for line in LOCAL_PATHS_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            user_paths.append(Path(line).expanduser())
    # 首次跑数（用户路径文件不存在或为空）→ 自动扫 VSCode 历史
    if auto_scan_if_empty and not user_paths:
        vscode_dirs = autoscan_vscode_history()
        if vscode_dirs:
            # 写入 .local-sql-paths.local 让下次直接用
            LOCAL_PATHS_FILE.parent.mkdir(parents=True, exist_ok=True)
            header = "# auto-scanned from VSCode history on first run; edit freely\n"
            body = "\n".join(str(d) for d in vscode_dirs) + "\n"
            LOCAL_PATHS_FILE.write_text(header + body, encoding="utf-8")
            user_paths = vscode_dirs
    paths.extend(user_paths)
    seen: set[str] = set()
    unique: list[Path] = []
    for p in paths:
        s = str(p)
        if s in seen:
            continue
        seen.add(s)
        if p.exists():
            unique.append(p)
    return unique


def grep_in_file(fp: Path, kw_lower: str, max_hits: int) -> list[dict[str, object]]:
    hits: list[dict[str, object]] = []
    try:
        with fp.open("r", encoding="utf-8", errors="replace") as handle:
            for i, line in enumerate(handle, 1):
                if kw_lower in line.lower():
                    snippet = line.strip()
                    if len(snippet) > 200:
                        snippet = snippet[:200] + "..."
                    hits.append({"file": str(fp), "line": i, "snippet": snippet})
                    if len(hits) >= max_hits:
                        break
    except (OSError, UnicodeDecodeError):
        return hits
    return hits


def grep_in_path(path: Path, kw_lower: str, max_per_file: int, total_cap: int) -> list[dict[str, object]]:
    hits: list[dict[str, object]] = []
    if path.is_file():
        if path.suffix.lower() in SEARCHABLE_SUFFIXES and path.stat().st_size <= MAX_FILE_SIZE:
            # 路径名命中：文件名/父目录含关键词，整文件作为"路径命中"加进候选
            if kw_lower in str(path).lower():
                hits.append({"file": str(path), "line": 0, "snippet": "[路径名命中] " + path.name})
            hits.extend(grep_in_file(path, kw_lower, max_per_file))
        return hits
    try:
        for root, _, files in os.walk(path):
            for name in files:
                if len(hits) >= total_cap:
                    return hits
                if not name.endswith(SEARCHABLE_SUFFIXES):
                    continue
                fp = Path(root) / name
                try:
                    if fp.stat().st_size > MAX_FILE_SIZE:
                        continue
                except OSError:
                    continue
                # 路径名命中（文件夹/文件名含关键词）→ 加一条"路径命中"标记
                if kw_lower in str(fp).lower():
                    hits.append({"file": str(fp), "line": 0, "snippet": "[路径名命中] " + fp.name})
                    if len(hits) >= total_cap:
                        return hits
                file_hits = grep_in_file(fp, kw_lower, max_per_file)
                hits.extend(file_hits)
                if len(hits) >= total_cap:
                    return hits
    except OSError:
        return hits
    return hits


def scan_path_name_hits(path: Path, kw_lower: str, total_cap: int) -> list[dict[str, object]]:
    """单独扫"路径名命中"——只看文件路径含关键词，不读文件内容。"""
    hits: list[dict[str, object]] = []
    if path.is_file():
        if path.suffix.lower() in SEARCHABLE_SUFFIXES and kw_lower in str(path).lower():
            hits.append({"file": str(path), "line": 0, "snippet": "[路径名命中] " + path.name})
        return hits
    try:
        for root, _, files in os.walk(path):
            for name in files:
                if len(hits) >= total_cap:
                    return hits
                if not name.endswith(SEARCHABLE_SUFFIXES):
                    continue
                fp = Path(root) / name
                if kw_lower in str(fp).lower():
                    hits.append({"file": str(fp), "line": 0, "snippet": "[路径名命中] " + fp.name})
    except OSError:
        pass
    return hits


INDEX_FILE = SKILL_DIR / "sql_index.json"


def _tokenize_query(q: str) -> list[str]:
    """把自然语言 query 拆成中文/英文关键词列表"""
    # 中英文都当 token
    tokens = re.findall(r"[一-龥]+|[A-Za-z_][A-Za-z0-9_]+", q)
    # 中文再拆一下（简单按 2-3 字滑窗补充，兼容"骑行/漏斗"这种词）
    extra: list[str] = []
    for t in tokens:
        if re.fullmatch(r"[一-龥]+", t) and len(t) > 3:
            for i in range(len(t) - 1):
                extra.append(t[i:i+2])
    return [t.lower() for t in tokens + extra if t]


def _score_entry(entry: dict, tokens: list[str]) -> float:
    """给一份 SQL 打分：one_liner 命中权重最高，其次表/tag/paradigm/file_name/ctes"""
    if not tokens:
        return 0.0
    text_fields = {
        "one_liner": (entry.get("one_liner", "") or "").lower(),
        "file_name": (entry.get("file_name", "") or "").lower(),
        "tables": " ".join(entry.get("tables", [])).lower(),
        "tags": " ".join(entry.get("tags", [])).lower(),
        "paradigms": " ".join(entry.get("paradigms", [])).lower(),
        "ctes": " ".join(entry.get("ctes", [])).lower(),
    }
    weights = {
        "one_liner": 3.0,
        "tags": 2.0,
        "paradigms": 2.0,
        "file_name": 1.5,
        "tables": 1.2,
        "ctes": 0.8,
    }
    score = 0.0
    for tok in tokens:
        for field, text in text_fields.items():
            if tok in text:
                score += weights[field]
    # 新鲜度加成：最近 30 天 +0.5，最近 90 天 +0.2
    now = time.time()
    age_days = (now - entry.get("mtime", 0)) / 86400
    if age_days < 30:
        score += 0.5
    elif age_days < 90:
        score += 0.2
    return score


def search_cases(query: str, top: int = 5) -> dict[str, object]:
    """基于 sql_index.json 做语义检索，返回排序卡片"""
    if not INDEX_FILE.exists():
        return {
            "ok": False,
            "error": f"索引文件不存在：{INDEX_FILE}\n请先跑：python3 {SCRIPT_PATH.parent}/build_sql_index.py",
        }
    try:
        index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "error": f"索引读失败：{e}"}

    tokens = _tokenize_query(query)
    scored = []
    for entry in index.get("sqls", []):
        s = _score_entry(entry, tokens)
        if s > 0:
            scored.append((s, entry))
    scored.sort(key=lambda x: -x[0])
    top_hits = scored[:top]
    return {
        "ok": True,
        "query": query,
        "tokens": tokens,
        "index_updated_at": index.get("updated_at"),
        "total_indexed": index.get("total"),
        "matched": len(scored),
        "hits": [
            {
                "score": round(s, 2),
                "one_liner": e.get("one_liner"),
                "rel_path": e.get("rel_path"),
                "line_count": e.get("line_count"),
                "mtime_iso": e.get("mtime_iso"),
                "tags": e.get("tags", []),
                "paradigms": e.get("paradigms", []),
                "tables": e.get("tables", [])[:4],  # 只留前 4 张，避免炸
                "ctes": e.get("ctes", [])[:6],
            }
            for s, e in top_hits
        ],
    }


def print_cases_result(result: dict[str, object]) -> None:
    if not result.get("ok"):
        print(f"❌ {result.get('error')}", file=sys.stderr)
        return
    print(f"查询：{result['query']}")
    print(f"索引：{result['total_indexed']} 条，更新于 {result['index_updated_at']}；命中 {result['matched']} 条，返回 top {len(result['hits'])}")
    print()
    for i, hit in enumerate(result["hits"], 1):
        print(f"#{i}  score={hit['score']}  {hit['one_liner']}")
        print(f"    路径: {hit['rel_path']}  ({hit['line_count']}行, {hit['mtime_iso']})")
        if hit.get("tags"):
            print(f"    标签: {', '.join(hit['tags'])}")
        if hit.get("paradigms"):
            print(f"    范式: {', '.join(hit['paradigms'])}")
        if hit.get("tables"):
            print(f"    主表: {', '.join(hit['tables'])}")
        print()


def search_local_sql(keyword: str, limit: int = 20) -> dict[str, object]:
    paths = collect_search_paths()
    kw_lower = keyword.lower()
    # 第一轮：所有目录都扫"路径名命中"（不读文件内容）
    path_hits: list[dict[str, object]] = []
    for path in paths:
        path_hits.extend(scan_path_name_hits(path, kw_lower, total_cap=20))
    # 第二轮：所有目录扫"内容命中"
    content_hits: list[dict[str, object]] = []
    cap = max(limit, 50)
    for path in paths:
        remaining = cap - len(content_hits)
        if remaining <= 0:
            break
        content_hits.extend(grep_in_path(path, kw_lower, max_per_file=5, total_cap=remaining))
    # 去重：路径命中按文件名去重，内容命中按 snippet 去重
    seen_snippets: set[str] = set()
    seen_files: set[str] = set()
    candidates: list[dict[str, object]] = []
    # 路径命中优先（每个文件保留一条）
    for hit in path_hits:
        f = str(hit.get("file", ""))
        if f in seen_files:
            continue
        seen_files.add(f)
        candidates.append(hit)
        if len(candidates) >= limit:
            break
    # 内容命中（跳过已被路径命中的同文件，避免重复噪音）
    for hit in content_hits:
        if hit.get("line") == 0:
            continue  # grep_in_path 也会返回路径命中，跳过避免重复
        f = str(hit.get("file", ""))
        if f in seen_files:
            # 同一文件已被路径命中收录，跳过其内容命中
            continue
        key = str(hit.get("snippet", ""))[:80]
        if key in seen_snippets:
            continue
        seen_snippets.add(key)
        candidates.append(hit)
        if len(candidates) >= limit:
            break
    return {
        "ok": True,
        "keyword": keyword,
        "count": len(candidates),
        "path_hit_count": len([c for c in candidates if c.get("line") == 0]),
        "content_hit_count": len([c for c in candidates if c.get("line") != 0]),
        "searched_paths": [str(p) for p in paths],
        "local_paths_file": str(LOCAL_PATHS_FILE),
        "local_paths_file_exists": LOCAL_PATHS_FILE.is_file(),
        "candidates": candidates,
    }


def print_search_result(result: dict[str, object]) -> None:
    if result.get("ok"):
        print(f"OK: 搜到 {result.get('count', 0)} 条候选 (关键词: {result.get('keyword')})")
    else:
        print(f"FAILED: {result.get('error', 'unknown')}")
    print(f"searched_paths: {len(result.get('searched_paths', []))} 个")
    for p in result.get("searched_paths", []):
        print(f"  - {p}")
    if not result.get("local_paths_file_exists"):
        print(f"⚠️ {result.get('local_paths_file')} 不存在 — 首次跑数时建议问用户补充本机参考 SQL 路径并写入该文件")
    candidates = result.get("candidates") or []
    if not candidates:
        print("（无候选 — 本地无参考 SQL，去 58 查表探结构）")
    for i, hit in enumerate(candidates, 1):
        print(f"\n[{i}] {hit.get('file')}:{hit.get('line')}")
        print(f"    {hit.get('snippet')}")


# ── verify-lifecycle 相关 ─────────────────────────────────

_TABLE_PATTERN = re.compile(
    r'\b(?:from|join)\s+([a-zA-Z_][\w]*(?:\.[a-zA-Z_][\w]*){0,2})',
    re.IGNORECASE,
)
# CTE: 匹配 "name AS (" 或 "WITH name AS ("，宽松识别（不要求前缀必须是 with/,）
# 注意：必须排除"FROM x AS y"这种表别名 → 要求 AS 前不是 from/join 子句的别名
# 简化做法：识别所有 "(\w+) AS (" 模式，因为表别名不会立刻跟着 "("
_CTE_PATTERN = re.compile(r'(\w+)\s+AS\s*\(\s*\n?\s*(?:--|SELECT|WITH)', re.IGNORECASE)
_DT_BETWEEN = re.compile(
    r"\bdt\s+between\s+'(\d{4}-\d{2}-\d{2})'\s+and\s+'(\d{4}-\d{2}-\d{2})'",
    re.IGNORECASE,
)
_DT_GE_LE = re.compile(
    r"\bdt\s*>=\s*'(\d{4}-\d{2}-\d{2})'(?:\s+and\s+dt\s*<=\s*'(\d{4}-\d{2}-\d{2})')",
    re.IGNORECASE,
)
_DT_EQ = re.compile(r"\bdt\s*=\s*'(\d{4}-\d{2}-\d{2})'", re.IGNORECASE)
_DT_IN = re.compile(r"\bdt\s+in\s*\(([^)]+)\)", re.IGNORECASE)
_DATE = re.compile(r"'(\d{4}-\d{2}-\d{2})'")
_LIFECYCLE_PATTERNS = [
    re.compile(r"'lifecycle'\s*=\s*'(\d+)'", re.IGNORECASE),
    re.compile(r"'ttl'\s*=\s*'(\d+)'", re.IGNORECASE),
    re.compile(r"'retention'\s*=\s*'(\d+)'", re.IGNORECASE),
    re.compile(r"\blifecycle\s*[:=]\s*(\d+)", re.IGNORECASE),
    re.compile(r"\bttl\s*[:=]\s*(\d+)", re.IGNORECASE),
    re.compile(r"\bretention\s*[:=]\s*(\d+)", re.IGNORECASE),
]


def extract_tables(sql: str) -> list[str]:
    ctes = {m.lower() for m in _CTE_PATTERN.findall(sql)}
    found: list[str] = []
    seen: set[str] = set()
    for m in _TABLE_PATTERN.finditer(sql):
        t = m.group(1)
        last = t.split(".")[-1].lower()
        if last in ctes or t.lower() in seen:
            continue
        seen.add(t.lower())
        found.append(t)
    return found


def extract_dt_range(sql: str) -> dict[str, object] | None:
    m = _DT_BETWEEN.search(sql)
    if m:
        return {"start": m.group(1), "end": m.group(2), "kind": "between"}
    m = _DT_GE_LE.search(sql)
    if m:
        start = m.group(1)
        end = m.group(2) or start
        return {"start": start, "end": end, "kind": "ge_le"}
    m = _DT_EQ.search(sql)
    if m:
        d = m.group(1)
        return {"start": d, "end": d, "kind": "eq"}
    m = _DT_IN.search(sql)
    if m:
        dates = sorted(set(_DATE.findall(m.group(1))))
        if dates:
            return {"start": dates[0], "end": dates[-1], "kind": "in", "count": len(dates)}
    return None


def parse_days(start: str, end: str) -> int:
    try:
        s = datetime.strptime(start, "%Y-%m-%d").date()
        e = datetime.strptime(end, "%Y-%m-%d").date()
        return (e - s).days + 1
    except Exception:
        return 0


def parse_lifecycle_from_sql_comment(sql: str, table: str) -> int | None:
    """从 SQL 顶部注释里找用户声明的 lifecycle。
    支持两种格式：
      -- @lifecycle <table>=<days>
      -- @lifecycle <table>=permanent  (永久 → 9999)
    例：
      -- @lifecycle hdp_zhuanzhuan_dm_global.dm_trade_order_detail_1d=permanent
      -- @lifecycle hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d=180
    """
    # 把 table 转为正则安全
    safe = re.escape(table)
    pat = re.compile(
        rf"--\s*@lifecycle\s+{safe}\s*=\s*(\w+)",
        re.IGNORECASE,
    )
    m = pat.search(sql)
    if not m:
        return None
    val = m.group(1).lower()
    if val in ("permanent", "永久", "forever", "infinite"):
        return 9999
    try:
        return int(val)
    except ValueError:
        return None


def parse_lifecycle_from_describe(lines: list[str]) -> int | None:
    text = "\n".join(lines)
    for pat in _LIFECYCLE_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                continue
    return None


def _extract_latest_dt_from_show_partitions(preview: list[str]) -> str | None:
    """从 SHOW PARTITIONS 输出里提取最新 dt。
    preview 每行形如 'dt=2026-06-29' 或 'dt=2026-06-29/hour=00'。取所有行 dt= 后 10 字符,排序取最大。
    """
    bare_date = re.compile(r"dt=(\d{4}-\d{2}-\d{2})")
    dts: list[str] = []
    for line in preview:
        m = bare_date.search(line)
        if m:
            dts.append(m.group(1))
    if not dts:
        return None
    return max(dts)


def check_partition_availability(table: str, dt_range: dict) -> dict:
    """检查表的最新可用分区是否覆盖 SQL 请求的 dt 范围。

    优化策略(2026-07-01 修问题 22):
    - **优先用 SHOW PARTITIONS**(元数据操作,毫秒级返回,不扫数据)
    - SHOW PARTITIONS 拿不到 → 降级到 **SELECT MAX(dt) 但窗口限定最近 7 天**
      (避免 `dt >= start_date` 全量扫大表)

    返回 {ok, latest_dt, requested_end, gap_days, hint, method}
    """
    requested_end = dt_range["end"]
    latest_dt: str | None = None
    method = "unknown"

    # === 方法 1: SHOW PARTITIONS(推荐,元数据毫秒返回,不扫数据) ===
    # 关键:必须读完整结果文件(几千行分区),不能用 preview_rows(截断会漏最新分区)
    try:
        show_sql = f"SHOW PARTITIONS {table}"
        result = run_with_xinghe_submit(show_sql, preview_rows=10)
        result_path = result.get("result_path")
        if result_path and Path(str(result_path)).is_file():
            all_lines = Path(str(result_path)).read_text(encoding="utf-8").splitlines()
            if all_lines:
                latest_dt = _extract_latest_dt_from_show_partitions(all_lines)
                if latest_dt:
                    method = "SHOW PARTITIONS"
    except Exception:
        latest_dt = None

    # === 方法 2 兜底: SELECT MAX(dt) 但窗口限定最近 7 天 ===
    # 只在方法 1 失败时用,避免全量扫大表
    if latest_dt is None:
        try:
            from datetime import timedelta as _td
            requested = datetime.strptime(requested_end, "%Y-%m-%d").date()
            probe_start = (requested - _td(days=6)).isoformat()  # 最近 7 天
            fallback_sql = (
                f"SELECT MAX(dt) AS max_dt FROM {table} "
                f"WHERE dt BETWEEN '{probe_start}' AND '{requested_end}'"
            )
            result = run_with_xinghe_submit(fallback_sql, preview_rows=10)
            preview = result.get("preview") or []
            bare_date = re.compile(r"^\d{4}-\d{2}-\d{2}$")
            for line in preview:
                s = line.strip()
                if bare_date.match(s):
                    latest_dt = s
                    method = f"SELECT MAX(dt) 近 7 天 fallback"
                    break
        except Exception:
            latest_dt = None

    if latest_dt is None:
        return {
            "ok": False,
            "latest_dt": None,
            "requested_end": requested_end,
            "gap_days": None,
            "hint": (
                f"无法从 {table} 拿到最新分区(SHOW PARTITIONS 和 MAX(dt) 都失败),"
                f"手动确认后可继续"
            ),
            "method": method,
        }

    try:
        latest = datetime.strptime(latest_dt, "%Y-%m-%d").date()
        requested = datetime.strptime(requested_end, "%Y-%m-%d").date()
        gap = (requested - latest).days
    except Exception:
        return {
            "ok": False,
            "latest_dt": latest_dt,
            "requested_end": requested_end,
            "gap_days": None,
            "hint": "日期解析失败",
            "method": method,
        }
    return {
        "ok": gap <= 0,  # 请求结束日 ≤ 最新分区 = OK
        "latest_dt": latest_dt,
        "requested_end": requested_end,
        "gap_days": gap,
        "hint": (
            f"✅ 最新分区 {latest_dt} ≥ 请求 {requested_end} (via {method})"
            if gap <= 0
            else f"❌ 最新分区 {latest_dt},请求 {requested_end},差 {gap} 天未就绪。请改 dt 到 {latest_dt} 或更早。(via {method})"
        ),
        "method": method,
    }


def verify_lifecycle(sql: str) -> dict[str, object]:
    tables = extract_tables(sql)
    if not tables:
        return {
            "ok": False,
            "verdict": "REFUSE_SUBMIT",
            "error": "未从 SQL 解析出任何表名（from/join 后）",
            "sql_head": sql[:200],
        }
    dt_range = extract_dt_range(sql)
    if not dt_range:
        return {
            "ok": False,
            "verdict": "REFUSE_SUBMIT",
            "error": "未从 SQL 解析出 dt 范围（支持 dt= / dt between / dt>= and dt<= / dt in）",
            "tables": tables,
            "hint": "无 dt 过滤 → 拒绝提交。请加 dt 过滤后再 verify。",
        }
    days_requested = parse_days(dt_range["start"], dt_range["end"])
    table_results: list[dict[str, object]] = []
    any_exceeded = False
    any_unknown = False
    any_partition_unavailable = False
    min_lifecycle: int | None = None
    for table in tables:
        # 1) 生命周期检查：优先用 SQL 顶部注释里的 @lifecycle 声明（人工确认过的留痕），再退到 describe formatted
        lifecycle_from_comment = parse_lifecycle_from_sql_comment(sql, table)
        if lifecycle_from_comment is not None:
            lifecycle_days = lifecycle_from_comment
            describe_ok = True  # 注释声明视为已知
        else:
            desc_sql = f"describe formatted {table}"
            result = run_with_xinghe_submit(desc_sql, preview_rows=200)
            preview = result.get("preview") or []
            lifecycle_days = parse_lifecycle_from_describe(preview)
            describe_ok = result.get("ok", False)
        exceeded = lifecycle_days is not None and days_requested > lifecycle_days
        if exceeded:
            any_exceeded = True
        if lifecycle_days is None:
            any_unknown = True
        if lifecycle_days is not None:
            if min_lifecycle is None or lifecycle_days < min_lifecycle:
                min_lifecycle = lifecycle_days
        # 2) 分区可用性检查（新增）
        partition = check_partition_availability(table, dt_range)
        if not partition["ok"]:
            any_partition_unavailable = True
        table_results.append({
            "table": table,
            "lifecycle_days": lifecycle_days,
            "days_requested": days_requested,
            "exceeded": exceeded,
            "describe_ok": describe_ok,
            "lifecycle_from_comment": lifecycle_from_comment is not None,
            "partition_ok": partition["ok"],
            "latest_dt": partition.get("latest_dt"),
            "partition_hint": partition.get("hint"),
        })
    # 判定优先级：分区不可用 > 生命周期超 > 生命周期未知放宽 > OK
    if any_partition_unavailable:
        verdict = "REFUSE_SUBMIT"
        ok = False
        reason = "存在表请求的 dt 超出最新可用分区，跑了也是 0 行"
    elif any_exceeded:
        verdict = "REFUSE_SUBMIT"
        ok = False
        reason = "存在表 dt 范围超过生命周期"
    elif any_unknown and days_requested > 30:
        # 生命周期未知 + 请求范围 > 30 天 → 拒绝
        verdict = "REFUSE_SUBMIT"
        ok = False
        reason = f"存在表生命周期未知，且请求 {days_requested} 天 > 30 天保守阈值，按保守策略拒绝"
    elif any_unknown:
        # 生命周期未知 + 请求 ≤ 30 天 → 放行（保守阈值内）
        verdict = "OK_TO_SUBMIT"
        ok = True
        reason = f"存在表生命周期未知但请求 {days_requested} 天 ≤ 30 天保守阈值，放行"
    else:
        verdict = "OK_TO_SUBMIT"
        ok = True
        reason = f"所有表 dt 范围在生命周期内，最小生命周期 {min_lifecycle} 天"
    return {
        "ok": ok,
        "verdict": verdict,
        "reason": reason,
        "tables": table_results,
        "dt_range": dt_range,
        "days_requested": days_requested,
        "min_lifecycle_days": min_lifecycle,
    }


def print_verify_lifecycle_result(result: dict[str, object]) -> None:
    if result.get("ok"):
        print(f"OK: {result.get('verdict')} — {result.get('reason')}")
    else:
        print(f"FAILED: {result.get('verdict')} — {result.get('reason', result.get('error', 'unknown'))}")
    dt = result.get("dt_range")
    if dt:
        print(f"dt_range: {dt.get('start')} ~ {dt.get('end')} ({dt.get('kind')}) = {result.get('days_requested')} 天")
    if result.get("min_lifecycle_days") is not None:
        print(f"min_lifecycle: {result.get('min_lifecycle_days')} 天")
    for tr in result.get("tables", []):
        if tr.get("exceeded"):
            flag = "❌超"
        elif tr.get("lifecycle_days") is None:
            flag = "⚠️未知"
        else:
            flag = "✅"
        lc = tr.get("lifecycle_days") if tr.get("lifecycle_days") is not None else "?"
        # 区分注释声明和探查结果
        source = " (来自 SQL 注释 @lifecycle)" if tr.get("lifecycle_from_comment") else ""
        print(f"  {flag} {tr.get('table')} lifecycle={lc}天{source} 请求={tr.get('days_requested')}天 describe_ok={tr.get('describe_ok')}")
        # 分区可用性提示
        partition_hint = tr.get("partition_hint")
        if partition_hint:
            partition_flag = "    🟢" if tr.get("partition_ok") else "    🔴"
            print(f"{partition_flag} 分区: {partition_hint}")


# ── init-paths 相关 ──────────────────────────────────────

def list_local_paths() -> dict[str, object]:
    paths = collect_search_paths()
    default_set = {str(p) for p in DEFAULT_SEARCH_PATHS}
    return {
        "ok": True,
        "default_paths": [str(p) for p in DEFAULT_SEARCH_PATHS],
        "user_paths_file": str(LOCAL_PATHS_FILE),
        "user_paths_file_exists": LOCAL_PATHS_FILE.is_file(),
        "user_paths": [str(p) for p in paths if str(p) not in default_set],
        "all_search_paths": [str(p) for p in paths],
    }


def add_local_path(path: str) -> dict[str, object]:
    target = Path(path).expanduser()
    resolved = str(target)
    existing: list[str] = []
    if LOCAL_PATHS_FILE.is_file():
        for line in LOCAL_PATHS_FILE.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s and not s.startswith("#"):
                existing.append(s)
    if resolved in existing:
        return {
            "ok": True,
            "already_existed": True,
            "path": resolved,
            "user_paths_file": str(LOCAL_PATHS_FILE),
            "user_paths": existing,
        }
    LOCAL_PATHS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOCAL_PATHS_FILE.open("a", encoding="utf-8") as handle:
        handle.write(resolved + "\n")
    existing.append(resolved)
    return {
        "ok": True,
        "already_existed": False,
        "path": resolved,
        "user_paths_file": str(LOCAL_PATHS_FILE),
        "user_paths": existing,
    }


def print_init_paths_result(result: dict[str, object]) -> None:
    if not result.get("ok"):
        print(f"FAILED: {result.get('error', 'unknown')}")
        return
    if "path" in result:
        action = "已存在" if result.get("already_existed") else "已追加"
        print(f"OK: {action} 路径 {result.get('path')}")
        print(f"   写入文件: {result.get('user_paths_file')}")
        user_paths = result.get("user_paths", [])
        print(f"   当前用户路径列表 ({len(user_paths)} 个):")
        for p in user_paths:
            print(f"     - {p}")
        return
    print("OK: 当前本地参考 SQL 搜索路径")
    print(f"   用户路径文件: {result.get('user_paths_file')}")
    print(f"   文件存在: {result.get('user_paths_file_exists')}")
    print(f"   默认路径 ({len(result.get('default_paths', []))} 个):")
    for p in result.get("default_paths", []):
        print(f"     - {p}")
    user_paths = result.get("user_paths", [])
    if user_paths:
        print(f"   用户补充路径 ({len(user_paths)} 个):")
        for p in user_paths:
            print(f"     - {p}")
    else:
        print("   用户补充路径: 0 个（建议用 --add 补充本机参考 SQL 路径）")


if __name__ == "__main__":
    raise SystemExit(main())

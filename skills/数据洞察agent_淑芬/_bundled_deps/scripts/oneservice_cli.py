#!/usr/bin/env python3
"""
One-Service CLI — 在命令行提交 SQL 到星河/Hive，下载结果，可选导入飞书多维表格。

Usage:
  oneservice_cli.py --sql "SELECT * FROM db.table LIMIT 100"
  oneservice_cli.py --file query.sql --output result.xlsx
  oneservice_cli.py --file query.sql --to-base --base-name "我的数据表"
  echo "SELECT 1" | oneservice_cli.py --format csv

Credentials (env vars):
  ONESERVICE_OA       — OA 账号
  ONESERVICE_ACCESS_KEY — accessKey
"""

import argparse
import csv
import io
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from urllib.parse import urlencode

API_SUBMIT = "https://oneservice.zhuanspirit.com/sqlTask/submit"
API_PROGRESS = "https://oneservice.zhuanspirit.com/sqlTask/queryTaskProgress"
API_RESULT = "https://oneservice.zhuanspirit.com/sqlTask/queryTaskResult"
API_DOWNLOAD = "https://oneservice.zhuanspirit.com/sqlTask/downloadTaskResult"


def get_credentials():
    oa = os.environ.get("ONESERVICE_OA")
    ak = os.environ.get("ONESERVICE_ACCESS_KEY")
    if not oa or not ak:
        print("ERROR: 凭证未配置。请设置环境变量:", file=sys.stderr)
        print("  export ONESERVICE_OA=\"你的OA账号\"", file=sys.stderr)
        print("  export ONESERVICE_ACCESS_KEY=\"你的accessKey\"", file=sys.stderr)
        sys.exit(1)
    return oa, ak


def submit_sql(sql, oa, ak):
    data = urlencode({"sql": sql, "oaName58": oa, "accessKey": ak}).encode()
    req = urllib.request.Request(API_SUBMIT, data=data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    if result.get("respCode") != "0":
        raise RuntimeError(f"提交失败: {result}")
    execute_id = result["respData"]["data"]["execute_id"]
    return execute_id


def poll_progress(execute_id, poll_interval=2, max_wait=600):
    start = time.time()
    while time.time() - start < max_wait:
        url = f"{API_PROGRESS}/{execute_id}"
        with urllib.request.urlopen(url, timeout=15) as resp:
            result = json.loads(resp.read())
        if result.get("respCode") != "0":
            raise RuntimeError(f"查询进度失败: {result}")
        progresses = result.get("respData", {}).get("data", [])
        if not progresses:
            raise RuntimeError("未获取到执行状态")
        status = progresses[0].get("status")
        if status == "SUCCESS":
            return True
        elif status in ("FAILED", "KILLED"):
            error_msg = progresses[0].get("error_msg", "未知错误")
            raise RuntimeError(f"执行失败: {error_msg}")
        elapsed = int(time.time() - start)
        print(f"\r  等待中... {elapsed}s (status={status})", end="", file=sys.stderr)
        time.sleep(poll_interval)
    raise RuntimeError(f"等待超时（{max_wait}秒）")


def get_result_meta(execute_id, oa, ak):
    url = f"{API_RESULT}/{execute_id}?oaName58={oa}&accessKey={ak}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        result = json.loads(resp.read())
    if result.get("respCode") != "0":
        raise RuntimeError(f"获取结果失败: {result}")
    return result["respData"]["data"]


def download_file(url, local_path, oa, ak):
    separator = "&" if "?" in url else "?"
    full_url = f"{url}{separator}oaName58={oa}&accessKey={ak}"
    urllib.request.urlretrieve(full_url, local_path)


def download_direct(execute_id, oa, ak):
    """直接下载 txt 结果"""
    url = f"{API_DOWNLOAD}/{execute_id}?oaName58={oa}&accessKey={ak}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read())


def inject_sql_column(csv_path, sql):
    """在 CSV 中追加 sql_script 列，首行填 SQL，其余行留空"""
    # 读取原 CSV（处理 BOM）
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        return

    # 加新列头 + 首行数据填 SQL
    rows[0].append("_sql_script")
    for i, row in enumerate(rows[1:], 1):
        if i == 1:
            row.append(sql)
        else:
            row.append("")

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def import_to_base(csv_path, base_name):
    """调用 lark-cli 导入 CSV 到飞书多维表格"""
    csv_dir = os.path.dirname(csv_path)
    csv_name = os.path.basename(csv_path)
    cmd = [
        "lark-cli", "drive", "+import",
        "--file", csv_name,
        "--type", "bitable",
        "--name", base_name,
    ]
    print(f"导入飞书多维表格: {base_name} ...", file=sys.stderr)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, cwd=csv_dir,
        )
        if result.returncode != 0:
            print(f"导入失败: {result.stderr}", file=sys.stderr)
            return None
        # 解析输出找 Base URL
        output = result.stdout + result.stderr
        for line in output.split("\n"):
            if "http" in line and ("/base/" in line or "/bitable/" in line):
                # 提取纯 URL（可能包裹在 JSON 中）
                import re
                m = re.search(r'https?://[^\s"\'\\]+', line)
                if m:
                    return m.group(0)
                return line.strip()
        # 如果找不到 URL，返回原始输出
        print(output, file=sys.stderr)
        return None
    except FileNotFoundError:
        print("ERROR: 未找到 lark-cli，请先安装", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("导入超时，文件可能已在后台处理中", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="One-Service CLI — 星河/Hive SQL 查询")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--sql", help="SQL 语句")
    group.add_argument("--file", help="包含 SQL 的文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--format", "-f", choices=["csv", "xlsx", "txt", "json"], default="csv",
                        help="输出格式（默认 csv）")
    parser.add_argument("--timeout", type=int, default=600, help="最大等待时间（秒）")
    parser.add_argument("--preview", action="store_true", help="终端预览结果")
    parser.add_argument("--to-base", action="store_true", help="导入飞书多维表格")
    parser.add_argument("--base-name", help="多维表格名称（默认: 星河数据_时间戳）")

    args = parser.parse_args()

    # 获取 SQL
    if args.sql:
        sql = args.sql
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            sql = f.read()
    else:
        if sys.stdin.isatty():
            parser.print_help()
            sys.exit(1)
        sql = sys.stdin.read()

    sql = sql.strip()
    if not sql:
        print("ERROR: SQL 为空", file=sys.stderr)
        sys.exit(1)

    oa, ak = get_credentials()

    # 提交
    print(f"提交 SQL ({len(sql)} 字符)...", file=sys.stderr)
    execute_id = submit_sql(sql, oa, ak)
    print(f"execute_id={execute_id}", file=sys.stderr)

    # 等待
    print("等待执行完成...", file=sys.stderr)
    poll_progress(execute_id, max_wait=args.timeout)
    print("\n执行成功!", file=sys.stderr)

    # 获取结果元数据
    meta = get_result_meta(execute_id, oa, ak)

    # 预览模式
    if args.preview:
        previews = meta.get("previews", [])
        if previews:
            for block in previews:
                headers = block[0]
                print(" | ".join(str(h) for h in headers))
                print("-" * 60)
                for row in block[1:]:
                    print(" | ".join(str(v) for v in row))
        else:
            data = download_direct(execute_id, oa, ak)
            resp_data = data.get("respData", [])
            if resp_data:
                print(json.dumps(resp_data, ensure_ascii=False, indent=2))
        return

    # 确定输出文件
    if args.output:
        output_path = args.output
    else:
        fmt = args.format
        ext = {"csv": ".csv", "xlsx": ".xlsx", "txt": ".txt", "json": ".json"}[fmt]
        output_path = os.path.join(
            os.path.expanduser("~/Downloads"),
            f"result_{execute_id}{ext}",
        )

    # 下载
    fmt = os.path.splitext(output_path)[1].lower()
    if fmt == ".xlsx":
        download_url = meta.get("filename_excel")
    elif fmt == ".csv":
        download_url = meta.get("filename_csv") or meta.get("filename")
    else:
        download_url = meta.get("filename")

    if download_url:
        print(f"下载: -> {output_path}", file=sys.stderr)
        download_file(download_url, output_path, oa, ak)
        print(f"已保存到: {output_path}")
    else:
        data = download_direct(execute_id, oa, ak)
        resp_data = data.get("respData", [])
        if fmt == ".json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(resp_data, f, ensure_ascii=False, indent=2)
        elif fmt == ".csv":
            with open(output_path, "w", encoding="utf-8") as f:
                for item in resp_data:
                    f.write(f"{item}\n")
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(str(resp_data))
        print(f"已保存到: {output_path}")

    # 导入飞书多维表格
    if args.to_base:
        base_name = args.base_name or f"星河数据_{datetime.now().strftime('%m%d_%H%M')}"
        inject_sql_column(output_path, sql)
        url = import_to_base(output_path, base_name)
        if url:
            print(f"多维表格: {url}")


if __name__ == "__main__":
    main()

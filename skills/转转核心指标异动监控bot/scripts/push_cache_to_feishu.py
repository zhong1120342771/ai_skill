#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
push_cache_to_feishu.py — 把周缓存 CSV 写入飞书电子表格的新 sheet

目标表：wiki「核心数据问答agent_缓存数据」
  wiki_token = LEVSwxYA1i9Df8kG8n1c5CcJnoe
  spreadsheet_token = WMkQsQ2RUhOPyZt9OYrcoY3Tnhc
每次一份新周期数据 → 新建一个以【{start}~{end}】命名的 sheet，一次性 csv-put 全量。

用法：
  python3 push_cache_to_feishu.py                       # 读 latest_cache.json 推最新一份
  python3 push_cache_to_feishu.py --csv <某份缓存.csv>   # 指定 CSV

写入通道：lark-cli sheets +csv-put --csv @file。
  - 走文件而非 --values 命令行内联，绕开 ~75KB 参数长度上限；23388 行一次写完。
  - +csv-put 的 @file 只认「cwd 下的相对路径」，故临时 CSV 落在 ~/.claude 并把 subprocess cwd 设成那里。
约定：身份走 --as user（用户自己的 wiki）；凭证由 lark-cli 管理，本脚本不碰。
"""
import argparse, json, os, subprocess, sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(SKILL_DIR, 'data_storage')
CLAUDE_ROOT = os.path.expanduser('~/.claude')   # +csv-put @file 的相对路径基准
SPREADSHEET_TOKEN = 'WMkQsQ2RUhOPyZt9OYrcoY3Tnhc'


def lark(args, cwd=None):
    r = subprocess.run(['lark-cli'] + args, capture_output=True, text=True, cwd=cwd)
    out = (r.stdout or '') + (r.stderr or '')
    try:
        start = out.index('{')
        obj = json.loads(out[start:out.rindex('}') + 1])
    except Exception:
        obj = {'ok': False, 'raw': out[:500]}
    return obj


def list_sheets():
    """返回 [{sheet_id,title}, ...]。+workbook-info 的结构是 data.sheets（可能多套一层）。"""
    obj = lark(['sheets', '+workbook-info', '--spreadsheet-token', SPREADSHEET_TOKEN, '--as', 'user'])
    node = obj.get('data', {}).get('sheets', [])
    if isinstance(node, dict):
        node = node.get('sheets', [])
    return [s for s in node if isinstance(s, dict)]


def sheet_title(s):
    # +workbook-info 用 sheet_name；旧 +info 用 title。两者都兼容。
    return s.get('sheet_name') or s.get('title')


def sheet_exists(title):
    for s in list_sheets():
        if sheet_title(s) == title:
            return s.get('sheet_id')
    return None


def create_sheet(title):
    obj = lark(['sheets', '+sheet-create', '--spreadsheet-token', SPREADSHEET_TOKEN,
                '--title', title, '--as', 'user'])
    if not obj.get('ok'):
        raise RuntimeError(f'建 sheet 失败: {str(obj)[:300]}')
    # 兼容不同返回结构：data.sheet.sheet_id / data.replies[].addSheet.properties.sheetId
    d = obj.get('data', {})
    if isinstance(d.get('sheet'), dict) and d['sheet'].get('sheet_id'):
        return d['sheet']['sheet_id']
    for k in ('sheet_id', 'sheetId'):
        if d.get(k):
            return d[k]
    sid = sheet_exists(title)
    if sid:
        return sid
    raise RuntimeError(f'建 sheet 成功但拿不到 sheet_id: {str(obj)[:300]}')


def put_csv(sheet_id, csv_path):
    """把整份 CSV 一次性 csv-put 进 sheet（A1 起）。
    @file 只认 cwd 下相对路径 → 临时拷到 CLAUDE_ROOT，subprocess cwd 设成 CLAUDE_ROOT。"""
    tmp_name = f'_cache_push_{sheet_id}.csv'
    tmp_path = os.path.join(CLAUDE_ROOT, tmp_name)
    import shutil
    shutil.copyfile(csv_path, tmp_path)
    try:
        obj = lark(['sheets', '+csv-put', '--spreadsheet-token', SPREADSHEET_TOKEN,
                    '--sheet-id', sheet_id, '--start-cell', 'A1',
                    '--csv', f'@./{tmp_name}', '--as', 'user'], cwd=CLAUDE_ROOT)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
    if not obj.get('ok'):
        raise RuntimeError(f'csv-put 失败: {json.dumps(obj.get("error", obj), ensure_ascii=False)[:300]}')
    return obj.get('data', {})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', help='缓存 CSV 路径；默认读 latest_cache.json')
    args = ap.parse_args()

    if args.csv:
        csv_path = args.csv
        base = os.path.basename(csv_path)
        title = base.replace('转转核心指标缓存数据.csv', '').strip('【】') or base
        if base.startswith('【') and '】' in base:
            title = base[1:base.index('】')]
    else:
        p = json.load(open(os.path.join(CACHE_DIR, 'latest_cache.json'), encoding='utf-8'))
        csv_path = p['csv_path']
        title = f"{p['period_start']}~{p['period_end']}"

    import pandas as pd
    df = pd.read_csv(csv_path)
    print(f'[push] CSV={csv_path}\n  sheet 名=「{title}」 行数={len(df)} 列数={len(df.columns)}')

    existing = sheet_exists(title)
    if existing:
        print(f'[skip] 已存在同名 sheet「{title}」(id={existing})，不重复建。'
              f'如需重推请先手动删该 sheet。')
        return 0

    sid = create_sheet(title)
    print(f'[ok] 新建 sheet id={sid}')

    data = put_csv(sid, csv_path)
    print(f'[done] 已写入飞书 sheet「{title}」，range={data.get("updated_range")} '
          f'cells={data.get("updated_cells_count")}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

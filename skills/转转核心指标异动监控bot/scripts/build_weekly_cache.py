#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_weekly_cache.py — 核心底表「过去一周全量」离线缓存构建器

每周一自动跑：把核心底表 hdp_zhuanzhuan_tmp_global.tmp_dws_zz_core_dataagent_zmt_v2_di
过去 7 天（默认 t-7 ~ t-1）的全量数据（全部 tag_01 口径族、全部维度）拉下来，
落到 skill 目录下的 data_storage/，供「数据问答」快捷分支在非时效性问题上离线命中。

产物：
  <skill>/data_storage/【{start}~{end}】转转核心指标缓存数据.csv   (utf-8-sig)
  <skill>/data_storage/latest_cache.json                          (指针：周期+路径+行数+构建时间)

用法：
  python3 build_weekly_cache.py                 # 默认 t-7 ~ t-1
  python3 build_weekly_cache.py --end 2026-07-08 --days 7
  python3 build_weekly_cache.py --start 2026-07-01 --end 2026-07-07

约定：
  - 凭证只走环境变量（XINGHE_CLIENT_USER/SECRET/OA），不硬编码、不打印。
  - 取数通道星河为主（Hive engine=5）；下载 xlsx 转 CSV 落盘。
  - 全量 = 不加 tag_01 过滤，拉整表该区间所有行。
"""
import argparse, json, os, sys, urllib.request
from datetime import date, timedelta

sys.path.insert(0, '/Users/zhongmengting/.claude/skills/xinghe-data/scripts')
from xinghe_client import XingheExplorer  # noqa: E402

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(SKILL_DIR, 'data_storage')
TABLE = 'hdp_zhuanzhuan_tmp_global.tmp_dws_zz_core_dataagent_zmt_v2_di'


def d(s):
    y, m, dd = map(int, s.split('-'))
    return date(y, m, dd)


def build_sql(start, end):
    # 全量：不加 tag_01 过滤，拉该区间所有口径族所有维度
    return f"""SELECT tag_01, wd,
       exp_pv, exp_uv, detail_pv, detail_uv,
       order_pv, order_uv, pay_pv,
       matched_dau_uv, matched_duan, matched_source, matched_type,
       dt
FROM {TABLE}
WHERE dt BETWEEN '{start}' AND '{end}'
ORDER BY dt, tag_01, wd
LIMIT 1000000"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--end', help='区间右端(YYYY-MM-DD)，默认 t-1')
    ap.add_argument('--start', help='区间左端(YYYY-MM-DD)，默认 end-(days-1)')
    ap.add_argument('--days', type=int, default=7, help='未给 start 时回看天数，默认 7')
    ap.add_argument('--max-wait', type=int, default=600, help='星河等待上限秒')
    ap.add_argument('--no-feishu', action='store_true', help='只落盘，不推飞书表格')
    args = ap.parse_args()

    end = d(args.end) if args.end else date.today() - timedelta(days=1)
    start = d(args.start) if args.start else end - timedelta(days=args.days - 1)
    start_s, end_s = start.isoformat(), end.isoformat()

    if not os.environ.get('XINGHE_CLIENT_USER'):
        print('[STOP] XINGHE_CLIENT_USER MISSING，先 source ~/.zshrc 或按 xinghe-data 配置凭证')
        return 2

    os.makedirs(CACHE_DIR, exist_ok=True)
    csv_name = f'【{start_s}~{end_s}】转转核心指标缓存数据.csv'
    csv_path = os.path.join(CACHE_DIR, csv_name)

    print(f'[cache] 区间 {start_s} ~ {end_s}（全量口径族），拉 {TABLE}')
    client = XingheExplorer()
    eid = client.run_sql(build_sql(start_s, end_s), sql_engine=5, submit_timeout=120)
    r = client.wait_and_get_result(eid, max_wait=args.max_wait)

    xlsx_url = r.get('filename_excel')
    if not xlsx_url:
        print(f'[STOP] 星河未返回下载地址，previews={str(r.get("previews"))[:200]}')
        return 2

    import pandas as pd
    xlsx_tmp = csv_path.replace('.csv', '.xlsx')
    urllib.request.urlretrieve(xlsx_url, xlsx_tmp)
    df = pd.read_excel(xlsx_tmp)
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    os.remove(xlsx_tmp)

    dts = sorted(df['dt'].astype(str).unique()) if 'dt' in df.columns else []
    pointer = {
        'period_start': start_s,
        'period_end': end_s,
        'dt_covered': dts,
        'rows': int(len(df)),
        'tag_01_families': int(df['tag_01'].nunique()) if 'tag_01' in df.columns else None,
        'csv_path': csv_path,
        'built_at': date.today().isoformat(),
    }
    with open(os.path.join(CACHE_DIR, 'latest_cache.json'), 'w', encoding='utf-8') as f:
        json.dump(pointer, f, ensure_ascii=False, indent=2)

    print(f'[done] 落盘 {csv_path}')
    print(f'  行数={pointer["rows"]}  口径族={pointer["tag_01_families"]}  覆盖 dt={dts[:3]}…{dts[-1:] }')
    print(f'  指针 latest_cache.json 已更新，period={start_s}~{end_s}')

    # 落盘成功后，自动把这份缓存追加写入飞书表格的新 sheet（sheet 名=时间周期）
    if not args.no_feishu:
        push_py = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'push_cache_to_feishu.py')
        print(f'[feishu] 推送到飞书表格新 sheet「{start_s}~{end_s}」…')
        rc = os.system(f'python3 "{push_py}" --csv "{csv_path}"')
        if rc != 0:
            print('[warn] 飞书推送非零退出，缓存本身已落盘；可手动重跑 push_cache_to_feishu.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())

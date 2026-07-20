#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_backfill.py — 底表回刷批量提交器（星河 SparkSQL engine=2，支持并发）

回刷目标表 tmp_dws_zz_core_dataagent_zmt_v2_di 指定日期区间 [--start, --end]。
默认「只查缺 + 只补缺」：先查区间内已有分区，只对缺失日期回刷，不动已有好数据。

两种回刷模式（--mode）：
  single (默认，推荐)——逐个缺失日单天回刷，读 backfill_single_day.sql，
      把 ${targetDay} 替换为该天，SQL 只扫 dt=该天单分区、insert overwrite 只写这 1 个分区。
      补 N 个缺失日 = N 个单天 job，各写各的分区，天然不重叠可自由并发，最省资源。
  window ——31 天滚动窗口，读 backfill_history.sql，${outFileSuffix}=窗口右端，
      单批覆盖 [right-30,right] 31 个分区（会顺带重刷窗口内已有分区）。
      仅当需要用后续更新的快照修正较早历史的退款口径时才用。

用法：
  # 补最近缺失日（默认单天模式，最省）：
  python3 run_backfill.py --start 2026-06-01 --end 2026-07-13 --parallel 4
  # 只看计划不提交（先跑这个确认要补哪几天）：
  python3 run_backfill.py --start 2026-06-01 --end 2026-07-13 --dry-run
  # 冒烟：只跑第一个缺失日并校验分区非空：
  python3 run_backfill.py --start 2026-06-01 --end 2026-07-13 --smoke
  # 修正历史退款口径时才用滚动窗口：
  python3 run_backfill.py --start 2025-05-01 --end 2025-05-31 --mode window --force-all

约定：
  - --start/--end 是「回刷区间」的闭区间端点。
  - 默认查缺口只补缺失日；--force-all 关闭缺口探测强刷整区间。
  - 凭证只走环境变量（XINGHE_CLIENT_USER/SECRET/OA），脚本不硬编码。
  - 每批完成后校验目标分区行数，为 0 记为空分区异常（info join 未命中）。
  - 引擎见 SQL_ENGINE 常量（默认 2=SparkSQL，规避 Hive 6h 上限）。
"""
import argparse, os, sys, time, urllib.request
from datetime import date, timedelta

sys.path.insert(0, '/Users/zhongmengting/.claude/skills/xinghe-data/scripts')
from xinghe_client import XingheExplorer, XingheAPIError  # noqa: E402

SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backfill_history.sql')
SINGLE_SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backfill_single_day.sql')
TABLE = 'hdp_zhuanzhuan_tmp_global.tmp_dws_zz_core_dataagent_zmt_v2_di'
INFO_TABLE = 'hdp_zhuanzhuan_dw_global.dw_mysql_info_full_1d'
WINDOW_DAYS = 31  # 仅 window 模式：单批 SQL 覆盖 [right-30, right]；步长必须 = 此值才能非重叠平铺
SQL_ENGINE = 2   # 2=SparkSQL(大批量回刷，规避 Hive 6h 上限) 4=StarRocks 5=Hive


def info_snapshot_dt(client):
    """商品维度快照钉到 t-1（相对运行日）。info 全量快照表只留最近~3周，
    历史日期取不到当时快照，统一用 t-1 这一份最新映射即可（品类映射相对稳定）。
    若 t-1 分区尚未就绪，回退到 show partitions 的最大可用分区。"""
    t1 = (date.today() - timedelta(days=1)).isoformat()
    eid = client.run_sql(f"show partitions {INFO_TABLE}", sql_engine=SQL_ENGINE)
    r = client.wait_and_get_result(eid, max_wait=180)
    dts = []
    for blk in (r.get('previews') or []):
        for row in blk:
            s = str(row[0]) if row else ''
            if 'dt=' in s:
                dts.append(s.split('dt=')[-1].strip())
    if t1 in dts:
        return t1
    if dts:
        print(f'[warn] info t-1={t1} 分区未就绪，回退到最新可用 {max(dts)}')
        return max(dts)
    raise RuntimeError('无法解析 info 分区列表')


def d(s):
    y, m, dd = map(int, s.split('-'))
    return date(y, m, dd)


def windows(start, end, step=WINDOW_DAYS):
    """返回 [(left, right)] 窗口列表。右端从 start 起步长 step 前向平铺，
    末批右端裁到 end。前向平铺天然非重叠；仅末批裁剪可能与前一批重叠，
    并发池用 overlap 守卫把这一对串行化（见 run_pool）。"""
    rights, cur = [], start
    while cur < end:
        rights.append(cur)
        cur = cur + timedelta(days=step)
    if not rights or rights[-1] != end:
        rights.append(end)
    out = []
    seen = set()
    for r in rights:
        if r > end:
            r = end
        if r in seen:
            continue
        seen.add(r)
        out.append((r - timedelta(days=WINDOW_DAYS - 1), r))
    return out


def existing_dts(client, start, end):
    """查目标表在 [start,end] 已有数据的 dt 集合。下载 distinct dt 结果文件
    再本地解析，避免 previews 50 行截断。"""
    sql = (f"select distinct dt from {TABLE} "
           f"where dt between '{start.isoformat()}' and '{end.isoformat()}' order by dt")
    eid = client.run_sql(sql, sql_engine=SQL_ENGINE)
    r = client.wait_and_get_result(eid, max_wait=600)
    url = r.get('filename') or r.get('filename_excel')
    have = set()
    if url:
        tmp = os.path.join('/tmp', f'backfill_have_{int(time.time())}.txt')
        urllib.request.urlretrieve(url, tmp)
        for tok in open(tmp, encoding='utf-8').read().split():
            if len(tok) == 10 and tok[4] == '-' and tok[:2] == '20':
                have.add(tok)
        os.remove(tmp)
    else:  # 结果为空文件时退回 previews
        for blk in (r.get('previews') or []):
            for row in blk:
                s = str(row[0]) if row else ''
                if len(s) == 10 and s[4] == '-':
                    have.add(s)
    return have


def missing_ranges(start, end, have):
    """[start,end] 内不在 have 里的日期，聚合成连续区间 [(a,b),...]。"""
    miss, cur = [], start
    while cur <= end:
        if cur.isoformat() not in have:
            miss.append(cur)
        cur += timedelta(days=1)
    ranges, s, prev = [], None, None
    for m in miss:
        if prev is None:
            s = m; prev = m
        elif (m - prev).days == 1:
            prev = m
        else:
            ranges.append((s, prev)); s = m; prev = m
    if s is not None:
        ranges.append((s, prev))
    return ranges


def windows_for_ranges(ranges):
    """对每个缺口连续区间独立切 31 天窗口，拼成总批次列表。
    单区间内：右端从 (左端+30) 起步长 31 前向平铺，末批右端裁到区间右端，
    保证所有窗口都落在缺口内、不覆写已有好数据。"""
    out = []
    for a, b in ranges:
        first_right = a + timedelta(days=WINDOW_DAYS - 1)
        if first_right > b:
            first_right = b
        for (l, r) in windows(first_right, b):
            l2 = l if l >= a else a          # 左端夹到缺口内
            out.append((l2, r))
    return out


def _each_day(a, b):
    """闭区间 [a,b] 逐日展开成 date 列表。"""
    out, cur = [], a
    while cur <= b:
        out.append(cur); cur += timedelta(days=1)
    return out


def load_sql(single=False):
    path = SINGLE_SQL_PATH if single else SQL_PATH
    with open(path, encoding='utf-8') as f:
        return f.read()


def part_count(client, dt_str):
    eid = client.run_sql(
        f"select count(1) as c from {TABLE} where dt='{dt_str}'", sql_engine=SQL_ENGINE)
    r = client.wait_and_get_result(eid, max_wait=300)
    for blk in (r.get('previews') or []):
        for row in blk:
            if row and str(row[0]).isdigit():
                return int(row[0])
    return -1


def _overlaps(w, running):
    """窗口 w=(left,right) 是否与任何在跑窗口有交集（同一天会撞动态分区写）。"""
    l, r = w
    for (rl, rr) in running:
        if l <= rr and rl <= r:
            return True
    return False


def run_pool(client, tmpl, info_dt, outs, parallel, max_wait, poll=15, single_day=False):
    """并发提交池：同时保持至多 parallel 个 job 在跑，用 get_progress 批量轮询，
    某个完成就补下一批。窗口有交集的批次不同时在跑（overlap 守卫，防抢写同分区）。
    single_day=True 时每个 out=(day,day) 只写 dt=day 单分区，用 ${targetDay} 占位符，
    各 job 天然不重叠可自由并发；否则走滚动窗口 ${outFileSuffix}（覆盖 [right-30,right]）。
    返回 (成功 dt 列表, 失败 [(dt,阶段,信息)])。"""
    pending = list(enumerate(outs, 1))     # [(idx,(left,right)), ...] 待提交
    inflight = {}                          # execute_id -> (idx, left, right, ts)
    done, fails = [], []
    total = len(outs)

    def submit(idx, left, right):
        osfx = right.isoformat()
        if single_day:
            sql = tmpl.replace('${infoSnapshotDt}', info_dt).replace('${targetDay}', osfx)
        else:
            sql = tmpl.replace('${infoSnapshotDt}', info_dt).replace('${outFileSuffix}', osfx)
        try:
            eid = client.run_sql(sql, sql_engine=SQL_ENGINE, submit_timeout=120)
            inflight[eid] = (idx, left, right, time.time())
            print(f'[submit 批{idx:02d}/{total}] [{left},{right}] → eid={eid} '
                  f'(在跑 {len(inflight)})', flush=True)
        except Exception as e:
            print(f'[ERR 批{idx:02d}] 提交失败: {str(e)[:180]}')
            fails.append((osfx, 'submit', str(e)[:180]))

    def fill():
        """在并发上限内，取第一个与在跑窗口不重叠的待提交批提交。"""
        running = [(l, r) for (_, l, r, _) in inflight.values()]
        i = 0
        while pending and len(inflight) < parallel and i < len(pending):
            idx, (l, r) = pending[i]
            if _overlaps((l, r), running):
                i += 1; continue          # 与在跑批重叠，跳过等它先完成
            pending.pop(i)
            submit(idx, l, r)
            running.append((l, r))
        # 若因重叠一个都没提交、且当前无在跑（不可能死锁的兜底）
        if not inflight and pending:
            idx, (l, r) = pending.pop(0)
            submit(idx, l, r)

    fill()
    while inflight:
        eids = list(inflight.keys())
        try:
            progs = client.get_progress(eids)
        except Exception as e:
            print(f'[warn] 进度查询失败，重试: {str(e)[:120]}')
            time.sleep(poll); continue
        status = {p['execute_id']: p for p in progs}
        for eid in eids:
            p = status.get(eid, {})
            st = p.get('status')
            idx, left, right, ts = inflight[eid]
            osfx = right.isoformat()
            if st == 'SUCCESS':
                dur = int(time.time() - ts)
                cr = part_count(client, osfx)
                tag = 'OK' if cr > 0 else 'EMPTY'
                print(f'[done 批{idx:02d}] 右端 {osfx} {dur}s 分区行数={cr} [{tag}]', flush=True)
                if cr > 0:
                    done.append(osfx)
                else:
                    fails.append((osfx, 'empty', f'rows={cr}'))
                del inflight[eid]
            elif st in ('FAILED', 'KILLED'):
                print(f'[FAIL 批{idx:02d}] 右端 {osfx}: {p.get("error_msg","")[:180]}')
                fails.append((osfx, 'exec', p.get('error_msg', '')[:180]))
                del inflight[eid]
            elif time.time() - ts > max_wait:
                print(f'[TIMEOUT 批{idx:02d}] 右端 {osfx} 超 {max_wait}s，放弃跟踪(不 kill)')
                fails.append((osfx, 'timeout', f'>{max_wait}s'))
                del inflight[eid]
        fill()
        if inflight:
            time.sleep(poll)
    return done, fails


def main():
    ap = argparse.ArgumentParser(
        description='回刷 tmp_dws_zz_core_dataagent_zmt_v2_di 指定日期区间。'
                    '默认自动跳过已有分区，只补缺失日期；不同日期窗口并发跑。')
    ap.add_argument('--start', required=True, help='回刷区间起始日 (YYYY-MM-DD，含)')
    ap.add_argument('--end', required=True, help='回刷区间结束日 (YYYY-MM-DD，含)')
    ap.add_argument('--parallel', type=int, default=4, help='并发在跑 job 数上限(默认4)')
    ap.add_argument('--dry-run', action='store_true', help='只打印批次计划不提交')
    ap.add_argument('--smoke', action='store_true', help='只跑第一批并校验非空')
    ap.add_argument('--max-wait', type=int, default=7200, help='单 job 等待上限秒(默认7200)')
    ap.add_argument('--force-all', action='store_true',
                    help='不查缺口，强制重刷整个区间(覆写已有分区)')
    ap.add_argument('--mode', choices=['single', 'window'], default='single',
                    help='single(默认)=逐个缺失日单天回刷,只写各自1个分区,最省; '
                         'window=31天滚动窗口(会顺带重刷窗口内已有分区,仅修正历史退款时用)')
    args = ap.parse_args()

    start, end = d(args.start), d(args.end)
    if start > end:
        print(f'[ERR] start {start} 晚于 end {end}'); return 1

    single = (args.mode == 'single')
    client = XingheExplorer()

    # 默认只补缺口；--force-all 重刷整个区间
    if args.force_all:
        if single:
            # 强刷 + 单天：整区间每天各一个单天批
            days = []
            cur = start
            while cur <= end:
                days.append((cur, cur)); cur += timedelta(days=1)
            outs = days
            print(f'[mode] 强制重刷整区间 [{start},{end}]（单天模式，逐天覆写各自分区，共 {len(outs)} 天）')
        else:
            outs = windows(start, end)
            print(f'[mode] 强制重刷整区间 [{start},{end}]（滚动窗口，覆写已有分区）')
    else:
        have = existing_dts(client, start, end)
        ranges = missing_ranges(start, end, have)
        span = (end - start).days + 1
        miss_days = [dd for (a, b) in ranges
                     for dd in _each_day(a, b)]
        print(f'[mode] 只补缺口：区间 [{start},{end}] 共 {span} 天，'
              f'已有 {len(have)} 天，缺 {span - len(have)} 天，{len(ranges)} 个连续段')
        for a, b in ranges:
            print(f'   缺口段: {a} ~ {b} ({(b - a).days + 1}d)')
        if not ranges:
            print('区间内无缺口，无需回刷。'); return 0
        if single:
            outs = [(dd, dd) for dd in miss_days]   # 每个缺失日一个单天批
        else:
            outs = windows_for_ranges(ranges)

    if args.smoke:
        outs = outs[:1]
    parallel = 1 if args.smoke else max(1, args.parallel)
    if single:
        print(f'[plan] {len(outs)} 个单天批，并发 {parallel}，每批只写 1 个分区(dt=该天)')
        for i, (l, r) in enumerate(outs, 1):
            print(f'   批{i:02d}: 写分区 dt={r}')
    else:
        print(f'[plan] {len(outs)} 批，并发 {parallel}，窗口 {WINDOW_DAYS} 天前向平铺'
              f'(重叠批由 overlap 守卫串行)')
        for i, (l, r) in enumerate(outs, 1):
            print(f'   批{i:02d}: 覆盖 [{l} , {r}]')
    if args.dry_run:
        return 0

    tmpl = load_sql(single)
    info_dt = info_snapshot_dt(client)
    print(f'[info] 商品维度快照钉在 t-1 分区 dt={info_dt}')

    done, fails = run_pool(client, tmpl, info_dt, outs, parallel, args.max_wait,
                           single_day=single)

    print('\n=== 回刷结束 ===')
    print(f'成功 {len(done)}/{len(outs)}')
    if fails:
        print('失败/异常批：')
        for f in fails:
            print('  ', f)
        return 2
    print('全部批完成，无空分区。')
    return 0


if __name__ == '__main__':
    sys.exit(main())

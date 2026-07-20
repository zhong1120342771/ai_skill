#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用户活跃指标查询（DAU / MAU / 30日活跃留存率），分端。

场景：转转各平台（转转APP/转转小程序/找靓机）活跃用户规模与留存的按需查询。
数据源：hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d
  · token 唯一用户标识；dt 分区(yyyy-MM-dd)，每分区=当天活跃用户快照。
  · terminal_name 分端。本表仅含活跃过的 token，算不了全站累计注册数。

口径（与 2026-07-16 群需求对齐，钟梦婷确认）：
  · DAU  = 取数日(默认 t-1)当天去重活跃用户
  · MAU  = 近30天(取数日-29 ~ 取数日)去重活跃用户
  · 30日活跃留存率 = 以(近30天起始-1)当天活跃用户为基准，
    看其在近30天窗口内是否再次活跃的占比（活跃口径，非注册后第N日留存）

用法：
  /usr/bin/python3 用户活跃指标_DAU_MAU_留存.py [--dau-dt 2026-07-15]
  不传 --dau-dt 时默认取 t-1。

注意：lark_oapi / xinghe_client 装在 /usr/bin/python3（系统解释器）下，用它跑。
"""
import sys
import argparse
from datetime import date, timedelta

sys.path.insert(0, "/Users/zhongmengting/.claude/skills/xinghe-data/scripts")
from xinghe_client import XingheExplorer  # noqa: E402

TABLE = "hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d"


def parse_rows(previews):
    """星河 previews -> [{col:val}]，首行是表头。"""
    if not previews:
        return []
    rows = previews[0] if isinstance(previews[0][0], list) else previews
    header, data = rows[0], rows[1:]
    return [dict(zip(header, r)) for r in data]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dau-dt", default=(date.today() - timedelta(days=1)).isoformat(),
                    help="DAU 取数日，默认 t-1")
    args = ap.parse_args()

    dau_dt = date.fromisoformat(args.dau_dt)
    mau_start = dau_dt - timedelta(days=29)
    mau_end = dau_dt
    ret_base = mau_start - timedelta(days=1)

    c = XingheExplorer()

    # 取数超时分级（2026-07-16，对照 0713 纪要 P0-1）：
    #   DAU 单天单表=轻查询，保持 900s，坏了快速失败别干等；
    #   MAU/留存跨 30 天扫描 + 大表 join=重查询，给 1 小时，别用偏小默认值。
    LIGHT_WAIT, HEAVY_WAIT = 900, 3600

    def run(sql, heavy=False):
        eid = c.run_sql(sql, sql_engine=5)
        wait = HEAVY_WAIT if heavy else LIGHT_WAIT
        return parse_rows(c.wait_and_get_result(eid, max_wait=wait)["previews"])

    dau = run(f"""select terminal_name, count(distinct token) dau
from {TABLE} where dt='{dau_dt}' group by terminal_name limit 50""")  # 轻

    mau = run(f"""select terminal_name, count(distinct token) mau
from {TABLE} where dt between '{mau_start}' and '{mau_end}'
group by terminal_name limit 50""", heavy=True)  # 重：30 天扫描

    # 留存基准日 = 近30天起始 - 1；第30天当天 = 基准日 + 30 = dau_dt
    day30 = dau_dt
    # 口径2：当天活跃后，后续30天内任一天(mau_start~mau_end)再活跃的占比（累计留存）
    ret2 = run(f"""select base.terminal_name,
  count(distinct base.token) base_uv,
  count(distinct ret.token) ret_uv,
  round(count(distinct ret.token)/count(distinct base.token)*100,2) ret_rate
from (select terminal_name, token from {TABLE} where dt='{ret_base}') base
left join (select distinct token from {TABLE}
           where dt between '{mau_start}' and '{mau_end}') ret
on base.token=ret.token
group by base.terminal_name limit 50""", heavy=True)  # 重：基准日 × 30天窗口 join
    # 口径1：当天活跃后，间隔第30天当天(day30)再活跃的占比（时点留存）
    ret1 = run(f"""select base.terminal_name,
  count(distinct base.token) base_uv,
  count(distinct d30.token) ret_uv,
  round(count(distinct d30.token)/count(distinct base.token)*100,2) ret_rate
from (select terminal_name, token from {TABLE} where dt='{ret_base}') base
left join (select distinct token from {TABLE} where dt='{day30}') d30
on base.token=d30.token
group by base.terminal_name limit 50""", heavy=True)  # 重：两天基准 join

    dau_m = {r["terminal_name"]: int(r["dau"]) for r in dau}
    mau_m = {r["terminal_name"]: int(r["mau"]) for r in mau}
    ret1_m = {r["terminal_name"]: r for r in ret1}
    ret2_m = {r["terminal_name"]: r for r in ret2}

    print(f"数据源 {TABLE}；DAU={dau_dt}；MAU={mau_start}~{mau_end}；"
          f"留存基准={ret_base}\n"
          f"  口径1(间隔第30天当天={day30})；口径2(后续30天内={mau_start}~{mau_end})\n")
    print(f"{'端':<8}{'DAU(万)':>12}{'MAU(万)':>14}"
          f"{'留存口径1':>14}{'留存口径2':>14}")
    for t in ["转转APP", "转转小程序", "找靓机"]:
        d = dau_m.get(t, 0) / 10000
        m = mau_m.get(t, 0) / 10000
        r1 = ret1_m.get(t, {}).get("ret_rate", "-")
        r2 = ret2_m.get(t, {}).get("ret_rate", "-")
        print(f"{t:<8}{d:>12.2f}{m:>14.2f}"
              f"{str(r1)+'%':>14}{str(r2)+'%':>14}")


if __name__ == "__main__":
    main()

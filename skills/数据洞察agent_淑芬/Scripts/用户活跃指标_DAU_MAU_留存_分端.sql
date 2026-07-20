-- ============================================================
-- 用户活跃指标查询（DAU / MAU / 30日活跃留存率），分端
-- 场景：群里临时需求，查转转各平台活跃用户规模与留存
-- 数据源：hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d
--   · DAU用户分层明细表，token 为唯一用户标识
--   · 有 dt 分区（yyyy-MM-dd），每个 dt 分区 = 当天活跃用户快照
--     （已验证：单分区内 active_date 恒 = dt）
--   · terminal_name 分端：转转APP / 转转小程序 / 找靓机
-- 引擎：星河 Hive，sql_engine=5；ORDER BY 必须带 limit
-- 口径参数（跑前按需替换）：
--   <DAU_DT>       = DAU 取数日，默认 t-1（如 2026-07-15）
--   <MAU_START>    = 近30天起始（如 2026-06-16 = DAU_DT-29）
--   <MAU_END>      = 近30天截止 = DAU_DT
--   <RET_BASE_DT>  = 留存基准日 = MAU_START-1（如 2026-06-15）
--   <RET_WIN_START>= 回访窗起 = MAU_START，<RET_WIN_END> = DAU_DT
-- 注意：本表是「活跃用户明细」，只含活跃过的 token，
--   算不了「全站累计注册数」；如需注册量须换注册底表。
-- ============================================================

-- (1) DAU：取数日当天分端去重活跃用户
select terminal_name, count(distinct token) as dau
from hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d
where dt = '<DAU_DT>'
group by terminal_name
limit 50;

-- (2) MAU：近30天分端去重活跃用户
select terminal_name, count(distinct token) as mau
from hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d
where dt between '<MAU_START>' and '<MAU_END>'
group by terminal_name
limit 50;

-- (3) 30日活跃留存率（两个口径，基准日 = RET_BASE_DT，分端）：
--   口径2（后续30天内累计留存）：base 用户在 [RET_WIN_START, RET_WIN_END]
--     任意一天再次活跃的占比。活跃口径，非「注册后第N日留存」。
--   口径1（间隔第30天时点留存）：base 用户恰好在第30天当天(<DAU_DT>=RET_BASE_DT+30)
--     再活跃的占比。只看那一个点，通常远低于口径2。

-- 口径2：后续30天内任一天再活跃
select base.terminal_name,
       count(distinct base.token) as base_uv,
       count(distinct ret.token)  as ret_uv,
       round(count(distinct ret.token) / count(distinct base.token) * 100, 2) as ret_rate_kj2
from (
    select terminal_name, token
    from hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d
    where dt = '<RET_BASE_DT>'
) base
left join (
    select distinct token
    from hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d
    where dt between '<RET_WIN_START>' and '<RET_WIN_END>'
) ret
on base.token = ret.token
group by base.terminal_name
limit 50;

-- 口径1：间隔第30天当天(<DAU_DT>)再活跃
select base.terminal_name,
       count(distinct base.token) as base_uv,
       count(distinct d30.token)  as ret_uv,
       round(count(distinct d30.token) / count(distinct base.token) * 100, 2) as ret_rate_kj1
from (
    select terminal_name, token
    from hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d
    where dt = '<RET_BASE_DT>'
) base
left join (
    select distinct token
    from hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d
    where dt = '<DAU_DT>'
) d30
on base.token = d30.token
group by base.terminal_name
limit 50;

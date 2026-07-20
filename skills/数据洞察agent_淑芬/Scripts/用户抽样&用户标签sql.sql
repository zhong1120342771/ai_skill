--用户抽样 (1/339 确定性抽样 1w 用户)
-- ★ 口径铁律：抽样必须走 hash(token) 确定性排序，与 data2-2/3-2/4-2 内联 data1 CTE
--   完全一致（那三张事实表用 LEFT SEMI JOIN data1 ON token 过滤，两侧 token 集必须相同）。
--   绝不能用 order by rand()——rand() 每次随机换一批人，与 hash(token) 抽出的池子不相交，
--   导致下游 token 子集校验崩塌（历史事故 2026-07-15：交集仅 23/10000，Step3 HARD 失败）。
--   含 hash(token) => 星河 Hive 引擎 engine=5（StarRocks 无 hash(varchar)）。
select
    dt
    ,token
    ,user_source
    ,user_type
from
    (select t3.dt
    ,t3.token
    ,user_source --用户来源 （自然新用户、自然留存用户、新媒新用户、新媒召回用户）
    ,get_json_object(t3.user_layer,'$.B2C核心业务') as user_type--用户资产（z0-z5分层）
    from hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d t3
    where  dt='${outFileSuffix}'
    and terminal_name in ('转转APP')
    group by 1,2,3,4
    ) a
order by hash(token)
limit 10000

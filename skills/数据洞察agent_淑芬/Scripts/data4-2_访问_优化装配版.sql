-- data4-2 页面访问&app停留时长装配版(优化) = 访问/启停事件 + 用户标签 + 页面名映射(无区域维表)
-- ★ 2026-07-13 默认扩四页:本条 pagetype 不限页面(全量访问,含 G1001-G1004),多出 page_id 列(=actiontype),下游按 page_id 过滤算逐页停留时长。单页模式下游只取 G1001。
-- ★ 2026-07-10 性能固化:经 dt=2026-07-09 新旧对照实测,行数/token集 全部0误差(口径未变)。
-- 优化点(join下推): LEFT SEMI JOIN data1 把抽样token过滤推到明细扫描层。
--   本条 pagetype 不限 G1001(全量页面访问),原装配对全天全量访问事件取datapool再join,数据量三条里最大。
--   注:2026-07-10并发实测三条净墙钟均约670s,主瓶颈是全分区扫描而非解析,下推省的是无用解析/并发稳定性,非墙钟。字段:原本仅取 eventduration,无可裁。
-- 口径铁律: 1/339抽样 ORDER BY hash(token) LIMIT 10000;pagetype IN(AppStart/AppEnd/zpmshow)。Hive engine=5。
WITH data1 AS (
    SELECT dt, token, user_source, user_type
    FROM (
        SELECT t3.dt, t3.token, user_source,
               get_json_object(t3.user_layer,'$.B2C核心业务') AS user_type
        FROM hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d t3
        WHERE dt = '${outFileSuffix}' AND terminal_name IN ('转转APP')
        GROUP BY 1,2,3,4
    ) a
    ORDER BY hash(token)
    LIMIT 10000
),
visit AS (
    SELECT
        '时长&页面访问数量' AS tag
        ,ev.pagetype
        ,ev.dt
        ,ev.token
        ,ev.actiontype
        ,ev.actiontype                AS page_id
        ,ev.datapool['eventduration'] AS eventduration
        ,ev.timestamp
    FROM hdp_zhuanzhuan_dw_global.dw_log_lego_action_1d ev
    LEFT SEMI JOIN data1 d ON ev.token = d.token
    WHERE ev.dt = '${outFileSuffix}'
      AND ev.pagetype IN ('AppStart','AppEnd','zpmshow')
),
page_dim AS (
    SELECT page_id, MAX(page_name) AS page_name
    FROM hdp_zhuanzhuan_dim_global.dim_zpm_page_info_full_1d_0p
    GROUP BY page_id
)
SELECT
    v.tag, v.dt, v.token,
    d1.user_source, d1.user_type,
    v.pagetype, v.actiontype, v.page_id,
    p.page_name AS page_name_zh,
    v.eventduration, v.timestamp
FROM visit v
INNER JOIN data1 d1 ON v.token = d1.token
LEFT JOIN page_dim p ON v.actiontype = p.page_id

-- data2-2 首页曝光装配版(优化) = 四页曝光事件 + 用户标签 + 页面名/区域名中文映射
-- ★ 2026-07-13 默认扩四页:actiontype IN ('G1001','G1002','G1003','G1004'),多出 page_id 列供下游按页分组。
--    单页模式(section-to-module.json pages=['G1001'])把 IN 收回 ('G1001') 即可,其余不变。
-- ★ 2026-07-10 性能固化:经 dt=2026-07-09 新旧对照实测,行数/token集/模块UV·PV 全部0误差(口径未变)。
-- 优化点1(join下推): 用 LEFT SEMI JOIN data1 把抽样token过滤推到 datapool 解析同层WHERE。
--   原装配对全天全量G1001行(约全量级)解析18个datapool字段,再INNER JOIN降到抽样存活行——多算约339倍无用功。
--   下推后 datapool 解析只作用于1w抽样用户的存活行。
-- 优化点2(字段裁剪): 删下游0引用字段 subSectionId/subSectionName/firsttab/infoid/sortIdList/tabId。
--   保留(下游必用): sectionId(切模块)/sortName+sortId(子元素坑位下钻)/goodsList+indexList(feed·金刚位)/
--                    tabName+tabNameList(场馆tab子元素)/eventduration(停留)/timestamp(feed翻页深度排序)。
-- 口径铁律(与旧版逐字一致,勿改): 1/339确定性抽样 ORDER BY hash(token) LIMIT 10000;UV当天token去重(下游);
--   场馆tab(section106) cap 仍在 Step2 做,SQL不做;含 hash(token) => 星河 Hive 引擎 engine=5。
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
-- 曝光原始事件:token过滤(LEFT SEMI JOIN)与分区/pagetype过滤同层,datapool只解析抽样存活行
exposure AS (
    SELECT
        '首页四页（G1001-G1004）曝光事件' AS tag
        ,ev.dt
        ,ev.token
        ,ev.pagetype
        ,ev.actiontype
        ,ev.actiontype                AS page_id
        ,ev.datapool['sectionId']     AS sectionId
        ,ev.datapool['goodsList']     AS goodsList
        ,ev.datapool['indexList']     AS indexList
        ,ev.datapool['sortId']        AS sortId
        ,ev.datapool['sortName']      AS sortName
        ,ev.datapool['tabNameList']   AS tabNameList
        ,ev.datapool['tabName']       AS tabName
        ,ev.datapool['eventduration'] AS eventduration
        ,ev.timestamp
    FROM hdp_zhuanzhuan_dw_global.dw_log_lego_action_1d ev
    LEFT SEMI JOIN data1 d ON ev.token = d.token
    WHERE ev.dt = '${outFileSuffix}'
      AND ev.actiontype IN ('G1001','G1002','G1003','G1004') AND ev.region = 'g'
      AND ev.pagetype IN ('zpmshow','Areaexposure','explosureGoods','explosureItems')
),
-- 维表无 dt 分区,MAX+GROUP BY 去重(勿加 WHERE dt)
page_dim AS (
    SELECT page_id, MAX(page_name) AS page_name
    FROM hdp_zhuanzhuan_dim_global.dim_zpm_page_info_full_1d_0p
    GROUP BY page_id
),
section_dim AS (
    SELECT section_id, MAX(section_name) AS section_name
    FROM hdp_zhuanzhuan_dim_global.dim_zpm_page_section_info_full_1d_0p
    GROUP BY section_id
)
SELECT
    e.tag, e.dt, e.token,
    d1.user_source, d1.user_type,
    e.pagetype, e.actiontype, e.page_id,
    p.page_name    AS page_name_zh,
    e.sectionId,
    s.section_name AS section_name_zh,
    e.goodsList, e.indexList, e.sortId, e.sortName,
    e.tabNameList, e.tabName, e.eventduration, e.timestamp
FROM exposure e
INNER JOIN data1 d1 ON e.token = d1.token
LEFT JOIN page_dim p ON e.actiontype = p.page_id
LEFT JOIN section_dim s ON e.sectionId = s.section_id

-- data3-2 首页点击装配版(优化) = 四页点击事件 + 用户标签 + 页面名/区域名中文映射
-- ★ 2026-07-13 默认扩四页:actiontype IN ('G1001'..'G1004'),多出 page_id 列。sectionId 白名单已含 300(品类tab)/301(品牌墙)/500(底部导航),四页所需齐全。单页模式把 IN 收回 ('G1001')。
-- ★ 2026-07-10 性能固化:经 dt=2026-07-09 新旧对照实测,行数/token集/模块UV·PV 全部0误差(口径未变)。
-- 优化点1(join下推): LEFT SEMI JOIN data1 把抽样token过滤推到 datapool 解析同层WHERE。
-- 优化点2(字段裁剪): 删 subSectionId/subSectionName/firsttab/infoid/sortIdList/tabId。
-- 口径铁律(逐字一致): sectionId IN(...) 白名单保留;1/339抽样;去重/cap同旧版。Hive engine=5。
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
click AS (
    SELECT
        '首页四页（G1001-G1004）点击事件' AS tag
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
      AND ev.pagetype = 'zpmclick'
      AND ev.datapool['sectionId'] IN ('100','101','106','102','103','105','2001','108','109','110','139','164','165','301','302','500','300')
),
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
    c.tag, c.dt, c.token,
    d1.user_source, d1.user_type,
    c.pagetype, c.actiontype, c.page_id,
    p.page_name    AS page_name_zh,
    c.sectionId,
    s.section_name AS section_name_zh,
    c.goodsList, c.indexList, c.sortId, c.sortName,
    c.tabNameList, c.tabName, c.eventduration, c.timestamp
FROM click c
INNER JOIN data1 d1 ON c.token = d1.token
LEFT JOIN page_dim p ON c.actiontype = p.page_id
LEFT JOIN section_dim s ON c.sectionId = s.section_id

/* @template
name: 搜索筛选/排序使用情况
scene: 拆解每个 query 在搜索结果页的筛选和排序使用情况——是否用筛选、用了哪种筛选（静态/品牌墙/快筛/抽屉/推荐）、用了哪种排序（默认/最新/价格/距离）
params:
  required:
    - query_scope_table: query 白名单表（来自 search_before_pay_query 的产物）
    - detail_table: 搜索明细表（提供 request_id 白名单，通常来自 search_before_pay_query 的中间明细产物）
    - cate_first_id: 品类 ID
    - start_dt: 时间窗起始
    - end_dt: 时间窗结束
  optional:
    - query_limit: 保留前 N 个热词，默认 1000
validated:
  - case: 骑行 top1000 词筛选/排序使用（2026-05-25 ~ 2026-06-14）
  - run_at: 2026-06-25
  - source_sql: /Users/zz/Desktop/测试代码/空间盘点/兴趣/骑行/搜索/4.召回筛选项.sql
notes:
  - 数据源是 dw_log_server_action_1d，datapool['searchfilter_click'] 是 JSON 字符串
  - JSON 字段字典：详见 references/search-backend-tables.md 的「searchfilter_click JSON 结构」段
business_statement:
  scene_desc: 看 top N 热词的搜索请求里，用户是否用了筛选、用了哪种筛选、用了哪种排序
  who: white list query 对应的搜索请求（request 级；request_id = dt#token#rstmark#query）
  metric_desc: 每 query 的请求数、筛选使用率、6 种筛选各自使用数、5 种排序各自使用数、筛选类型总使用次数、各类筛选在筛选总量中的占比
  hidden_assumptions:
    - 一个 request 内用户可能触发多种筛选，取 MAX 表示"至少用过一次"
    - filter_type_use_cnt = 6 类筛选的加总次数（可 > request_cnt，因为一个 request 可用多种）
    - 分母 filter_usage_rate 用 request 数（去重），不是筛选总次数
  source:
    - hdp_zhuanzhuan_dw_global.dw_log_server_action_1d（action=zzappsearch，datapool JSON）
    - ${query_scope_table}, ${detail_table}
*/

-- @lifecycle hdp_zhuanzhuan_dw_global.dw_log_server_action_1d=permanent

SET hive.map.aggr = true;
SET hive.exec.parallel = true;
SET hive.exec.parallel.thread.number = 40;
SET hive.auto.convert.join = true;

WITH query_scope AS ( -- query 白名单
    SELECT
        TRIM(LOWER(query)) AS query,
        search_pv AS origin_search_pv,
        search_user_cnt AS origin_search_user_cnt,
        info_cnt AS origin_info_cnt,
        intention_class
    FROM ${query_scope_table}
    WHERE query IS NOT NULL
      AND TRIM(query) <> ''
    ORDER BY search_pv DESC
    LIMIT ${query_limit}
),

request_scope AS ( -- 只保留 white list query 相关的 request_id
    SELECT
        d.query,
        d.request_id,
        MAX(d.user_id) AS user_id
    FROM ${detail_table} d
    JOIN query_scope q ON d.query = q.query
    WHERE d.dt BETWEEN '${start_dt}' AND '${end_dt}'
      AND d.request_id IS NOT NULL
      AND d.query IS NOT NULL
    GROUP BY d.query, d.request_id
),

filter_log AS ( -- 从 server_action 拆 JSON 出筛选/排序 flag
    SELECT
        TRIM(LOWER(REGEXP_REPLACE(l.datapool['orikeyword'], unhex('01'), ' '))) AS query,
        CONCAT(
            l.dt, '#',
            l.token, '#',
            l.datapool['rstmark'], '#',
            TRIM(LOWER(REGEXP_REPLACE(l.datapool['orikeyword'], unhex('01'), ' ')))
        ) AS request_id,
        CASE WHEN get_json_object(l.datapool['searchfilter_click'], '$.staticFilterUsage')     = '1' THEN 1 ELSE 0 END AS static_used,
        CASE WHEN get_json_object(l.datapool['searchfilter_click'], '$.brandWallFilterUsage')  = '1' THEN 1 ELSE 0 END AS brand_wall_used,
        CASE WHEN get_json_object(l.datapool['searchfilter_click'], '$.fastFilterUsage')       = '1' THEN 1 ELSE 0 END AS fast_used,
        CASE WHEN get_json_object(l.datapool['searchfilter_click'], '$.drawerFilterUsage')     = '1' THEN 1 ELSE 0 END AS drawer_used,
        CASE WHEN get_json_object(l.datapool['searchfilter_click'], '$.recommendFilterUsage')  = '1' THEN 1 ELSE 0 END AS recommend_used,
        CASE WHEN get_json_object(l.datapool['searchfilter_click'], '$.sortpolicyFilter') IS NOT NULL
               AND get_json_object(l.datapool['searchfilter_click'], '$.sortpolicyFilter') <> '0'
             THEN 1 ELSE 0 END AS sort_used,
        CASE WHEN get_json_object(l.datapool['searchfilter_click'], '$.sortpolicyFilter') = '0' THEN 1 ELSE 0 END AS default_sort_used,
        CASE WHEN get_json_object(l.datapool['searchfilter_click'], '$.sortpolicyFilter') = '1' THEN 1 ELSE 0 END AS latest_sort_used,
        CASE WHEN get_json_object(l.datapool['searchfilter_click'], '$.sortpolicyFilter') IN ('2','3') THEN 1 ELSE 0 END AS price_sort_used,
        CASE WHEN get_json_object(l.datapool['searchfilter_click'], '$.sortpolicyFilter') = '4' THEN 1 ELSE 0 END AS distance_sort_used,
        CASE WHEN get_json_object(l.datapool['searchfilter_click'], '$.sortpolicyFilter') IS NOT NULL
               AND get_json_object(l.datapool['searchfilter_click'], '$.sortpolicyFilter') NOT IN ('0','1','2','3','4')
             THEN 1 ELSE 0 END AS other_sort_used
    FROM hdp_zhuanzhuan_dw_global.dw_log_server_action_1d l
    JOIN query_scope q
      ON TRIM(LOWER(REGEXP_REPLACE(l.datapool['orikeyword'], unhex('01'), ' '))) = q.query
    WHERE l.dt BETWEEN '${start_dt}' AND '${end_dt}'
      AND l.region = 'z'
      AND l.action = 'zzappsearch'
      AND l.terminal IN (15, 16, 103)
      AND l.datapool['tabid'] = '0'
      AND l.token IS NOT NULL
      AND l.datapool['rstmark'] IS NOT NULL
      AND l.datapool['orikeyword'] IS NOT NULL
      AND TRIM(REGEXP_REPLACE(l.datapool['orikeyword'], unhex('01'), ' ')) <> ''
      AND get_json_object(l.datapool['searchfilter_click'], '$.filterUsage') = '1' -- 只取用过筛选的
),

request_filter AS ( -- request 粒度聚合筛选 flag
    SELECT
        r.query,
        r.request_id,
        MAX(COALESCE(f.static_used, 0))         AS static_used,
        MAX(COALESCE(f.brand_wall_used, 0))     AS brand_wall_used,
        MAX(COALESCE(f.fast_used, 0))           AS fast_used,
        MAX(COALESCE(f.drawer_used, 0))         AS drawer_used,
        MAX(COALESCE(f.recommend_used, 0))      AS recommend_used,
        MAX(COALESCE(f.sort_used, 0))           AS sort_used,
        MAX(COALESCE(f.default_sort_used, 0))   AS default_sort_used,
        MAX(COALESCE(f.latest_sort_used, 0))    AS latest_sort_used,
        MAX(COALESCE(f.price_sort_used, 0))     AS price_sort_used,
        MAX(COALESCE(f.distance_sort_used, 0))  AS distance_sort_used,
        MAX(COALESCE(f.other_sort_used, 0))     AS other_sort_used
    FROM request_scope r
    LEFT JOIN filter_log f
      ON r.request_id = f.request_id
     AND r.query = f.query
    GROUP BY r.query, r.request_id
),

filter_metric AS ( -- query 级筛选使用统计
    SELECT
        query,
        COUNT(1) AS request_cnt, -- 请求总数（已在 request_scope 去重）
        SUM(CASE WHEN static_used + brand_wall_used + fast_used + drawer_used + recommend_used + sort_used > 0 THEN 1 ELSE 0 END) AS filter_used_request_cnt,
        SUM(static_used)      AS static_filter_request_cnt,
        SUM(brand_wall_used)  AS brand_wall_filter_request_cnt,
        SUM(fast_used)        AS fast_filter_request_cnt,
        SUM(drawer_used)      AS drawer_filter_request_cnt,
        SUM(recommend_used)   AS recommend_filter_request_cnt,
        SUM(sort_used)        AS sort_filter_request_cnt,
        SUM(default_sort_used)  AS default_sort_request_cnt,
        SUM(latest_sort_used)   AS latest_sort_request_cnt,
        SUM(price_sort_used)    AS price_sort_request_cnt,
        SUM(distance_sort_used) AS distance_sort_request_cnt,
        SUM(other_sort_used)    AS other_sort_request_cnt,
        SUM(static_used + brand_wall_used + fast_used + drawer_used + recommend_used + sort_used) AS filter_type_use_cnt
    FROM request_filter
    GROUP BY query
)

SELECT
    '${start_dt}' AS period_start,
    '${end_dt}'   AS period_end,
    q.query,
    q.origin_search_pv,
    q.origin_search_user_cnt,
    q.origin_info_cnt,
    q.intention_class,
    COALESCE(m.request_cnt, 0)                       AS request_cnt,
    COALESCE(m.filter_used_request_cnt, 0)           AS filter_used_request_cnt,
    COALESCE(m.static_filter_request_cnt, 0)         AS static_filter_request_cnt,
    COALESCE(m.brand_wall_filter_request_cnt, 0)     AS brand_wall_filter_request_cnt,
    COALESCE(m.fast_filter_request_cnt, 0)           AS fast_filter_request_cnt,
    COALESCE(m.drawer_filter_request_cnt, 0)         AS drawer_filter_request_cnt,
    COALESCE(m.recommend_filter_request_cnt, 0)      AS recommend_filter_request_cnt,
    COALESCE(m.sort_filter_request_cnt, 0)           AS sort_filter_request_cnt,
    COALESCE(m.default_sort_request_cnt, 0)          AS default_sort_request_cnt,
    COALESCE(m.latest_sort_request_cnt, 0)           AS latest_sort_request_cnt,
    COALESCE(m.price_sort_request_cnt, 0)            AS price_sort_request_cnt,
    COALESCE(m.distance_sort_request_cnt, 0)         AS distance_sort_request_cnt,
    COALESCE(m.other_sort_request_cnt, 0)            AS other_sort_request_cnt,
    COALESCE(m.filter_type_use_cnt, 0)               AS filter_type_use_cnt,
    -- 使用率与占比
    CASE WHEN COALESCE(m.request_cnt, 0) > 0
         THEN ROUND(m.filter_used_request_cnt * 1.0 / m.request_cnt, 6) ELSE 0 END AS filter_usage_rate,
    CASE WHEN COALESCE(m.filter_type_use_cnt, 0) > 0 THEN ROUND(m.static_filter_request_cnt     * 1.0 / m.filter_type_use_cnt, 6) ELSE 0 END AS static_filter_share,
    CASE WHEN COALESCE(m.filter_type_use_cnt, 0) > 0 THEN ROUND(m.brand_wall_filter_request_cnt * 1.0 / m.filter_type_use_cnt, 6) ELSE 0 END AS brand_wall_filter_share,
    CASE WHEN COALESCE(m.filter_type_use_cnt, 0) > 0 THEN ROUND(m.fast_filter_request_cnt       * 1.0 / m.filter_type_use_cnt, 6) ELSE 0 END AS fast_filter_share,
    CASE WHEN COALESCE(m.filter_type_use_cnt, 0) > 0 THEN ROUND(m.drawer_filter_request_cnt     * 1.0 / m.filter_type_use_cnt, 6) ELSE 0 END AS drawer_filter_share,
    CASE WHEN COALESCE(m.filter_type_use_cnt, 0) > 0 THEN ROUND(m.recommend_filter_request_cnt  * 1.0 / m.filter_type_use_cnt, 6) ELSE 0 END AS recommend_filter_share,
    CASE WHEN COALESCE(m.filter_type_use_cnt, 0) > 0 THEN ROUND(m.sort_filter_request_cnt       * 1.0 / m.filter_type_use_cnt, 6) ELSE 0 END AS sort_filter_share
FROM query_scope q
LEFT JOIN filter_metric m ON q.query = m.query
ORDER BY q.origin_search_pv DESC
LIMIT ${query_limit};

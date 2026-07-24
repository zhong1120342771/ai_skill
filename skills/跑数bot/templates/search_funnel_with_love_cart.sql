/* @template
name: 搜索全链路漏斗（含收藏加购）
scene: 支付前搜索的全链路漏斗——曝光 PV → 点击 → 收藏（addlove）→ 加购（cart）→ 支付；比宽表默认漏斗多两级中间行为
params:
  required:
    - cate_first_id: 一级品类 ID
    - start_dt: 时间窗起始
    - end_dt: 时间窗结束
    - snapshot_dt: 订单快照分区（YYYY-MM-DD）
    - detail_output_table: 输出的漏斗明细表名（tmp 库）
    - query_scope_table: query 白名单表（可选，若为空则不筛 query，跑品类全量）
  optional:
    - query_limit: query 白名单前 N，默认 1000
validated:
  - case: 骑行 top1000 词全链路漏斗（2026-05-25 ~ 2026-06-14）
  - run_at: 2026-06-26
  - source_sql: /Users/zz/Desktop/测试代码/空间盘点/兴趣/骑行/搜索/5.搜索漏斗（PV，click，收藏加购，pay).sql
notes:
  - 收藏/加购 join 用 4 键：dt + token + metric_md5 + request_mark（比标准三键多 metric_md5，因为 addlove/cart 表按曝光实例落）
  - addlove/cart 用 first_from IN ('search','weixin_search') 过滤搜索来源
  - 时间对齐：a.timestamp >= d.search_ts（收藏/加购必须发生在搜索之后）
business_statement:
  scene_desc: 看 top N 热词在支付前的完整行为链路：曝光 → 点击 → 收藏 → 加购 → 支付
  who: white list query × request × info 明细粒度
  metric_desc: 每条明细带 pv/click/love_cnt/has_love/cart_cnt/has_cart/pay/has_pay 及各阶段时间戳
  hidden_assumptions:
    - 只保留 search_ts < pay_ts 的搜索行为
    - 一次曝光可能触发多次收藏/加购，用 COUNT(1) 聚合，另标 has_* flag
    - metric_md5 是曝光实例的唯一标识，跨表 join 用
  source:
    - hdp_zhuanzhuan_dw_global.dw_dwb_search_full_link_full_1d
    - hdp_zhuanzhuan_dm_global.dm_trade_addlove_detail_1d
    - hdp_zhuanzhuan_dm_global.dm_trade_list2cart_detail_1d
    - hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d
    - ${query_scope_table}
*/

-- @lifecycle hdp_zhuanzhuan_dw_global.dw_dwb_search_full_link_full_1d=permanent
-- @lifecycle hdp_zhuanzhuan_dm_global.dm_trade_addlove_detail_1d=permanent
-- @lifecycle hdp_zhuanzhuan_dm_global.dm_trade_list2cart_detail_1d=permanent
-- @lifecycle hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d=180

DROP TABLE IF EXISTS ${detail_output_table};

CREATE TABLE ${detail_output_table} AS
WITH order_full AS ( -- 品类下单用户全量
    SELECT DISTINCT
        order_id,
        CAST(buyer_id AS string) AS user_id,
        UNIX_TIMESTAMP(pay_time) AS pay_ts
    FROM hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d
    WHERE dt = '${snapshot_dt}'
      AND cate_first_id = ${cate_first_id}
      AND pay_time IS NOT NULL
      AND buyer_id IS NOT NULL
      AND TO_DATE(pay_time) BETWEEN '${start_dt}' AND '${end_dt}'
),

query_scope AS ( -- white list（若表为空则跑全品类）
    SELECT TRIM(LOWER(query)) AS query, search_pv
    FROM ${query_scope_table}
    WHERE query IS NOT NULL AND TRIM(query) <> ''
    ORDER BY search_pv DESC
    LIMIT ${query_limit}
),

search_base AS ( -- 搜索宽表明细（品类内 + query 内）
    SELECT
        s.dt,
        CAST(s.uid AS string) AS user_id,
        CAST(s.token AS string) AS token,
        CAST(s.rstmark AS string) AS rstmark,
        TRIM(LOWER(s.query)) AS query,
        CAST(s.md5 AS string) AS md5,
        CAST(s.info_id AS string) AS info_id,
        s.page,
        s.`index` AS idx,
        COALESCE(s.pv, 0) AS pv,
        COALESCE(s.click, 0) AS click,
        COALESCE(s.pay, 0) AS pay,
        s.pv_timestamp,
        s.click_timestamp,
        s.pay_timestamp,
        CASE
            WHEN LENGTH(CAST(s.pv_timestamp AS string)) >= 13
                THEN CAST(CAST(s.pv_timestamp AS bigint) / 1000 AS bigint) -- 毫秒 → 秒
            ELSE CAST(s.pv_timestamp AS bigint)
        END AS search_ts
    FROM hdp_zhuanzhuan_dw_global.dw_dwb_search_full_link_full_1d s
    JOIN query_scope q ON TRIM(LOWER(s.query)) = q.query
    WHERE s.dt BETWEEN '${start_dt}' AND '${end_dt}'
      AND s.action = 'search'
      AND s.is_spam = 0
      AND s.terminal IN (15, 16, 103)
      AND s.period = 1
      AND s.uid IS NOT NULL
      AND s.query IS NOT NULL AND TRIM(s.query) <> ''
      AND s.cate1id = ${cate_first_id}
      AND s.info_id IS NOT NULL
      AND s.token IS NOT NULL
      AND s.rstmark IS NOT NULL
      AND s.md5 IS NOT NULL
      AND s.pv_timestamp IS NOT NULL
),

search_before_order AS ( -- 支付前搜索行为
    SELECT DISTINCT
        s.dt, s.user_id, s.token, s.rstmark, s.query,
        CONCAT(s.dt, '#', s.token, '#', s.rstmark, '#', s.query) AS request_id,
        s.md5, s.info_id, s.page, s.idx,
        s.pv, s.click, s.pay,
        s.pv_timestamp, s.click_timestamp, s.pay_timestamp, s.search_ts
    FROM search_base s
    JOIN order_full o
      ON s.user_id = o.user_id
     AND s.search_ts < o.pay_ts
),

love_item AS ( -- 收藏行为（4 键关联）
    SELECT
        d.dt, d.token, d.rstmark, d.query, d.request_id, d.md5, d.info_id,
        COUNT(1) AS love_cnt,
        MIN(a.timestamp) AS first_love_ts
    FROM search_before_order d
    JOIN hdp_zhuanzhuan_dm_global.dm_trade_addlove_detail_1d a
      ON a.dt = d.dt
     AND CAST(a.token AS string)         = d.token
     AND CAST(a.info_id AS string)       = d.info_id
     AND CAST(a.metric_md5 AS string)    = d.md5
     AND CAST(a.request_mark AS string)  = d.rstmark
    WHERE a.dt BETWEEN '${start_dt}' AND '${end_dt}'
      AND a.cate_first_id = ${cate_first_id}
      AND a.terminal IN ('15','16','103')
      AND a.first_from IN ('search','weixin_search') -- 搜索来源
      AND a.uid IS NOT NULL
      AND a.token IS NOT NULL
      AND a.info_id IS NOT NULL
      AND a.metric_md5 IS NOT NULL
      AND CAST(a.metric_md5 AS string) <> 'null'
      AND a.request_mark IS NOT NULL
      AND a.timestamp IS NOT NULL
      AND a.timestamp >= d.search_ts -- 时间对齐
    GROUP BY d.dt, d.token, d.rstmark, d.query, d.request_id, d.md5, d.info_id
),

cart_item AS ( -- 加购行为（4 键关联）
    SELECT
        d.dt, d.token, d.rstmark, d.query, d.request_id, d.md5, d.info_id,
        COUNT(1) AS cart_cnt,
        MIN(c.timestamp) AS first_cart_ts
    FROM search_before_order d
    JOIN hdp_zhuanzhuan_dm_global.dm_trade_list2cart_detail_1d c
      ON c.dt = d.dt
     AND CAST(c.token AS string)         = d.token
     AND CAST(c.info_id AS string)       = d.info_id
     AND CAST(c.metric_md5 AS string)    = d.md5
     AND CAST(c.request_mark AS string)  = d.rstmark
    WHERE c.dt BETWEEN '${start_dt}' AND '${end_dt}'
      AND c.cate_first_id = ${cate_first_id}
      AND c.terminal IN ('15','16','103')
      AND c.first_from IN ('search','weixin_search')
      AND c.uid IS NOT NULL
      AND c.token IS NOT NULL
      AND c.info_id IS NOT NULL
      AND c.metric_md5 IS NOT NULL
      AND CAST(c.metric_md5 AS string) <> 'null'
      AND c.request_mark IS NOT NULL
      AND c.timestamp IS NOT NULL
      AND c.timestamp >= d.search_ts
    GROUP BY d.dt, d.token, d.rstmark, d.query, d.request_id, d.md5, d.info_id
)

SELECT
    s.dt, s.user_id, s.token, s.rstmark, s.query, s.request_id,
    s.md5, s.info_id, s.page, s.idx,
    s.pv, s.click,
    COALESCE(l.love_cnt, 0) AS love_cnt,
    CASE WHEN COALESCE(l.love_cnt, 0) > 0 THEN 1 ELSE 0 END AS has_love,
    l.first_love_ts,
    COALESCE(c.cart_cnt, 0) AS cart_cnt,
    CASE WHEN COALESCE(c.cart_cnt, 0) > 0 THEN 1 ELSE 0 END AS has_cart,
    c.first_cart_ts,
    s.pay,
    CASE WHEN COALESCE(s.pay, 0) > 0 THEN 1 ELSE 0 END AS has_pay,
    s.pv_timestamp, s.click_timestamp, s.pay_timestamp, s.search_ts
FROM search_before_order s
LEFT JOIN love_item l
  ON s.dt = l.dt AND s.token = l.token AND s.rstmark = l.rstmark
 AND s.query = l.query AND s.request_id = l.request_id
 AND s.md5 = l.md5 AND s.info_id = l.info_id
LEFT JOIN cart_item c
  ON s.dt = c.dt AND s.token = c.token AND s.rstmark = c.rstmark
 AND s.query = c.query AND s.request_id = c.request_id
 AND s.md5 = c.md5 AND s.info_id = c.info_id;

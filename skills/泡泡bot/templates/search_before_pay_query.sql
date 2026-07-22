/* @template
name: 下单前搜索词
scene: 看某品类下单用户在支付前搜过什么词，为搜索专项、query 分层、意图分类准备主表；通常作为后续"召回商品数/CTR/筛选/漏斗"分析的 query_scope 基础表
params:
  required:
    - cate_first_id: 一级品类 ID（如骑行=105，二奢=按 business_line_id 拆，详见飞书 Hive 表导航）
    - start_dt: 时间窗起始日期（YYYY-MM-DD）
    - end_dt: 时间窗结束日期（YYYY-MM-DD，通常也作为主表快照日期）
    - snapshot_dt: 订单快照分区（YYYY-MM-DD，通常 = end_dt）
  optional:
    - result_table: 输出表名（tmp 库），默认 hdp_zhuanzhuan_tmp_global.tmp_query_before_pay
validated:
  - case: 骑行下单用户搜索词（2026-03-02 ~ 2026-06-14）
  - run_at: 2026-06-22
  - source_sql: /Users/zz/Desktop/测试代码/空间盘点/兴趣/骑行/搜索/1.下单用户搜索词.sql
business_statement:
  scene_desc: 看 X 品类近 Y 天有下单的用户，在支付前搜过哪些词，输出 query 级别的 PV / UV / 召回商品数 / 意图分类
  who: X 品类的下单用户（uid 级），只保留搜索发生在支付之前的搜索记录（search_ts < pay_ts）
  metric_desc: 每个 query 的搜索 PV / 搜索用户数 / 召回商品数 / 命中品牌数 / 意图分类
  hidden_assumptions:
    - 主表是 c2b 寄售订单快照（tmp_consignment_order_sale_detail_new_full_1d），按 cate_first_id 筛品类
    - 搜索行为主表是宽表 dw_dwb_search_full_link_full_1d，terminal in (15,16,103)、is_spam=0、period=1、cate1id=${cate_first_id}
    - 搜索时间用宽表的 pv_timestamp 与订单表的 pay_time (unix ts) 做 < 对比
    - query 做了 TRIM(LOWER(...)) 归一，未做 \x01 清洗（宽表 query 已清洗，主表 datapool 需要额外清洗）
    - 意图分类：intention_type=5 精确，1-4 泛意图，其他无明确意图
  source:
    - hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d（订单快照，筛品类）
    - hdp_zhuanzhuan_dw_global.dw_dwb_search_full_link_full_1d（搜索宽表）
    - hdp_zhuanzhuan_dw_global.dw_traffic_ub_zzappsearch_query_intention_detail_inc_1d（意图分类）
*/

-- @lifecycle hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d=180
-- @lifecycle hdp_zhuanzhuan_dw_global.dw_dwb_search_full_link_full_1d=permanent
-- @lifecycle hdp_zhuanzhuan_dw_global.dw_traffic_ub_zzappsearch_query_intention_detail_inc_1d=permanent

-- 下单前搜索词模板 — 参数化版本
CREATE TABLE IF NOT EXISTS ${result_table} AS
WITH order_full AS ( -- 品类下单用户全量快照
    SELECT DISTINCT
        order_id,
        CAST(buyer_id AS string) AS user_id,
        pay_time,
        UNIX_TIMESTAMP(pay_time) AS pay_ts
    FROM hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d
    WHERE dt = '${snapshot_dt}' -- 订单快照分区
      AND cate_first_id = ${cate_first_id} -- 目标品类
      AND pay_time IS NOT NULL
      AND buyer_id IS NOT NULL
      AND TO_DATE(pay_time) BETWEEN '${start_dt}' AND '${end_dt}' -- 支付时间窗
),

search_base AS ( -- 搜索宽表明细（品类内）
    SELECT
        dt,
        CAST(uid AS string) AS user_id,
        token,
        rstmark,
        TRIM(LOWER(query)) AS query,
        info_id,
        brand,
        model,
        pv_timestamp AS search_ts
    FROM hdp_zhuanzhuan_dw_global.dw_dwb_search_full_link_full_1d
    WHERE dt BETWEEN '${start_dt}' AND '${end_dt}'
      AND action = 'search'
      AND is_spam = 0            -- 反作弊过滤（详见 sql-pitfalls.md）
      AND terminal IN (15, 16, 103)
      AND period = 1              -- 埋点标准过滤
      AND uid IS NOT NULL
      AND query IS NOT NULL
      AND TRIM(query) <> ''
      AND cate1id = ${cate_first_id} -- 品类命中
      AND pv_timestamp IS NOT NULL
),

search_before_order AS ( -- 支付前搜索行为：search_ts < pay_ts
    SELECT DISTINCT s.*
    FROM search_base s
    JOIN order_full o
      ON s.user_id = o.user_id
     AND s.search_ts < o.pay_ts
),

query_base AS ( -- 每个 query 的基础指标
    SELECT
        query,
        COUNT(DISTINCT CONCAT(dt, '#', token, '#', rstmark, '#', query)) AS search_pv, -- 会话唯一键
        COUNT(DISTINCT user_id) AS search_user_cnt,
        COUNT(DISTINCT info_id) AS info_cnt,
        COUNT(DISTINCT brand) AS hit_brand_cnt,
        COUNT(DISTINCT model) AS hit_model_cnt,
        CONCAT_WS(',', COLLECT_SET(CAST(brand AS string))) AS hit_brand_ids,
        CONCAT_WS(',', COLLECT_SET(CAST(model AS string))) AS hit_model_ids
    FROM search_before_order
    GROUP BY query
),

query_intention AS ( -- 意图分类（精确/泛/无明确）
    SELECT
        TRIM(LOWER(keyword)) AS query,
        CASE
            WHEN MAX(CASE WHEN intention_type = 5 THEN 1 ELSE 0 END) = 1 THEN '精确意图'
            WHEN MAX(CASE WHEN intention_type IN (1,2,3,4) THEN 1 ELSE 0 END) = 1 THEN '泛意图'
            ELSE '无明确意图'
        END AS intention_class
    FROM hdp_zhuanzhuan_dw_global.dw_traffic_ub_zzappsearch_query_intention_detail_inc_1d
    WHERE dt BETWEEN '${start_dt}' AND '${end_dt}'
      AND keyword IS NOT NULL
      AND TRIM(keyword) <> ''
    GROUP BY TRIM(LOWER(keyword))
)

SELECT
    q.query,
    q.search_pv,
    q.search_user_cnt,
    q.info_cnt,
    q.hit_brand_cnt,
    q.hit_model_cnt,
    q.hit_brand_ids,
    q.hit_model_ids,
    COALESCE(i.intention_class, '无明确意图') AS intention_class
FROM query_base q
LEFT JOIN query_intention i
  ON q.query = i.query;

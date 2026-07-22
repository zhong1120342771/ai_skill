/* @template
name: 品类转化关键时机（行为次数分桶 × 支付用户率）
scene: 看品类内用户"商详浏览次数 / 收藏次数 / 加购次数"分桶后，各桶的日均支付用户率——识别哪一档行为强度是支付转化的关键分水岭
params:
  required:
    - cate_first_id: 一级品类 ID
    - start_dt: 时间窗起始
    - end_dt: 时间窗结束
    - snapshot_dt: 订单/商品快照分区
validated:
  - case: 骑行近 3.5 个月转化关键时机（2026-03-02 ~ 2026-06-14）
  - run_at: 2026-06-25
  - source_sql: /Users/zz/Desktop/测试代码/空间盘点/兴趣/骑行/现状/转化关键时机.sql
notes:
  - 分桶阈值默认沿用骑行专项 8 档：0 / 1 / 2 / 3 / 4-5 / 6-10 / 11-20 / 20+
  - 用户行为聚合在 uid + dt 粒度（同一用户同一天算一条）
business_statement:
  scene_desc: 看 X 品类用户在商详/收藏/加购各行为强度分桶下，"下单用户占比"的差异，识别高转化门槛
  who: 品类范围内的商品对应的行为用户（uid × dt）
  metric_desc: 每个 metric_type × cnt_bucket 的日均用户数 / 日均下单用户数 / 日均下单用户率 / 日均订单数
  hidden_assumptions:
    - 商品范围来自 c2b 寄售全量快照（tmp_consignment_info_detail_full_1d）按 cate_first_id 筛
    - 行为表用 dm_trade_visit_detail_1d / addlove / list2cart，通过 info_id 关联品类
    - 订单来自 tmp_consignment_order_sale_detail_new_full_1d
    - 分桶阈值可改，如需自定义分桶请先跟用户确认
  source:
    - hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d
    - hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_info_detail_full_1d
    - hdp_zhuanzhuan_dm_global.dm_trade_visit_detail_1d
    - hdp_zhuanzhuan_dm_global.dm_trade_addlove_detail_1d
    - hdp_zhuanzhuan_dm_global.dm_trade_list2cart_detail_1d
*/

-- @lifecycle hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d=180
-- @lifecycle hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_info_detail_full_1d=180
-- @lifecycle hdp_zhuanzhuan_dm_global.dm_trade_visit_detail_1d=permanent
-- @lifecycle hdp_zhuanzhuan_dm_global.dm_trade_addlove_detail_1d=permanent
-- @lifecycle hdp_zhuanzhuan_dm_global.dm_trade_list2cart_detail_1d=permanent

WITH order_full AS ( -- 品类支付订单，日粒度
    SELECT DISTINCT
        TO_DATE(pay_time) AS dt,
        order_id,
        buyer_id AS user_id
    FROM hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d
    WHERE dt = '${snapshot_dt}'
      AND cate_first_id = ${cate_first_id}
      AND pay_time IS NOT NULL
      AND buyer_id IS NOT NULL
      AND TO_DATE(pay_time) BETWEEN '${start_dt}' AND '${end_dt}'
),

product_scope AS ( -- 品类内商品范围
    SELECT DISTINCT info_id
    FROM hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_info_detail_full_1d
    WHERE dt = '${snapshot_dt}'
      AND cate_first_id = ${cate_first_id}
),

detail_user_day AS ( -- 商详浏览
    SELECT a.dt, a.uid AS user_id, COUNT(1) AS detail_cnt
    FROM hdp_zhuanzhuan_dm_global.dm_trade_visit_detail_1d a
    JOIN product_scope b ON a.info_id = b.info_id
    WHERE a.dt BETWEEN '${start_dt}' AND '${end_dt}'
      AND a.uid IS NOT NULL
    GROUP BY a.dt, a.uid
),

addlove_user_day AS ( -- 收藏
    SELECT a.dt, a.uid AS user_id, COUNT(1) AS love_cnt
    FROM hdp_zhuanzhuan_dm_global.dm_trade_addlove_detail_1d a
    JOIN product_scope b ON a.info_id = b.info_id
    WHERE a.dt BETWEEN '${start_dt}' AND '${end_dt}'
      AND a.uid IS NOT NULL
    GROUP BY a.dt, a.uid
),

cart_user_day AS ( -- 加购
    SELECT a.dt, a.uid AS user_id, COUNT(1) AS cart_cnt
    FROM hdp_zhuanzhuan_dm_global.dm_trade_list2cart_detail_1d a
    JOIN product_scope b ON a.info_id = b.info_id
    WHERE a.dt BETWEEN '${start_dt}' AND '${end_dt}'
      AND a.uid IS NOT NULL
    GROUP BY a.dt, a.uid
),

base_user_day AS ( -- 有任一行为的 uid × dt
    SELECT dt, user_id FROM detail_user_day
    UNION
    SELECT dt, user_id FROM addlove_user_day
    UNION
    SELECT dt, user_id FROM cart_user_day
),

user_feature_day AS ( -- uid × dt 全行为特征
    SELECT
        u.dt,
        u.user_id,
        COALESCE(d.detail_cnt, 0) AS detail_cnt,
        COALESCE(l.love_cnt, 0)   AS love_cnt,
        COALESCE(c.cart_cnt, 0)   AS cart_cnt,
        COUNT(DISTINCT o.order_id) AS order_cnt,
        CASE WHEN COUNT(DISTINCT o.order_id) > 0 THEN 1 ELSE 0 END AS is_order
    FROM base_user_day u
    LEFT JOIN detail_user_day d ON u.dt = d.dt AND u.user_id = d.user_id
    LEFT JOIN addlove_user_day l ON u.dt = l.dt AND u.user_id = l.user_id
    LEFT JOIN cart_user_day    c ON u.dt = c.dt AND u.user_id = c.user_id
    LEFT JOIN order_full       o ON u.dt = o.dt AND u.user_id = o.user_id
    GROUP BY u.dt, u.user_id,
             COALESCE(d.detail_cnt, 0),
             COALESCE(l.love_cnt, 0),
             COALESCE(c.cart_cnt, 0)
),

metric_bucket AS ( -- 三种指标 × 8 档分桶 UNION ALL 长表
    SELECT dt, '商详浏览次数' AS metric_type,
           CASE
             WHEN detail_cnt = 0 THEN '0'
             WHEN detail_cnt = 1 THEN '1'
             WHEN detail_cnt = 2 THEN '2'
             WHEN detail_cnt = 3 THEN '3'
             WHEN detail_cnt BETWEEN 4 AND 5 THEN '4-5'
             WHEN detail_cnt BETWEEN 6 AND 10 THEN '6-10'
             WHEN detail_cnt BETWEEN 11 AND 20 THEN '11-20'
             ELSE '20+'
           END AS cnt_bucket,
           user_id, is_order, order_cnt
    FROM user_feature_day
    UNION ALL
    SELECT dt, '收藏次数' AS metric_type,
           CASE
             WHEN love_cnt = 0 THEN '0'
             WHEN love_cnt = 1 THEN '1'
             WHEN love_cnt = 2 THEN '2'
             WHEN love_cnt = 3 THEN '3'
             WHEN love_cnt BETWEEN 4 AND 5 THEN '4-5'
             WHEN love_cnt BETWEEN 6 AND 10 THEN '6-10'
             WHEN love_cnt BETWEEN 11 AND 20 THEN '11-20'
             ELSE '20+'
           END AS cnt_bucket,
           user_id, is_order, order_cnt
    FROM user_feature_day
    UNION ALL
    SELECT dt, '加购次数' AS metric_type,
           CASE
             WHEN cart_cnt = 0 THEN '0'
             WHEN cart_cnt = 1 THEN '1'
             WHEN cart_cnt = 2 THEN '2'
             WHEN cart_cnt = 3 THEN '3'
             WHEN cart_cnt BETWEEN 4 AND 5 THEN '4-5'
             WHEN cart_cnt BETWEEN 6 AND 10 THEN '6-10'
             WHEN cart_cnt BETWEEN 11 AND 20 THEN '11-20'
             ELSE '20+'
           END AS cnt_bucket,
           user_id, is_order, order_cnt
    FROM user_feature_day
),

daily_bucket AS ( -- 日聚合
    SELECT
        dt, metric_type, cnt_bucket,
        COUNT(DISTINCT user_id) AS user_cnt,
        COUNT(DISTINCT CASE WHEN is_order = 1 THEN user_id END) AS order_user_cnt,
        SUM(order_cnt) AS order_cnt
    FROM metric_bucket
    GROUP BY dt, metric_type, cnt_bucket
)

SELECT
    metric_type,
    cnt_bucket,
    ROUND(AVG(user_cnt), 2)         AS avg_daily_user_cnt,
    ROUND(AVG(order_user_cnt), 2)   AS avg_daily_order_user_cnt,
    ROUND(SUM(order_user_cnt) / SUM(user_cnt), 4) AS avg_daily_order_user_rate,
    ROUND(AVG(order_cnt), 2)        AS avg_daily_order_cnt
FROM daily_bucket
GROUP BY metric_type, cnt_bucket;

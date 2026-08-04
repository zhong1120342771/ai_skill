-- 转转用户分层 探索性打标 SQL（原始值版，不打分不分层）v2
-- 目的：给每个用户打上圈选条件对应指标的【原始值】，PMOD 哈希抽样约 100 万全站 APP 用户
--       （不限自然留存），供分位线探索 + 阈值校准。
-- 占位符：${dt} = 统计日期 YYYY-MM-DD ；引擎：Hive engine=5
--
-- 【v2 三处口径变更（依据 商品表相关信息.sql）】
-- 1. 业务线/品类打标改从商品表 dw_mysql_info_full_1d 取：cus_business_bu + business_line_id + cate_id 映射
--    出 cate（消费电子/二奢/兴趣/其他）与 cate_02（手机/包袋/腕表/台球杆…）。
--    二奢打标 = cate='二奢'（重奢 business_line_id IN(915051,915061)），替换旧的 cate_first_name='奢侈品'（已停用）。
-- 2. 订单限定在商品范围内：订单 INNER JOIN info_tag（info_id），只保留落在圈定业务线内商品的订单，
--    R/F/M 随之收敛到消电/兴趣/二奢等业务线范围。
-- 3. 价敏改为【同分类价格分位】：PERCENT_RANK() OVER(PARTITION BY cate_02 ORDER BY info_price)，
--    每单商品在其 cate_02 内的成交价分位，按用户取均值；越低=越买同类里便宜的=越价敏。替换失效的红包率口径。
--
-- 【降量根因（保留 v1 结论）】dw_trade_order_company_all_detail_full_1d 是每日全量快照表：
--   单分区即含全部历史订单，只取单分区 dt='${dt}' + 用 pay_time 过滤最近 180/90 天，不要扫多分区。
-- 抽样：PMOD(HASH(uid/buyer_id),3)=0，约占 DAU 的 1/3；同一套哈希下推到订单，聚合量对齐降到 1/3。

WITH info_tag AS (        -- 商品打标：业务线范围 + cate/cate_02 映射
    SELECT info_id,
        CASE WHEN cus_business_bu IN ('消费电子') THEN '消费电子'
             WHEN cus_business_bu IN ('二奢') AND business_line_id IN(915051,915061) THEN '二奢'
             WHEN cus_business_bu IN ('二奢') THEN '兴趣'
             WHEN cus_business_bu IN ('长尾N') THEN '兴趣'
             ELSE '其他' END AS cate,
        CASE WHEN cate_first_id IN ('101') THEN '手机'
             WHEN cate_first_id IN ('119') THEN '平板'
             WHEN cate_third_id IN ('1100000016') THEN '笔记本'
             WHEN cate_third_id IN ('1100000170') THEN '智能手表'
             WHEN cate_third_id IN ('1100000186','1100000325') THEN '耳机'
             WHEN cus_business_bu IN ('消费电子') THEN '消费电子N-其他'
             WHEN cus_business_bu IN ('长尾N') AND cate_id IN ('1100003483','1100003484') THEN '乐器'
             WHEN cus_business_bu IN ('长尾N') AND cate_id IN ('1100001943') THEN '台球杆'
             WHEN cus_business_bu IN ('长尾N') AND cate_id IN ('1100001204','1100001202') THEN '骑行'
             WHEN cus_business_bu IN ('长尾N') AND cate_id IN ('1100000874','1100003648') THEN '潮玩'
             WHEN cus_business_bu IN ('长尾N') AND cate_id IN ('1100001939','1100003419') THEN '球拍'
             WHEN cus_business_bu IN ('长尾N') THEN '兴趣N-其他'
             WHEN cate_first_id = '1100000354' THEN '包袋'
             WHEN cate_third_id IN ('1100001005','1100001007') THEN '腕表'
             WHEN cate_second_id IN ('1100003055','1100001004','2111008','1100001516') THEN '饰品'
             WHEN cate_second_id IN ('2111003','2111004','2111010','2111011','2111012','2111013','2111014','2111015','2111019','1100000315','1100001428','1100001438','1100003527') THEN '鞋服'
             ELSE '奢侈品-其他' END AS cate_02
    FROM hdp_zhuanzhuan_dw_global.dw_mysql_info_full_1d
    WHERE dt = '${dt}'
      AND cus_business_extend['is_cp_flag'] = '0'      -- 剔除充配
      AND cus_business_extend['is_live_flag'] = '0'    -- 剔除直播代下单
      AND (cus_business_bu IN ('消费电子','长尾N','二奢')
           OR (cus_business_belong IN ('B2C') AND cate_second_id IN ('120'))
           OR (cate_id ='2120006' AND cus_business_belong IN ('B2C')))
),
order_detail AS (         -- 订单 INNER JOIN 商品限范围 + 算同 cate_02 价格分位（近180天，单分区快照）
    SELECT o.buyer_id AS uid, o.order_id, o.pay_time, o.total_amt, o.pack_amt,
        o.info_price, o.is_seckill_order, o.order_type, o.pay_type,
        t.cate, t.cate_02,
        PERCENT_RANK() OVER (PARTITION BY t.cate_02 ORDER BY o.info_price) AS price_pctl_in_cate
    FROM hdp_zhuanzhuan_dw_global.dw_trade_order_company_all_detail_full_1d o
    JOIN info_tag t ON o.info_id = t.info_id     -- 限定订单商品落在圈定业务线内
    WHERE o.dt = '${dt}'                          -- 单分区快照即含全量历史订单，不扫多分区
      AND SUBSTR(o.pay_time,1,10) >= DATE_SUB('${dt}',180)
      AND o.is_pure_pay_success=1 AND o.order_structure_type IN (0,1) AND o.buyer_id IS NOT NULL
      AND PMOD(HASH(o.buyer_id), 3) = 0           -- 与 user_base 对齐的抽样键
),
order_agg AS (            -- 按用户聚合 R/F/M + 二奢 + 90天价敏（同类价格分位均值）
    SELECT uid,
        DATEDIFF('${dt}', MAX(SUBSTR(pay_time,1,10)))  AS r_last_pay_days,
        COUNT(DISTINCT order_id)                        AS f_pay_cnt_180d,
        SUM(total_amt)/100.0                            AS m_pay_amt_180d,
        MAX(CASE WHEN cate='二奢' THEN 1 ELSE 0 END)                       AS is_lux_buyer_180d,
        COUNT(DISTINCT CASE WHEN cate='二奢' THEN order_id END)            AS lux_order_cnt_180d,
        -- 价敏：近90天订单在同 cate_02 内的价格分位均值（越低越买同类里便宜的）
        AVG(CASE WHEN SUBSTR(pay_time,1,10)>=DATE_SUB('${dt}',90) THEN price_pctl_in_cate END) AS price_pctl_90d,
        COUNT(DISTINCT CASE WHEN SUBSTR(pay_time,1,10)>=DATE_SUB('${dt}',90) THEN order_id END) AS p_total_cnt_90,
        COUNT(DISTINCT CASE WHEN SUBSTR(pay_time,1,10)>=DATE_SUB('${dt}',90) AND pack_amt>0 THEN order_id END) AS p_coupon_cnt_90,
        COUNT(DISTINCT CASE WHEN SUBSTR(pay_time,1,10)>=DATE_SUB('${dt}',90) AND (is_seckill_order=1 OR order_type IN(4,8,23)) THEN order_id END) AS p_promo_cnt_90
    FROM order_detail
    GROUP BY uid
),
user_base AS (
    SELECT token, uid, user_source,
        get_json_object(user_layer, '$.B2C核心业务') AS user_type,
        DATEDIFF('${dt}', SUBSTR(regist_time, 1, 10)) AS regist_days,
        COALESCE(visit_pv_30d, 0)   AS a_visit_pv_30d,
        COALESCE(search_pv_30d, 0)  AS a_search_pv_30d,
        COALESCE(love_pv_30d, 0)    AS a_love_pv_30d,
        COALESCE(b2c_all_order_num_365d, 0) AS a_hist_order_cnt
    FROM hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d
    WHERE dt = '${dt}' AND terminal_name = '转转APP'
      AND PMOD(HASH(uid), 3) = 0
)
SELECT '${dt}' AS dt, u.token, u.user_type, u.user_source, u.regist_days,
    COALESCE(o.r_last_pay_days,9999)      AS r_last_pay_days,
    COALESCE(o.f_pay_cnt_180d,0)          AS f_pay_cnt_180d,
    ROUND(COALESCE(o.m_pay_amt_180d,0),2) AS m_pay_amt_180d,
    u.a_visit_pv_30d, u.a_search_pv_30d, u.a_love_pv_30d, u.a_hist_order_cnt,
    COALESCE(o.is_lux_buyer_180d,0)  AS is_lux_buyer_180d,
    COALESCE(o.lux_order_cnt_180d,0) AS lux_order_cnt_180d,
    COALESCE(o.p_total_cnt_90,0)     AS p_total_cnt_90,
    ROUND(o.price_pctl_90d,4)        AS price_pctl_90d,   -- 同类价格分位均值(越低越价敏),无90天单为 null
    CASE WHEN o.p_total_cnt_90>0 THEN ROUND(o.p_coupon_cnt_90*1.0/o.p_total_cnt_90,4) ELSE 0 END AS p_coupon_rate,
    CASE WHEN o.p_total_cnt_90>0 THEN ROUND(o.p_promo_cnt_90*1.0/o.p_total_cnt_90,4)  ELSE 0 END AS p_promo_rate
FROM user_base u
LEFT JOIN order_agg o ON u.uid=o.uid;


-- 转转用户分层 价敏叠加分群取数：dualwindow(D+7/D+365 outcome) + 同类价格分位价敏
-- 在 rfmlap_dualwindow 基础上并入 price_pctl_90d(同 cate_02 成交价 PERCENT_RANK 均值,近90天,越低越价敏)。
-- 占位符：${D}=活跃/抽样日；${SNAP}=订单全量快照(须≥D+365)。本次 D=2025-07-27, SNAP=2026-08-03。
-- 单快照取全量历史,pay_time 切窗口,抽样 PMOD(HASH,3)=0。价敏口径同 rfmlap_explore_query.sql。

WITH info_tag AS (
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
    WHERE dt = '${SNAP}'
      AND cus_business_extend['is_cp_flag'] = '0'
      AND cus_business_extend['is_live_flag'] = '0'
      AND (cus_business_bu IN ('消费电子','长尾N','二奢')
           OR (cus_business_belong IN ('B2C') AND cate_second_id IN ('120'))
           OR (cate_id ='2120006' AND cus_business_belong IN ('B2C')))
),
ord AS (
    SELECT o.buyer_id AS uid, o.order_id, SUBSTR(o.pay_time,1,10) AS pay_dt,
        o.total_amt, o.info_price, t.cate, t.cate_02,
        PERCENT_RANK() OVER (PARTITION BY t.cate_02 ORDER BY o.info_price) AS price_pctl_in_cate,
        CASE WHEN SUBSTR(o.pay_time,1,10) <= '${D}' AND SUBSTR(o.pay_time,1,10) >= DATE_SUB('${D}',180) THEN 1 ELSE 0 END AS in_hist180,
        CASE WHEN SUBSTR(o.pay_time,1,10) <= '${D}' AND SUBSTR(o.pay_time,1,10) >= DATE_SUB('${D}',90)  THEN 1 ELSE 0 END AS in_hist90,
        CASE WHEN SUBSTR(o.pay_time,1,10) >  '${D}' AND SUBSTR(o.pay_time,1,10) <= DATE_ADD('${D}',7)   THEN 1 ELSE 0 END AS in_fwd7,
        CASE WHEN SUBSTR(o.pay_time,1,10) >  '${D}' AND SUBSTR(o.pay_time,1,10) <= DATE_ADD('${D}',365) THEN 1 ELSE 0 END AS in_fwd365
    FROM hdp_zhuanzhuan_dw_global.dw_trade_order_company_all_detail_full_1d o
    JOIN info_tag t ON o.info_id = t.info_id
    WHERE o.dt = '${SNAP}'
      AND SUBSTR(o.pay_time,1,10) >= DATE_SUB('${D}',180)
      AND SUBSTR(o.pay_time,1,10) <= DATE_ADD('${D}',365)
      AND o.is_pure_pay_success=1 AND o.order_structure_type IN (0,1) AND o.buyer_id IS NOT NULL
      AND PMOD(HASH(o.buyer_id), 3) = 0
),
rfm_hist AS (
    SELECT uid,
        DATEDIFF('${D}', MAX(CASE WHEN in_hist180=1 THEN pay_dt END)) AS r_last_pay_days,
        COUNT(DISTINCT CASE WHEN in_hist180=1 THEN order_id END)       AS f_pay_cnt_180d,
        SUM(CASE WHEN in_hist180=1 THEN total_amt ELSE 0 END)/100.0    AS m_pay_amt_180d,
        MAX(CASE WHEN in_hist180=1 AND cate='二奢' THEN 1 ELSE 0 END)  AS is_lux_buyer_180d,
        AVG(CASE WHEN in_hist90=1 THEN price_pctl_in_cate END)         AS price_pctl_90d,
        COUNT(DISTINCT CASE WHEN in_hist90=1 THEN order_id END)        AS p_cnt_90d
    FROM ord GROUP BY uid
),
fwd AS (
    SELECT uid,
        COUNT(DISTINCT CASE WHEN in_fwd7=1   THEN order_id END)        AS order_cnt_7d,
        SUM(CASE WHEN in_fwd7=1   THEN total_amt ELSE 0 END)/100.0     AS pay_amt_7d,
        COUNT(DISTINCT CASE WHEN in_fwd365=1 THEN order_id END)        AS order_cnt_365d,
        SUM(CASE WHEN in_fwd365=1 THEN total_amt ELSE 0 END)/100.0     AS pay_amt_365d
    FROM ord GROUP BY uid
),
user_base AS (
    SELECT token, uid, user_source,
        get_json_object(user_layer, '$.B2C核心业务') AS user_type,
        DATEDIFF('${D}', SUBSTR(regist_time, 1, 10)) AS regist_days,
        COALESCE(visit_pv_30d, 0)   AS a_visit_pv_30d,
        COALESCE(search_pv_30d, 0)  AS a_search_pv_30d,
        COALESCE(love_pv_30d, 0)    AS a_love_pv_30d,
        COALESCE(b2c_all_order_num_365d, 0) AS a_hist_order_cnt
    FROM hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d
    WHERE dt = '${D}' AND terminal_name = '转转APP'
      AND PMOD(HASH(uid), 3) = 0
)
SELECT '${D}' AS d, u.token, u.user_type, u.user_source, u.regist_days,
    COALESCE(h.r_last_pay_days,9999)      AS r_last_pay_days,
    COALESCE(h.f_pay_cnt_180d,0)          AS f_pay_cnt_180d,
    ROUND(COALESCE(h.m_pay_amt_180d,0),2) AS m_pay_amt_180d,
    COALESCE(h.is_lux_buyer_180d,0)       AS is_lux_buyer_180d,
    ROUND(h.price_pctl_90d,4)             AS price_pctl_90d,
    COALESCE(h.p_cnt_90d,0)               AS p_cnt_90d,
    u.a_visit_pv_30d, u.a_search_pv_30d, u.a_love_pv_30d, u.a_hist_order_cnt,
    COALESCE(f.order_cnt_7d,0)            AS order_cnt_7d,
    ROUND(COALESCE(f.pay_amt_7d,0),2)     AS pay_amt_7d,
    CASE WHEN COALESCE(f.order_cnt_7d,0)   > 0 THEN 1 ELSE 0 END AS is_paid_7d,
    COALESCE(f.order_cnt_365d,0)          AS order_cnt_365d,
    ROUND(COALESCE(f.pay_amt_365d,0),2)   AS pay_amt_365d,
    CASE WHEN COALESCE(f.order_cnt_365d,0) > 0 THEN 1 ELSE 0 END AS is_paid_365d
FROM user_base u
LEFT JOIN rfm_hist h ON u.uid=h.uid
LEFT JOIN fwd f      ON u.uid=f.uid;

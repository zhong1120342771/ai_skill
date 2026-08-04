-- 转转用户分层 分层效果后验：一年前抽样→看各层未来一年付费转化率与 LTV
-- 目的：D 日（约一年前）抽活跃样本→用「截至 D 的特征」打价值层→看 (D, D+365] 净支付转化率、
--       人均订单量、人均 GMV（LTV），比对各层量级差距，作为分层是否有效的后验验证。
-- 占位符：${D}=一年前活跃/抽样日 ；${SNAP}=订单全量快照日(须 ≥ D+365) ；引擎 Hive engine=5
--   本次：D=2025-07-27，SNAP=2026-08-03（前瞻窗口 2025-07-28~2026-07-27 满一年，已完全落数）。
-- 【单快照取全量历史】dw_trade_order_company_all_detail_full_1d 单分区含全部历史订单，
--   只取 dt='${SNAP}' 一分区，pay_time 切「截至D的180天RFM」与「D后365天LTV」两窗口，不扫多分区。
-- 抽样：PMOD(HASH(uid/buyer_id),3)=0。

WITH info_tag AS (
    SELECT info_id,
        CASE WHEN cus_business_bu IN ('消费电子') THEN '消费电子'
             WHEN cus_business_bu IN ('二奢') AND business_line_id IN(915051,915061) THEN '二奢'
             WHEN cus_business_bu IN ('二奢') THEN '兴趣'
             WHEN cus_business_bu IN ('长尾N') THEN '兴趣'
             ELSE '其他' END AS cate
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
        o.total_amt, t.cate,
        CASE WHEN SUBSTR(o.pay_time,1,10) <= '${D}'
              AND SUBSTR(o.pay_time,1,10) >= DATE_SUB('${D}',180) THEN 1 ELSE 0 END AS in_hist180,
        CASE WHEN SUBSTR(o.pay_time,1,10) >  '${D}'
              AND SUBSTR(o.pay_time,1,10) <= DATE_ADD('${D}',365) THEN 1 ELSE 0 END AS in_fwd365
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
        MAX(CASE WHEN in_hist180=1 AND cate='二奢' THEN 1 ELSE 0 END)  AS is_lux_buyer_180d
    FROM ord GROUP BY uid
),
fwd365 AS (               -- (D, D+365] 净支付 LTV
    SELECT uid,
        COUNT(DISTINCT CASE WHEN in_fwd365=1 THEN order_id END)        AS order_cnt_1y,
        SUM(CASE WHEN in_fwd365=1 THEN total_amt ELSE 0 END)/100.0     AS pay_amt_1y
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
    u.a_visit_pv_30d, u.a_search_pv_30d, u.a_love_pv_30d, u.a_hist_order_cnt,
    COALESCE(f.order_cnt_1y,0)            AS order_cnt_1y,
    ROUND(COALESCE(f.pay_amt_1y,0),2)     AS pay_amt_1y,
    CASE WHEN COALESCE(f.order_cnt_1y,0) > 0 THEN 1 ELSE 0 END AS is_paid_1y
FROM user_base u
LEFT JOIN rfm_hist h ON u.uid=h.uid
LEFT JOIN fwd365 f   ON u.uid=f.uid;

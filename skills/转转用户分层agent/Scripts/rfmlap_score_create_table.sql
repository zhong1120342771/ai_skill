-- 转转用户分层 RFMLAP 评分 — Step 1：写 Hive tmp 表（无行数限制）
-- 占位符：${dt} = 统计日期 YYYY-MM-DD
-- 引擎：星河 Hive engine=5（含 DATEDIFF / COALESCE / CASE，必须走 Hive）
-- 执行后 tmp 表供 rfmlap_score_fetch_batch.sql 分批取数

CREATE TABLE hdp_zhuanzhuan_tmp_global.tmp_rfmlap_${dt}
STORED AS ORC AS

WITH user_base AS (
    SELECT token, uid, user_source,
        get_json_object(user_layer, '$.B2C核心业务') AS user_type,
        DATEDIFF('${dt}', SUBSTR(regist_time, 1, 10)) AS regist_days,
        COALESCE(visit_pv_30d, 0)               AS a_visit_pv_30d,
        COALESCE(search_pv_30d, 0)              AS a_search_pv_30d,
        COALESCE(love_pv_30d, 0)                AS a_love_pv_30d,
        COALESCE(b2c_all_order_num_365d, 0)     AS a_hist_order_cnt
    FROM hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d
    WHERE dt = '${dt}' AND terminal_name = '转转APP'
),
order_rfm AS (
    SELECT buyer_id AS uid,
        DATEDIFF('${dt}', MAX(SUBSTR(pay_time,1,10))) AS r_last_pay_days,
        COUNT(DISTINCT order_id)    AS f_pay_cnt_180d,
        SUM(total_amt) / 100.0      AS m_pay_amt_180d
    FROM hdp_zhuanzhuan_dw_global.dw_trade_order_company_all_detail_full_1d
    WHERE dt >= DATE_SUB('${dt}', 180) AND dt <= '${dt}'
      AND is_pure_pay_success = 1
      AND order_structure_type IN (0, 1)
      AND buyer_id IS NOT NULL
    GROUP BY buyer_id
),
order_p AS (
    SELECT buyer_id AS uid,
        COUNT(DISTINCT order_id) AS p_total_cnt,
        COUNT(DISTINCT CASE WHEN pack_amt > 0 THEN order_id END) AS p_coupon_cnt,
        COUNT(DISTINCT CASE WHEN is_seckill_order = 1 OR order_type IN (4, 8, 23) THEN order_id END) AS p_promo_cnt,
        COUNT(DISTINCT CASE WHEN pay_type IN (105,108,109,110,111,1007,1012,1013,1016,1017) THEN order_id END) AS p_install_cnt
    FROM hdp_zhuanzhuan_dw_global.dw_trade_order_company_all_detail_full_1d
    WHERE dt >= DATE_SUB('${dt}', 90) AND dt <= '${dt}'
      AND is_pure_pay_success = 1
      AND order_structure_type IN (0, 1)
      AND buyer_id IS NOT NULL
    GROUP BY buyer_id
),
scored AS (
    SELECT
        u.token, u.uid, u.regist_days, u.user_type, u.user_source,
        u.a_visit_pv_30d, u.a_search_pv_30d, u.a_love_pv_30d, u.a_hist_order_cnt,
        COALESCE(o.r_last_pay_days, 9999)           AS r_last_pay_days,
        COALESCE(o.f_pay_cnt_180d, 0)               AS f_pay_cnt_180d,
        ROUND(COALESCE(o.m_pay_amt_180d, 0), 2)     AS m_pay_amt_180d,
        CASE WHEN p.p_total_cnt > 0 THEN ROUND(p.p_coupon_cnt * 1.0 / p.p_total_cnt, 4) ELSE 0 END AS p_coupon_rate,
        CASE WHEN p.p_total_cnt > 0 THEN ROUND(p.p_promo_cnt  * 1.0 / p.p_total_cnt, 4) ELSE 0 END AS p_promo_rate,
        -- R评分
        CASE WHEN COALESCE(o.r_last_pay_days, 9999) <= 30  THEN 3
             WHEN COALESCE(o.r_last_pay_days, 9999) <= 90  THEN 2
             WHEN COALESCE(o.r_last_pay_days, 9999) <= 180 THEN 1 ELSE 0 END AS r_score,
        -- F评分
        CASE WHEN COALESCE(o.f_pay_cnt_180d, 0) >= 5 THEN 4
             WHEN COALESCE(o.f_pay_cnt_180d, 0) >= 3 THEN 3
             WHEN COALESCE(o.f_pay_cnt_180d, 0)  = 2 THEN 2
             WHEN COALESCE(o.f_pay_cnt_180d, 0)  = 1 THEN 1 ELSE 0 END AS f_score,
        -- M评分
        CASE WHEN COALESCE(o.m_pay_amt_180d, 0) >= 10000 THEN 3
             WHEN COALESCE(o.m_pay_amt_180d, 0) >= 1000  THEN 2
             WHEN COALESCE(o.m_pay_amt_180d, 0) >= 100   THEN 1 ELSE 0 END AS m_score,
        -- L评分
        CASE WHEN u.regist_days <= 30 THEN 1
             WHEN u.regist_days BETWEEN 31 AND 180 THEN 2
             WHEN u.regist_days > 180 AND COALESCE(o.f_pay_cnt_180d, 0) >= 1 THEN 3
             ELSE 0 END AS l_score,
        -- A评分
        (CASE WHEN u.a_visit_pv_30d >= 5   THEN 1 ELSE 0 END +
         CASE WHEN u.a_search_pv_30d >= 3  THEN 1 ELSE 0 END +
         CASE WHEN u.a_love_pv_30d >= 1    THEN 2 ELSE 0 END +
         CASE WHEN u.a_hist_order_cnt >= 1 THEN 2 ELSE 0 END) AS a_score,
        -- P评分
        LEAST(3,
            CASE WHEN (CASE WHEN p.p_total_cnt > 0 THEN p.p_coupon_cnt * 1.0 / p.p_total_cnt ELSE 0 END >= 0.5)
                      OR (CASE WHEN p.p_total_cnt > 0 THEN p.p_promo_cnt * 1.0 / p.p_total_cnt ELSE 0 END >= 0.3) THEN 3
                 WHEN (CASE WHEN p.p_total_cnt > 0 THEN p.p_coupon_cnt * 1.0 / p.p_total_cnt ELSE 0 END >= 0.3)
                      OR (CASE WHEN p.p_total_cnt > 0 THEN p.p_promo_cnt * 1.0 / p.p_total_cnt ELSE 0 END >= 0.15) THEN 2
                 WHEN  CASE WHEN p.p_total_cnt > 0 THEN p.p_coupon_cnt * 1.0 / p.p_total_cnt ELSE 0 END >= 0.1 THEN 1
                 ELSE 0 END
            + CASE WHEN (CASE WHEN p.p_total_cnt > 0 THEN p.p_install_cnt * 1.0 / p.p_total_cnt ELSE 0 END >= 0.3) THEN 1 ELSE 0 END
        ) AS p_score
    FROM user_base u
    LEFT JOIN order_rfm o ON u.uid = o.uid
    LEFT JOIN order_p   p ON u.uid = p.uid
)
SELECT
    '${dt}' AS dt,
    token, user_type, user_source, regist_days,
    r_last_pay_days, f_pay_cnt_180d, m_pay_amt_180d,
    a_visit_pv_30d, a_search_pv_30d, a_love_pv_30d, a_hist_order_cnt,
    p_coupon_rate, p_promo_rate,
    r_score, f_score, m_score, l_score, a_score, p_score,
    (r_score*2 + f_score*3 + m_score + l_score + a_score*2 + p_score) AS total_score,
    CASE WHEN (r_score*2 + f_score*3 + m_score + l_score + a_score*2 + p_score) >= 28 THEN 'L5'
         WHEN (r_score*2 + f_score*3 + m_score + l_score + a_score*2 + p_score) >= 20 THEN 'L4'
         WHEN (r_score*2 + f_score*3 + m_score + l_score + a_score*2 + p_score) >= 13 THEN 'L3'
         WHEN (r_score*2 + f_score*3 + m_score + l_score + a_score*2 + p_score) >= 7  THEN 'L2'
         ELSE 'L1' END AS segment_level
FROM scored;

-- 用户标签（转转APP留存用户分析专项）
-- 占位符：${outFileSuffix} = 最新分区日期 YYYY-MM-DD（统计窗口末日 = t-1）
-- 统计窗口：[DATE_SUB(${outFileSuffix}, 6), ${outFileSuffix}] 共7天
-- 30天活跃回溯：[DATE_SUB(${outFileSuffix}, 37), ${outFileSuffix}]
-- 365天付费回溯：[DATE_SUB(${outFileSuffix}, 371), ${outFileSuffix}]
-- 引擎：星河 Hive engine=5

CREATE TABLE hdp_zhuanzhuan_tmp_global.tmp_act_label_02_${outFileSuffix} AS
WITH info AS (
    SELECT
        CASE
            WHEN cus_business_bu IN ('消费电子') THEN '消费电子'
            WHEN cus_business_bu IN ('二奢') AND business_line_id IN (915051, 915061) THEN '二奢'
            WHEN cus_business_bu IN ('二奢') THEN '兴趣'
            WHEN cus_business_bu IN ('长尾N') THEN '兴趣'
            ELSE '其他'
        END AS cate,
        CASE
            WHEN cate_first_id IN ('101') THEN '手机'
            WHEN cate_first_id IN ('119') THEN '平板'
            WHEN cate_third_id IN ('1100000016') THEN '笔记本'
            WHEN cate_third_id IN ('1100000170') THEN '智能手表'
            WHEN cate_third_id IN ('1100000186', '1100000325') THEN '耳机'
            WHEN cate_third_id IN (
                1100001788, 1100001798, 1100001791, 1100001790, 1100001787, 1100001789,
                1100001792, 1100001793, 1100001127, 1100000182, 1100001139, 1100000179,
                1100001138, 1100000192, 1100000177, 1100001140, 1100000467, 1100000193,
                1100001141, 1100000176, 1100000172, 1100000180, 1100001143, 1100000181,
                1100001806, 1100001805, 1100001807, 1100001794, 1100001801, 1100001811,
                1100000208, 1100001812, 1100000211, 1100001809, 1100001808, 1100001142,
                1100001126, 1100000194, 1100001810, 1100001804, 1100000209, 1100003433
            ) THEN '摄影摄像矩阵'
            WHEN cate_third_id IN (1100000187, 1100000188, 1100000665, 1100000189) THEN '游戏矩阵'
            WHEN cus_business_bu IN ('消费电子') THEN '消费电子N-其他'
            -- ⚠️ 原SQL此处有截断，长尾N第一个品类条件（cate_id列表）缺失，需人工补全
            -- WHEN cus_business_bu IN ('长尾N') AND cate_id IN ('[缺失]') THEN '[缺失]'
            WHEN cus_business_bu IN ('长尾N') AND cate_id IN ('1100001204', '1100001202') THEN '骑行'
            WHEN cus_business_bu IN ('长尾N') AND cate_id IN ('1100000874', '1100003648') THEN '潮玩'
            WHEN cus_business_bu IN ('长尾N') AND cate_id IN ('1100001939', '1100003419') THEN '球拍'
            WHEN cus_business_bu IN ('长尾N') THEN '兴趣N-其他'
            WHEN cate_first_id = '1100000354' THEN '包袋'
            WHEN cate_third_id IN ('1100001005', '1100001007') THEN '腕表'
            WHEN cate_second_id IN ('1100003055', '1100001004', '2111008', '1100001516') THEN '饰品'
            WHEN cate_second_id IN (
                '2111003', '2111004', '2111010', '2111011', '2111012', '2111013',
                '2111014', '2111015', '2111019', '1100000315', '1100001428',
                '1100001438', '1100003527'
            ) THEN '鞋服'
            ELSE '奢侈品-其他'
        END AS cate_02,
        info_id
    FROM hdp_zhuanzhuan_dw_global.dw_mysql_info_full_1d t1
    WHERE t1.dt = '${outFileSuffix}'
        AND t1.cus_business_extend['is_cp_flag'] = '0'
        AND t1.cus_business_extend['is_live_flag'] = '0'
        AND (
            t1.cus_business_bu IN ('消费电子', '长尾N', '二奢')
            OR (cus_business_belong IN ('B2C') AND cate_second_id IN ('120'))
            OR (cate_id = '2120006' AND cus_business_belong IN ('B2C'))
        )
    GROUP BY 1, 2, 3
),

-- 过去30天活跃情况（供计算每个分析日前30天的活跃天数）
-- 范围：[DATE_SUB(${outFileSuffix}, 37), ${outFileSuffix}]，覆盖窗口最早分析日(${outFileSuffix}-6)往前30天+1天缓冲
dau_t_30 AS (
    SELECT
        dt,
        token,
        user_source
    FROM hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d
    WHERE dt BETWEEN DATE_SUB('${outFileSuffix}', 37) AND '${outFileSuffix}'
        AND terminal_name IN ('转转APP')
    GROUP BY 1, 2, 3
),

-- 过去365天付费情况
-- 范围：pay_time >= DATE_SUB(${outFileSuffix}, 371)，覆盖窗口最早分析日(${outFileSuffix}-6)往前365天
ord_t_365 AS (
    SELECT
        a1.token,
        a1.cate,
        a1.order_id,
        a1.dt
    FROM (
        SELECT a.dt, a.token, a.order_id, c.cate
        FROM hdp_zhuanzhuan_dm_global.dm_trade_pay_detail_1d a
        INNER JOIN info c ON a.info_id = c.info_id
        WHERE a.dt >= DATE_SUB('${outFileSuffix}', 371)
            AND a.terminal IN (15, 16, 20)
    ) a1
    INNER JOIN (
        SELECT
            TO_DATE(aa.pay_time) AS dt,
            aa.buyer_id,
            aa.order_id,
            aa.total_amt,
            aa.token,
            aa.info_id
        FROM hdp_zhuanzhuan_dw_global.dw_trade_order_company_all_detail_full_1d aa
        WHERE aa.dt = '${outFileSuffix}'
            AND TO_DATE(aa.pay_time) >= DATE_SUB('${outFileSuffix}', 371)
            AND aa.is_pure_pay_the_day = 1
            AND aa.is_exchange_order_flag = 0
    ) a2 ON a1.order_id = a2.order_id AND a1.dt = a2.dt
    GROUP BY 1, 2, 3, 4
),

-- 统计窗口内（7天）活跃用户
dau AS (
    SELECT
        dt,
        token,
        user_source
    FROM hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d
    WHERE dt BETWEEN DATE_SUB('${outFileSuffix}', 6) AND '${outFileSuffix}'
        AND terminal_name IN ('转转APP')
    GROUP BY 1, 2, 3
),

-- 注册信息（统计窗口内）
dau_zhuce AS (
    SELECT
        dt,
        token,
        date_diff AS register_gap
    FROM hdp_zhuanzhuan_dm_global.dm_oper_key_user_detail_inc_1d
    WHERE dt BETWEEN DATE_SUB('${outFileSuffix}', 6) AND '${outFileSuffix}'
    GROUP BY 1, 2, 3
),

-- 统计窗口内7天付费订单
ord_7 AS (
    SELECT
        a1.token,
        a1.cate,
        a1.order_id,
        a1.dt
    FROM (
        SELECT a.dt, a.token, a.order_id, c.cate
        FROM hdp_zhuanzhuan_dm_global.dm_trade_pay_detail_1d a
        INNER JOIN info c ON a.info_id = c.info_id
        WHERE a.dt >= DATE_SUB('${outFileSuffix}', 6)
            AND a.terminal IN (15, 16, 20)
    ) a1
    INNER JOIN (
        SELECT
            TO_DATE(aa.pay_time) AS dt,
            aa.buyer_id,
            aa.order_id,
            aa.total_amt,
            aa.token,
            aa.info_id
        FROM hdp_zhuanzhuan_dw_global.dw_trade_order_company_all_detail_full_1d aa
        WHERE aa.dt = '${outFileSuffix}'
            AND TO_DATE(aa.pay_time) >= DATE_SUB('${outFileSuffix}', 6)
            AND aa.is_pure_pay_the_day = 1
            AND aa.is_exchange_order_flag = 0
    ) a2 ON a1.order_id = a2.order_id AND a1.dt = a2.dt
    GROUP BY 1, 2, 3, 4
),

-- 商详访问 PV（统计窗口内）
sx_pv AS (
    SELECT dt, token, cate, COUNT(1) AS pv
    FROM (
        SELECT a.dt, a.token, c.cate
        FROM hdp_zhuanzhuan_dm_global.dm_trade_visit_detail_1d a
        JOIN info c ON a.info_id = c.info_id
        WHERE dt BETWEEN DATE_SUB('${outFileSuffix}', 6) AND '${outFileSuffix}'
            AND a.terminal IN (15, 16, 20)
    ) a
    GROUP BY 1, 2, 3
),

-- 收藏 UV（统计窗口内）
sc_uv AS (
    SELECT a.dt, a.token, c.cate, COUNT(1) AS pv
    FROM (
        SELECT dt, token, info_id
        FROM hdp_zhuanzhuan_dm_global.dm_trade_addlove_detail_1d
        WHERE dt BETWEEN DATE_SUB('${outFileSuffix}', 6) AND '${outFileSuffix}'
            AND terminal IN (15, 16, 20)
        GROUP BY 1, 2, 3
    ) a
    JOIN info c ON a.info_id = c.info_id
    GROUP BY 1, 2, 3
),

-- 加购 UV（统计窗口内）
jiagou_uv AS (
    SELECT a.dt, a.token, c.cate, COUNT(1) AS pv
    FROM (
        SELECT dt, token, info_id
        FROM hdp_zhuanzhuan_dw_global.dw_log_server_action_1d
        WHERE dt BETWEEN DATE_SUB('${outFileSuffix}', 6) AND '${outFileSuffix}'
            AND region = 'd'
        GROUP BY 1, 2, 3
    ) a
    JOIN info c ON a.info_id = c.info_id
    GROUP BY 1, 2, 3
),

-- 下单点击 UV（统计窗口内）
xd_uv AS (
    SELECT a.dt, a.token, c.cate, COUNT(1) AS pv
    FROM (
        SELECT
            dt,
            token,
            REGEXP_EXTRACT(a.datapool['pagequery'], 'infoId=([^&]+)', 1) AS info_id
        FROM hdp_zhuanzhuan_dw_global.dw_log_lego_action_1d a
        WHERE actiontype = 'J2275'
            AND region = 'j'
            AND pagetype = 'zpmshow'
            AND dt BETWEEN DATE_SUB('${outFileSuffix}', 6) AND '${outFileSuffix}'
        GROUP BY 1, 2, 3
    ) a
    JOIN info c ON a.info_id = c.info_id
    GROUP BY 1, 2, 3
)

SELECT
    a.dt,
    a.token,
    a.user_source,
    a.register_gap,
    NVL(b.act_30, 0)              AS act_30,
    NVL(t1.sc_all, 0)             AS sc_all,
    NVL(t1.sc_xfdz, 0)            AS sc_xfdz,
    NVL(t1.sc_es, 0)              AS sc_es,
    NVL(t1.sc_xq, 0)              AS sc_xq,
    NVL(t2.jg_all, 0)             AS jg_all,
    NVL(t2.jg_xfdz, 0)            AS jg_xfdz,
    NVL(t2.jg_es, 0)              AS jg_es,
    NVL(t2.jg_xq, 0)              AS jg_xq,
    NVL(t3.xd_all, 0)             AS xd_all,
    NVL(t3.xd_xfdz, 0)            AS xd_xfdz,
    NVL(t3.xd_es, 0)              AS xd_es,
    NVL(t3.xd_xq, 0)              AS xd_xq,
    NVL(t4.sx_all, 0)             AS sx_all,
    NVL(t4.sx_xfdz, 0)            AS sx_xfdz,
    NVL(t4.sx_es, 0)              AS sx_es,
    NVL(t4.sx_xq, 0)              AS sx_xq,
    NVL(t5.ord_7, 0)              AS ord_7,
    NVL(t5.ord_xfdz_7, 0)         AS ord_xfdz_7,
    NVL(t5.ord_es_7, 0)           AS ord_es_7,
    NVL(t5.ord_xq_7, 0)           AS ord_xq_7,
    NVL(t6.ord_t_365, 0)          AS ord_t_365,
    NVL(t6.ord_xfdz_t_365, 0)     AS ord_xfdz_t_365,
    NVL(t6.ord_es_t_365, 0)       AS ord_es_t_365,
    NVL(t6.ord_xq_t_365, 0)       AS ord_xq_t_365,
    NVL(t7.pay_gap_all, 9999)     AS pay_gap_all,
    NVL(t7.pay_gap_xfdz, 9999)    AS pay_gap_xfdz,
    NVL(t7.pay_gap_es, 9999)      AS pay_gap_es,
    NVL(t7.pay_gap_xq, 9999)      AS pay_gap_xq
FROM (
    SELECT a.dt, a.token, a.user_source, b.register_gap
    FROM dau a
    LEFT JOIN dau_zhuce b ON a.dt = b.dt AND a.token = b.token
    GROUP BY 1, 2, 3, 4
) a
LEFT JOIN (
    -- 过去30天平均活跃天数（不含当天，0 < gap < 30）
    SELECT
        a1.dt,
        a1.token,
        a1.user_source,
        COUNT(DISTINCT CASE WHEN DATEDIFF(a1.dt, a2.dt) > 0 AND DATEDIFF(a1.dt, a2.dt) < 30 THEN a2.dt ELSE NULL END) AS act_30
    FROM dau a1
    LEFT JOIN dau_t_30 a2 ON a1.token = a2.token
    GROUP BY 1, 2, 3
) b ON a.token = b.token AND a.dt = b.dt AND a.user_source = b.user_source
LEFT JOIN (
    SELECT
        dt, token,
        SUM(pv) AS sc_all,
        SUM(CASE WHEN cate = '消费电子' THEN pv ELSE 0 END) AS sc_xfdz,
        SUM(CASE WHEN cate = '二奢' THEN pv ELSE 0 END)     AS sc_es,
        SUM(CASE WHEN cate = '兴趣' THEN pv ELSE 0 END)     AS sc_xq
    FROM sc_uv
    GROUP BY 1, 2
) t1 ON a.token = t1.token AND a.dt = t1.dt
LEFT JOIN (
    SELECT
        dt, token,
        SUM(pv) AS jg_all,
        SUM(CASE WHEN cate = '消费电子' THEN pv ELSE 0 END) AS jg_xfdz,
        SUM(CASE WHEN cate = '二奢' THEN pv ELSE 0 END)     AS jg_es,
        SUM(CASE WHEN cate = '兴趣' THEN pv ELSE 0 END)     AS jg_xq
    FROM jiagou_uv
    GROUP BY 1, 2
) t2 ON a.token = t2.token AND a.dt = t2.dt
LEFT JOIN (
    SELECT
        dt, token,
        SUM(pv) AS xd_all,
        SUM(CASE WHEN cate = '消费电子' THEN pv ELSE 0 END) AS xd_xfdz,
        SUM(CASE WHEN cate = '二奢' THEN pv ELSE 0 END)     AS xd_es,
        SUM(CASE WHEN cate = '兴趣' THEN pv ELSE 0 END)     AS xd_xq
    FROM xd_uv
    GROUP BY 1, 2
) t3 ON a.token = t3.token AND a.dt = t3.dt
LEFT JOIN (
    SELECT
        dt, token,
        SUM(pv) AS sx_all,
        SUM(CASE WHEN cate = '消费电子' THEN pv ELSE 0 END) AS sx_xfdz,
        SUM(CASE WHEN cate = '二奢' THEN pv ELSE 0 END)     AS sx_es,
        SUM(CASE WHEN cate = '兴趣' THEN pv ELSE 0 END)     AS sx_xq
    FROM sx_pv
    GROUP BY 1, 2
) t4 ON a.token = t4.token AND a.dt = t4.dt
LEFT JOIN (
    -- 后续7天付费订单数（0 <= gap < 7，含当天）
    SELECT
        a1.dt,
        a1.token,
        a1.user_source,
        COUNT(DISTINCT CASE WHEN DATEDIFF(a2.dt, a1.dt) >= 0 AND DATEDIFF(a2.dt, a1.dt) < 7 THEN a2.order_id ELSE NULL END) AS ord_7,
        COUNT(DISTINCT CASE WHEN DATEDIFF(a2.dt, a1.dt) >= 0 AND DATEDIFF(a2.dt, a1.dt) < 7 AND cate = '消费电子' THEN a2.order_id ELSE NULL END) AS ord_xfdz_7,
        COUNT(DISTINCT CASE WHEN DATEDIFF(a2.dt, a1.dt) >= 0 AND DATEDIFF(a2.dt, a1.dt) < 7 AND cate = '二奢' THEN a2.order_id ELSE NULL END) AS ord_es_7,
        COUNT(DISTINCT CASE WHEN DATEDIFF(a2.dt, a1.dt) >= 0 AND DATEDIFF(a2.dt, a1.dt) < 7 AND cate = '兴趣' THEN a2.order_id ELSE NULL END) AS ord_xq_7
    FROM dau a1
    LEFT JOIN ord_7 a2 ON a1.token = a2.token
    GROUP BY 1, 2, 3
) t5 ON a.token = t5.token AND a.dt = t5.dt
LEFT JOIN (
    -- 过去365天付费订单数（0 < gap < 365）
    SELECT
        a1.dt,
        a1.token,
        a1.user_source,
        COUNT(DISTINCT CASE WHEN DATEDIFF(a1.dt, a2.dt) > 0 AND DATEDIFF(a1.dt, a2.dt) < 365 THEN a2.order_id ELSE NULL END) AS ord_t_365,
        COUNT(DISTINCT CASE WHEN DATEDIFF(a1.dt, a2.dt) > 0 AND DATEDIFF(a1.dt, a2.dt) < 365 AND cate = '消费电子' THEN a2.order_id ELSE NULL END) AS ord_xfdz_t_365,
        COUNT(DISTINCT CASE WHEN DATEDIFF(a1.dt, a2.dt) > 0 AND DATEDIFF(a1.dt, a2.dt) < 365 AND cate = '二奢' THEN a2.order_id ELSE NULL END) AS ord_es_t_365,
        COUNT(DISTINCT CASE WHEN DATEDIFF(a1.dt, a2.dt) > 0 AND DATEDIFF(a1.dt, a2.dt) < 365 AND cate = '兴趣' THEN a2.order_id ELSE NULL END) AS ord_xq_t_365
    FROM dau a1
    LEFT JOIN ord_t_365 a2 ON a1.token = a2.token
    GROUP BY 1, 2, 3
) t6 ON a.token = t6.token AND a.dt = t6.dt
LEFT JOIN (
    -- 过去365天最近一次付费距今天数（0 < gap < 365）
    SELECT
        dt, token, user_source,
        MIN(pay_gap)                                             AS pay_gap_all,
        MIN(CASE WHEN cate = '消费电子' THEN pay_gap ELSE 9999 END) AS pay_gap_xfdz,
        MIN(CASE WHEN cate = '二奢'    THEN pay_gap ELSE 9999 END) AS pay_gap_es,
        MIN(CASE WHEN cate = '兴趣'    THEN pay_gap ELSE 9999 END) AS pay_gap_xq
    FROM (
        SELECT
            a1.dt, a1.token, a1.user_source, a2.cate,
            MIN(DATEDIFF(a1.dt, a2.dt)) AS pay_gap
        FROM dau a1
        LEFT JOIN ord_t_365 a2 ON a1.token = a2.token
        WHERE DATEDIFF(a1.dt, a2.dt) > 0 AND DATEDIFF(a1.dt, a2.dt) < 365
        GROUP BY 1, 2, 3, 4
    ) a1
    GROUP BY 1, 2, 3
) t7 ON a.token = t7.token AND a.dt = t7.dt;

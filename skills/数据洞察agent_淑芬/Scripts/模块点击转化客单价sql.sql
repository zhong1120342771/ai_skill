-- ============================================================
-- 四页(G1001-G1004) 10 核心模块：有点击 vs 无点击 用户的净支付转化率 & 客单价差异
-- ★ 2026-07-13 默认扩四页:clk 按 page_id×module 切,clicked_agg 分 (page_id,module) 组;新增品类tab(300)/品牌墙(301)。
--    无点击组 = 全量DAU − 该(页,模块)有点击用户(与旧口径一致,只多了 page_id 维度)。单页模式 runner 只注入 G1001。
--    GMV折算主排页仍是 primary_page(G1001,首页为主),场馆页乘数供参考。
-- 人群：全量转转APP DAU（无抽样）
-- 净支付：限定 info CTE 品类（消费电子/二奢/兴趣等），is_pure_pay_the_day=1 且 is_exchange_order_flag=0
-- 客单价金额：取支付明细 pay_price（dm_trade_pay_detail_1d，分→元 /100），人均 & 笔均都算
-- 转化率口径：净支付 PV 转化率 = 净支付订单数 / 组用户数（分子用订单量，非付费人数；理论可 >100%）
-- dt：${outFileSuffix}（t-1，YYYY-MM-DD）
-- 引擎：星河 SparkSQL（engine=2），map 字段 datapool['x'] / get_json_object / to_date 均兼容
-- ============================================================

WITH dau AS (
    -- 全量转转APP DAU，distinct token
    SELECT t3.token
    FROM hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d t3
    WHERE t3.dt = '${outFileSuffix}'
      AND t3.terminal_name IN ('转转APP')
    GROUP BY t3.token
),

info AS (
    -- 品类限定商品池（与支付 SQL 的 join info 口径一致）
    SELECT info_id
    FROM hdp_zhuanzhuan_dw_global.dw_mysql_info_full_1d
    WHERE dt = '${outFileSuffix}'                                   -- 分区表必带 dt
      AND cus_business_extend['is_cp_flag'] = '0'        -- 剔除充配
      AND cus_business_extend['is_live_flag'] = '0'      -- 剔除直播代下单
      AND ( cus_business_bu IN ('消费电子','长尾N','二奢')
            OR (cus_business_belong IN ('B2C') AND cate_second_id IN ('120'))
            OR (cate_id = '2120006' AND cus_business_belong IN ('B2C')) )
    GROUP BY info_id
),

clk_raw AS (
    -- 四页点击事件，映射 sectionId → 10 核心模块，带 page_id
    SELECT
        token,
        actiontype AS page_id,
        CASE datapool['sectionId']
            WHEN '101' THEN '搜索框'
            WHEN '106' THEN '场馆tab'
            WHEN '300' THEN '品类tab'
            WHEN '301' THEN '品牌墙'
            WHEN '102' THEN '大促banner'
            WHEN '103' THEN '金刚位'
            WHEN '105' THEN '回收模块'
            WHEN '165' THEN '新人条'
            WHEN '302' THEN '栏目区'
            WHEN '108' THEN '商卡feed流'
            WHEN '109' THEN 'feed轮播图'
            ELSE '其他'
        END AS module
    FROM hdp_zhuanzhuan_dw_global.dw_log_lego_action_1d
    WHERE dt = '${outFileSuffix}'
      AND actiontype IN (${pageInList}) AND region = 'g'
      AND pagetype = 'zpmclick'
      AND datapool['sectionId'] IN ('101','106','300','301','102','103','105','165','302','108','109')
),

clk_user AS (
    -- DAU 内、每个 token 在哪些(页,核心模块)有过点击（distinct token×page_id×module）
    SELECT DISTINCT c.token, c.page_id, c.module
    FROM clk_raw c
    JOIN dau d ON c.token = d.token
    WHERE c.module <> '其他'
),

pay_orders AS (
    -- 净支付订单（订单粒度，限定品类 + DAU 用户），order_amt = pay_price（支付明细，分）
    SELECT a.token, a.order_id, MAX(a.pay_price) AS order_amt
    FROM (
        SELECT dt, token, order_id, info_id, pay_price
        FROM hdp_zhuanzhuan_dm_global.dm_trade_pay_detail_1d
        WHERE dt = '${outFileSuffix}'
          AND terminal IN (15,16,20,103,182,80,79,78,141)
    ) a
    JOIN dau b ON a.token = b.token
    JOIN info c ON a.info_id = c.info_id
    INNER JOIN (
        SELECT to_date(aa.pay_time) AS dt, aa.order_id
        FROM hdp_zhuanzhuan_dw_global.dw_trade_order_company_all_detail_full_1d aa
        WHERE aa.dt = '${outFileSuffix}'
          AND to_date(aa.pay_time) = '${outFileSuffix}'
          AND aa.is_pure_pay_the_day = 1
          AND aa.is_exchange_order_flag = 0
    ) d ON a.order_id = d.order_id and a.dt = d.dt
    GROUP BY a.token, a.order_id
),

pay_user AS (
    -- 每个净支付用户：订单数、净支付总额（分）
    SELECT token,
           COUNT(order_id) AS n_orders,
           SUM(order_amt)  AS pay_amt_total
    FROM pay_orders
    GROUP BY token
),

total_agg AS (
    -- 全量 DAU 总盘（一次性算好，用于推 not_clicked = total - clicked）
    SELECT
        COUNT(DISTINCT d.token) AS total_users,
        COUNT(DISTINCT CASE WHEN pu.token IS NOT NULL THEN d.token END) AS total_payers,
        SUM(COALESCE(pu.pay_amt_total,0)) AS total_amt,
        SUM(COALESCE(pu.n_orders,0))      AS total_orders
    FROM dau d
    LEFT JOIN pay_user pu ON d.token = pu.token
),

clicked_agg AS (
    -- 每(页,模块)「有点击」组的用户数 / 付费数 / 金额 / 订单数
    SELECT
        c.page_id,
        c.module,
        COUNT(DISTINCT c.token) AS clk_users,
        COUNT(DISTINCT CASE WHEN pu.token IS NOT NULL THEN c.token END) AS clk_payers,
        SUM(COALESCE(pu.pay_amt_total,0)) AS clk_amt,
        SUM(COALESCE(pu.n_orders,0))      AS clk_orders
    FROM clk_user c
    LEFT JOIN pay_user pu ON c.token = pu.token
    GROUP BY c.page_id, c.module
)

SELECT
    '${outFileSuffix}' AS dt,
    ca.page_id,
    ca.module,
    -- 有点击组
    ca.clk_users                                                AS clicked_users,
    ca.clk_payers                                               AS clicked_payers,
    ca.clk_orders                                               AS clicked_orders,
    ROUND(ca.clk_orders / ca.clk_users, 6)                      AS clicked_pv_conv_rate,   -- 净支付PV转化率=订单/用户
    ROUND(ca.clk_amt/100.0, 2)                                  AS clicked_gmv_yuan,        -- 组净支付GMV(元)
    ROUND(ca.clk_amt/100.0 / NULLIF(ca.clk_payers,0), 2)        AS clicked_aov_per_user,    -- 人均客单价
    ROUND(ca.clk_amt/100.0 / NULLIF(ca.clk_orders,0), 2)        AS clicked_aov_per_order,   -- 笔均客单价
    -- 无点击组 = 全量 - 有点击
    (t.total_users - ca.clk_users)                              AS notclk_users,
    (t.total_payers - ca.clk_payers)                            AS notclk_payers,
    (t.total_orders - ca.clk_orders)                            AS notclk_orders,
    ROUND((t.total_orders - ca.clk_orders) / (t.total_users - ca.clk_users), 6) AS notclk_pv_conv_rate,
    ROUND((t.total_amt - ca.clk_amt)/100.0, 2)                  AS notclk_gmv_yuan,
    ROUND((t.total_amt - ca.clk_amt)/100.0 / NULLIF(t.total_payers - ca.clk_payers,0), 2) AS notclk_aov_per_user,
    ROUND((t.total_amt - ca.clk_amt)/100.0 / NULLIF(t.total_orders - ca.clk_orders,0), 2) AS notclk_aov_per_order,
    -- 差值（有点击 - 无点击），喂机会计算器算单量/GMV增量
    ROUND(ca.clk_orders/ca.clk_users - (t.total_orders - ca.clk_orders)/(t.total_users - ca.clk_users), 6) AS pv_conv_rate_diff,
    ROUND( (ca.clk_orders/ca.clk_users) / NULLIF((t.total_orders - ca.clk_orders)/(t.total_users - ca.clk_users),0) - 1, 4) AS pv_conv_rate_lift,
    ROUND( ca.clk_amt/100.0/NULLIF(ca.clk_orders,0) - (t.total_amt - ca.clk_amt)/100.0/NULLIF(t.total_orders - ca.clk_orders,0), 2) AS aov_per_order_diff,
    ROUND( ca.clk_amt/100.0/NULLIF(ca.clk_payers,0) - (t.total_amt - ca.clk_amt)/100.0/NULLIF(t.total_payers - ca.clk_payers,0), 2) AS aov_per_user_diff
FROM clicked_agg ca
CROSS JOIN total_agg t
ORDER BY clicked_pv_conv_rate DESC;

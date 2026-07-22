/* @template
name: 品类用户画像（性别 × 新老客 × 兴趣分类）
scene: 任何品类下单用户的"人"维度画像——性别 / 新老客（历史是否买过） / 兴趣分类（沿用 0.03 阈值 8 类划分）；摸清"买的人长什么样"
params:
  required:
    - cate_first_id: 一级品类 ID（如骑行=105）
    - start_dt: 时间窗起始日期
    - end_dt: 时间窗结束日期
    - snapshot_dt: 主表快照分区
  optional:
    - time_field: create_time（下单日，默认）
notes:
  - 大表风险：dw_log_server_action_1d 是几十亿行/天的服务端日志，30 天范围扫需要 15-25 分钟
  - 建议窗口 ≤30 天；超过得显式拍板（缩窗口 / 加超时 / 用 fetch 续拉）
  - 默认本地超时 900s，大窗口建议 STARIVER_QUERY_TIMEOUT=1800
validated:
  - case: 骑行近 30 天画像
  - run_at: 2026-06-29
  - sql_result: /Users/zz/claude-output/sql_result_743254145.xlsx
  - 跑时: 约 18 分钟（30 天窗口，4 表 join + 大流量表扫描）
business_statement:
  scene_desc: 看 X 品类近 Y 天买过的人都长什么样——男女、新老客、兴趣偏好
  who: X 品类在时间窗内下过单的买家（事件级，每笔订单一条样本）
  metric_desc: 每个维度下每个分桶的订单数 + 占比
  hidden_assumptions:
    - 一个人买了多笔订单算多次（事件级）—— 如果想"每人只算一次"换 uid 级口径
    - "买过"指下过单，不论是否支付完成
    - "老客"指历史上买过该品类的人（不限时间窗口）——窗口内首次买 = 新客
    - 性别 / 兴趣分按"下单那一天"用户的状态算（不是用最新状态）
    - 兴趣分按公司算法默认阈值 0.03 划分（8 类：3C 独占 / 二奢独占 / 兴趣品类独占 / 三项全能交叉 / 等）
    - 只看转转主 App 的数据（不含小程序、找靓机）
  source:
    - hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d （订单主表）
    - hdp_zhuanzhuan_dm_global.dm_trade_visit_detail_1d （uid ↔ token 过桥）
    - hdp_zhuanzhuan_dw_global.dw_log_server_action_1d （兴趣分原始 datapool['result']）
    - hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d （性别）
*/

-- @lifecycle hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d=180
-- @lifecycle hdp_zhuanzhuan_dm_global.dm_trade_visit_detail_1d=permanent
-- @lifecycle hdp_zhuanzhuan_dw_global.dw_log_server_action_1d=permanent
-- @lifecycle hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d=permanent
-- 品类用户画像（性别 × 新老客 × 兴趣分类）模板 — 参数化版本
-- 粒度：事件级（每笔订单一条）；跨表过桥：订单 uid → 兴趣分 token 用 dm_trade_visit_detail_1d
WITH category_orders AS (
    -- 时间窗内每一笔目标品类下单（事件级）
    SELECT
        order_id,
        buyer_id AS uid,
        to_date(${time_field}) AS order_dt
    FROM hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d
    WHERE dt = '${snapshot_dt}'
    AND cate_first_id = ${cate_first_id}
    AND ${time_field} IS NOT NULL
    AND to_date(${time_field}) BETWEEN '${start_dt}' AND '${end_dt}'
),
historic_first_dt AS (
    -- 每个 buyer_id 历史首次下该品类单（不限时间，判定新老客）
    SELECT
        buyer_id AS uid,
        min(to_date(${time_field})) AS first_category_dt
    FROM hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d
    WHERE dt = '${snapshot_dt}' AND cate_first_id = ${cate_first_id} AND ${time_field} IS NOT NULL
    GROUP BY buyer_id
),
uid_token AS (
    -- 跨表过桥：uid → token（同 uid 当天多 token 取一个代表，减少笛卡尔）
    SELECT dt, uid, token FROM (
        SELECT dt, uid, token,
            ROW_NUMBER() OVER (PARTITION BY dt, uid ORDER BY token) AS rn
        FROM hdp_zhuanzhuan_dm_global.dm_trade_visit_detail_1d
        WHERE dt BETWEEN '${start_dt}' AND '${end_dt}'
        AND uid IS NOT NULL AND token IS NOT NULL
    ) t WHERE rn = 1
),
interest_score AS (
    -- 兴趣分原始 JSON 解析（取每天每个 token 最后一次）
    SELECT dt, token, s1, s2, s3
    FROM (
        SELECT
            dt, token,
            COALESCE(CAST(get_json_object(datapool['result'], '$.s1') AS DOUBLE), 0) AS s1, -- 3C
            COALESCE(CAST(get_json_object(datapool['result'], '$.s2') AS DOUBLE), 0) AS s2, -- 二奢
            COALESCE(CAST(get_json_object(datapool['result'], '$.s3') AS DOUBLE), 0) AS s3, -- 兴趣品类
            ROW_NUMBER() OVER (PARTITION BY dt, token ORDER BY `timestamp` DESC) AS rn
        FROM hdp_zhuanzhuan_dw_global.dw_log_server_action_1d
        WHERE dt BETWEEN '${start_dt}' AND '${end_dt}'
        AND token IS NOT NULL
        AND terminal IN (15, 16, 20) -- 转转 APP
        AND cmd = 'getfeedflowinfo'
        AND action = 'compute_user_layer'
        AND datapool['result'] REGEXP 's1'
        AND region = 'c'
    ) t WHERE rn = 1
),
interest_category AS (
    -- 沿用历史 SQL 的 8 类兴趣划分（阈值 0.03）
    SELECT
        dt, token,
        CASE
            WHEN s1 >= 0.03 AND s2 < 0.03 AND s3 < 0.03 THEN '3C独占用户'
            WHEN s2 >= 0.03 AND s1 < 0.03 AND s3 < 0.03 THEN '二奢独占用户'
            WHEN s3 >= 0.03 AND s1 < 0.03 AND s2 < 0.03 THEN '兴趣品类独占用户'
            WHEN s1 >= 0.03 AND s2 >= 0.03 AND s3 >= 0.03 THEN '三项全能交叉用户'
            WHEN s1 >= 0.03 AND s2 >= 0.03 AND s3 < 0.03 THEN '3C与二奢交叉用户'
            WHEN s1 >= 0.03 AND s3 >= 0.03 AND s2 < 0.03 THEN '3C与兴趣品类交叉用户'
            WHEN s2 >= 0.03 AND s3 >= 0.03 AND s1 < 0.03 THEN '二奢与兴趣品类交叉用户'
            ELSE '无明显兴趣分用户'
        END AS user_category
    FROM interest_score
),
user_gender AS (
    -- 性别按 token + 当天最新一条
    SELECT dt, token, gender FROM (
        SELECT dt, token, gender,
            ROW_NUMBER() OVER (PARTITION BY dt, token ORDER BY active_date DESC) AS rn
        FROM hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d
        WHERE dt BETWEEN '${start_dt}' AND '${end_dt}'
        AND uid IS NOT NULL AND terminal_name = '转转APP'
    ) t WHERE rn = 1
),
event_with_profile AS (
    -- 主结果：每笔订单事件关联当天 token → 兴趣 / 性别 / 新老客
    SELECT
        c.order_id,
        c.uid,
        c.order_dt,
        CASE
            WHEN h.first_category_dt >= c.order_dt THEN '新客（历史首次买该品类）'
            ELSE '老客（历史买过该品类）'
        END AS user_type,
        nvl(g.gender, '未知') AS gender,
        nvl(ic.user_category, '未知') AS user_category
    FROM category_orders c
    LEFT JOIN historic_first_dt h ON c.uid = h.uid -- buyer_id 直接对 uid，全局通用
    LEFT JOIN uid_token ut ON c.uid = ut.uid AND c.order_dt = ut.dt
    LEFT JOIN interest_category ic ON ut.token = ic.token AND c.order_dt = ic.dt
    LEFT JOIN user_gender g ON ut.token = g.token AND c.order_dt = g.dt
)
-- 三维度纵向叠加输出
SELECT '性别' AS dim, gender AS value, count(order_id) AS cnt FROM event_with_profile GROUP BY gender
UNION ALL
SELECT '兴趣分类', user_category, count(order_id) FROM event_with_profile GROUP BY user_category
UNION ALL
SELECT '新老客', user_type, count(order_id) FROM event_with_profile GROUP BY user_type
ORDER BY dim, cnt DESC

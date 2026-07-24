/* @template
name: 品类订单来源（一级场景渠道）
scene: 任何品类的支付/下单订单按场景渠道拆分（主搜/同款推荐/CBC运营栏目等 10 类），看订单来源结构；常用于"X 来自哪"类问题
params:
  required:
    - cate_first_id: 一级品类 ID（如骑行=105）
    - start_dt: 时间窗起始日期
    - end_dt: 时间窗结束日期
    - snapshot_dt: 主表快照分区
  optional:
    - time_field: create_time（下单日，默认）/ pay_time（支付日）
validated:
  - case: 骑行 5/18 异动周渠道归因（5/11-5/17 vs 5/18-5/24）
  - run_at: 2026-06-29
  - sql_result: /Users/zz/claude-output/sql_result_743146140.xlsx
business_statement:
  scene_desc: 看 X 品类在 Y 时间段订单都来自哪些场景渠道（主搜/同款推荐/CBC运营栏目/榜单 等 10 类）
  who: X 品类的所有订单（事件级，每笔订单一条）
  metric_desc: 每个一级场景下的订单数 + 占比
  hidden_assumptions:
    - 一级场景的 10 类映射沿用历史 SQL（first_from 字段映射；详见 SQL 内 CASE WHEN）
    - 关联交易明细表的 first_from 字段拿场景，订单粒度 = c2b 寄售订单表
    - 时间字段同主表 ${time_field}（默认下单日）
  source:
    - hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d （订单来源，筛品类）
    - hdp_zhuanzhuan_dm_global.dm_trade_order_detail_1d （场景字段 first_from 来源）
*/

-- @lifecycle hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d=180
-- @lifecycle hdp_zhuanzhuan_dm_global.dm_trade_order_detail_1d=permanent
-- 品类订单来源（一级场景渠道）模板 — 参数化版本
WITH category_orders AS (
    -- 目标品类在时间窗内的所有订单（事件级）
    SELECT DISTINCT
        order_id,
        buyer_id AS uid,
        to_date(${time_field}) AS order_dt
    FROM hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d
    WHERE dt = '${snapshot_dt}'
    AND cate_first_id = ${cate_first_id} -- 目标品类
    AND ${time_field} IS NOT NULL
    AND to_date(${time_field}) BETWEEN '${start_dt}' AND '${end_dt}'
),
order_with_scene AS (
    -- 关联场景字段 first_from（来自 dm_trade_order_detail_1d）+ 10 类映射
    SELECT
        b.order_id,
        b.order_dt,
        CASE
            WHEN a.first_from = 'int_detail_same' THEN '同款推荐'
            WHEN a.first_from IN ('detailRecommend', 'b2c_detail_no_metric', 'sameParagraph') THEN '同款推荐'
            WHEN a.first_from = 'addedServicePage' THEN '增值服务'
            WHEN a.first_from = 'recommendRank' THEN '榜单'
            WHEN a.first_from IN ('search', 'recommend4Search', 'weixin_search') THEN '主搜'
            WHEN a.first_from IN ('homepage_rec', 'homepage_rec_personal', 'homepage_filter', 'homepage_rec_mix') THEN '首页推荐'
            WHEN a.first_from = 'homepage_column' THEN 'CBC运营栏目'
            WHEN a.first_from = 'MF' THEN '魔方'
            WHEN a.first_from = 'new_billionSub_64' OR a.init_from LIKE 'G100_%\\_shiyibutie\\_%' THEN '十亿补贴'
            WHEN a.init_from LIKE '2\\_%\\_0' THEN '首页金刚位'
            ELSE '其他'
        END AS scene_l1
    FROM hdp_zhuanzhuan_dm_global.dm_trade_order_detail_1d a
    JOIN category_orders b ON a.order_id = b.order_id -- order_id 直接 join，事件级粒度统一
    WHERE a.dt BETWEEN '${start_dt}' AND '${end_dt}'
)
SELECT
    scene_l1,
    count(DISTINCT order_id) AS order_cnt -- 该场景下的订单数
FROM order_with_scene
GROUP BY scene_l1
ORDER BY order_cnt DESC

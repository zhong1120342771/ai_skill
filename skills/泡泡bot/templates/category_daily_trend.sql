/* @template
name: 品类日趋势
scene: 任何品类的日订单量/GMV 趋势分析，看一段时间内日级走势
params:
  required:
    - cate_first_id: 一级品类 ID（如骑行=105，详见飞书 Hive 表导航）
    - start_dt: 时间窗起始日期（YYYY-MM-DD）
    - end_dt: 时间窗结束日期（YYYY-MM-DD）
    - snapshot_dt: 主表快照分区（YYYY-MM-DD，通常 = end_dt 或最新可用分区）
  optional:
    - time_field: create_time（下单日，默认）/ pay_time（支付日）
    - metric: order_cnt（订单数，默认）/ gmv（金额）
validated:
  - case: 骑行近 2 个月日下单量趋势（2026-04-29 ~ 2026-06-28）
  - run_at: 2026-06-29
  - sql_result: /Users/zz/claude-output/sql_result_743121959.xlsx
business_statement:
  scene_desc: 看 X 品类近 Y 天的日订单量走势，识别峰值、跌幅、周期性
  who: X 品类的所有下单买家（事件级，每笔订单一条）
  metric_desc: 日订单数（去重 order_id）
  hidden_assumptions:
    - 按"下单时间（create_time）"算，不论支付状态——如要看"已支付订单"改 time_field=pay_time
    - 一笔订单算一条，同一个人下多次算多次
    - 主表是 c2b 寄售订单全量快照，每天 dt 是当天的历史快照
  source: hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d
*/

-- @lifecycle hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d=180
-- 品类日趋势模板 — 参数化版本
SELECT
    to_date(${time_field}) AS order_dt, -- 日粒度（按 ${time_field}）
    count(DISTINCT order_id) AS order_cnt -- 订单数（去重）
FROM
    hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d
WHERE dt = '${snapshot_dt}' -- 快照分区
AND cate_first_id = ${cate_first_id} -- 目标品类
AND ${time_field} IS NOT NULL
AND to_date(${time_field}) BETWEEN '${start_dt}' AND '${end_dt}' -- 时间窗
GROUP BY to_date(${time_field})
ORDER BY order_dt

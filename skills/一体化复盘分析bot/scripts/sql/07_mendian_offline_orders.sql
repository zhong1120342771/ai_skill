-- 门店线下成交单量（小店 + pro店）
-- 来源：一体化项目相关.sql（门店线下零售宽表）
-- 用途：取门店线下成交订单明细/单量。两张表结构不同但取数字段口径一致。
-- 关键字段：outbound_date(售卖日期) / city_name(城市) / order_id(订单id)
-- 过滤口径：store_name 排除测试门店；order_type in (1,2)=门店订单+线下销售
-- 分区：两表均按 dt(yyyy-MM-dd) 分区；${dt} 替换为目标日期（复盘按周期时改成 dt between 起 and 止）

-- ========== 1. 小店线下成交单量 ==========
-- 源表：hdp_zhuanzhuan_dw_global.dw_trade_retail_offline_data_full_1d（帮卖业务，线下门店零售业务宽表；主键无，成交明细用 order_id）
select
    buyer_id                                                    as `买家uid`
  , deal_price / 100                                            as `成交价元`
  , qc_code                                                     as `质检码`
  , unix_timestamp(outbound_time, 'yyyy-MM-dd HH:mm:ss')        as `出库时间戳`
  , to_date(outbound_time)                                      as `售卖日期`
  , city_name                                                   as `城市`
  , order_id                                                    as `订单id`
from hdp_zhuanzhuan_dw_global.dw_trade_retail_offline_data_full_1d
where dt = '${dt}'
  and store_name not like '%测试%'
  and order_type in (1, 2)
;

-- ========== 2. pro店线下成交单量 ==========
-- 源表：hdp_ubu_zhuanzhuan_dw_c2b.dw_trade_sale_store_pro_retail_offline_data_full_1d（门店Pro店零售订单数据，主键 order_id）
select
    buyer_id                                                    as `买家uid`
  , deal_price / 100                                            as `成交价元`
  , qc_code                                                     as `质检码`
  , unix_timestamp(outbound_time, 'yyyy-MM-dd HH:mm:ss')        as `出库时间戳`
  , to_date(outbound_time)                                      as `售卖日期`
  , city_name                                                   as `城市`
  , order_id                                                    as `订单id`
from hdp_ubu_zhuanzhuan_dw_c2b.dw_trade_sale_store_pro_retail_offline_data_full_1d
where dt = '${dt}'
  and store_name not like '%测试%'
  and order_type in (1, 2)
;

-- ========== 门店线下成交单量（小店+pro 合并按城市/日期汇总）示例 ==========
-- 复盘常用：按 售卖日期 + 城市 聚合单量（count distinct order_id）
-- select 售卖日期, 城市, count(distinct order_id) 门店线下单量 from (
--   <上面两段 union all，字段对齐>
-- ) t group by 售卖日期, 城市;

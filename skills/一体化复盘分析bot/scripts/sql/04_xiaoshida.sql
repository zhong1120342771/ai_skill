-- 小时达订单
-- 源表：hdp_zhuanzhuan_dw_global.dws_yth_core_xsd_layer01_zmt_v1_di
-- 用途：算「小时达订单量(jzf_pv)」
-- 时间范围：2026-01-01 起
select
    dt
  , city          as `城市`
  , abgroup       as `仓店类型`
  , sum(jzf_pv)   as `小时达订单量`
from hdp_zhuanzhuan_dw_global.dws_yth_core_xsd_layer01_zmt_v1_di a
where dt >= '2026-01-01'
group by 1, 2, 3
;

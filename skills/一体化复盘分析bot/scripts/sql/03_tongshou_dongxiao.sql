-- 同售动销_一体化
-- 源表：hdp_zhuanzhuan_dw_global.dws_yth_ts_kc_ord_zmt_di
-- 实测字段：city, type_md, kc_all, kc_ts, pay_pv, dt
-- 门店类型：仅取 '小店' 和 'pro店'
-- 用途：算「同售订单量(pay_pv)」、「同售动销率 = pay_pv / kc_ts」（kc_ts = 同售库存）
-- 时间范围：2025-01-01 起（与飞书原文保持一致）
select
    dt
  , city           as `城市`
  , type_md        as `门店类型`
  , sum(kc_ts)     as `同售库存`
  , sum(pay_pv)    as `同售单量`
from hdp_zhuanzhuan_dw_global.dws_yth_ts_kc_ord_zmt_di
where dt >= '2025-01-01'
  and type_md in ('小店', 'pro店')
group by 1, 2, 3
;

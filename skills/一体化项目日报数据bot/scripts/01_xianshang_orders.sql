-- 线上订单 by 城市
-- 源表：hdp_zhuanzhuan_tmp_global.dws_yth_core_xianshang_layer01_zmt_v1_di
--       (飞书原文里 schema 写作 dbzz_zeye_offline_global，但目标库注释为 hdp_zhuanzhuan_tmp_global，以后者为准)
-- 用途：算「同城订单量」、「同城订单占比 = 本地订单量/总订单量」
-- 时间范围：2026-01-01 起
select
    cast(dt as date) as `日期`
  , city            as `城市`
  , sum(ct)                                          as `总订单量`
  , sum(case when if_bd = 1 then ct else 0 end)      as `本地订单量`
from hdp_zhuanzhuan_tmp_global.dws_yth_core_xianshang_layer01_zmt_v1_di
where dt >= '2026-01-01'
group by 1, 2
;

-- 一体化线索量 — 包含「线下线索」和「线索转化总量」原始明细
-- 源表 1：hdp_zhuanzhuan_dw_global.dws_yth_xs01_yykj_zmt_v1_di（预约看件类）
-- 源表 2：hdp_zhuanzhuan_dw_global.dws_yth_xs02_mdkh_zmt_v1_di（门店看货类）
-- 用途：算「线下线索量」、「线索转化总量（pay_uv 汇总）」
-- 时间范围：2026-01-01 起
-- 注意：飞书原文用的是 sum(xs_uv)/count(distinct dt) 即「日均线索量」，本日报需要的是按日明细，去掉除以 dt
select
    dt          as `日期`
  , 'yykj'      as `来源表`
  , tag         as `线索类型`
  , sum(xs_uv)  as `线索uv`
  , sum(pay_uv) as `支付uv`
from hdp_zhuanzhuan_dw_global.dws_yth_xs01_yykj_zmt_v1_di
where dt >= '2026-01-01'
group by 1, 2, 3
union all
select
    dt          as `日期`
  , 'mdkh'      as `来源表`
  , tag         as `线索类型`
  , sum(xs_uv)  as `线索uv`
  , sum(pay_uv) as `支付uv`
from hdp_zhuanzhuan_dw_global.dws_yth_xs02_mdkh_zmt_v1_di
where dt >= '2026-01-01'
group by 1, 2, 3
;

-- 同售动销_城市拆解（对照城市 / 一体化覆盖城市（小店） / 其他城市）
-- 源表：hdp_zhuanzhuan_dw_global.dws_yth_ts_kc_ord_zmt_di
-- 用途：把小店的同售库存 / 同售单量，按城市拆三档
--       对照城市（重庆&西安）= 重庆市、西安市
--       一体化覆盖城市（小店）= 郑州市、成都市
--       其他城市 = 其余全部
-- 门店类型：仅取 '小店'
-- 时间范围：2025-01-01 起（与 03_tongshou_dongxiao 保持一致）
-- 口径：字段统一用 kc_ts / pay_pv，与 03_tongshou_dongxiao 主口径对齐，
--       保证「小店城市拆解三档之和」= 报告主口径里的小店同售数，不会对不上账。
select
    dt
  , case
      when city in ('重庆市', '西安市') then '对照城市（重庆&西安）'
      when city in ('郑州市', '成都市') then '一体化覆盖城市（小店）'
      else '其他城市'
    end            as `是否一体化城市`
  , type_md        as `门店类型`
  , sum(kc_ts)     as `同售库存`
  , sum(pay_pv)    as `同售单量`
from hdp_zhuanzhuan_dw_global.dws_yth_ts_kc_ord_zmt_di
where dt >= '2025-01-01'
  and type_md in ('小店')
group by 1, 2, 3
;

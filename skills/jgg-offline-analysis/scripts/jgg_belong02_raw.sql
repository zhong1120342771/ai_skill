-- 九宫格下线影响分析 - 原始数据 SQL
-- 数据源: 星河 Xinghe / hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_belong02_v2_di
-- 引擎: SparkSQL (sql_engine=2)
-- 业务背景: xcx-九宫格 渠道于 2026-06-10 下线，需评估对小程序大盘的影响
-- 时间窗: 2025-05 ~ 2025-06 (同期对照组) + 2026-05 ~ 2026-06 (实际下线期)
-- 维度:
--   tag_01: 拆分端
--   wd: 子端 (转转小程序 / xcx-九宫格 / 转转APP / 找靓机)
--     - "小程序大盘" = 转转小程序 + xcx-九宫格
--     - "非九宫格小程序" = 转转小程序
-- 指标:
--   exp_pv/uv, detail_pv/uv, order_pv/uv, pay_pv, uv_all (dau),
--   dau_pay_rate (净支付转化率 = pay_pv/uv_all),
--   dau_sx_rate (商详渗透率 = detail_uv/uv_all),
--   sx_pay_rate (商详转化率 = order_uv/detail_uv 或类似口径，以原表为准)
-- 分区: dt (yyyy-MM-dd)

select
    *
from
    hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_belong02_v2_di
where
    substring(dt, 1, 7) in ('2026-05', '2026-06', '2025-06', '2025-05')
    and dt >= '2025-01-01'
    and tag_01 = '拆分端';

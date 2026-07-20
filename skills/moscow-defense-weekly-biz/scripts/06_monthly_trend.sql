-- 06 月度核心指标趋势（25 vs 26 同比对照）
-- 输出文件：06_monthly_trend.csv
-- 取数范围：dt >= 2025-01-01（覆盖 2025 全年 + 2026 至今）
-- 月口径：substring(dt, 1, 7) AS 月份
--
-- 【同比日期对齐】26 年最新月（当前进行中的月）通常只有部分天（如截止 07-19 只有 19 天），
-- 为与 25 年同月做同窗口同比，把 25 年同月也裁到相同的「日」窗口：
--   仅保留 dt 的「日」<= ${ALIGN_DAY}（= week_end 的日，如 2026-07-19 → 19）的那些天，
--   且只对「25 年最新月」这一个月生效（月份 = ${ALIGN_MONTH_25}，如 2025-07）。
-- 历史整月（1~6 月及更早）不受影响，仍按整月聚合。
-- 参数由取数 agent 用 week_end 替换：
--   ${ALIGN_DAY}       = week_end 的日（两位，如 19）
--   ${ALIGN_MONTH_25}  = '2025-' + week_end 的月（如 '2025-07'）

select
    tag_01
    ,wd
    ,substring(dt, 1, 7) AS `月份`
    ,count(distinct dt) as `天数`
    ,avg(uv_all) as `dau_日均`
    ,avg(pay_pv) as `单量`
    ,avg(detail_uv) as `商详uv`
    ,avg(exp_uv) as `曝光uv`
    ,concat(round(avg(pay_pv)/avg(uv_all)*100,3),'%')  as `dau-净支付pv转化率`
    ,concat(round(avg(pay_pv)/avg(detail_uv)*100,2),'%')  as `商详转化率`
    ,concat(round(avg(detail_uv)/avg(uv_all)*100,2),'%')  as `商详渗透率`
    ,concat(round(avg(exp_uv)/avg(uv_all)*100,2),'%')  as `曝光渗透率`
    ,concat(round(avg(detail_uv)/avg(exp_uv)*100,2),'%')  as `商详到达率`
    ,concat(round(avg(order_uv)/avg(detail_uv)*100,2),'%')  as `下单率`
    ,concat(round(avg(pay_pv)/avg(order_uv)*100,2),'%')  as `支付率`
    ,concat(round(avg(pay_pv)/avg(exp_uv)*100,3),'%')  as `提袋率`
    ,round(avg(exp_pv)/avg(exp_uv)*100,2) as `人均曝光pv`
from
    hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zhibiao_zmt_v2_di
where
    dt >= '2025-01-01'
    -- 25 年最新月裁到与 26 年最新月相同的日窗口；其余月份全保留
    and not (
        substring(dt, 1, 7) = '${ALIGN_MONTH_25}'
        and cast(substring(dt, 9, 2) as int) > ${ALIGN_DAY}
    )
group by 1,2,3;

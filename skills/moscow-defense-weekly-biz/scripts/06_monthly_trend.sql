-- 06 月度核心指标趋势（25 vs 26 同比对照）
-- 输出文件：06_monthly_trend.csv
-- 取数范围：dt >= 2025-01-01（覆盖 2025 全年 + 2026 至今）
-- 月口径：substring(dt, 1, 7) AS 月份

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
group by 1,2,3;

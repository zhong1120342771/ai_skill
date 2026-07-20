-- 05 过去 8 周核心指标变化趋势（按周）
-- 输出文件：05_trend.csv
-- 取数范围：dt >= ${outFileSuffix} - 55 天（约 8 周）
-- 周口径：周一为 week_start，周日为 week_end（pmod(datediff(dt,'1970-01-05'),7)）

select
    tag_01
    ,wd
    ,date_sub(dt, pmod(datediff(dt, '1970-01-05'), 7)) AS week_start
    ,date_add(date_sub(dt, pmod(datediff(dt, '1970-01-05'), 7)), 6) AS week_end
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
    hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di
where
    dt >= date_sub('${outFileSuffix}', 55)
group by 1,2,3,4;

-- 02 核心指标分日数据（质检交叉验证用）
-- 输出文件：02_daily.csv
-- 时间范围：dt in [date_sub('${outFileSuffix}',70), '${outFileSuffix}']  覆盖本月完整 + 上月，供 Step3 校验月均与分日加和一致
-- 硬规则：必须有上界 dt <= '${outFileSuffix}'（本月末日），否则会捞进下一月初分区造成穿月
-- ${outFileSuffix} 渲染为 month_end（本月最后一天，如 2026-06-30）
-- 与周报 07_daily 同结构，仅收紧时间窗到月度校验所需范围

    select
    tag_01 as `维度`
    ,wd as `变量值`
    ,dt  as `日期`
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
    dt >= date_sub('${outFileSuffix}', 70)
    and dt <= '${outFileSuffix}'
    group by 1,2,3;

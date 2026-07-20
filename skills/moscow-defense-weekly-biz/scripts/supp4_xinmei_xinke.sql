-- 补充4：新客新媒关注数据
-- 数据源：hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di
-- 按周聚合新客/新媒用户（手机 + 2_5类目）的 DAU净支付转化率/曝光渗透率/人均曝光PV
-- tag_01: 交叉-品类_新老用户 / 交叉-品类_新媒vs自然
-- 时间范围：dt >= date_sub('${outFileSuffix}', 55)

    select
    tag_01 as `一级标签`
    ,wd as `二级标签`
    ,date_add(date_sub(dt, pmod(datediff(dt, '1970-01-05'), 7)), 6) AS `周(结束日)` -- 周结束（周日）
    ,concat(round(avg(pay_pv)/avg(uv_all)*100,3),'%')  as `dau-净支付pv转化率`
    ,concat(round(avg(exp_uv)/avg(uv_all)*100,2),'%')  as `曝光渗透率`
    ,round(avg(exp_pv)/avg(exp_uv),2) as `人均曝光pv`
    from
    hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di
    where
    dt>=date_sub('${outFileSuffix}',55)
    and tag_01 in ('交叉-品类_新老用户','交叉-品类_新媒vs自然')
    and (wd like '%新媒%' or wd like '%新客%')
    and (wd like '%2_5类目%' or wd like '%手机%')
    group by 1,2,3
    order by `一级标签`, `二级标签`,  `周(结束日)` desc
    limit 10000;

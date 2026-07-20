-- 补充2：商详商列升级
-- 数据源：hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di
-- 按周聚合品类（1-手机 / 2_5类目）+ 整体的商详转化率/商详渗透率/曝光渗透率/提袋率
-- 时间范围：dt >= date_sub('${outFileSuffix}', 55)

    (select
    tag_01
    ,wd as `分类`
    ,date_add(date_sub(dt, pmod(datediff(dt, '1970-01-05'), 7)), 6) AS `周（结束日）` -- 周结束（周日）
    ,concat(round(avg(pay_pv)/avg(detail_uv)*100,2),'%')  as `商详转化率`
    ,concat(round(avg(detail_uv)/avg(uv_all)*100,2),'%')  as `商详渗透率`
    ,concat(round(avg(exp_uv)/avg(uv_all)*100,2),'%')  as `曝光渗透率`
    ,concat(round(avg(pay_pv)/avg(exp_uv)*100,3),'%')  as `提袋率`
    from
    hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di
    where
    dt>=date_sub('${outFileSuffix}',55)
    and tag_01='拆分品类'
    and wd in ('1-手机','2_5类目')
    group by 1,2,3
    order by tag_01,`分类`, `周（结束日）` desc
    limit 10000
    )
    union all
    (
    select
    tag_01
    ,wd as `分类`
    ,date_add(date_sub(dt, pmod(datediff(dt, '1970-01-05'), 7)), 6) AS `周（结束日）` -- 周结束（周日）
    ,concat(round(avg(pay_pv)/avg(detail_uv)*100,2),'%')  as `商详转化率`
    ,concat(round(avg(detail_uv)/avg(uv_all)*100,2),'%')  as `商详渗透率`
    ,concat(round(avg(exp_uv)/avg(uv_all)*100,2),'%')  as `曝光渗透率`
    ,concat(round(avg(pay_pv)/avg(exp_uv)*100,3),'%')  as `提袋率`
    from
    hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di
    where
    dt>=date_sub('${outFileSuffix}',55)
    and tag_01='整体'
    group by 1,2,3
    order by tag_01,`分类`, `周（结束日）` desc
    limit 10000
    );

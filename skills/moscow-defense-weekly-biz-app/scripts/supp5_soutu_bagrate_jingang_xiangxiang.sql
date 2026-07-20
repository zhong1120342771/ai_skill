-- ============================================================
-- supp5_soutu_bagrate_jingang_xiangxiang.sql
-- 用途：搜推场景提袋率 — 金刚位 & 商详同款推荐 分周数据
-- 数据：dws_msk_zmt_app_v2_di（拆分场景）
-- 周口径：周日为 week_end（date_add(date_sub(dt, pmod(datediff(dt,'1970-01-05'),7)), 6)）
-- 取数范围：dt>=date_sub('${outFileSuffix}', 55) ≈ 8 周
-- 注意：搜索提袋率不在此口径里，搜索从飞书 wiki 表（spreadsheet WrB7sjN0VhvIgjttMn2cHuALnlf）单独读取
-- ============================================================
select
    tag_01
    ,wd
    ,date_add(date_sub(dt, pmod(datediff(dt, '1970-01-05'), 7)), 6) AS week_end
    ,concat(round(avg(pay_pv)/avg(exp_uv)*100,3),'%')  as `提袋率`
from
    hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di
where
    dt>=date_sub('${outFileSuffix}',55)
    and tag_01='拆分场景'
    and wd in ('首页金刚位','商详同款推荐')
group by 1,2,3;

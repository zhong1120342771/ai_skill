-- 08 苹果系列转化漏斗（整体 + 分品类），口径对齐大盘（含 DAU 分母）
-- 输出文件：08_apple_funnel.csv
-- 数据源：raw 漏斗明细表（曝光/商详/下单/支付）join 苹果商品池(brand_id=10530)，DAU 取大盘整体聚合表
--   · 苹果 = dw_mysql_info_full_1d 中 brand_id=10530（品牌名『苹果』唯一 id，实测 2026-08-09）
--   · 分品类：手机(cate_first_id=101)/平板(119)/笔记本(cate_third_id=1100000016)/智能手表(1100000170)/耳机(1100000186,1100000325)
--   · 整体 = 上述 5 品类之和（『其他』苹果配件类不计入，保证分品类之和=整体）
-- 口径说明（重要）：
--   · 本表『支付PV』= 支付明细表归因支付订单数，属漏斗归因口径，非大盘净支付ETL口径，两者可能差几个百分点，仅供漏斗结构参考
--   · UV = 每日 count(distinct token) 后按 7 天求日均（对齐大盘 avg 口径）
--   · DAU 为大盘整体（非苹果专属），渗透率 = 苹果节点UV / 大盘DAU，衡量苹果在全站用户中的渗透
-- 参数占位（渲染时全局替换）：
--   · ${outFileSuffix}    = week_end (YYYY-MM-DD)
--   · ${TERMINAL_FILTER}  = 全三端为空串；仅app为 " and terminal in ('15','16') "（terminal 15=安卓 16=iOS）
--   · ${DAU_TABLE}        = 全三端 hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zhibiao_zmt_v2_di
--                           仅app  hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di
-- 周口径：本周 dt in [week_end-6, week_end]；上周 dt in [week_end-13, week_end-7]

with apple_info as (
    select info_id
        ,case when cate_first_id in (101) then '手机'
              when cate_first_id in (119) then '平板'
              when cate_third_id in (1100000016) then '笔记本'
              when cate_third_id in (1100000170) then '智能手表'
              when cate_third_id in (1100000186,1100000325) then '耳机'
         end as `品类`
    from hdp_zhuanzhuan_dw_global.dw_mysql_info_full_1d
    where dt='${outFileSuffix}'
      and brand_id=10530
      and (cate_first_id in (101,119) or cate_third_id in (1100000016,1100000170,1100000186,1100000325))
    group by info_id
        ,case when cate_first_id in (101) then '手机'
              when cate_first_id in (119) then '平板'
              when cate_third_id in (1100000016) then '笔记本'
              when cate_third_id in (1100000170) then '智能手表'
              when cate_third_id in (1100000186,1100000325) then '耳机'
         end
)
-- 每日曝光UV（品类行 + 苹果整体行；整体=跨品类去重 distinct token）
--   曝光/商详明细自带 brand_id+cate，直接 WHERE brand_id=10530 过滤，免去与全量商品表的巨型 join
,exp_daily as (
    select e.dt
        ,case when grouping(e.`品类`)=1 then '苹果整体' else e.`品类` end as `品类`
        ,count(distinct e.token) as uv
    from (
        select dt, token
            ,case when cate_first_id in (101) then '手机'
                  when cate_first_id in (119) then '平板'
                  when cate_third_id in (1100000016) then '笔记本'
                  when cate_third_id in (1100000170) then '智能手表'
                  when cate_third_id in (1100000186,1100000325) then '耳机' end as `品类`
        from hdp_zhuanzhuan_dm_global.dm_trade_exposure_info_detail_inc_1d
        where dt>=date_sub('${outFileSuffix}',13) and dt<='${outFileSuffix}'
          and brand_id=10530
          and (cate_first_id in (101,119) or cate_third_id in (1100000016,1100000170,1100000186,1100000325))
          ${TERMINAL_FILTER}
    ) e
    group by e.dt, e.`品类` grouping sets ((e.dt, e.`品类`), (e.dt))
)
-- 每日商详UV
,det_daily as (
    select v.dt
        ,case when grouping(v.`品类`)=1 then '苹果整体' else v.`品类` end as `品类`
        ,count(distinct v.token) as uv
    from (
        select dt, token
            ,case when cate_first_id in (101) then '手机'
                  when cate_first_id in (119) then '平板'
                  when cate_third_id in (1100000016) then '笔记本'
                  when cate_third_id in (1100000170) then '智能手表'
                  when cate_third_id in (1100000186,1100000325) then '耳机' end as `品类`
        from hdp_zhuanzhuan_dm_global.dm_trade_visit_detail_1d
        where dt>=date_sub('${outFileSuffix}',13) and dt<='${outFileSuffix}'
          and brand_id=10530
          and (cate_first_id in (101,119) or cate_third_id in (1100000016,1100000170,1100000186,1100000325))
          ${TERMINAL_FILTER}
    ) v
    group by v.dt, v.`品类` grouping sets ((v.dt, v.`品类`), (v.dt))
)
-- 每日下单UV
,ord_daily as (
    select o.dt
        ,case when grouping(i.`品类`)=1 then '苹果整体' else i.`品类` end as `品类`
        ,count(distinct o.token) as uv
    from hdp_zhuanzhuan_dm_global.dm_trade_order_detail_1d o
    join apple_info i on o.info_id=i.info_id
    where o.dt>=date_sub('${outFileSuffix}',13) and o.dt<='${outFileSuffix}' ${TERMINAL_FILTER}
    group by o.dt, i.`品类` grouping sets ((o.dt, i.`品类`), (o.dt))
)
-- 每日支付PV（支付订单数；整体=跨品类去重 distinct order_id）
,pay_daily as (
    select p.dt
        ,case when grouping(i.`品类`)=1 then '苹果整体' else i.`品类` end as `品类`
        ,count(distinct p.order_id) as pv
    from hdp_zhuanzhuan_dm_global.dm_trade_pay_detail_1d p
    join apple_info i on p.info_id=i.info_id
    where p.dt>=date_sub('${outFileSuffix}',13) and p.dt<='${outFileSuffix}' ${TERMINAL_FILTER}
    group by p.dt, i.`品类` grouping sets ((p.dt, i.`品类`), (p.dt))
)
-- 大盘DAU日均（本周/上周）
,dau_wk as (
    select
        sum(case when dt>=date_sub('${outFileSuffix}',6) then uv_all else 0 end)/7.0 as dau_cur
        ,sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then uv_all else 0 end)/7.0 as dau_pre
    from ${DAU_TABLE}
    where dt>=date_sub('${outFileSuffix}',13) and dt<='${outFileSuffix}' and tag_01='整体'
)
-- 品类维度节点日均（本周cur/上周pre）
,cat_num as (
    select coalesce(e.`品类`,d.`品类`,o.`品类`,p.`品类`) as `品类`
        ,nvl(e.cur,0) as exp_cur, nvl(e.pre,0) as exp_pre
        ,nvl(d.cur,0) as det_cur, nvl(d.pre,0) as det_pre
        ,nvl(o.cur,0) as ord_cur, nvl(o.pre,0) as ord_pre
        ,nvl(p.cur,0) as pay_cur, nvl(p.pre,0) as pay_pre
    from (select `品类`,sum(case when dt>=date_sub('${outFileSuffix}',6) then uv else 0 end)/7.0 as cur
                ,sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then uv else 0 end)/7.0 as pre
          from exp_daily group by `品类`) e
    full outer join (select `品类`,sum(case when dt>=date_sub('${outFileSuffix}',6) then uv else 0 end)/7.0 as cur
                ,sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then uv else 0 end)/7.0 as pre
          from det_daily group by `品类`) d on e.`品类`=d.`品类`
    full outer join (select `品类`,sum(case when dt>=date_sub('${outFileSuffix}',6) then uv else 0 end)/7.0 as cur
                ,sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then uv else 0 end)/7.0 as pre
          from ord_daily group by `品类`) o on coalesce(e.`品类`,d.`品类`)=o.`品类`
    full outer join (select `品类`,sum(case when dt>=date_sub('${outFileSuffix}',6) then pv else 0 end)/7.0 as cur
                ,sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then pv else 0 end)/7.0 as pre
          from pay_daily group by `品类`) p on coalesce(e.`品类`,d.`品类`,o.`品类`)=p.`品类`
)
-- 排序键（整体置顶，其余按品类固定序），整体行已由 grouping sets 去重得出，不再加和
,num_all as (
    select case `品类` when '苹果整体' then 0 when '手机' then 1 when '平板' then 2
                       when '笔记本' then 3 when '智能手表' then 4 when '耳机' then 5 else 9 end as ord_key
        ,`品类` as `维度`
        ,exp_cur, exp_pre, det_cur, det_pre, ord_cur, ord_pre, pay_cur, pay_pre
    from cat_num
)
select
    n.`维度`
    ,'苹果' as `品牌`
    ,round(d.dau_cur) as `大盘DAU-周日均`
    ,round(n.exp_cur) as `曝光UV-周日均`
    ,concat(round((n.exp_cur-n.exp_pre)/n.exp_pre*100,2),'%') as `曝光UV-周环比`
    ,round(n.det_cur) as `商详UV-周日均`
    ,concat(round((n.det_cur-n.det_pre)/n.det_pre*100,2),'%') as `商详UV-周环比`
    ,round(n.ord_cur) as `下单UV-周日均`
    ,concat(round((n.ord_cur-n.ord_pre)/n.ord_pre*100,2),'%') as `下单UV-周环比`
    ,round(n.pay_cur) as `支付PV-周日均`
    ,concat(round((n.pay_cur-n.pay_pre)/n.pay_pre*100,2),'%') as `支付PV-周环比`
    ,concat(round(n.exp_cur/d.dau_cur*100,3),'%') as `曝光渗透率`
    ,concat(round((n.exp_cur/d.dau_cur-n.exp_pre/d.dau_pre)/(n.exp_pre/d.dau_pre)*100,2),'%') as `曝光渗透率-周环比`
    ,concat(round(n.det_cur/d.dau_cur*100,3),'%') as `商详渗透率`
    ,concat(round((n.det_cur/d.dau_cur-n.det_pre/d.dau_pre)/(n.det_pre/d.dau_pre)*100,2),'%') as `商详渗透率-周环比`
    ,concat(round(n.det_cur/n.exp_cur*100,2),'%') as `商详到达率`
    ,concat(round((n.det_cur/n.exp_cur-n.det_pre/n.exp_pre)/(n.det_pre/n.exp_pre)*100,2),'%') as `商详到达率-周环比`
    ,concat(round(n.pay_cur/n.det_cur*100,2),'%') as `商详转化率`
    ,concat(round((n.pay_cur/n.det_cur-n.pay_pre/n.det_pre)/(n.pay_pre/n.det_pre)*100,2),'%') as `商详转化率-周环比`
    ,concat(round(n.ord_cur/n.det_cur*100,2),'%') as `下单率`
    ,concat(round((n.ord_cur/n.det_cur-n.ord_pre/n.det_pre)/(n.ord_pre/n.det_pre)*100,2),'%') as `下单率-周环比`
    ,concat(round(n.pay_cur/n.ord_cur*100,2),'%') as `支付率`
    ,concat(round((n.pay_cur/n.ord_cur-n.pay_pre/n.ord_pre)/(n.pay_pre/n.ord_pre)*100,2),'%') as `支付率-周环比`
    ,concat(round(n.pay_cur/n.exp_cur*100,3),'%') as `提袋率`
    ,concat(round((n.pay_cur/n.exp_cur-n.pay_pre/n.exp_pre)/(n.pay_pre/n.exp_pre)*100,2),'%') as `提袋率-周环比`
    ,concat(round(n.pay_cur/d.dau_cur*100,3),'%') as `dau-净支付pv转化率`
    ,concat(round((n.pay_cur/d.dau_cur-n.pay_pre/d.dau_pre)/(n.pay_pre/d.dau_pre)*100,2),'%') as `dau-净支付pv转化率-周环比`
    ,'${outFileSuffix}' as `数据更新日期`
from num_all n
cross join dau_wk d
order by n.ord_key;

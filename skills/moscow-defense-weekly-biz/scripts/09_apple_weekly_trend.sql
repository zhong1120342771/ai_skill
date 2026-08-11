-- 09 苹果系列 过去 8 周核心指标趋势（整体 + 分品类，按周；含去年同期对比）
-- 输出文件：09_apple_trend.csv（长表：每行 = 一个品类 × 一周 × 年份）
-- 数据源：与 08 同源，raw 漏斗明细（曝光/商详/下单/支付）join 苹果商品池(brand_id=10530)，DAU 取大盘整体聚合表
--   · 苹果 = dw_mysql_info_full_1d 中 brand_id=10530
--   · 分品类：手机(cate_first_id=101)/平板(119)/笔记本(cate_third_id=1100000016)/智能手表(1100000170)/耳机(1100000186,1100000325)
--   · 苹果整体 = 跨品类 distinct token 去重（grouping sets），非 5 品类加和
-- 周口径：与 05_weekly_trend 一致，week_start = 周一，week_end = 周日
--   week_key = date_sub(dt, pmod(datediff(dt,'1970-01-05'),7))
-- UV 口径：每日 count(distinct token)，再按该周有数天数求日均（对齐大盘 avg 口径）
-- 去年同期：今年窗口整体回退 364 天（=52 周，保证周一对齐周一）；`对齐周结束`把去年周映射到今年日历以便虚线叠加
-- 12 指标：dau-净支付pv转化率 / 曝光UV / 商详UV / 下单UV / 支付PV / 提袋率(=支付PV/曝光UV)
--          / 曝光渗透率 / 商详渗透率 / 商详到达率 / 商详转化率 / 下单率 / 支付率
-- 参数占位（渲染时全局替换，与 08 相同机制）：
--   · ${outFileSuffix}   = week_end (YYYY-MM-DD)
--   · ${TERMINAL_FILTER} = 全三端为空串；仅app为 " and terminal in ('15','16') "
--   · ${DAU_TABLE}       = 全三端 tmp_dws_msk_zhibiao_zmt_v2_di / 仅app tmp_dws_msk_zmt_app_v2_di
-- 取数范围：本年 dt∈[week_end-55, week_end]；去年 dt∈[week_end-419, week_end-364]

with apple_info as (
    -- 苹果商品池：今年+去年两个快照并集，按 info_id 去重（分品类映射两年一致，取其一）
    select info_id, max(`品类`) as `品类`
    from (
        select info_id
            ,case when cate_first_id in (101) then '手机'
                  when cate_first_id in (119) then '平板'
                  when cate_third_id in (1100000016) then '笔记本'
                  when cate_third_id in (1100000170) then '智能手表'
                  when cate_third_id in (1100000186,1100000325) then '耳机'
             end as `品类`
        from hdp_zhuanzhuan_dw_global.dw_mysql_info_full_1d
        where dt in ('${outFileSuffix}', date_sub('${outFileSuffix}',364))
          and brand_id=10530
          and (cate_first_id in (101,119) or cate_third_id in (1100000016,1100000170,1100000186,1100000325))
    ) s
    group by info_id
)
-- 每日曝光UV（品类行 + 苹果整体行；整体=跨品类去重 distinct token）
,exp_daily as (
    select e.dt
        ,date_sub(e.dt, pmod(datediff(e.dt,'1970-01-05'),7)) as week_key
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
        where ((dt>=date_sub('${outFileSuffix}',55) and dt<='${outFileSuffix}')
            or (dt>=date_sub('${outFileSuffix}',419) and dt<=date_sub('${outFileSuffix}',364)))
          and brand_id=10530
          and (cate_first_id in (101,119) or cate_third_id in (1100000016,1100000170,1100000186,1100000325))
          ${TERMINAL_FILTER}
    ) e
    group by e.dt, date_sub(e.dt, pmod(datediff(e.dt,'1970-01-05'),7)), e.`品类`
        grouping sets ((e.dt, date_sub(e.dt, pmod(datediff(e.dt,'1970-01-05'),7)), e.`品类`)
                      ,(e.dt, date_sub(e.dt, pmod(datediff(e.dt,'1970-01-05'),7))))
)
-- 每日商详UV
,det_daily as (
    select v.dt
        ,date_sub(v.dt, pmod(datediff(v.dt,'1970-01-05'),7)) as week_key
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
        where ((dt>=date_sub('${outFileSuffix}',55) and dt<='${outFileSuffix}')
            or (dt>=date_sub('${outFileSuffix}',419) and dt<=date_sub('${outFileSuffix}',364)))
          and brand_id=10530
          and (cate_first_id in (101,119) or cate_third_id in (1100000016,1100000170,1100000186,1100000325))
          ${TERMINAL_FILTER}
    ) v
    group by v.dt, date_sub(v.dt, pmod(datediff(v.dt,'1970-01-05'),7)), v.`品类`
        grouping sets ((v.dt, date_sub(v.dt, pmod(datediff(v.dt,'1970-01-05'),7)), v.`品类`)
                      ,(v.dt, date_sub(v.dt, pmod(datediff(v.dt,'1970-01-05'),7))))
)
-- 每日下单UV
,ord_daily as (
    select o.dt
        ,date_sub(o.dt, pmod(datediff(o.dt,'1970-01-05'),7)) as week_key
        ,case when grouping(i.`品类`)=1 then '苹果整体' else i.`品类` end as `品类`
        ,count(distinct o.token) as uv
    from hdp_zhuanzhuan_dm_global.dm_trade_order_detail_1d o
    join apple_info i on o.info_id=i.info_id
    where ((o.dt>=date_sub('${outFileSuffix}',55) and o.dt<='${outFileSuffix}')
        or (o.dt>=date_sub('${outFileSuffix}',419) and o.dt<=date_sub('${outFileSuffix}',364))) ${TERMINAL_FILTER}
    group by o.dt, date_sub(o.dt, pmod(datediff(o.dt,'1970-01-05'),7)), i.`品类`
        grouping sets ((o.dt, date_sub(o.dt, pmod(datediff(o.dt,'1970-01-05'),7)), i.`品类`)
                      ,(o.dt, date_sub(o.dt, pmod(datediff(o.dt,'1970-01-05'),7))))
)
-- 每日支付PV（支付订单数；整体=跨品类去重 distinct order_id）
,pay_daily as (
    select p.dt
        ,date_sub(p.dt, pmod(datediff(p.dt,'1970-01-05'),7)) as week_key
        ,case when grouping(i.`品类`)=1 then '苹果整体' else i.`品类` end as `品类`
        ,count(distinct p.order_id) as pv
    from hdp_zhuanzhuan_dm_global.dm_trade_pay_detail_1d p
    join apple_info i on p.info_id=i.info_id
    where ((p.dt>=date_sub('${outFileSuffix}',55) and p.dt<='${outFileSuffix}')
        or (p.dt>=date_sub('${outFileSuffix}',419) and p.dt<=date_sub('${outFileSuffix}',364))) ${TERMINAL_FILTER}
    group by p.dt, date_sub(p.dt, pmod(datediff(p.dt,'1970-01-05'),7)), i.`品类`
        grouping sets ((p.dt, date_sub(p.dt, pmod(datediff(p.dt,'1970-01-05'),7)), i.`品类`)
                      ,(p.dt, date_sub(p.dt, pmod(datediff(p.dt,'1970-01-05'),7))))
)
-- 各节点按周求日均（sum(每日UV)/该周有数天数）
,exp_wk as (select week_key,`品类`,sum(uv)/count(distinct dt) as v from exp_daily group by week_key,`品类`)
,det_wk as (select week_key,`品类`,sum(uv)/count(distinct dt) as v from det_daily group by week_key,`品类`)
,ord_wk as (select week_key,`品类`,sum(uv)/count(distinct dt) as v from ord_daily group by week_key,`品类`)
,pay_wk as (select week_key,`品类`,sum(pv)/count(distinct dt) as v from pay_daily group by week_key,`品类`)
-- 大盘DAU按周日均
,dau_wk as (
    select date_sub(dt, pmod(datediff(dt,'1970-01-05'),7)) as week_key
        ,avg(uv_all) as dau
    from ${DAU_TABLE}
    where ((dt>=date_sub('${outFileSuffix}',55) and dt<='${outFileSuffix}')
        or (dt>=date_sub('${outFileSuffix}',419) and dt<=date_sub('${outFileSuffix}',364)))
      and tag_01='整体'
    group by date_sub(dt, pmod(datediff(dt,'1970-01-05'),7))
)
-- 品类 × 周 全外连接拼齐 4 个节点
,joined as (
    select coalesce(e.week_key,d.week_key,o.week_key,p.week_key) as week_key
        ,coalesce(e.`品类`,d.`品类`,o.`品类`,p.`品类`) as `品类`
        ,nvl(e.v,0) as exp_uv, nvl(d.v,0) as det_uv, nvl(o.v,0) as ord_uv, nvl(p.v,0) as pay_pv
    from exp_wk e
    full outer join det_wk d on e.week_key=d.week_key and e.`品类`=d.`品类`
    full outer join ord_wk o on coalesce(e.week_key,d.week_key)=o.week_key and coalesce(e.`品类`,d.`品类`)=o.`品类`
    full outer join pay_wk p on coalesce(e.week_key,d.week_key,o.week_key)=p.week_key and coalesce(e.`品类`,d.`品类`,o.`品类`)=p.`品类`
)
select
    j.`品类` as `维度`
    ,case when j.week_key >= date_sub('${outFileSuffix}',55) then '本年' else '去年' end as `年份`
    ,j.week_key as `week_start`
    ,date_add(j.week_key,6) as `week_end`
    -- 对齐周结束：去年周 +364 天映射到今年日历，本年周原样（供虚线叠加对齐 x 轴）
    ,case when j.week_key >= date_sub('${outFileSuffix}',55)
          then date_add(j.week_key,6)
          else date_add(j.week_key,6+364) end as `对齐周结束`
    ,round(dw.dau) as `大盘DAU-周日均`
    ,round(j.exp_uv) as `曝光UV`
    ,round(j.det_uv) as `商详UV`
    ,round(j.ord_uv) as `下单UV`
    ,round(j.pay_pv) as `支付PV`
    ,concat(round(j.pay_pv/dw.dau*100,3),'%') as `dau-净支付pv转化率`
    ,concat(round(j.pay_pv/j.exp_uv*100,2),'%') as `提袋率`
    ,concat(round(j.exp_uv/dw.dau*100,3),'%') as `曝光渗透率`
    ,concat(round(j.det_uv/dw.dau*100,3),'%') as `商详渗透率`
    ,concat(round(j.det_uv/j.exp_uv*100,2),'%') as `商详到达率`
    ,concat(round(j.pay_pv/j.det_uv*100,2),'%') as `商详转化率`
    ,concat(round(j.ord_uv/j.det_uv*100,2),'%') as `下单率`
    ,concat(round(j.pay_pv/j.ord_uv*100,2),'%') as `支付率`
from joined j
left join dau_wk dw on j.week_key=dw.week_key
where (j.week_key >= date_sub('${outFileSuffix}',55)
    or (j.week_key >= date_sub('${outFileSuffix}',419) and j.week_key <= date_sub('${outFileSuffix}',364)))
order by
    case j.`品类` when '苹果整体' then 0 when '手机' then 1 when '平板' then 2
                  when '笔记本' then 3 when '智能手表' then 4 when '耳机' then 5 else 9 end
    ,`对齐周结束`
    ,`年份`;

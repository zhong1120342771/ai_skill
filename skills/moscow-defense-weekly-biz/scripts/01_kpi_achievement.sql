--01达成率数据
        select
        a.*
        from
        (select
        substring('${outFileSuffix}',1,7) as `月份`
        ,'1-核心指标' as `口径`
        ,'1-dau-净支付转化率' as `变量`
        ,'1.26%(6月)' as `目标`
        ,concat(round(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then pay_pv else 0 end)/sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then uv_all else 0 end)*100,3),'%') as `月均值`
        ,concat(round(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then pay_pv else 0 end)/sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then uv_all else 0 end)/1.26*10000,2),'%') as `达成率`
        ,concat(round(sum(case when dt>=date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',6) then uv_all else 0 end)*100,3),'%') as `周均值`
        ,concat(round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then uv_all else 0 end)*100,3),'%') as `上周均值`
        ,concat(round((((round(sum(case when dt>=date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',6) then uv_all else 0 end),6))-(round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then uv_all else 0 end),6)))/round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then uv_all else 0 end) ,6))*100,2),'%') as `周环比`
        ,max(dt) as `数据更新日期`
        from
        hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zhibiao_zmt_v2_di
        where
        dt>='2026-05-01'
        and tag_01='整体'
        group by 1
        union all
        select
        substring('${outFileSuffix}',1,7) as `月份`
        ,'1-核心指标' as `口径`
        ,'2-dau(单位：万)' as `变量`
        ,'450w' as `目标`
        ,int(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then uv_all else 0 end)/ count(distinct case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then dt else null end)/10000) as `月均值`
        ,concat(round((sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then uv_all else 0 end)/ count(distinct case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then dt else null end)) /4500000*100),'%') as `达成率`
        ,int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then uv_all else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end)/10000)  as `周均值`
        ,int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then uv_all else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)/10000)  as  `上周均值`
        ,concat(round(((int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then uv_all else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end)/10000) -int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then uv_all else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)/10000) )/int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then uv_all else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)/10000) )*100,2),'%')  as `周环比`
        ,max(dt) as `数据更新日期`
        from
        hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zhibiao_zmt_v2_di
        where
        dt>='2026-05-01'
        and tag_01='整体'
        group by 1
        union all
        select
        substring('${outFileSuffix}',1,7) as `月份`
        ,'1-核心指标' as `口径`
        ,'3-单量' as `变量`
        ,'56674（6月）' as `目标`
        ,int(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then pay_pv else 0 end)/ count(distinct case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then dt else null end)) as `月均值`
        ,concat(round((sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then pay_pv else 0 end)/ count(distinct case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then dt else null end)) /56674*100),'%') as `达成率`
        ,int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then pay_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end))  as `周均值`
        ,int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then pay_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end))  as  `上周均值`
        ,concat(round(((int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then pay_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end)) -int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then pay_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )/int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then pay_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )*100,2),'%')  as `周环比`
        ,max(dt) as `数据更新日期`
        from
        hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zhibiao_zmt_v2_di
        where
        dt>='2026-05-01'
        and tag_01='整体'
        group by 1
        ) a
        order by `月份`,`口径`,`变量`
        limit 10000;

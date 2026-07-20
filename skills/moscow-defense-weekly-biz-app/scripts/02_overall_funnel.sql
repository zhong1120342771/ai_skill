--02 大盘漏斗数据
    select 
    a.`月份` 
    ,a.`口径` 
    ,a.`变量`  
    ,a.`月均值` as  `净支付转化率-月均值`
    ,concat(a.`周均值`,' (环比：',a.`周环比`,')')  as `净支付转化率-周均值`
    ,concat(nvl(c.`周均值`,'-'),' (环比：',nvl(c.`周环比`,'-'),')') as `dau-周均值`
    ,concat(e.`周均值`,' (环比：',e.`周环比`,')') as `曝光uv-周均值`
    ,concat(d.`周均值`,' (环比：',d.`周环比`,')')  as `商详uv-周均值`
    ,concat(t11.`周均值`,' (环比：',t11.`周环比`,')')  as `下单uv-周均值`
    ,concat(b.`周均值`,' (环比：',b.`周环比` ,')') as `净支付pv-周均值`
    ,concat(t3.`周均值`,' (环比：',t3.`周环比`,')') as `商详渗透率-周均值`
    ,concat(t2.`周均值`,' (环比：',t2.`周环比`,')') as `商详转化率-周均值`
    ,concat(t7.`周均值`,' (环比：',t7.`周环比`,')') as `提袋率-周均值`
    ,concat(t6.`周均值` ,' (环比：',t6.`周环比`,')') as  `曝光渗透率-周均值`
    ,concat(t4.`周均值` ,' (环比：',t4.`周环比`,')') as  `商详到达率-周均值`
    ,concat(t13.`周均值` ,' (环比：',t13.`周环比`,')') as  `下单率-周均值`
    ,concat(t14.`周均值` ,' (环比：',t14.`周环比`,')') as  `支付率-周均值`
    ,a.`数据更新日期`
    from   
   (select 
        substring('${outFileSuffix}',1,7) as `月份`
        ,'2-dau净支付转化率' as `口径`
        ,wd as `变量`
        ,'-' as `目标`
        ,concat(round(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then pay_pv else 0 end)/sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then uv_all else 0 end)*100,3),'%') as `月均值`
        ,'-' as `达成率` 
        ,concat(round(sum(case when dt>=date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',6) then uv_all else 0 end)*100,3),'%') as `周均值`
        ,concat(round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then uv_all else 0 end)*100,3),'%') as `上周均值`
        ,concat(round((((round(sum(case when dt>=date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',6) then uv_all else 0 end),6))-(round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then uv_all else 0 end),6)))/round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then uv_all else 0 end) ,6))*100,2),'%') as `周环比`
        ,max(dt) as `数据更新日期`
        from 
        hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
        where 
        dt>='2026-05-01' 
        and tag_01='整体'
        group by 1,2,3,4
    ) a 
    left join 
    (
        --3单量维度指标
        select 
        substring('${outFileSuffix}',1,7) as `月份`
        ,'2-净支付pv' as `口径`
        ,wd as `变量`
        ,'-' as `目标`
        ,int(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then pay_pv else 0 end)/ count(distinct case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then dt else null end)) as `月均值`
        ,'-' as `达成率` 
        ,int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then pay_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end))  as `周均值`
        ,int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then pay_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end))  as  `上周均值`
        ,concat(round(((int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then pay_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end)) -int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then pay_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )/int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then pay_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )*100,2),'%')  as `周环比`
        ,max(dt) as `数据更新日期`
        from 
        hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
        where 
        dt>='2026-05-01' 
        and tag_01='整体'
        group by 1,2,3,4
    ) b on a.`数据更新日期`=b.`数据更新日期` and split(a.`口径`,'-')[0]=split(b.`口径`,'-')[0] and a.`变量`=b.`变量` 
    left join 
    (
        --4 dau 维度指标
        select 
        substring('${outFileSuffix}',1,7) as `月份`
        ,'2-dau(流量)' as `口径`
        ,wd as `变量`
        ,'-' as `目标`
        ,int(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then uv_all else 0 end)/ count(distinct case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then dt else null end)) as `月均值`
        ,'-' as `达成率` 
        ,int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then uv_all else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end))  as `周均值`
        ,int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then uv_all else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end))  as  `上周均值`
        ,concat(round(((int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then uv_all else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end)) -int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then uv_all else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )/int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then uv_all else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )*100,2),'%')  as `周环比`
        ,max(dt) as `数据更新日期`
        from 
        hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
        where 
        dt>='2026-05-01' 
        and tag_01='整体'
        group by 1,2,3,4
    ) c on a.`数据更新日期`=c.`数据更新日期` and split(a.`口径`,'-')[0]=split(c.`口径`,'-')[0] and a.`变量`=c.`变量` 
    left join 
    (
        select 
        substring('${outFileSuffix}',1,7) as `月份`
        ,'2-商详uv' as `口径`
        ,wd as `变量`
        ,'-' as `目标`
        ,int(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then detail_uv else 0 end)/ count(distinct case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then dt else null end)) as `月均值`
        ,'-' as `达成率` 
        ,int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then detail_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end))  as `周均值`
        ,int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then detail_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end))  as  `上周均值`
        ,concat(round(((int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then detail_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end)) -int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then detail_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )/int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then detail_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )*100,2),'%')  as `周环比`
        ,max(dt) as `数据更新日期`
        from 
        hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
        where 
        dt>='2026-05-01' 
        and tag_01='整体'
        group by 1,2,3,4
    ) d on a.`数据更新日期`=d.`数据更新日期` and split(a.`口径`,'-')[0]=split(d.`口径`,'-')[0] and a.`变量`=d.`变量`  
    left join 
    (
        --3单量维度指标
            select 
            substring('${outFileSuffix}',1,7) as `月份`
            ,'2-曝光uv' as `口径`
            ,wd as `变量`
            ,'-' as `目标`
            ,int(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then exp_uv else 0 end)/ count(distinct case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then dt else null end)) as `月均值`
            ,'-' as `达成率` 
            ,int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then exp_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end))  as `周均值`
            ,int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end))  as  `上周均值`
            ,concat(round(((int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then exp_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end)) -int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )/int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )*100,2),'%')  as `周环比`
            ,max(dt) as `数据更新日期`
            from 
            hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
            where 
            dt>='2026-05-01' 
            and tag_01='整体'
            group by 1,2,3,4
       ) e on a.`数据更新日期`=e.`数据更新日期` and split(a.`口径`,'-')[0]=split(e.`口径`,'-')[0] and a.`变量`=e.`变量`  
            left join 
            (
        
            select 
            substring('${outFileSuffix}',1,7) as `月份`
            ,'2-曝光pv' as `口径`
            ,wd as `变量`
            ,'-' as `目标`
            ,int(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then exp_uv else 0 end)/ count(distinct case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then dt else null end)) as `月均值`
            ,'-' as `达成率` 
            ,int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then exp_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end))  as `周均值`
            ,int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end))  as  `上周均值`
            ,concat(round(((int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then exp_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end)) -int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )/int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )*100,2),'%')  as `周环比`
            ,max(dt) as `数据更新日期`
            from 
            hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
            where 
            dt>='2026-05-01' 
            and tag_01='整体'
            group by 1,2,3,4
            ) t1 on a.`数据更新日期`=t1.`数据更新日期` and split(a.`口径`,'-')[0]=split(t1.`口径`,'-')[0] and a.`变量`=t1.`变量` 
                left join 
                (select 
            substring('${outFileSuffix}',1,7) as `月份`
            ,'2-商详转化率' as `口径`
            ,wd as `变量`
            ,'-' as `目标`
            ,concat(round(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then pay_pv else 0 end)/sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then detail_uv else 0 end)*100,2),'%') as `月均值`
            ,'-' as `达成率` 
            ,concat(round(sum(case when dt>=date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',6) then detail_uv else 0 end)*100,2),'%') as `周均值`
            ,concat(round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then detail_uv else 0 end)*100,2),'%') as `上周均值`
            ,concat(round((((round(sum(case when dt>=date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',6) then detail_uv else 0 end),6))-(round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then detail_uv else 0 end),6)))/round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then detail_uv else 0 end) ,6))*100,2),'%') as `周环比`
            ,max(dt) as `数据更新日期`
            from 
            hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
            where 
            dt>='2026-05-01' 
            and tag_01='整体'
            group by 1,2,3,4
            ) t2 on a.`数据更新日期`=t2.`数据更新日期` and split(a.`口径`,'-')[0]=split(t2.`口径`,'-')[0] and a.`变量`=t2.`变量` 
            left join 
            (select 
            substring('${outFileSuffix}',1,7) as `月份`
            ,'2-商详渗透率' as `口径`
            ,wd as `变量`
            ,'-' as `目标`
            ,concat(round(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then detail_uv else 0 end)/sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then uv_all else 0 end)*100,2),'%') as `月均值`
            ,'-' as `达成率` 
            ,concat(round(sum(case when dt>=date_sub('${outFileSuffix}',6) then detail_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',6) then uv_all else 0 end)*100,2),'%') as `周均值`
            ,concat(round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then detail_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then uv_all else 0 end)*100,2),'%') as `上周均值`
            ,concat(round((((round(sum(case when dt>=date_sub('${outFileSuffix}',6) then detail_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',6) then uv_all else 0 end),6))-(round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then detail_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then uv_all else 0 end),6)))/round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then detail_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then uv_all else 0 end) ,6))*100,2),'%') as `周环比`
            ,max(dt) as `数据更新日期`
            from 
            hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
            where 
            dt>='2026-05-01' 
            and tag_01='整体'
            group by 1,2,3,4
            ) t3 on a.`数据更新日期`=t3.`数据更新日期` and split(a.`口径`,'-')[0]=split(t3.`口径`,'-')[0] and a.`变量`=t3.`变量` 
             left join 
            (select 
            substring('${outFileSuffix}',1,7) as `月份`
            ,'2-曝光渗透率' as `口径`
            ,wd as `变量`
            ,'-' as `目标`
            ,concat(round(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then exp_uv else 0 end)/sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then uv_all else 0 end)*100,2),'%') as `月均值`
            ,'-' as `达成率` 
            ,concat(round(sum(case when dt>=date_sub('${outFileSuffix}',6) then exp_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',6) then uv_all else 0 end)*100,2),'%') as `周均值`
            ,concat(round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then exp_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then uv_all else 0 end)*100,2),'%') as `上周均值`
            ,concat(round((((round(sum(case when dt>=date_sub('${outFileSuffix}',6) then exp_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',6) then uv_all else 0 end),6))-(round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then exp_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then uv_all else 0 end),6)))/round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then exp_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then uv_all else 0 end) ,6))*100,2),'%') as `周环比`
            ,max(dt) as `数据更新日期`
            from 
            hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
            where 
            dt>='2026-05-01' 
            and tag_01='整体'
            group by 1,2,3,4
            ) t6 on a.`数据更新日期`=t6.`数据更新日期` and split(a.`口径`,'-')[0]=split(t6.`口径`,'-')[0] and a.`变量`=t6.`变量` 
                left join 
            (select 
            substring('${outFileSuffix}',1,7) as `月份`
            ,'2-提袋率' as `口径`
            ,wd as `变量`
            ,'-' as `目标`
            ,concat(round(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then pay_pv else 0 end)/sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then exp_uv else 0 end)*100,2),'%') as `月均值`
            ,'-' as `达成率` 
            ,concat(round(sum(case when dt>=date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',6) then exp_uv else 0 end)*100,2),'%') as `周均值`
            ,concat(round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_uv else 0 end)*100,2),'%') as `上周均值`
            ,concat(round((((round(sum(case when dt>=date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',6) then exp_uv else 0 end),6))-(round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_uv else 0 end),6)))/round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_uv else 0 end) ,6))*100,2),'%') as `周环比`
            ,max(dt) as `数据更新日期`
            from 
            hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
            where 
            dt>='2026-05-01' 
            and tag_01='整体'
            group by 1,2,3,4
            ) t7 on a.`数据更新日期`=t7.`数据更新日期` and split(a.`口径`,'-')[0]=split(t7.`口径`,'-')[0] and a.`变量`=t7.`变量` 
            left join 
            (select 
            substring('${outFileSuffix}',1,7) as `月份`
            ,'2-商详到达率' as `口径`
            ,wd as `变量`
            ,'-' as `目标`
            ,concat(round(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then detail_uv else 0 end)/sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then exp_uv else 0 end)*100,2),'%') as `月均值`
            ,'-' as `达成率` 
            ,concat(round(sum(case when dt>=date_sub('${outFileSuffix}',6) then detail_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',6) then exp_uv else 0 end)*100,2),'%') as `周均值`
            ,concat(round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then detail_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_uv else 0 end)*100,2),'%') as `上周均值`
            ,concat(round((((round(sum(case when dt>=date_sub('${outFileSuffix}',6) then detail_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',6) then exp_uv else 0 end),6))-(round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then detail_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_uv else 0 end),6)))/round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then detail_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_uv else 0 end) ,6))*100,2),'%') as `周环比`
            ,max(dt) as `数据更新日期`
            from 
            hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
            where 
            dt>='2026-05-01' 
            and tag_01='整体'
            group by 1,2,3,4
            ) t4 on a.`数据更新日期`=t4.`数据更新日期` and split(a.`口径`,'-')[0]=split(t4.`口径`,'-')[0] and a.`变量`=t4.`变量` 
              left join 
            (
                --3单量维度指标
                select 
                substring('${outFileSuffix}',1,7) as `月份`
                ,'2-下单uv' as `口径`
                ,wd as `变量`
                ,'-' as `目标`
                ,int(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then order_uv else 0 end)/ count(distinct case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then dt else null end)) as `月均值`
                ,'-' as `达成率` 
                ,int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then order_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end))  as `周均值`
                ,int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then order_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end))  as  `上周均值`
                ,concat(round(((int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then order_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end)) -int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then order_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )/int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then order_uv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )*100,2),'%')  as `周环比`
                ,max(dt) as `数据更新日期`
                from 
                hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
                where 
                dt>='2026-05-01' 
                and tag_01='整体'
                group by 1,2,3,4
            ) t11 on a.`数据更新日期`=t11.`数据更新日期` and split(a.`口径`,'-')[0]=split(t11.`口径`,'-')[0] and a.`变量`=t11.`变量` 
            left join 
            (select 
            substring('${outFileSuffix}',1,7) as `月份`
            ,'2-下单率' as `口径`
            ,wd as `变量`
            ,'-' as `目标`
            ,concat(round(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then order_uv else 0 end)/sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then detail_uv else 0 end)*100,2),'%') as `月均值`
            ,'-' as `达成率` 
            ,concat(round(sum(case when dt>=date_sub('${outFileSuffix}',6) then order_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',6) then detail_uv else 0 end)*100,2),'%') as `周均值`
            ,concat(round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then order_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then detail_uv else 0 end)*100,2),'%') as `上周均值`
            ,concat(round((((round(sum(case when dt>=date_sub('${outFileSuffix}',6) then order_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',6) then detail_uv else 0 end),6))-(round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then order_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then detail_uv else 0 end),6)))/round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then order_uv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then detail_uv else 0 end) ,6))*100,2),'%') as `周环比`
            ,max(dt) as `数据更新日期`
            from 
            hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
            where 
            dt>='2026-05-01' 
            and tag_01='整体'
            group by 1,2,3,4
            ) t13 on a.`数据更新日期`=t13.`数据更新日期` and split(a.`口径`,'-')[0]=split(t13.`口径`,'-')[0] and a.`变量`=t13.`变量` 
            left join 
            (select 
            substring('${outFileSuffix}',1,7) as `月份`
            ,'2-支付率' as `口径`
            ,wd as `变量`
            ,'-' as `目标`
            ,concat(round(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then pay_pv else 0 end)/sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then order_uv else 0 end)*100,2),'%') as `月均值`
            ,'-' as `达成率` 
            ,concat(round(sum(case when dt>=date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',6) then order_uv else 0 end)*100,2),'%') as `周均值`
            ,concat(round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then order_uv else 0 end)*100,2),'%') as `上周均值`
            ,concat(round((((round(sum(case when dt>=date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',6) then order_uv else 0 end),6))-(round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then order_uv else 0 end),6)))/round(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6) then pay_pv else 0 end)/sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then order_uv else 0 end) ,6))*100,2),'%') as `周环比`
            ,max(dt) as `数据更新日期`
            from 
            hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
            where 
            dt>='2026-05-01' 
            and tag_01='整体'
            group by 1,2,3,4
            ) t14 on a.`数据更新日期`=t14.`数据更新日期` and split(a.`口径`,'-')[0]=split(t14.`口径`,'-')[0] and a.`变量`=t14.`变量`;

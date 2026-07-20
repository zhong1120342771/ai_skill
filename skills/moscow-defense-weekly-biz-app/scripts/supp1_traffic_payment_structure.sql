--补充1： 流量&支付结构 
    select 
    a.`月份` 
    ,a.`口径` 
    ,a.`变量` 
    ,a.`支付PV周均值` 
    ,a.`支付PV占比`
    ,c.`曝光UV占比` 
    ,d.`曝光PV占比`  
    ,nvl(b.`活跃UV占比`,'-') as `活跃UV占比` 
    ,(`支付PV占比`-`上周支付PV占比`)/`上周支付PV占比`  as `支付PV占比-周环比`
    ,(`曝光UV占比`-`上周曝光UV占比`)/`上周曝光UV占比`  as `曝光UV占比变化-周环比`
    ,nvl((`活跃UV占比`-`上周活跃UV占比`)/`上周活跃UV占比`,'-')  as `活跃UV占比变化-周环比`
    ,a.`数据更新日期`
    from 
    (
    --00-01 支付结构
        select 
        `月份`
        ,`口径`
        ,`变量`
        ,`周均值` as `支付PV周均值`
        ,`周均值`/(sum(`周均值`) over (partition by `月份`,`口径`) ) as `支付PV占比`
        ,`上周均值`/(sum(`上周均值`) over (partition by `月份`,`口径`) ) as `上周支付PV占比`
        ,`数据更新日期`
        from 
        (
            --3单量维度指标
            select 
            substring('${outFileSuffix}',1,7) as `月份`
            ,'2-端' as `口径`
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
            and tag_01='拆分端'
            group by 1,2,3,4
            union all 
            select 
            substring('${outFileSuffix}',1,7) as `月份`
            ,'3-拆分场景' as `口径`
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
            and wd <>'找靓机-不区分场景'
            and tag_01='拆分场景'
            group by 1,2,3,4 
            union all 
            select 
            substring('${outFileSuffix}',1,7) as `月份`
            ,'4-拆分用户来源' as `口径`
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
            and tag_01='拆分用户来源'
            group by 1,2,3,4 
            union all 
                select 
            substring('${outFileSuffix}',1,7) as `月份`
            ,'5-拆分用户资产分层' as `口径`
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
            and tag_01='拆分用户资产分层'
            group by 1,2,3,4 

            union all 
            select 
            substring('${outFileSuffix}',1,7) as `月份`
            ,'6-拆分品类' as `口径`
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
            and tag_01='拆分品类'
            group by 1,2,3,4 
        ) b  
        --group by 1,2,3,4 
    ) a 
    left join 
    (
    --流量结构 
    --00-02 活跃UV占比 
        select 
        `月份`
        ,`口径`
        ,`变量`
        ,`周均值` as `活跃UV周均值`
        ,`周均值`/(sum(`周均值`) over (partition by `月份`,`口径`) ) as `活跃UV占比`
        ,`上周均值`/(sum(`上周均值`) over (partition by `月份`,`口径`) ) as `上周活跃UV占比`
        ,`数据更新日期`
        from 
        (
            --4 dau 维度指标
            select 
            substring('${outFileSuffix}',1,7) as `月份`
            ,'2-端' as `口径`
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
            and tag_01='拆分端'
            group by 1,2,3,4
            union all 
            select 
            substring('${outFileSuffix}',1,7) as `月份`
            ,'4-拆分用户来源' as `口径`
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
            and tag_01='拆分用户来源'
            group by 1,2,3,4  
            union all 
            select 
            substring('${outFileSuffix}',1,7) as `月份`
            ,'5-拆分用户资产分层' as `口径`
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
            and tag_01='拆分用户资产分层'
            group by 1,2,3,4 
        ) b  
        --group by 1,2,3,4 
    ) b on a.`月份`=b.`月份` and a.`口径`=b.`口径` and a.`变量`=b.`变量` and a.`数据更新日期`=b.`数据更新日期`
    left join 
    (
    --00-03曝光UV占比 
        select 
        `月份`
        ,`口径`
        ,`变量`
        ,`周均值` as `曝光UV周均值`
        ,`周均值`/(sum(`周均值`) over (partition by `月份`,`口径`) ) as `曝光UV占比`
        ,`上周均值`/(sum(`上周均值`) over (partition by `月份`,`口径`) ) as `上周曝光UV占比`
        ,`数据更新日期`
        from 
        (
            --3单量维度指标
                select 
                substring('${outFileSuffix}',1,7) as `月份`
                ,'2-端' as `口径`
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
                and tag_01='拆分端'
                group by 1,2,3,4
                union all 
                select 
                substring('${outFileSuffix}',1,7) as `月份`
                ,'3-拆分场景' as `口径`
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
                and wd <>'找靓机-不区分场景'
                and tag_01='拆分场景'
                group by 1,2,3,4 
                union all 
                select 
                substring('${outFileSuffix}',1,7) as `月份`
                ,'4-拆分用户来源' as `口径`
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
                and tag_01='拆分用户来源'
                group by 1,2,3,4 
                UNION ALL 
                select 
                substring('${outFileSuffix}',1,7) as `月份`
                ,'5-拆分用户资产分层' as `口径`
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
                and tag_01='拆分用户资产分层'
                group by 1,2,3,4 

                union all 
                select 
                substring('${outFileSuffix}',1,7) as `月份`
                ,'6-拆分品类' as `口径`
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
                and tag_01='拆分品类'
                group by 1,2,3,4 
        ) b  
        --group by 1,2,3,4 
    ) c on a.`月份`=c.`月份` and a.`口径`=c.`口径` and a.`变量`=c.`变量` and a.`数据更新日期`=c.`数据更新日期`
    left join  
    (
    --00-04曝光PV占比 
        select 
        `月份`
        ,`口径`
        ,`变量`
        ,`周均值` as `曝光PV周均值`
        ,`周均值`/(sum(`周均值`) over (partition by `月份`,`口径`) ) as `曝光PV占比` 
        ,`上周均值`/(sum(`上周均值`) over (partition by `月份`,`口径`) ) as `上周曝光PV占比`
        ,`数据更新日期`
        from 
        (
            --3单量维度指标
                select 
                substring('${outFileSuffix}',1,7) as `月份`
                ,'2-端' as `口径`
                ,wd as `变量`
                ,'-' as `目标`
                ,int(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then exp_pv else 0 end)/ count(distinct case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then dt else null end)) as `月均值`
                ,'-' as `达成率` 
                ,int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end))  as `周均值`
                ,int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end))  as  `上周均值`
                ,concat(round(((int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end)) -int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )/int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )*100,2),'%')  as `周环比`
                ,max(dt) as `数据更新日期`
                from 
                hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
                where 
                dt>='2026-05-01' 
                and tag_01='拆分端'
                group by 1,2,3,4
                union all 
                select 
                substring('${outFileSuffix}',1,7) as `月份`
                ,'3-拆分场景' as `口径`
                ,wd as `变量`
                ,'-' as `目标`
                ,int(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then exp_pv else 0 end)/ count(distinct case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then dt else null end)) as `月均值`
                ,'-' as `达成率` 
                ,int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end))  as `周均值`
                ,int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end))  as  `上周均值`
                ,concat(round(((int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end)) -int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )/int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )*100,2),'%')  as `周环比`

                ,max(dt) as `数据更新日期`
                from 
                hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
                where 
                dt>='2026-05-01' 
                and wd <>'找靓机-不区分场景'
                and tag_01='拆分场景'
                group by 1,2,3,4 
                union all 
                select 
                substring('${outFileSuffix}',1,7) as `月份`
                ,'4-拆分用户来源' as `口径`
                ,wd as `变量`
                ,'-' as `目标`
                ,int(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then exp_pv else 0 end)/ count(distinct case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then dt else null end)) as `月均值`
                ,'-' as `达成率` 
                ,int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end))  as `周均值`
                ,int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end))  as  `上周均值`
                ,concat(round(((int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end)) -int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )/int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )*100,2),'%')  as `周环比`

                ,max(dt) as `数据更新日期`
                from 
                hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
                where 
                dt>='2026-05-01' 
                and tag_01='拆分用户来源'
                group by 1,2,3,4 
                UNION ALL 
                select 
                substring('${outFileSuffix}',1,7) as `月份`
                ,'5-拆分用户资产分层' as `口径`
                ,wd as `变量`
                ,'-' as `目标`
                ,int(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then exp_pv else 0 end)/ count(distinct case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then dt else null end)) as `月均值`
                ,'-' as `达成率` 
                ,int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end))  as `周均值`
                ,int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end))  as  `上周均值`
                ,concat(round(((int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end)) -int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )/int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )*100,2),'%')  as `周环比`
                ,max(dt) as `数据更新日期`
                from 
                hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
                where 
                dt>='2026-05-01' 
                and tag_01='拆分用户资产分层'
                group by 1,2,3,4 

                union all 
                select 
                substring('${outFileSuffix}',1,7) as `月份`
                ,'6-拆分品类' as `口径`
                ,wd as `变量`
                ,'-' as `目标`
                ,int(sum(case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then exp_pv else 0 end)/ count(distinct case when substring(dt,1,7)=substring('${outFileSuffix}',1,7) then dt else null end)) as `月均值`
                ,'-' as `达成率` 
                ,int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end))  as `周均值`
                ,int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end))  as  `上周均值`
                ,concat(round(((int(sum(case when dt>=date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',6)  then dt else null end)) -int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )/int(sum(case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then exp_pv else 0 end)/ count(distinct case when dt>=date_sub('${outFileSuffix}',13) and dt<date_sub('${outFileSuffix}',6)  then dt else null end)) )*100,2),'%')  as `周环比`

                ,max(dt) as `数据更新日期`
                from 
                hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di 
                where 
                dt>='2026-05-01' 
                and tag_01='拆分品类'
                group by 1,2,3,4 
        ) b  

    ) d on  a.`月份`=d.`月份` and a.`口径`=d.`口径` and a.`变量`=d.`变量` and a.`数据更新日期`=d.`数据更新日期`;




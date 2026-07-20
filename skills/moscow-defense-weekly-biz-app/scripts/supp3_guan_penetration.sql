-- 补充3：重点场领建设 — 电子馆点击率、UV-CVR后端转化率
-- 数据源：hdp_zhuanzhuan_dw_global.dw_log_lego_action_1d
-- 按周聚合各馆（二奢/兴趣/电子）的馆曝光UV + 馆渗透率（馆曝光UV / 首页曝光UV）
-- actiontype: G1001=首页, G1002=二奢, G1003=兴趣, G1004=电子
-- 时间范围：dt >= date_sub('${outFileSuffix}', 55)

        select
        a.tag
        ,date_add(date_sub(a.dt, pmod(datediff(a.dt, '1970-01-05'), 7)), 6)  AS `周（结束日）` -- 周结束（周日）
        ,a.area as `馆名称`
        ,avg(b.exp_uv)  as `首页曝光uv`--DAU
        ,avg(a.exp_uv) as `馆曝光uv`--馆渗透UV
        ,concat(round((avg(a.exp_uv)/avg(b.exp_uv))*100,2),'%') as `馆渗透率`
        from
        (
        SELECT
        '首页tab点击-分馆' as tag
        ,a.dt
        ,case when actiontype='G1002' then '二奢' WHEN actiontype='G1003' then '兴趣' when actiontype='G1004' then '电子'  when actiontype='G1001' then '首页' end as area
        ,count(distinct case when pagetype in ('zpmshow') AND  actiontype in   ('G1002','G1003','G1004') then a.token else null end) as exp_uv
        ,sum(case when pagetype in ('zpmshow') AND actiontype in  ('G1002','G1003','G1004') then 1 else 0 end) as exp_pv
        from hdp_zhuanzhuan_dw_global.dw_log_lego_action_1d  a
        where a.dt>=date_sub('${outFileSuffix}',55)
        AND actiontype in  ('G1002','G1003','G1004') and region='g' --(注：新版本四页面 G1001、G1002、G1003、G1004)
        and pagetype ='zpmshow'
        group by 1,2,3
        ) a
        left join
        (
        SELECT
        a.dt
        ,count(distinct a.token) as exp_uv
        from hdp_zhuanzhuan_dw_global.dw_log_lego_action_1d  a
        where a.dt>=date_sub('${outFileSuffix}',55)
        AND actiontype in  ('G1001') and region='g' --(注：新版本四页面 G1001、G1002、G1003、G1004)
        --1.首页范围：首页整体只包含 g1001,在此页面产生的所有区域/元素/商品卡曝光和点击
        and pagetype ='zpmshow'
        group by 1
        ) b on  a.dt=b.dt
        group by 1,2,3
        order by a.tag,`馆名称`,`周（结束日）` desc
        limit 10000;

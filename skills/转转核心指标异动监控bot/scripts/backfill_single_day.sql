    -- ============================================================================
    -- backfill_single_day.sql — 底表单天回刷（只补一个缺失分区，不触碰其他分区）
    --   源自 backfill_history.sql，唯一差异 = 把 31 天滚动窗口塌缩成单天：
    --     所有 `dt between date_sub(D,30) AND D`  ->  `dt between D AND D`（= dt=D 单分区）
    --     净支付两块 `aa.dt = D`（当天快照）+ `to_date(pay_time) = D`（当天支付）。
    --   ${targetDay} 为要回刷的那一天；insert overwrite PARTITION(dt) 只写 dt=${targetDay} 一个分区。
    --   由 run_backfill.py 逐个缺失日替换 ${targetDay} 提交星河(SparkSQL engine=2)。
    --   口径说明：单天版用 targetDay 当天商品/订单快照，与滚动版在 outFileSuffix=targetDay
    --     那一批对 targetDay 的读数一致；放弃了滚动版「后续批用更新快照反复修正历史退款」的能力。
    --     对「日更补漏最近缺失日」场景足够；若要修正较早历史的退款口径，仍用 backfill_history.sql。
    -- ============================================================================
    set hive.exec.dynamic.partition.mode=nonstrict;
    set hive.exec.dynamic.partition=true;

    -- ============================================================
    -- 完整内联版（无临时表）：脚本1 漏斗指标 + DAU 通用降级分母
    -- 输出列 = 最终 Excel 字段，去掉全部 *_rate 字段；matched_dau_uv 替代 uv_all
    -- 结构：info/dau/raw_funnel（脚本1）→ s1(聚合块内联) → dau_cube → matched(降级) → 最终 select
    -- ============================================================
    WITH info as (
    select case when cus_business_bu in ('消费电子') then '消费电子'
                when cus_business_bu in ('二奢') and business_line_id in(915051,915061) then '二奢'
                when cus_business_bu in ('二奢') then '兴趣'
                when cus_business_bu in ('长尾N') then '兴趣'
            else '其他' end as cate
        ,case when cate_first_id in ('101') then '手机'
                when cate_first_id in ('119') then '平板'
                when cate_third_id in ('1100000016') then '笔记本'
                when cate_third_id in ('1100000170') then '智能手表'
                when cate_third_id in ('1100000186','1100000325') then '耳机'
                when cate_third_id in (1100001788,1100001798,1100001791,1100001790,1100001787,1100001789,1100001792,1100001793,1100001127,1100000182,1100001139,1100000179,1100001138,1100000192,1100000177,1100001140,1100000467,1100000193,1100001141,1100000176,1100000172,1100000180,1100001143,1100000181,1100001806,1100001805,1100001807,1100001794,1100001801,1100001811,1100000208,1100001812,1100000211,1100001809,1100001808,1100001142,1100001126,1100000194,1100001810,1100001804,1100000209,1100003433) then '摄影摄像矩阵'
                when cate_third_id in (1100000187,1100000188,1100000665,1100000189) then '游戏矩阵'
                when cus_business_bu in ('消费电子') then '消费电子N-其他'
                when cus_business_bu in ('长尾N') and cate_id in ('1100003483','1100003484') then '乐器'
                when cus_business_bu in ('长尾N') and cate_id in ('1100001943') then '台球杆'
                when cus_business_bu in ('长尾N') and cate_id in ('1100001204','1100001202') then '骑行'
                when cus_business_bu in ('长尾N') and cate_id in ('1100000874','1100003648') then '潮玩'
                when cus_business_bu in ('长尾N') and cate_id in ('1100001939','1100003419') then '球拍'
                when cus_business_bu in ('长尾N') then '兴趣N-其他'
                when cate_first_id = '1100000354' then '包袋'
                when cate_third_id in ('1100001005','1100001007') then '腕表'
                when cate_second_id in ('1100003055','1100001004','2111008','1100001516') then '饰品'
                when cate_second_id in ('2111003','2111004','2111010','2111011','2111012','2111013','2111014','2111015','2111019','1100000315','1100001428','1100001438','1100003527') then '鞋服'
                else '奢侈品-其他' end as cate_02
        ,info_id
    from hdp_zhuanzhuan_dw_global.dw_mysql_info_full_1d a
    where 1 = 1
        -- 【回刷改动】商品维度全量快照表只保留最近~3周，历史日期无分区。
        -- 品类映射相对稳定，回刷统一钉到 t-1 这一份快照(由 run_backfill.py 注入字面量)，
        -- 否则历史 info CTE 为空、与漏斗事实 inner join 会把当天所有行 drop 成空分区。
        -- 代价：早于快照窗口下架/删除的 info_id 无法命中，历史绝对量系统性偏低(越老越狠)，
        --       且品类口径= t-1 快照口径，非历史当日口径。转化率受影响小(分子分母同步少)。
        and a.dt = '${infoSnapshotDt}'
        and cus_business_extend['is_cp_flag'] = '0'
        and cus_business_extend['is_live_flag'] = '0'
        and (cus_business_bu in ('消费电子','长尾N','二奢') or (cus_business_belong in ('B2C') and cate_second_id in ('120')) or (cate_id ='2120006' and cus_business_belong in ('B2C')))
    group by 1,2,3
    ),
    -- dau：当日活跃用户明细 + 用户来源 / 资产分层标签
    dau as (
        select t3.dt ,t3.token ,user_source ,terminal_name
            ,get_json_object(t3.user_layer,'$.B2C核心业务') as user_type
        from hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d t3
        where t3.dt between '${targetDay}' AND '${targetDay}'
        and terminal_name in ('转转APP','转转小程序','找靓机')
        group by 1,2,3,4,5
    ),
    -- raw_funnel：流量漏斗明细（曝光/商详/下单/净支付），每行一个事件
    -- 列序严格一致（共23列）：dt, first_from, init_from, user_type, user_source, cate, cate_02,
    --   main_scene, scene_02, scene_03, dau, exposedpv, exposeduv, visitpv, visituv,
    --   orderId, orderU, payId, payU, ClearpayId, ClearpayU, Clearmoney, duan
    raw_funnel as
    (--raw流量漏斗
        SELECT --曝光
                a.dt, a.first_from, a.init_from, b.user_type, b.user_source, c.cate, c.cate_02,
                case when first_from in ('search','recommend4Search') then '搜索'
                        when first_from in ('homepage_rec','homepage_rec_personal','homepage_filter','homepage_rec_mix') then '首页feeds'
                        when init_from like 'G1001%\_column\_%' or first_from = 'homepage_column' and sec_from='home_tuijian_jingxuan' then '首页栏目区'
                        when init_from like '2\_%\_0' then '首页金刚位'
                        when ((sec_from like 'home\_shepinguan%' or init_from like 'G1002%' or sec_from like 'home\_xingqukeng%' or init_from like 'G1003%' or sec_from like 'home\_shumaji%' or init_from like 'G1004%')
                        or (first_from like 'homepage\_cate%' or init_from like 'G1001\_%\_diamond%'))
                        then '馆'
                        when first_from in ('int_detail_same','one_detail_spu_page') then '商详同款推荐'
                        when init_from like 'G100_%\_threecut\_%' then '大促三切分'
                        else '其他' end as main_scene,
                -- 本次新增 scene_02
                case when first_from in ('search','recommend4Search') then '搜索'
                    when first_from in ('homepage_rec','homepage_rec_personal','homepage_filter','homepage_rec_mix') OR init_from like '2\_%\_0' or init_from like 'G1001%' or sec_from like 'home\_tuijian%' then '首页'
                    when sec_from like 'home\_shepinguan%' or init_from like 'G1002%' then '奢品馆'
                    when sec_from like 'home\_xingqukeng%' or init_from like 'G1003%' then '兴趣馆'
                    when sec_from like 'home\_shumaji%' or init_from like 'G1004%' then '数码馆'
                    else '其他' end as `scene_02`,
                -- 本次新增 scene_03
                case when first_from in ('search','recommend4Search') then '搜索'
                    when first_from in ('homepage_rec','homepage_rec_personal','homepage_filter','homepage_rec_mix') then '首页feeds'
                    when init_from like 'G1001%\_column\_%' or first_from = 'homepage_column' and sec_from='home_tuijian_jingxuan' then '首页栏目区'
                    when init_from like '2\_%\_0' then '首页金刚位'
                    when (init_from like 'G100_%\_rg\_%' or init_from like 'G1001\_%\_diamond%') then '馆金刚位'
                    when first_from like 'homepage\_cate%' then '馆feed流'
                    when (init_from like 'G100_%\_column\_%' or first_from like 'homepage\_cate%') then '馆栏目区'
                    else '其他' end as `scene_03`,
                NULL as dau, 1 AS exposedpv, a.token AS exposeduv, 0 AS visitpv, NULL AS visituv,
                NULL AS orderId, NULL AS orderU, NULL AS payId, NULL AS payU,
                NULL AS ClearpayId, NULL AS ClearpayU, 0 AS Clearmoney, duan
            FROM
            (SELECT a.dt, a.first_from, a.sec_from, a.init_from, a.token, a.info_id, a.request_mark, a.page, a.idx,
                case when terminal in (15,16,20) then '转转APP' when terminal in (103) then '转转小程序' when terminal in (182,80,79,78,141) then '找靓机' else '其他' end as duan
            FROM hdp_zhuanzhuan_dm_global.dm_trade_exposure_info_detail_inc_1d a
            WHERE dt between '${targetDay}' AND '${targetDay}' and terminal in (15,16,20,103,182,80,79,78,141)
            ) a
            join info c on a.info_id = c.info_id
            join dau b on a.token = b.token and a.dt = b.dt

            UNION ALL

            SELECT --商详
                a.dt, a.first_from, a.init_from, b.user_type, b.user_source, c.cate, c.cate_02,
                case when first_from in ('search','recommend4Search') then '搜索'
                        when first_from in ('homepage_rec','homepage_rec_personal','homepage_filter','homepage_rec_mix') then '首页feeds'
                        when init_from like 'G1001%\_column\_%' or first_from = 'homepage_column' and sec_from='home_tuijian_jingxuan' then '首页栏目区'
                        when init_from like '2\_%\_0' then '首页金刚位'
                        when ((sec_from like 'home\_shepinguan%' or init_from like 'G1002%' or sec_from like 'home\_xingqukeng%' or init_from like 'G1003%' or sec_from like 'home\_shumaji%' or init_from like 'G1004%')
                        or (first_from like 'homepage\_cate%' or init_from like 'G1001\_%\_diamond%'))
                        then '馆'
                        when first_from in ('int_detail_same','one_detail_spu_page') then '商详同款推荐'
                        when init_from like 'G100_%\_threecut\_%' then '大促三切分'
                        else '其他' end as main_scene,
                -- 本次新增 scene_02
                case when first_from in ('search','recommend4Search') then '搜索'
                    when first_from in ('homepage_rec','homepage_rec_personal','homepage_filter','homepage_rec_mix') OR init_from like '2\_%\_0' or init_from like 'G1001%' or sec_from like 'home\_tuijian%' then '首页'
                    when sec_from like 'home\_shepinguan%' or init_from like 'G1002%' then '奢品馆'
                    when sec_from like 'home\_xingqukeng%' or init_from like 'G1003%' then '兴趣馆'
                    when sec_from like 'home\_shumaji%' or init_from like 'G1004%' then '数码馆'
                    else '其他' end as `scene_02`,
                -- 本次新增 scene_03
                case when first_from in ('search','recommend4Search') then '搜索'
                    when first_from in ('homepage_rec','homepage_rec_personal','homepage_filter','homepage_rec_mix') then '首页feeds'
                    when init_from like 'G1001%\_column\_%' or first_from = 'homepage_column' and sec_from='home_tuijian_jingxuan' then '首页栏目区'
                    when init_from like '2\_%\_0' then '首页金刚位'
                    when (init_from like 'G100_%\_rg\_%' or init_from like 'G1001\_%\_diamond%') then '馆金刚位'
                    when first_from like 'homepage\_cate%' then '馆feed流'
                    when (init_from like 'G100_%\_column\_%' or first_from like 'homepage\_cate%') then '馆栏目区'
                    else '其他' end as `scene_03`,
                NULL as dau, 0 AS exposedpv, NULL AS exposeduv, 1 AS visitpv, a.token AS visituv,
                NULL AS orderId, NULL AS orderU, NULL AS payId, NULL AS payU,
                NULL AS ClearpayId, NULL AS ClearpayU, 0 AS Clearmoney, duan
            FROM
            (SELECT a.dt, a.first_from, a.sec_from, a.init_from, a.token, a.info_id, a.request_mark, a.page, a.idx,
                case when terminal in (15,16,20) then '转转APP' when terminal in (103) then '转转小程序' when terminal in (182,80,79,78,141) then '找靓机' else '其他' end as duan
            FROM hdp_zhuanzhuan_dm_global.dm_trade_visit_detail_1d a
            WHERE dt between '${targetDay}' AND '${targetDay}' and terminal in (15,16,20,103,182,80,79,78,141)
            ) a
            join info c on a.info_id = c.info_id
            join dau b on a.token = b.token and a.dt = b.dt

            UNION ALL

            SELECT --下单
            a.dt, a.first_from, a.init_from, b.user_type, b.user_source, c.cate, c.cate_02,
                case when first_from in ('search','recommend4Search') then '搜索'
                        when first_from in ('homepage_rec','homepage_rec_personal','homepage_filter','homepage_rec_mix') then '首页feeds'
                        when init_from like 'G1001%\_column\_%' or first_from = 'homepage_column' and sec_from='home_tuijian_jingxuan' then '首页栏目区'
                        when init_from like '2\_%\_0' then '首页金刚位'
                        when ((sec_from like 'home\_shepinguan%' or init_from like 'G1002%' or sec_from like 'home\_xingqukeng%' or init_from like 'G1003%' or sec_from like 'home\_shumaji%' or init_from like 'G1004%')
                        or (first_from like 'homepage\_cate%' or init_from like 'G1001\_%\_diamond%'))
                        then '馆'
                        when first_from in ('int_detail_same','one_detail_spu_page') then '商详同款推荐'
                        when init_from like 'G100_%\_threecut\_%' then '大促三切分'
                        else '其他' end as main_scene,
                -- 本次新增 scene_02
                case when first_from in ('search','recommend4Search') then '搜索'
                    when first_from in ('homepage_rec','homepage_rec_personal','homepage_filter','homepage_rec_mix') OR init_from like '2\_%\_0' or init_from like 'G1001%' or sec_from like 'home\_tuijian%' then '首页'
                    when sec_from like 'home\_shepinguan%' or init_from like 'G1002%' then '奢品馆'
                    when sec_from like 'home\_xingqukeng%' or init_from like 'G1003%' then '兴趣馆'
                    when sec_from like 'home\_shumaji%' or init_from like 'G1004%' then '数码馆'
                    else '其他' end as `scene_02`,
                -- 本次新增 scene_03
                case when first_from in ('search','recommend4Search') then '搜索'
                    when first_from in ('homepage_rec','homepage_rec_personal','homepage_filter','homepage_rec_mix') then '首页feeds'
                    when init_from like 'G1001%\_column\_%' or first_from = 'homepage_column' and sec_from='home_tuijian_jingxuan' then '首页栏目区'
                    when init_from like '2\_%\_0' then '首页金刚位'
                    when (init_from like 'G100_%\_rg\_%' or init_from like 'G1001\_%\_diamond%') then '馆金刚位'
                    when first_from like 'homepage\_cate%' then '馆feed流'
                    when (init_from like 'G100_%\_column\_%' or first_from like 'homepage\_cate%') then '馆栏目区'
                    else '其他' end as `scene_03`,
                NULL as dau, 0 AS exposedpv, NULL AS exposeduv, 0 AS visitpv, NULL AS visituv,
                a.order_id AS orderId, a.uid AS orderU, NULL AS payId, NULL AS payU,
                NULL AS ClearpayId, NULL AS ClearpayU, 0 AS Clearmoney, duan
            FROM
            (SELECT *, case when terminal in (15,16,20) then '转转APP' when terminal in (103) then '转转小程序' when terminal in (182,80,79,78,141) then '找靓机' else '其他' end as duan
            FROM hdp_zhuanzhuan_dm_global.dm_trade_order_detail_1d
            WHERE dt between '${targetDay}' AND '${targetDay}' and terminal in (15,16,20,103,182,80,79,78,141)
            ) a
            join info c on a.info_id = c.info_id
            join dau b on a.token = b.token and a.dt = b.dt

            UNION ALL

            SELECT --净支付（非找靓机主口径，含场景）
                a.dt, a.first_from, a.init_from, b.user_type, b.user_source, c.cate, c.cate_02,
                case when first_from in ('search','recommend4Search') then '搜索'
                        when first_from in ('homepage_rec','homepage_rec_personal','homepage_filter','homepage_rec_mix') then '首页feeds'
                        when init_from like 'G1001%\_column\_%' or first_from = 'homepage_column' and sec_from='home_tuijian_jingxuan' then '首页栏目区'
                        when init_from like '2\_%\_0' then '首页金刚位'
                        when ((sec_from like 'home\_shepinguan%' or init_from like 'G1002%' or sec_from like 'home\_xingqukeng%' or init_from like 'G1003%' or sec_from like 'home\_shumaji%' or init_from like 'G1004%')
                        or (first_from like 'homepage\_cate%' or init_from like 'G1001\_%\_diamond%'))
                        then '馆'
                        when first_from in ('int_detail_same','one_detail_spu_page') then '商详同款推荐'
                        when init_from like 'G100_%\_threecut\_%' then '大促三切分'
                        else '其他' end as main_scene,
                -- 本次新增 scene_02
                case when first_from in ('search','recommend4Search') then '搜索'
                    when first_from in ('homepage_rec','homepage_rec_personal','homepage_filter','homepage_rec_mix') OR init_from like '2\_%\_0' or init_from like 'G1001%' or sec_from like 'home\_tuijian%' then '首页'
                    when sec_from like 'home\_shepinguan%' or init_from like 'G1002%' then '奢品馆'
                    when sec_from like 'home\_xingqukeng%' or init_from like 'G1003%' then '兴趣馆'
                    when sec_from like 'home\_shumaji%' or init_from like 'G1004%' then '数码馆'
                    else '其他' end as `scene_02`,
                -- 本次新增 scene_03
                case when first_from in ('search','recommend4Search') then '搜索'
                    when first_from in ('homepage_rec','homepage_rec_personal','homepage_filter','homepage_rec_mix') then '首页feeds'
                    when init_from like 'G1001%\_column\_%' or first_from = 'homepage_column' and sec_from='home_tuijian_jingxuan' then '首页栏目区'
                    when init_from like '2\_%\_0' then '首页金刚位'
                    when (init_from like 'G100_%\_rg\_%' or init_from like 'G1001\_%\_diamond%') then '馆金刚位'
                    when first_from like 'homepage\_cate%' then '馆feed流'
                    when (init_from like 'G100_%\_column\_%' or first_from like 'homepage\_cate%') then '馆栏目区'
                    else '其他' end as `scene_03`,
                NULL as dau, 0 AS exposedpv, NULL AS exposeduv, 0 AS visitpv, NULL AS visituv,
                NULL AS orderId, NULL AS orderU, NULL AS payId, NULL AS payU,
                a.order_id AS ClearpayId, a.uid AS ClearpayU, a.pay_price AS Clearmoney, duan
            FROM
            (SELECT *, case when terminal in (15,16,20) then '转转APP' when terminal in (103) then '转转小程序' when terminal in (182,80,79,78,141) then '找靓机' else '其他' end as duan
            FROM hdp_zhuanzhuan_dm_global.dm_trade_pay_detail_1d
            WHERE dt between '${targetDay}' AND '${targetDay}' and terminal in (15,16,20,103,182,80,79,78,141)
            ) a
            join dau b on a.token = b.token and a.dt = b.dt
            inner join (
                select to_date(aa.pay_time) as dt, aa.buyer_id, aa.order_id, aa.total_amt, aa.token, aa.info_id
                from hdp_zhuanzhuan_dw_global.dw_trade_order_company_all_detail_full_1d aa
                where aa.dt = '${targetDay}' and to_date(aa.pay_time) between '${targetDay}' AND '${targetDay}'
                    and aa.is_pure_pay_the_day = 1 and aa.is_exchange_order_flag=0
            ) d on a.order_id=d.order_id and a.dt=d.dt
            join info c on a.info_id = c.info_id

            UNION ALL

            SELECT --净支付（找靓机，不区分场景）
                a.dt, NULL as first_from, NULL as init_from, b.user_type, b.user_source, c.cate, c.cate_02,
                '找靓机-不区分场景' as main_scene,
                '其他' as `scene_02`,   -- 本次新增：该块无 first_from/init_from/sec_from，直接给字面量
                '其他' as `scene_03`,   -- 本次新增：同上
                NULL as dau, 0 AS exposedpv, NULL AS exposeduv, 0 AS visitpv, NULL AS visituv,
                NULL AS orderId, NULL AS orderU, NULL AS payId, NULL AS payU,
                a.order_id AS ClearpayId, a.buyer_id AS ClearpayU, a.total_amt AS Clearmoney, duan
            FROM
            ( select to_date(aa.pay_time) as dt, aa.buyer_id, aa.order_id, aa.total_amt, aa.token, aa.info_id, '找靓机' as duan
                from hdp_zhuanzhuan_dw_global.dw_trade_order_company_all_detail_full_1d aa
                where aa.dt = '${targetDay}' and to_date(aa.pay_time) between '${targetDay}' AND '${targetDay}'
                    and aa.app_type in (79,78,141) and aa.is_pure_pay_the_day = 1 and aa.is_exchange_order_flag=0
            ) a
            join dau b on a.token = b.token and a.dt = b.dt
            join info c on a.info_id = c.info_id
    ),
    -- s1：脚本1 的 29 个聚合块内联（替代临时表 tmp_dws_all_app_zhibiao_zmt_v2_di）
    s1 as (
        select tag_01, wd, dt,
               exp_pv, exp_uv, datail_pv as detail_pv, detail_uv,
               order_pv, order_uv, pay_pv
        from (-- 整体
        SELECT '整体' as tag_01, '整体' as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        union all
        -- 单维度-拆分端
        SELECT '单维度-拆分端' as tag_01, duan as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        union all
        -- 单维度-拆分用户来源
        SELECT '单维度-拆分用户来源' as tag_01, user_source as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        union all
        -- 单维度-拆分用户资产分层
        SELECT '单维度-拆分用户资产分层' as tag_01, user_type as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        union all
        -- 单维度-拆分场景
        SELECT '单维度-拆分场景' as tag_01, main_scene as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        union all
        -- 单维度-拆分品类（业务）
        SELECT '单维度-拆分品类' as tag_01, concat('业务_',cate) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        union all
        -- 单维度-拆分品类（品类）
        SELECT '单维度-拆分品类' as tag_01, concat('品类_',cate,cate_02) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        union all
        -- 2维度交叉-端_品类
        SELECT '2维度交叉-端_业务/品类' as tag_01, concat(duan,'_品类',cate,cate_02) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        union all
        -- 2维度交叉-端_业务
        SELECT '2维度交叉-端_业务/品类' as tag_01, concat(duan,'_业务',cate) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        union all
        -- 2维度交叉-端_用户来源
        SELECT '2维度交叉-端_用户来源' as tag_01, concat(duan,user_source) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        union all
        -- 3维度交叉-端_品类_场景
        SELECT '3维度交叉-端_业务/品类_场景' as tag_01, concat(duan,'_品类',cate,cate_02,'_',main_scene) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        union all
        -- 3维度交叉-端_业务_场景
        SELECT '3维度交叉-端_业务/品类_场景' as tag_01, concat(duan,'_业务',cate,'_',main_scene) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        union all
        -- 3维度交叉-端_品类_用户来源
        SELECT '3维度交叉-端_业务/品类_用户来源' as tag_01, concat(duan,'_品类',cate,cate_02,'_',user_source) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        union all
        -- 3维度交叉-端_业务_用户来源
        SELECT '3维度交叉-端_业务/品类_用户来源' as tag_01, concat(duan,'_业务',cate,'_',user_source) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        union all
        -- 4维度交叉-端_品类_用户来源_场景
        SELECT '4维度交叉-端_业务/品类_用户来源_场景' as tag_01, concat(duan,'_品类',cate,cate_02,'_',user_source,'_',main_scene) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        union all
        -- 4维度交叉-端_业务_用户来源_场景
        SELECT '4维度交叉-端_业务/品类_用户来源_场景' as tag_01, concat(duan,'_业务',cate,'_',user_source,'_',main_scene) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        union all
        -- 3维度交叉-端_品类_资产分层
        SELECT '3维度交叉-端_业务/品类_资产分层' as tag_01, concat(duan,'_品类',cate,cate_02,'_',user_type) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        union all
        -- 3维度交叉-端_业务_资产分层
        SELECT '3维度交叉-端_业务/品类_资产分层' as tag_01, concat(duan,'_业务',cate,'_',user_type) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        -- ======================= 本次新增 START =======================
        -- 新增A1：单维度-拆分scene_02
        union all
        SELECT '单维度-拆分scene_02' as tag_01, scene_02 as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        -- 新增A2：单维度-拆分scene_03
        union all
        SELECT '单维度-拆分scene_03' as tag_01, scene_03 as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        -- 新增B1：2维度交叉-scene组合_端  (scene_combined = concat(scene_02,'_',main_scene))
        union all
        SELECT '2维度交叉-scene组合_端' as tag_01, concat(scene_02,'_',main_scene,'_',duan) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        -- 新增B2：2维度交叉-scene组合_业务
        union all
        SELECT '2维度交叉-scene组合_业务/品类' as tag_01, concat(scene_02,'_',main_scene,'_业务',cate) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        -- 新增B3：2维度交叉-scene组合_品类
        union all
        SELECT '2维度交叉-scene组合_业务/品类' as tag_01, concat(scene_02,'_',main_scene,'_品类',cate,cate_02) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        -- 新增B4：2维度交叉-scene组合_用户来源
        union all
        SELECT '2维度交叉-scene组合_用户来源' as tag_01, concat(scene_02,'_',main_scene,'_',user_source) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        -- 新增B5：2维度交叉-scene组合_资产分层
        union all
        SELECT '2维度交叉-scene组合_资产分层' as tag_01, concat(scene_02,'_',main_scene,'_',user_type) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        -- ======================= 本次新增 END =======================
        -- ======================= V2 三维度交叉 START =======================
        -- scene组合(scene_02+main_scene) × 端(duan) × [业务/品类/用户来源/资产分层]
        -- 新增C1：3维度交叉-scene组合_端_业务
        union all
        SELECT '3维度交叉-scene组合_端_业务/品类' as tag_01, concat(scene_02,'_',main_scene,'_',duan,'_业务',cate) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        -- 新增C2：3维度交叉-scene组合_端_品类
        union all
        SELECT '3维度交叉-scene组合_端_业务/品类' as tag_01, concat(scene_02,'_',main_scene,'_',duan,'_品类',cate,cate_02) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        -- 新增C3：3维度交叉-scene组合_端_用户来源
        union all
        SELECT '3维度交叉-scene组合_端_用户来源' as tag_01, concat(scene_02,'_',main_scene,'_',duan,'_',user_source) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        -- 新增C4：3维度交叉-scene组合_端_资产分层
        union all
        SELECT '3维度交叉-scene组合_端_资产分层' as tag_01, concat(scene_02,'_',main_scene,'_',duan,'_',user_type) as wd, dt,
            cast(sum(exposedpv) AS bigint) exp_pv, count(DISTINCT exposeduv) exp_uv,
            cast(sum(visitpv) AS bigint) datail_pv, count(DISTINCT visituv) detail_uv,
            count(DISTINCT ClearpayId) pay_pv, count(DISTINCT orderId) AS order_pv, count(DISTINCT orderU) as order_uv
        FROM raw_funnel a GROUP BY 1,2,3
        -- ======================= V2 三维度交叉 END =======================
        ) a
    ),
    -- dau_cube：DAU 三属性(端/来源/分层) 8 组合，未参与维度填 'ALL'
    dau_cube as (
        select dt, 'ALL' as duan, 'ALL' as user_source, 'ALL' as user_type, count(distinct token) as uv from dau group by 1,2,3,4
        union all
        select dt, terminal_name as duan, 'ALL', 'ALL', count(distinct token) from dau group by 1,2,3,4
        union all
        select dt, 'ALL', user_source, 'ALL', count(distinct token) from dau group by 1,2,3,4
        union all
        select dt, 'ALL', 'ALL', user_type, count(distinct token) from dau group by 1,2,3,4
        union all
        select dt, terminal_name, user_source, 'ALL', count(distinct token) from dau group by 1,2,3,4
        union all
        select dt, terminal_name, 'ALL', user_type, count(distinct token) from dau group by 1,2,3,4
        union all
        select dt, 'ALL', user_source, user_type, count(distinct token) from dau group by 1,2,3,4
        union all
        select dt, terminal_name, user_source, user_type, count(distinct token) from dau group by 1,2,3,4
    ),
    -- dim_vals：从 dau 派生三类用户属性的真实取值集合（带类型标记）
    --   用来探测每条 wd 实际含有哪几类用户属性——单维取值一定存在，探测可靠。
    dim_vals as (
        select dt, 'duan'   as dim, terminal_name as val from dau where terminal_name is not null group by 1,2,3
        union all
        select dt, 'source' as dim, user_source   as val from dau where user_source   is not null group by 1,2,3
        union all
        select dt, 'type'   as dim, user_type     as val from dau where user_type      is not null group by 1,2,3
    ),
    -- req：每条 wd 实际含有的用户属性维度类型数（required）
    --   同一 wd 每类最多命中一个，按“该类型是否被命中”计数。
    req as (
        select a.wd as s1_wd, a.dt as s1_dt,
               count(distinct v.dim) as required
        from s1 a
        left join dim_vals v
          on a.dt = v.dt and instr(a.wd, v.val) > 0
        group by 1,2
    ),
    -- matched：脚本1 每条 wd 降级匹配到最细可用的 DAU 分母格
    matched as (
        select s1_wd, s1_dt, uv as matched_dau_uv, duan, user_source, user_type, n_specific,
               row_number() over (partition by s1_wd, s1_dt order by n_specific desc) as rn
        from (
            select a.wd as s1_wd, a.dt as s1_dt, c.uv, c.duan, c.user_source, c.user_type,
                   ( (case when c.duan        <> 'ALL' then 1 else 0 end)
                   + (case when c.user_source <> 'ALL' then 1 else 0 end)
                   + (case when c.user_type   <> 'ALL' then 1 else 0 end) ) as n_specific
            from s1 a
            join dau_cube c
              on a.dt = c.dt
             and (c.duan        = 'ALL' or instr(a.wd, c.duan)        > 0)
             and (c.user_source = 'ALL' or instr(a.wd, c.user_source) > 0)
             and (c.user_type   = 'ALL' or instr(a.wd, c.user_type)   > 0)
        ) j
    )
            insert overwrite table hdp_zhuanzhuan_tmp_global.tmp_dws_zz_core_dataagent_zmt_v2_di  PARTITION  ( dt)      
    -- 最终输出：去掉全部 *_rate；matched_dau_uv 替代 uv_all
    --   完整性闸门：只有匹配格覆盖了 wd 里实际含有的全部用户属性(n_specific = required)
    --   才保留分母；若精确格缺失被迫跨维度回退(n_specific < required)，分母及匹配维度置 null。
    select s1.tag_01, s1.wd,
           s1.exp_pv, s1.exp_uv, s1.detail_pv, s1.detail_uv,
           s1.order_pv, s1.order_uv, s1.pay_pv,
           case when m.n_specific = r.required then m.matched_dau_uv else null end as matched_dau_uv,
           case when m.n_specific = r.required then m.duan        else null end as matched_duan,
           case when m.n_specific = r.required then m.user_source else null end as matched_source,
           case when m.n_specific = r.required then m.user_type   else null end as matched_type,
           s1.dt
    from s1
    left join req     r on s1.wd = r.s1_wd and s1.dt = r.s1_dt
    left join matched m on s1.wd = m.s1_wd and s1.dt = m.s1_dt and m.rn = 1
    ;

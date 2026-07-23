-- ============================================================================
-- 同售动销表回刷 SQL —— insert overwrite hdp_zhuanzhuan_dw_global.dws_yth_ts_kc_ord_zmt_di
-- ----------------------------------------------------------------------------
-- 用途：当日/t-1 同售动销表未被上游 ETL 写到位（count=0）时，用本 SQL 回刷该分区。
-- 由 refresh_tongshou.py 读取本文件，把 ${dt} / ${outFileSuffix} 占位替换为目标分区日期后提交（星河 hive, sql_engine=5）。
--
-- 口径来源：/Users/zhongmengting/Desktop/转转code/ai指令/一体化bot脚本.sql 的「【调度】当日」段（2026-07-20 用户提供完整版）。
-- 仅取调度 insert overwrite 段；不含 CREATE TABLE DDL（建表只需一次，回刷不重建）。
--
-- ⚠️ 高风险：INSERT OVERWRITE 生产表，覆盖目标分区。仅在确认该分区 count=0 时回刷。
-- 首次启用前先用 refresh_tongshou.py --dt <已知有数据的历史日> --force 验证回刷结果与现有分区一致。
-- ============================================================================

with a1 as
    (
    select
        dt
        ,cate
        ,brand
        ,sku
        ,store_id
        ,city
        ,concat_ws('-',cate,brand,sku) as skuu
        ,count(case when mart_state not in (4,5,6)then qc_code else null end) as kc_all
        ,count(case when is_mart=1 and mart_state =3 then qc_code else null end ) as kc_ts
    from
    (
        select DISTINCT
            dt
            ,city_name as city
            ,store_id as store_id
            ,qc_code
            ,storage_age
            ,cate_name as cate
            ,brand_name as brand
            ,LOWER(model_name) as sku
            ,capacity_desc as rongliang
            ,valuer_grade_desc as dengji
            ,case when condition_desc = '8成新' then '8新' when condition_desc = '9成新' then '9新' else condition_desc END AS chengse
            ,is_mart
            ,is_hour_mart
            ,mart_state
            ,actual_cost_price/100 as chengben
            ,is_reserve
            ,product_type
            ,case when retail_price/100 >=4000 then retail_price/100-140
                    when retail_price/100 >=2000 then retail_price/100-90
                    when retail_price/100 >=1000 then retail_price/100-60 else retail_price/100 end as lingshoujiaquanhou
            ,case when storage_state = 1 then '待入库'
                when storage_state = 2 then '已入库'
                when storage_state = 3 then '待出库'
                when storage_state = 4 then '已出库' else null end as kc_status
            ,up_price/100 as jiajia
            ,purchaser_type
            ,is_reserve_label
            ,purchase_channels
        from hdp_zhuanzhuan_dw_global.dw_trade_retail_offline_data_full_1d
        where dt = '${outFileSuffix}'
        and store_name not like '%测试%'
        and storage_state in (1,2,3)
        and recall_state != 2
    ) a
    group by dt,cate,brand,sku,store_id
            ,city
            ,concat_ws('-',cate,brand,sku)
    )
    ,info as
            (
            --限制1+N
        select info_id,dt
            from hdp_zhuanzhuan_dw_global.dw_mysql_info_full_1d t1
            where 1 = 1
                and t1.dt = '${outFileSuffix}'
                and t1.cus_business_extend['is_cp_flag'] = '0' -- 剔除充配
                and t1.cus_business_extend['is_live_flag'] = '0'  --剔除直播代下单账号
                and (t1.cus_business_bu in ('消费电子','长尾N','二奢')  or (cus_business_belong in ('B2C') and cate_second_id in ('120')) or (business_line_id in ('901026','901030','901035') and cus_business_bu='其他')) -- ('901026','901030','901035')投放的业务线id
                and (cate_first_id in ('101','119')  or  cate_third_id in ('1100000016','1100000170','1100000186') )
            group by 1,2
            )
    ,cd_fw as
            (
                select
                store_id
                ,store_name
                ,city
            -- ,store_type_id --商户类型 (store_type_name归属类型 仓、验机中心等)
                from
                hdp_zhuanzhuan_dim_global.dim_perform_warehouse_store_info_full_1d_0p
                where store_type_id in (1,21,22)--限定为大仓/中心仓
                group by 1,2,3
            )
        ,info_cd as
            (
            select
            info_id
            ,dt
            ,warehouse_area_id --对应dim_perform_warehouse_store_info_full_1d_0p store_id
            ,oms_sku_id
            from
            hdp_zhuanzhuan_dw_global.dw_info_prod_detail_full_1d
        where dt  = '${outFileSuffix}'
                and status = 1
                and surplus_stk_qty>0
                and is_searchable = 1
                and cus_small_cate_name<>'非消费电子类目'
                and (cate_first_id in ('101','119')  or  cate_third_id in ('1100000016','1100000170','1100000186') )
                group by 1,2,3,4
            )
        ,cd as
        (
            select
            '仓' as type_md
            ,a.dt
            ,a.info_id
            ,a.oms_sku_id
            ,b.city
            from
            info_cd a
            inner join cd_fw b on a.warehouse_area_id =b.store_id
            group by 1,2,3,4,5
        )
        ,md_ts as
        (
        --02b2c 小店
        select
        '小店' as type_md
        ,order_id
        ,city_name as city
        from hdp_zhuanzhuan_dw_global.dw_trade_retail_offline_data_full_1d--门店数码零售
        where
        dt =  '${outFileSuffix}'
        and order_type=3
        group by 1,2,3
        union all
        select
        'pro店' as type_md
        ,order_id
        ,city_name as city
        from
        hdp_ubu_zhuanzhuan_dw_c2b.dw_trade_sale_store_pro_retail_offline_data_full_1d
        where
        dt= '${outFileSuffix}'
        and order_type =3 --同时售
        group by 1,2,3
        )
    insert overwrite table  hdp_zhuanzhuan_dw_global.dws_yth_ts_kc_ord_zmt_di PARTITION  ( dt='${outFileSuffix}')
    select
    kc.city
    ,kc.type_md
    ,kc.kc_all
    ,kc.kc_ts
    ,nvl(ord.pay_pv,0) as  pay_pv
    from
    (
    select
    dt
    ,'小店' as type_md
    ,city
    ,sum(kc_all) as kc_all --总库存
    ,sum(kc_ts) as kc_ts--同售库存
    from a1
    where cate in ('平板电脑','手机','智能手表','耳机/耳麦','笔记本')
    and dt not like '%test%'
    group by 1,2,3
    union all
    select
    t1.dt
    ,'pro店' as type_md
    ,t1.city_name as city
    ,count(distinct t1.qc_code) as kc_all --总库存
    ,count(distinct case when t1.mart_state in (3) then t1.qc_code else null end) as kc_ts--同售库存
    from hdp_ubu_zhuanzhuan_dw_c2b.dw_trade_store_sale_product_info_full_1d t1
    left join hdp_ubu_zhuanzhuan_dw_c2b.dw_trade_sale_store_pro_retail_offline_data_full_1d t2 on t1.info_id = t2.info_id and t1.store_id = t2.store_id and t1.dt = substr(t2.outbound_time,1,10) and t2.dt = '${outFileSuffix}'
    where stock_state in (2,3) ---已入库和待出库
    and t1.dt= '${outFileSuffix}'
    and t1.store_name like '%循环%'
    and t1.cate_name in ('平板电脑','手机','智能手表','耳机/耳麦','笔记本')
    group by 1,2,3
    union all
    select
    dt
    ,'仓' as type_md
    ,city
    ,count(distinct a.oms_sku_id) as kc_all
    ,count(distinct a.oms_sku_id) as kc_ts
    from
    cd a
    group by 1,2,3
    ) kc
    left join
    (
        select
        a.dt
        ,nvl(t2.type_md,t3.type_md)  as type_md
        ,nvl(t2.city,t3.city) as city
        ,count(distinct a.order_id) as pay_pv
        from
            ( --一体化城市线上订单
                select
                order_id
                ,a.info_id
                ,FROM_UNIXTIME(CAST(pay_time/1000 AS BIGINT),'yyyy-MM-dd') AS dt --支付日期
                ,receiving_city
                from
                hdp_zhuanzhuan_dim_global.dim_trade_order_sale_all_full_1d a inner join (select info_id from info) c on a.info_id=c.info_id
                where
                receiving_city is not null and receiving_city<>''
                and dt= '${outFileSuffix}'
                and FROM_UNIXTIME(CAST(pay_time/1000 AS BIGINT),'yyyy-MM-dd')='${outFileSuffix}'
                group by 1,2,3,4
            ) a
            inner join
                (SELECT
                order_id
                ,dt
                    FROM hdp_zhuanzhuan_dm_global.dm_trade_pay_detail_1d a
                    WHERE a.dt ='${outFileSuffix}'
                    group by 1,2
                    ) b on a.order_id=b.order_id
                    inner join (
                        select ----净支付口径
                            to_date(aa.pay_time) as dt
                            ,aa.order_id
                            from hdp_zhuanzhuan_dw_global.dw_trade_order_company_all_detail_full_1d aa
                            left join hdp_ubu_zhuanzhuan_dm_b2c.dm_finance_trade_order_dtl_full_1d bb
                            on aa.order_id = bb.order_id and bb.dt = '${outFileSuffix}' and to_date(bb.pay_time)='${outFileSuffix}'
                            where aa.dt = '${outFileSuffix}'
                            and to_date(aa.pay_time)='${outFileSuffix}'
                            and aa.app_type in (15,16,103,20)
                            and aa.is_pure_pay_the_day = 1---限制天内净支付
                            and aa.is_exchange_order_flag=0
                            group by 1,2
                    ) d
            on a.order_id=d.order_id and a.dt=d.dt
            left join md_ts t2 on a.order_id =t2.order_id
            left join cd t3 on a.info_id = t3.info_id
            group by 1,2,3
    ) ord on kc.dt=ord.dt and kc.city=ord.city and kc.type_md=ord.type_md

-- 数据就绪检查 — 5 张表的最大 dt
-- 用法：依次或合并跑，确认 max(dt) >= ${target_dt}
-- engine：星河 hive (sql_engine=5) 或 starrocks (sql_engine=4) 都可
select '01_xianshang' as `表`, max(dt) as `max_dt` from hdp_zhuanzhuan_tmp_global.dws_yth_core_xianshang_layer01_zmt_v1_di
union all
select '02_yykj_xs',           max(dt)              from hdp_zhuanzhuan_dw_global.dws_yth_xs01_yykj_zmt_v1_di
union all
select '03_mdkh_xs',           max(dt)              from hdp_zhuanzhuan_dw_global.dws_yth_xs02_mdkh_zmt_v1_di
union all
select '04_tongshou',          max(dt)              from hdp_zhuanzhuan_dw_global.dws_yth_core_tongshou_layer01_zmt_v1_di
union all
select '05_xiaoshida',         max(dt)              from hdp_zhuanzhuan_dw_global.dws_yth_core_xsd_layer01_zmt_v1_di
;

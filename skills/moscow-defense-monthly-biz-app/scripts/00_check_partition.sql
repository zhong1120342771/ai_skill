--00 验分区数据
select
max(dt) as dt_max
from
hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di
where dt>='2026-06-01';

CREATE TABLE `hdp_zhuanzhuan_dim_global.dim_zpm_page_section_info_full_1d_0p`(
    `link_id` string COMMENT '关联ID-页面ID/子页面ID',
    `section_id` string COMMENT '区域ID',
    `section_name` string COMMENT '区域名称')
COMMENT '高斯区域维表'
ROW FORMAT SERDE
    'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
STORED AS INPUTFORMAT
    'org.apache.hadoop.mapred.TextInputFormat'
OUTPUTFORMAT
    'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION
    'viewfs://58-cluster/home/hdp_ubu_zhuanzhuan/warehouse/hdp_zhuanzhuan_dim_global/dim_zpm_page_section_info_full_1d_0p'
TBLPROPERTIES (
    'transient_lastDdlTime'='1781367084')

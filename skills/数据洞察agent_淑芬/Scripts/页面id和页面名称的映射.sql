CREATE TABLE `hdp_zhuanzhuan_dim_global.dim_zpm_page_info_full_1d_0p`(
    `page_id` string COMMENT '页面ID',
    `page_name` string COMMENT '页面名称',
    `page_url` string COMMENT '页面链接',
    `page_level` string COMMENT '页面层级',
    `parent_page_id` string COMMENT '父页面id',
    `parent_page_name` string COMMENT '父页面名称',
    `project_id` string COMMENT '所属项目ID',
    `project_name` string COMMENT '所属项目名称',
    `mofang_page_id` string COMMENT '魔方页面id',
    `mofang_page_name` string COMMENT '魔方页面名称')
COMMENT '高斯页面维表'
ROW FORMAT SERDE
    'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
STORED AS INPUTFORMAT
    'org.apache.hadoop.mapred.TextInputFormat'
OUTPUTFORMAT
    'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION
    'viewfs://58-cluster/home/hdp_ubu_zhuanzhuan/warehouse/hdp_zhuanzhuan_dim_global/dim_zpm_page_info_full_1d_0p'
TBLPROPERTIES (
    'last_modified_by'='hdp_ubu_zhuanzhuan',
    'last_modified_time'='1738827594',
    'transient_lastDdlTime'='1781368589')

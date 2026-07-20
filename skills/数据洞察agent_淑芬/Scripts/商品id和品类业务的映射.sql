-- ============================================================
-- 商品表 dw_mysql_info_full_1d：建表结构 + 商品id→业务/品类 映射逻辑（只读参考，勿直接跑全表）
-- 用途：当分析涉及「品类 / 业务 / 商品颗粒度」信息时，用本文件取口径——
--   · 部分1：info_id → cate(业务类型:消费电子/二奢/兴趣/其他) + cate_02(品类:手机/平板/包袋/腕表…) 的官方映射 CASE。
--     淑芬流水线里 module_click_conv_aov 的 info 品类限定就用同一套 cus_business_bu/cate 口径，需要按品类/业务下钻时复用这段。
--   · 部分2：商品表 hdp_zhuanzhuan_dw_global.dw_mysql_info_full_1d 的完整字段结构（CREATE 语句，只读，勿执行建表）。
-- 平台：星河（Hive/SparkSQL 均可，无 hash 依赖）。
-- 分区：dw_mysql_info_full_1d 按 dt 分区，必带 WHERE a.dt='${outFileSuffix}'（默认 t-1），否则扫全表被拒。
-- 口径铁律：官方业务/品类映射以本 CASE 为准，不要自己臆造品类归并；剔充配(is_cp_flag='0')、剔直播代下单(is_live_flag='0')。
-- ============================================================


/*部分1: 商品id info_id 和 业务类型 cate 以及 品类类型 cate_02的映射逻辑 */
        select  case when cus_business_bu in ('消费电子') then '消费电子'
                                when cus_business_bu in ('二奢') and business_line_id in(915051,915061) then '二奢'--重奢部分
                                when cus_business_bu in ('二奢') then '兴趣'--主要是兴趣n的球鞋部分
                                when cus_business_bu in ('长尾N') then '兴趣'
                            -- when cus_business_belong in ('B2C') and cate_second_id in ('120') then '二手车'
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
                                when cus_business_bu in ('长尾N') and cate_id in ('1100001939','1100003419')then '球拍'
                                when cus_business_bu in ('长尾N') then '兴趣N-其他'

                                when cate_first_id = '1100000354' then '包袋'
                                when cate_third_id in ('1100001005','1100001007') then '腕表'
                                when cate_second_id in ('1100003055','1100001004','2111008','1100001516') then '饰品'
                                when cate_second_id in ('2111003','2111004','2111010','2111011','2111012','2111013','2111014','2111015','2111019','1100000315','1100001428','1100001438','1100003527') then '鞋服'
                                else '奢侈品-其他' end as cate_02
                ,info_id
            from hdp_zhuanzhuan_dw_global.dw_mysql_info_full_1d a
            where 1 = 1
                and a.dt = '${outFileSuffix}'
                and cus_business_extend['is_cp_flag'] = '0' -- 剔除充配
                and cus_business_extend['is_live_flag'] = '0'  --剔除直播代下单账号
                and (cus_business_bu in ('消费电子','长尾N','二奢')  or (cus_business_belong in ('B2C') and cate_second_id in ('120')) or (cate_id ='2120006' and cus_business_belong in ('B2C')))
            group by 1,2,3


/*部分2: 商品表的表结构 hdp_zhuanzhuan_dw_global.dw_mysql_info_full_1d（只读结构，勿执行建表） */
CREATE EXTERNAL TABLE `hdp_zhuanzhuan_dw_global.dw_mysql_info_full_1d`(
  `info_id` bigint COMMENT '商品Id',
  `uid` bigint COMMENT '卖家id（官方卖家:36554880997655,48851789433103,41175708073236,34857644331526,48387006057751,47614546120980,48412354403344）',
  `cate_third_id` int COMMENT '三级分类Id',
  `cate_second_id` int COMMENT '二级分类Id',
  `cate_first_id` int COMMENT '一级分类Id',
  `cate_third_name` string COMMENT '三级分类',
  `cate_second_name` string COMMENT '二级分类',
  `cate_first_name` string COMMENT '一级分类',
  `timestamp` bigint COMMENT '发布时间戳（毫秒）',
  `title` string COMMENT '标题',
  `content` string COMMENT '商品描述',
  `ori_price` int COMMENT '原价（分）',
  `now_price` int COMMENT '现价（分）',
  `pics` string COMMENT '图片列表',
  `label` string COMMENT '商品标签',
  `status` smallint COMMENT '1正常 2交易中 3交易完成（下架） 4用户删除（已售出） 5用户删除（不想卖了） 6系统删除 7 过期下架 8彻底删除 9商品被spam干掉了，可以上架 10商品被spam干掉了，不可以上架',
  `city_id` string COMMENT '城市id',
  `area_id` string COMMENT '地区id',
  `city_name` string COMMENT '城市',
  `area_name` string COMMENT '地区',
  `village` bigint COMMENT '乡村',
  `longitude` double COMMENT '经度',
  `latitude` double COMMENT '纬度',
  `freight` int COMMENT '邮费（分）',
  `update_timestamp` bigint COMMENT '更新时间（毫秒）',
  `sex_identify` smallint COMMENT '0表示中性，1代表男性，2代表女性',
  `business` int COMMENT '街道id',
  `postage_explain` tinyint COMMENT '邮费说明, 0表示用户输入, 1表示待议, 2表示包邮',
  `audited` tinyint COMMENT '商品被审核的状态，0表示未被审核，1表示已被审核',
  `searchable` tinyint COMMENT '商品 是否能搜索，0不能搜索，1可以搜索，默认1',
  `info_type` smallint COMMENT '0代表普通商品，1表示优品，20：一元购，21：普通多库存商品（临时运营活动的商品请从100开始编号）',
  `first_price` int COMMENT '首次发布价格（分）',
  `act_type_id` int COMMENT '活动类型id,参考info_act_type',
  `info_op_type` int COMMENT '商品操作类型, 比如用户商品报名参加了某个活动之后, 不允许其对商品进行修改 ,0表示没有限制, 1:母婴活动, 不允许用户编辑商品',
  `source_type` int COMMENT '商品来源',
  `is_new` tinyint COMMENT '是否是当天新发布商品',
  `is_valid_pub` tinyint COMMENT '是否有效发布的商品',
  `cate_sex_identify` smallint COMMENT '0表示中性，1代表男性，2代表女性',
  `cate_label` string COMMENT '分类标签',
  `cate_min_age` smallint COMMENT '该品类适用最小年龄',
  `cate_max_age` smallint COMMENT '该品类适用最大年龄',
  `extra_services` string COMMENT '服务信息',
  `extra_params` string COMMENT '参数信息',
  `brand_id` bigint COMMENT '商品品牌id',
  `brand_name` string COMMENT '商品品牌名称',
  `other_info_id` bigint COMMENT '其他部门商品id',
  `app_id` tinyint COMMENT '卖家类型，0转转内部,1优品,39图书',
  `present` string COMMENT '赠品',
  `total_count` int COMMENT '总库存数',
  `surplus_unit_count` int COMMENT '剩余库存',
  `virtual_surplus_unit_count` int COMMENT '剩余的虚拟库存数,用来锁定',
  `pt_type` smallint COMMENT '商品所属：1 平台、2 欢乐送',
  `credit_price` int COMMENT '商品兑换积分',
  `refresh_time` bigint COMMENT '商品刷新时间',
  `cate_fourth_id` int COMMENT '四级分类id',
  `cate_fourth_name` string COMMENT '四级分类',
  `cate_fifth_id` int COMMENT '五级分类id',
  `cate_fifth_name` string COMMENT '五级分类',
  `business_line_id` int COMMENT '业务线Id',
  `model_id` int COMMENT '机型id',
  `model_name` string COMMENT '机型名称',
  `o_full_path` string COMMENT '老分类体系分类全路径',
  `n_full_path` string COMMENT '新分类体系分类全路径',
  `cate_grand_id` int COMMENT '最细分类id',
  `spu_id` bigint COMMENT 'SPU ID',
  `son_status` int COMMENT '商品子状态',
  `extra_params_new` string COMMENT '盘古参数信息',
  `new_business_line_id` string COMMENT '拆分业务线',
  `belong_bu` string COMMENT 'BU归属',
  `cus_business_belong` string COMMENT '自定义一级业务归属',
  `cus_business_bu` string COMMENT '自定义二级业务归属',
  `cus_business_extend` map<string,string> COMMENT '自定义业务扩展信息，is_cp_flag：是否充配类目；is_live_flag：是否直播代下单用户；cus_big_cate_name：B2C消费电子自定义大类目；cus_small_cate_name：B2C消费电子自定义小类目',
  `oms_sku_id` string COMMENT 'oms_sku_id',
  `qc_code` string COMMENT '质检码',
  `goods_source` string COMMENT '货源',
  `business_mode` string COMMENT '业务模式',
  `cate_id` int COMMENT '末级品类id(可能是一二三级)',
  `c2_goods_source` string COMMENT 'c2卖场货源',
  `c2_business_mode` string COMMENT 'c2卖场业务模式',
  `series_id` int COMMENT '系列id',
  `series_name` string COMMENT '系统名称',
  `spec_appearance_quality` string COMMENT '外观成色',
  `spec_function_quality` string COMMENT '功能成色')
COMMENT '全量商品表（转转+找靓机数据）'
PARTITIONED BY (
  `dt` string COMMENT '分区，yyyy-MM-dd')
ROW FORMAT SERDE
  'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
WITH SERDEPROPERTIES (
  'colelction.delim'=',',
  'field.delim'='',
  'mapkey.delim'=':',
  'serialization.format'='',
  'serialization.null.format'='')
STORED AS INPUTFORMAT
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat'
OUTPUTFORMAT
  'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION
  'viewfs://58-cluster/home/hdp_ubu_zhuanzhuan/warehouse/hdp_zhuanzhuan_dw_global/dw_mysql_info_full_1d'
TBLPROPERTIES (
  'last_modified_by'='hdp_ubu_zhuanzhuan',
  'last_modified_time'='1734509189',
  'transient_lastDdlTime'='1734509190')

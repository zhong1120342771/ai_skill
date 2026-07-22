<!--
本文件由 sync_data_map.py 每天自动同步自飞书数据地图，不要手改。
飞书源：https://zhuanspirit.feishu.cn/docx/KyzVdTWxtoQdpaxSPekctvJHneb
最后同步：2026-07-02 13:54:20
revision_id：58

要改数据地图请去飞书文档改（业务方唯一维护源），改完等次日 08:57 自动同步；
急用可手动跑 `python3 $SKILL_DIR/scripts/sync_data_map.py`
-->

<title>转转数据地图 · 常用Hive表导航</title>

<callout emoji="📌">
**数据地图总览**：28张常用Hive表，按**平台型**（用户/流量/商品/日志/搜索/订单回收/推荐特征）和**业务型**（二奢/潮玩/骑行）两大类组织。
顶部为思维导图视觉总览，下方为按分支顺序的表清单，每个表节点包含**中文名+Hive表名+核心信息+星河超链接**。
分区字段统一为 `dt`（yyyy-MM-dd），所有查询必须带 dt 条件。`dw_log_lego_action_1d` 另有 `region` 二级分区。
</callout>

<callout emoji="🔑">
**通用速查（所有表都会用到，写 SQL 前必看）**
**terminal 编码**：`15`=iOS / `16`=Android / `20`=转转小程序 / `103`=其他/微信小程序等 —— 一般组合 `terminal IN (15,16,20)` 或 `(15,16,103)`
**行为漏斗三键关联**：`dt + token + request_mark`（`dw_log_server_action_1d` 内 `request_mark = datapool['rstmark']`）
**收藏/加购四键关联**：`dt + token + info_id + metric_md5 + request_mark`（收藏/加购表按曝光实例落，比行为漏斗多一个 `metric_md5`）
**搜索会话唯一键**：`request_id = CONCAT(dt, '#', token, '#', rstmark, '#', query)`；宽表新增 `ws_id`（session 粒度）
**反作弊过滤**：搜索宽表必加 `is_spam = 0 AND period = 1`；`dw_log_server_action_1d` 必加 `region = 'z'`
**SQL 硬规则**：脱敏禁止 `SELECT *`（CTE 内也不行）；大整数（`info_id / order_id` 19 位）必须 `CAST AS string`；中文别名必须反引号；搜索词清洗 `regexp_replace(query, unhex('01'), '')`
**ID 系映射**：`buyer_id = seller_id = uid = user_id`（可直接 join）；`token ≠ uid`（需过桥表转换）
</callout>

---

# 🗺️ 数据地图思维导图

<whiteboard token="A85swYwZKhXuTxbtCQ9cv81Mntg"></whiteboard>

（下方为放射状思维导图白板，可点击节点文字查看。详细表信息和星河超链接见下方各章节）

# 一、平台型

覆盖用户、流量、商品、日志、搜索、订单回收、推荐特征 7 个子域，共 22 张表。

## 1.1 用户与分层

- **用户活跃明细** · `hdp_zhuanzhuan_dm_global.dm_oper_key_user_detail_inc_1d` · DAU 和核心 UV 明细表 · 核心字段: `uid, token, is_key_user, user_type, scene_type1/2, first_from, sec_from, channel` · [星河表详情](https://dp.58corp.com/data-map/detail-page/716426)
- **用户分层明细** · `hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d` · 平台用户分层（八大人群/B2C核心业务/terminal_name） · 核心字段: `token, terminal_name, user_layer, user_source` · [星河表详情](https://dp.58corp.com/data-map/detail-page/862662)
- **人群标签(uid维度)** · `hdp_zhuanzhuan_dw_global.dw_user_label_group_uid_full_1d` · 按 uid 维度的人群圈选表（价格敏感度等） · [星河表详情](https://dp.58corp.com/data-map/detail-page/659126)
- **人群标签(token维度)** · `hdp_zhuanzhuan_dw_global.dw_user_label_group_token_full_1d` · 按 token 维度的人群圈选表 · [星河表详情](https://dp.58corp.com/data-map/detail-page/658774)

用户身份、分层、标签圈选相关表。

## 1.2 流量漏斗

- **列表页曝光明细** · `hdp_zhuanzhuan_dm_global.dm_trade_exposure_info_detail_inc_1d` · 列表页曝光商品明细 · 字段: `token, uid, info_id, page, idx, first_from, sec_from, cate_first/second/third_id` · [星河](https://dp.58corp.com/data-map/detail-page/708892)
- **商详访问明细** · `hdp_zhuanzhuan_dm_global.dm_trade_visit_detail_1d` · 访问详情页商品明细 · 字段: `token, uid, info_id, first_from, sec_from, cate_*` · [星河](https://dp.58corp.com/data-map/detail-page/101937)
- **商品收藏明细** · `hdp_zhuanzhuan_dm_global.dm_trade_addlove_detail_1d` · 商品收藏事件明细 · 字段: `token, uid, info_id, page, idx` · [星河](https://dp.58corp.com/data-map/detail-page/164240)
- **加购明细** · `hdp_zhuanzhuan_dm_global.dm_trade_list2cart_detail_1d` · 加入购物车事件明细 · 字段: `token, uid, info_id, request_mark, business_line_id, business_belong, init_from` · [星河](https://dp.58corp.com/data-map/detail-page/118316)
- **下单页明细** · `hdp_zhuanzhuan_dm_global.dm_trade_buy_page_detail_1d` · 进入下单页事件（C1C2漏斗关键节点） · 字段: `token, uid, info_id, order_id, first_from, sec_from, init_from, business_line_id` · [星河](https://dp.58corp.com/data-map/detail-page/102475)
- **拍下订单明细** · `hdp_zhuanzhuan_dm_global.dm_trade_order_detail_1d` · 拍下订单事实表（订单渠道来源归因） · 字段: `order_id, uid, info_id, first_from, sec_from, init_from, pay_price, business_line_id, parent_order_id` · [星河](https://dp.58corp.com/data-map/detail-page/102537)
- **支付订单明细** · `hdp_zhuanzhuan_dm_global.dm_trade_pay_detail_1d` · 支付订单事实表 · 字段: `order_id, uid, info_id, pay_price, pay_service_price, first_from, sec_from` · [星河](https://dp.58corp.com/data-map/detail-page/102558)

曝光→商详→收藏/加购→下单页→拍下→支付 的完整漏斗事实表。

## 1.3 商品域

- **全量商品表** · `hdp_zhuanzhuan_dw_global.dw_mysql_info_full_1d` · 全量商品（转转+找靓机，MySQL同步） · 字段: `info_id, uid(卖家), title, cate_first/second/third_id/name, now_price, ori_price, status, business_mode, brand_name, model_name, goods_source, cus_business_bu, business_line_id, cus_business_extend` · [星河](https://dp.58corp.com/data-map/detail-page/476956)
- **购物车** · `hdp_zhuanzhuan_rawdb_global.cart_info` · rawdb 购物车表 · 字段: `id, buyer_id, info_id, info_amount, is_selected, seller_id, price, metric` · [星河](https://dp.58corp.com/data-map/detail-page/132861)
- **商品属性维度** · `hdp_zhuanzhuan_dim_global.dim_info_spu_model_full_1d_0p` · SPU型号属性维度表（param/value 维度） · [星河](https://dp.58corp.com/data-map/detail-page/650510)
- **品类维度** · `hdp_zhuanzhuan_dim_global.dim_info_category_full_1d_0p` · 类目ID/名称/层级维度表 · [星河](https://dp.58corp.com/data-map/detail-page/572929)

商品 info、购物车、商品属性、品类维度。

## 1.4 日志域

- **前端埋点日志** · `hdp_zhuanzhuan_dw_global.dw_log_lego_action_1d` · lego 前端埋点日志（有 region 二级分区） · 字段: `uid, token, cookieid, timestamp, pagetype, actiontype, source, datapool, appid` · [星河](https://dp.58corp.com/data-map/detail-page/99416)
- **服务端行动日志** · `hdp_zhuanzhuan_dw_global.dw_log_server_action_1d` · 服务端行动日志（搜索query/召回/feed流计算） · **关键过滤**：`region='z'`、`action='zzappsearch'`（搜索行为）、`datapool['tabid']='0'`（商品搜索 tab） · 字段: `token, uid, action, cmd, region, terminal`；**datapool 常用 key**：`orikeyword`（搜索词原文，含 \x01 分隔符需清洗；`keyword` 常空**勿用**）、`rstmark`（= 下游 `request_mark`）、`tabid`（=`0` 商品搜索）、`qrhitcate`（命中类目）、`infoid_list`（曝光商品列表）、`result`（召回结果）、`searchfilter_click`（筛选/排序使用 JSON，见下） · [星河](https://dp.58corp.com/data-map/detail-page/98640)
- 

  <callout emoji="🔍">
  **`searchfilter_click` JSON 结构**（用 `get_json_object(datapool['searchfilter_click'], '$.key')` 拆）：
  `$.filterUsage`（是否用了任意筛选，'1'=用）、`$.staticFilterUsage`（静态筛选）、`$.brandWallFilterUsage`（品牌墙）、`$.fastFilterUsage`（快筛/顶部tag）、`$.drawerFilterUsage`（抽屉筛选）、`$.recommendFilterUsage`（推荐筛选）、`$.sortpolicyFilter`（排序：`0`默认/`1`最新/`2,3`价格升降/`4`距离/其他=自定义）
  </callout>
- **保卖前端日志** · `hdp_ubu_zhuanzhuan_dw_c2b.dw_traffic_zz_ub_lego_dtl_inc_1d` · 保卖 C2B 前端埋点明细 · 字段: `app_type, terminal, channel_id, cate_id, page_type, action_type, token, uid, log_time` · [星河](https://dp.58corp.com/data-map/detail-page/542763)

前端埋点、服务端行动、保卖前端日志。

## 1.5 搜索域

- **搜索全链路明细** · `hdp_zhuanzhuan_dw_global.dw_dwb_search_full_link_full_1d` · 搜索 query → 曝光 → 点击 → 订单归因全链路（二级分区: period/action/is_spam/seller_type/terminal） · **关键过滤**：`action='search'`、`is_spam=0`（反作弊）、`period=1`（埋点标准）、`terminal IN (15,16,103)` · 字段: `uid, token, ws_id`（session id，一次搜索到分页共享）、`rstmark`（request 粒度）、`query, info_id, brand, model, cate1id, context, seller_type`、**漏斗计数**``pv/click/`order`/pay``（`order` 是保留字需反引号）、**坑位**`` page/`index` ``（0-indexed，`index` 也是保留字）、**时间戳**`pv_timestamp/click_timestamp/pay_timestamp`（长度≥13 位为毫秒需 /1000）、**曝光唯一标识**`md5`（跨曝光/收藏/加购 join 用，对应下游 `metric_md5`） · [星河](https://dp.58corp.com/data-map/detail-page/717429)
- **搜索意图分类表** · `hdp_zhuanzhuan_dw_global.dw_traffic_ub_zzappsearch_query_intention_detail_inc_1d` · 每个 query 的意图类型标签（精确/泛意图） · 字段: `dt, token, keyword, request_mark, intention_type`（`intention_type=5` 精确意图，`1-4` 泛意图） · [星河](https://dp.58corp.com/data-map/detail-page/436733450)

搜索全链路明细（query→曝光→点击→订单归因）。

## 1.6 订单与回收

- **全局订单模型表** · `hdp_zhuanzhuan_dw_global.dw_trade_order_company_all_detail_full_1d` · 全状态/全类型订单事实表 · 字段: `order_id, parent_order_id, status`（`1`待支付/`3`支付成功/`4`已发货/`5,6,21,22`交易成功/`7,16,17`退款成功/`13,19`买家取消/`14,20`卖家取消）`, order_type, pay_type, info_id, total_amt`（分）`, seller_id, buyer_id, pay_time, create_time, brand_name, model_name, cate_*, order_source, order_flag, logistics_company, is_pure_pay_the_day, is_exchange_order_flag, app_type` · **净支付口径**：`is_pure_pay_the_day=1 AND is_exchange_order_flag=0`（当日净支付、非换货单） · [星河](https://dp.58corp.com/data-map/detail-page/633721)
- **回收订单明细** · `hdp_ubu_zhuanzhuan_dm_c2b.dm_recycle_order_detail_full_1d` · C2B 回收订单（含转转/找靓机） · 字段: `rec_order_id, rec_parent_order_id, order_source, perform(履约方式), platform_id(1转转/2找靓机), rec_state, seller_id, create_time, pay_time, deal_time, cancel_time, total_real_price, qc_code, order_cate_name, order_brand_name, order_model_name` · [星河](https://dp.58corp.com/data-map/detail-page/533772)
- **估价成功明细** · `hdp_ubu_zhuanzhuan_dw_c2b.dw_trade_recycle_eval_success_dtl_inc_1d` · 估价成功事件明细 · 字段: `token, uid, channel, terminal, cate_id, brand_id, model_id, qc_code, highest_price, predict_price, coupon_price, eval_source, eva_from` · [星河](https://dp.58corp.com/data-map/detail-page/520809)

全局订单模型、回收订单、估价成功。

## 1.7 推荐特征

- **推荐模型特征输出** · `hdp_zhuanzhuan_dm_rec.dm_model2_features_output_full_1d` · model2 推荐特征输出全量表（3C/二奢/N 类评分 + 特征 KV 串） · 二级分区: `type`(req/inventory等) · 字段: `token, timestamp, logid, features(特征集合), score_3c, score_ershe, score_n, type` · [星河](https://dp.58corp.com/data-map/detail-page/909795)

推荐模型特征输出。

# 二、业务型

二奢、潮玩、骑行 3 个业务线的专属表。骑行复用潮玩寄卖表（`cate_first_id=105`）。

## 2.1 二奢

- **二奢用户行动表** · `hdp_ubu_zhuanzhuan_ads_lux.ads_lux_traffic_zz_user_action_inc_1d` · 二奢用户行动/分层/新老客/来源（业务视角） · 字段: `token, life_cycle(二奢新老客), user_tag(深度用户), user_tag2(新媒/自然), user_source` · [星河](https://dp.58corp.com/data-map/detail-page/909174)
- **二奢商品明细** · `hdp_zhuanzhuan_dw_global.dwd_lux_info_detail_full_1d` · 二奢货盘 ABC/XYZ 分级（全渠道/转转/红布林/线下仓店） · 字段: `ref_info_id, type, abc_xyz_class, zz_abc_xyz_class, hbl_abc_xyz_class, warehouse_abc_xyz_class` · [星河](https://dp.58corp.com/data-map/detail-page/851571)
- **奢品馆流量明细** · `hdp_ubu_zhuanzhuan_dw_lux.dwd_traffic_ub_lux_zz_detail_inc_1d` · 奢品馆金刚位/运营Banner组货场景流量漏斗（曝光/访问/交易/订单/支付计数） · 字段: `token, business_line_id, terminal, module_name_1/2, exposure_cnt, visit_cnt, trade_cnt, order_cnt, pay_cnt, info_id, lux_token_identity, lux_intent_type, lux_first_visit_date` · [星河](https://dp.58corp.com/data-map/detail-page/898973)

二奢用户行动、二奢商品、奢品馆流量。

## 2.2 兴趣品类

### 2.2.1 潮玩

- **潮玩商品范围主表** · `hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_info_detail_full_1d` · 潮玩寄卖商品范围主表（`cate_second_id=1100003636` 或 `business_line_id in (904011)`） · 字段: `info_id, cate_first_id, cate_second_id, business_line_id, status, model_name, brand_name, surplus_unit_count`（`status=1` 在售 / `surplus_unit_count>0` 有库存） · [星河](https://dp.58corp.com/data-map/detail-page/898139)
- **潮玩订单销售事实表** · `hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d` · 潮玩寄卖订单销售事实表（支付/交付订单过滤） · 字段: `order_id, cate_first_id, cate_second_id, deliver_time, info_id, buyer_id, pay_time, create_time, price, is_trade_success` · **完成交易过滤**：`is_trade_success=1`（供给匹配度/成交订单分析必加） · [星河](https://dp.58corp.com/data-map/detail-page/898006)

潮玩商品范围、潮玩订单销售。

### 2.2.2 骑行

- **骑行商品范围** · `hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_info_detail_full_1d` · 复用潮玩寄卖商品表，按 `cate_first_id=105` 过滤骑行商品 · [星河](https://dp.58corp.com/data-map/detail-page/898139)
- **骑行订单销售** · `hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d` · 复用潮玩订单销售表，按 `cate_first_id=105` 过滤骑行订单 · [星河](https://dp.58corp.com/data-map/detail-page/898006)

<callout emoji="💡">
骑行专项分析还用到平台型表：`dm_trade_order_detail_1d`(支付订单来源)、`dm_trade_visit_detail_1d`(商详转化)、`dm_trade_addlove_detail_1d`(收藏)、`dm_trade_list2cart_detail_1d`(加购)、`dm_trade_pay_detail_1d`(消费电子交叉)、`dw_dwb_search_full_link_full_1d`(搜索词)、`dw_mysql_info_full_1d`(商品详情)。详见 \~/Desktop/测试代码/空间盘点/兴趣/骑行/。
</callout>

复用潮玩寄卖两张表，按 `cate_first_id=105` 过滤。
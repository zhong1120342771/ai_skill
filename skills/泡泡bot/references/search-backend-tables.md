# 转转搜索/交易后端表清单

> 来源：海仓 `zhuanzhuan-data-query` skill 的 backend-tables，多次实测取数验证。
> 与 `business-glossary.md` 的关系：`business-glossary.md` 是全局 ID / 字段映射（`buyer_id = uid`、`token ≠ uid`），本文件是**搜索链路**专用的表和字段清单。
> 库名：`hdp_zhuanzhuan_dw_global` / `hdp_zhuanzhuan_dm_global`

## 核心表

| 表名 | 用途 | 关键字段 / 过滤 |
|---|---|---|
| `dw_dwb_search_full_link_full_1d` | **搜索全链路宽表（推荐）** | 单表含完整漏斗 `pv` / `click` / `order` / `pay` + 商品/类目 id；`ws_id` / `rstmark` / `pv_timestamp` / `page` / `index` / `md5` / `brand` / `model` / `is_spam=0` / `period=1` / `cate1id` |
| `dw_log_server_action_1d` | 在线行为序列表 / 搜索主表 | `action='zzappsearch'`、`region='z'`、`terminal in(15,16,20)`、`datapool['tabid']='0'`；`datapool` 内：`searchfilter_click`(JSON,含 `filterUsage` 等)、`orikeyword`(搜索词,`keyword` 常空**勿用**)、`rstmark`(=`request_mark`) |
| `dm_trade_exposure_info_detail_inc_1d` | 曝光行为（商品/商详） | `dt` / `token` / `info_id` / `request_mark` |
| `dm_trade_visit_detail_1d` | 访问/商详表 | `dt` / `token` / `info_id` / `request_mark`；`first_from`（一级流量来源）、`init_from`（原生流量来源） |
| `dm_trade_order_detail_1d` | 下单 | `dt` / `token` / `info_id` / `request_mark` / `order_id` |
| `dm_trade_pay_detail_1d` | 支付 | `dt` / `token` / `info_id` / `request_mark` / `order_id` |
| `dw_trade_order_company_all_detail_full_1d` | 净支付 | `pay_time` / `order_id` / `app_type`；`is_pure_pay_the_day=1 AND is_exchange_order_flag=0` |
| `dw_mysql_info_full_1d` | 商品信息维表 | `info_id` / `title` / `brand_name` / `model_name`；`cate_first/second/third/fourth/fifth_name+_id`；`cus_business_bu` |
| `dw_traffic_ub_zzappsearch_query_intention_detail_inc_1d` | 搜索意图表 | `dt` / `token` / `request_mark` / `intention_type` |
| `dm_oper_user_layer_dtl_inc_1d` | B2C 用户分层表 | `user_layer`（JSON, 含 Z0-Z5 等）；**token 粒度**，需 token→uid 转换 |
| `dm_trade_addlove_detail_1d` | 收藏行为 | `dt` / `token` / `info_id` / `request_mark` / `metric_md5`；`first_from IN ('search','weixin_search')` 过滤搜索来源 |
| `dm_trade_list2cart_detail_1d` | 加购行为 | 同上 |

## 关联键

- **商品维度**：`a.info_id = c.info_id`
- **行为 ↔ 漏斗 ↔ 意图**：三键 `dt + token + request_mark`
  - `server_action` 表里 `request_mark = datapool['rstmark']`
- **搜索会话唯一键**（骑行专项实战范式）：
  ```
  request_id = CONCAT(dt, '#', token, '#', rstmark, '#', query)
  ```
- **`ws_id` vs `rstmark`**：宽表新增了 `ws_id`（会话 id），一次搜索到分页翻页共享同一个 `ws_id`；`rstmark` 是每次请求粒度。session 粒度分析用 `ws_id`，请求粒度分析用 `rstmark`。

## 指标口径

- 曝光 PV = `count(info_id)`
- 搜索次数 = `count(distinct token, logid)` 或 `count(distinct request_id)`
- 搜索 UV / 曝光 UV = `count(distinct token)`
- 意图分类：`case when intention_type=5 then '精确意图' else '泛意图' end`
- 整体 UV / 曝光 UV **必须 SQL 全集 `count(distinct)` 去重**，禁止"使用筛选 + 未使用"相加（人跨组重叠会虚高，详见 `sql-pitfalls.md` 坑4）
- 大整数（`info_id` 19 位）取数**必须 `cast as string`**（详见 `sql-pitfalls.md` 坑2）
- 脱敏规则禁止 `SELECT *`（CTE 内也不行）；中文列别名必须反引号

## 宽表 `dw_dwb_search_full_link_full_1d` 字段映射

| 字段 | 含义 |
|---|---|
| `pv` | 曝光 PV |
| `click` | 商详点击 PV/UV |
| `order` | 下单量（保留字，写 SQL 用反引号 `` `order` ``） |
| `pay` | 支付量 |
| `pv_timestamp` | 曝光时间戳（毫秒/秒混用，长度 ≥13 位为毫秒，需 `/1000`） |
| `click_timestamp` | 点击时间戳 |
| `pay_timestamp` | 支付时间戳 |
| `is_spam` | 反作弊标记，`=0` 才是有效数据 |
| `period` | 埋点周期，`=1` 标准过滤 |
| `page` / `index` | 分页页码 / 位置（0-indexed，`index` 是保留字需反引号 `` `index` ``） |
| `md5` / `metric_md5` | 商品曝光的唯一标识，跨曝光/收藏/加购 join 用 |

## `datapool` 常用 key（`dw_log_server_action_1d`）

| key | 含义 |
|---|---|
| `datapool['orikeyword']` | 搜索词原文（含 `\x01` 分隔符，需 `regexp_replace(..., unhex('01'), '')`） |
| `datapool['rstmark']` | 请求标识，= 下游漏斗表 `request_mark` |
| `datapool['tabid']` | tab 分类，`'0'` 是商品搜索 tab |
| `datapool['searchfilter_click']` | JSON 字符串，含筛选/排序使用情况（下方展开） |

## `datapool['searchfilter_click']` JSON 结构（骑行专项实战）

用 `get_json_object(l.datapool['searchfilter_click'], '$.xxx')` 拆解。

| JSON key | 含义 | 取值 |
|---|---|---|
| `$.filterUsage` | 本次请求是否用了任意筛选 | `'1'` 用 / 其他 未用 |
| `$.staticFilterUsage` | 静态筛选（例如品类/成色 checkbox） | `'1'` / 其他 |
| `$.brandWallFilterUsage` | 品牌墙筛选 | `'1'` / 其他 |
| `$.fastFilterUsage` | 快筛（顶部快捷 tag） | `'1'` / 其他 |
| `$.drawerFilterUsage` | 抽屉筛选（右侧完整筛选面板） | `'1'` / 其他 |
| `$.recommendFilterUsage` | 推荐筛选（智能推荐 tag） | `'1'` / 其他 |
| `$.sortpolicyFilter` | 排序策略 | `'0'` 默认 / `'1'` 最新 / `'2'`,`'3'` 价格升降 / `'4'` 距离 / 其他 |

## 取数环境

One-Service：https://oneservice.zhuanspirit.com

**性能预期**（海仓实测）：
- **单表宽表**：2-3 分钟/条
- **5 表 join**：6-12 分钟/条

优先用宽表，除非宽表未覆盖的特殊字段（如 `searchfilter_click` JSON）才回退到 `dw_log_server_action_1d`。

## 相关参考

- 通用 SQL 陷阱 → `sql-pitfalls.md`
- 全局 ID 映射（`buyer_id` / `uid` / `token`）→ `business-glossary.md`
- 场景字段（`first_from` / `sec_from` / `init_from` / `page`+`idx` / `module_name_*`）→ `business-glossary.md` §"渠道/场景/坑位字段"

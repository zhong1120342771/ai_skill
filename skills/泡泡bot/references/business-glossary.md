# 业务术语 & ID 全局映射

> 跑数 skill 里**全局通用的字段/术语映射**。写 SQL 时遇到这些字段，**直接当已知映射使用，不要再去 describe 表试图发现"它跟其他字段啥关系"**。

业务侧每次更新就同步本文件，是单一事实来源。

## ID 字段通用映射

| 字段名 | 等价于 | 出现场景 |
| --- | --- | --- |
| `buyer_id` | = `user_id`（买家的 UID） | 订单表、寄售表、交易明细表 |
| `seller_id` | = `user_id`（卖家的 UID） | 订单表、寄售表 |
| `uid` | = `user_id`（通用用户 ID，平台粒度） | 用户维表、行为日志表 |
| `user_id` | 平台用户唯一标识 | 标准字段，所有 user-level 表都对得上 |
| `token` | 设备/会话级标识（**注意：不是 user_id**） | 行为埋点表、流量曝光表；需要 join `token-uid` 转换表才能跟 user_id 对得上 |

**关键提醒**：
- `buyer_id` / `seller_id` / `uid` 都是 user_id 系，**互相可以直接 JOIN**
- `token` ≠ `user_id`，需要转换表过桥
- 如果某张表只有 `token` 没 `uid`，写 SQL 前先确认转换表怎么 join

## 品类字段

| 字段名 | 含义 |
| --- | --- |
| `cate_first_id` | 一级品类 ID |
| `cate_first_name` | 一级品类名 |
| `cate_second_id` | 二级品类 ID |
| `cate_third_id` | 三级品类 ID |

**常用品类 ID 备忘**：
- 105 = 骑行（c2b 寄售订单口径）

## 时间字段

| 字段名 | 含义 | 何时用 |
| --- | --- | --- |
| `create_time` | 下单时间 | 看"什么时候下的单"（不论支付状态） |
| `pay_time` | 支付时间 | 看"什么时候支付的"（只算已支付订单） |
| `dt` | 分区日期 | 数据落表的日期，仅做分区过滤，**不当业务日期用** |

## 渠道/场景/坑位字段(埋点五级)

**分不清"场景/坑位/资源位"是最常见的错**——五个字段各有定位,不能混用。

| 字段名 | 语义层级 | 例子 | 表 |
| --- | --- | --- | --- |
| `first_from` | **一级场景**(用户从哪个大入口来) | `search` / `homepage_rec` / `homepage_column` / `int_detail_same` | 订单/行为主表 |
| `sec_from` | **二级来源**(该场景的子分类/落地页/推荐来源) | `home_tuijian_jingxuan` / `1`(直接搜索) / `133`(联想词) / `myLoveInfosM` | 同上 |
| `init_from` | **入口资源位字符串**(含活动 ID / 页面标识) | `G100_2xxx_shiyibutie_yyy` / `2_xxx_0`(首页金刚位) | 同上 |
| `page` + `idx` | **真正的坑位号**(第几页第几个位置,0-indexed) | `page=0 idx=0` → 首屏第一个;`idx=20+` 长尾 | 曝光/商详/下单/支付明细表 |
| `module_name_1/2/3` | **组货模块**(奢品馆/包袋/腕表 频道页里的具体楼层) | `module_name_1='奢品馆'`, `module_name_2 RLIKE '金刚位'` | `hdp_ubu_zhuanzhuan_dw_lux.dwd_traffic_ub_lux_zz_detail_inc_1d` |

**判断口诀**:
- 用户问"来自哪个**场景**" → `first_from` (+`sec_from` 拆二级)
- 用户问"来自哪个**坑位**" → `page`/`idx` 是**首要**(0-19 具体位置 + 20+ 长尾);沿用参考 SQL `首页推荐topN坑位流量漏斗from冯凯丽.sql` 的 topN_clk 模式
- 用户问"来自哪个**资源位**/**活动**" → `init_from` (常见模式 `G100_XXX_YYY_ZZZ`)
- 用户问"来自哪个**模块**/**楼层**" → 走 dw_lux 明细的 `module_name_*` 三级

**沿用参考 SQL 时必看**:
- 一级场景 CASE WHEN 映射:`大漏斗（业务视角）.sql` 的 scene_detail 段(6 类:主搜/频道页/奢品馆feeds/首页精选feeds/同款推荐/其他)
- 二级渠道映射:`骑行/现状/支付订单来源.sql` source_scene_l2(联想词=`sec_from IN ('133','134')` 等)
- 坑位 topN:`首页推荐topN坑位流量漏斗from冯凯丽.sql` `case when page=0 and idx in (0-19) then idx else '20+' end`

**沿用时的自检**:场景映射 CASE WHEN 覆盖不全 → "其他" 占比会 >15%(前提 QA 会 warning),遇到就补映射规则,不能默默塞到"其他"里。

## 用户分层 / 维度字段

| 字段 | 含义 | 表 |
| --- | --- | --- |
| `user_layer` | 平台用户分层标签 JSON（含 Z0-Z5 等） | `hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d` |
| `terminal_name` | 终端（转转APP / 转转M / 微信小程序 等） | 同上 |
| `plat_token_segment` | 平台用户分层（新媒/留存/新增 等） | 待补 |

注意：`dm_oper_user_layer_dtl_inc_1d` 是 **token 粒度**，跟订单表 join 需要先做 token → uid 转换。

---

## 维护说明

- 新发现的全局通用映射 → 写本文件
- 业务侧字段定义变了 → 改本文件 + 通知所有引用方
- 不要把"项目专属的字段"塞进来——只放真正全局通用的

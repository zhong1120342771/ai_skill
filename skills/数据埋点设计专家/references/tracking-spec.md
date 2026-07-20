# 转转埋点规范（设计前必读）

本文件是设计埋点的唯一规范来源。事件名、属性名严格照此写，不要自造。
在线权威版：`https://zhuanspirit.feishu.cn/wiki/LihXwJaUmiIAp8kMpw8cy3i5nBk`（如需最新版用 lark-doc 读取）。

## 目录
- 一、页面整体结构
- 二、事件类型定义（Areaexposure / explosureItems / Sortexposure / zpmclick / explosureGoods / zpmshow / Lengthofstay）
- 三、区域与子区域
- 四、sortId 与 index 的区别
- 五、一级/二级 TAB
- 六、位置模型结构
- 七、区域曝光 vs 组合元素曝光
- 八、数据量级校验
- 九、同页面不同物料卡片
- 十、事件属性速查表
- 十一、事件 × 字段强绑定

---

## 一、页面整体结构

页面级事件：

| 事件名称 | 事件标识 | 属性说明 |
|-|-|-|
| 页面加载 | zpmshow | 当前页面参数 pagequery、是否返回 isback |
| 停留时长 | Lengthofstay | 停留时长(秒) eventduration |

页面内一级 TAB 名称 firsttab、位置顺序 index。**若页面存在一级 TAB，页面内所有事件都要上报 firsttab。**

---

## 二、事件类型定义

### 2.1 区域曝光 — Areaexposure
用途：区域整体曝光，判断功能模块是否出现。

| 属性 | 说明 |
|-|-|
| sectionId | **必填。**区域 ID，从 100 开始三位纯数字，区域中文名在高斯埋点方案维护 |
| subSectionId | 子区域 ID，与所属区域 sectionId 拼接顺序（如 100_0） |
| subSectionName | 子区域名称，中文名随属性上报 |
| secTab | 区域内二级 TAB 名称 |
| index | 位置顺序 |
| title | 运营位标题（部分场景） |
| postid | 运营计划（部分场景） |
| goodsList | 商品 ID 数组（部分场景） |
| rstmark | 会话 ID（部分场景） |

上报规则：随内容展示立即上报；滑动重复展示不再重复上报；离开页面再返回需再次上报。

### 2.2 组合元素曝光 — explosureItems
用途：重复出现且非 feed 流商品的多个元素曝光（金刚位、品牌墙、轮播图），作为元素点击率的分母。

| 属性 | 说明 |
|-|-|
| sectionId | 区域 ID |
| subSectionId | 子区域 ID |
| subSectionName | 子区域名称 |
| sortIdList | 元素 ID 数组，& 分隔 |
| sortNameList | 元素名称数组，& 分隔 |
| postidList | 运营计划数组，& 分隔 |
| goodsList | 商品 ID 数组（部分场景） |

上报规则：离开页面或重新请求时上报；仅记录每个元素第一次出现打包成一条日志；金刚位左右滑、底词轮播不重复记录；各属性拼成 List，& 分隔；某元素缺属性时用空串占位保持分隔符数量（即 `&&`）。
常用属性：sortIdList、sortNameList、搜索词 keyWordList、postidList、榜单 ID rankIdList、TAB 名 tabNameList、顺序 indexList。

### 2.3 区域内元素曝光 — Sortexposure

| 属性 | 说明 |
|-|-|
| sectionId | 区域 ID |
| idList | 元素 ID 数组 |
| nameList | 元素名称数组 |
| postidList | 运营计划数组 |

注意：sortid 使用分段格式，标记轮播图顺序和元素位置。

### 2.4 点击事件 — zpmclick

| 属性 | 说明 |
|-|-|
| sectionId | 区域 ID |
| subSectionId | 子区域 ID |
| subSectionName | 子区域名称 |
| sortId | 元素 ID，从 0 开始 |
| sortName | 元素名称，区分具体元素的任何文案 |
| postid | 运营计划 |
| infoid / infoId | 商品 ID |
| is_rec | 是否动态推荐 |
| index | 位置顺序 |
| price | 商品价格（部分场景） |
| tagName | 商品标签（部分场景） |
| rankName | 榜单入口（部分场景） |
| title | 运营位标题（部分场景） |
| rstmark | 会话 ID（部分场景） |

### 2.5 商品曝光 — explosureGoods

| 属性 | 说明 |
|-|-|
| sectionId | 区域 ID |
| indexList | 位置顺序数组 |
| goodsList | 商品 ID 数组 |
| priceList | 商品价格数组 |
| tagNameList | 商品标签数组 |
| rankNameList | 榜单入口数组 |
| rstmark | 会话 ID |

---

## 三、区域与子区域定义

区域、子区域组成**位置模型**的必要结构。

- **区域整体**：上报一次 Areaexposure，sectionId=100（从 100 起三位纯数字）。
- **子区域**：每个子区域各上报一次 Areaexposure，sectionId 与所属区域一致，subSectionId=100_0（拼接顺序），subSectionName=子区域名称。
- **区域内元素点击（无子区域）**：zpmclick，sectionId=100，sortId=0（从 0 起一位纯数字），sortName=元素名称。
- **子区域内元素点击**：zpmclick，sectionId=100，subSectionId=100_0，subSectionName=子区域名称，sortId=0，sortName=元素名称。

---

## 四、sortId 与 index 的区别

- **sortId**：定位区域内可交互元素，从 0 开始，是【页面→区域→元素】结构的最小单位。
- **index**：标记组件内相同项的排序顺序（TAB 栏、商品卡片），**不是**埋点结构的必要组成。

---

## 五、一级/二级 TAB

TAB 是前端功能组件，不是位置模型的必要结构。但一级、二级 TAB 切换会影响整个页面内容。
**关键规则：页面内若用了一级/二级 TAB 栏，页面内所有区域的曝光、点击事件均需上报 firsttab 和 secTab。**
- firsttab：页面内一级 TAB 名称，属性含 firsttab + index。
- secTab：区域内二级 TAB 名称，属性含 secTab + index。

---

## 六、位置模型结构（V2 五层容器）

容器层级五层，页面嵌套区域、区域嵌套事件、事件嵌套属性：

```
页面(actionType) > 区域(sectionId) > 子区域(subSectionId+subSectionName) > 元素(sortId+sortName) > 商品(infoId)
```

- 子区域 subSectionId 用**下划线** `sectionId_顺序号`，如 `302_0`、`302_1`（顺序号从 0 起）。不要用短横线。
- 核心页面 ID：G1001 首页、G1002 奢品馆、G1003 兴趣圈、G1004 数码集。非新增页面时从页面维表 `hdp_zhuanzhuan_dim_global.dim_zpm_page_info_full_1d_0p`（page_id/page_name）检索，不臆造。
- 非核心区域从区域维表 `hdp_zhuanzhuan_dim_global.dim_zpm_page_section_info_full_1d_0p` 检索。**该维表只有三列 `link_id`（=页面ID/子页面ID，字段名是 link_id 不是 page_id）、`section_id`、`section_name`，且无 dt 分区。**

**section_id 与区域名是一对多，必须带页面限定（实测）：** 同一个 section_id 会被不同页面复用成完全不同的区域。实测单查 section_id=103 返回 377 个不同 section_name，106 有 190 个；只有加上 `link_id`（如 `link_id='G1001'`）才收敛到唯一区域。所以核对区域名务必 `link_id + section_id` 联合查，不能只按 section_id。

下面这张核心区域 ID 对照**仅是 G1001 首页场景下的快速参考，不是全局唯一映射**。脱离首页用到别的页面时，section_id 对应的区域名可能完全不同，真实名称一律以 `link_id + section_id` 实查为准：

| sectionId | 区域名称 | sectionId | 区域名称 |
|-|-|-|-|
| 101 | 搜索栏 | 300 | 品类tab（一级TAB firsttab） |
| 102 | 大促三切分 | 301 | 品牌墙 |
| 103 | 金刚位 | 302 | 栏目区 |
| 105 | 回收模块 | 303 | 大卡片运营 |
| 106 | 场馆tab | 304 | 小卡片运营 |
| 108 | feed商品卡片 | 305 | 场馆氛围条 |
| 109 | feed轮播图 | 306 | 品类氛围条 |
| 110 | feed物料卡片 | 165 | 新人 |

---

## 七、区域曝光 vs 组合元素曝光

| 维度 | 区域曝光 Areaexposure | 组合元素曝光 explosureItems |
|-|-|-|
| 适用场景 | 区域整体曝光，判断模块是否出现 | 重复出现且非 feed 流商品的多个元素（金刚位、品牌墙、轮播图） |
| 上报时机 | 随内容展示立即上报 | 离开页面或重新请求时上报 |
| 重复处理 | 滑动重复展示不再上报；离开再返回需再次上报 | 仅记录每个元素第一次出现，打包成一条日志 |
| 必填属性 | sectionId | sectionId + 元素 ID/名称数组 |
| 数据格式 | 单条事件 | 多条元素拼一条日志，& 分隔 |

---

## 八、数据量级校验（上线后自查）

| 校验规则 | 预期关系 |
|-|-|
| 页面内所有区域 Areaexposure 整体 UV vs 页面整体 zpmshow UV | = 相等 |
| 页面内第一屏区域 Areaexposure 各自 PV vs 页面整体 zpmshow PV | = 相等 |
| 页面内第一屏元素 Sortexposure 整体 PV vs 页面整体 zpmshow PV | >= 大于等于 |

---

## 九、同一页面不同物料卡片

同页面下不同物料卡片，区域 ID 保持一致，通过 **title** 区分类型。

---

## 十、事件属性速查表

| 属性名 | 类型 | 说明 |
|-|-|-|
| sectionId | String | 区域 ID，从 100 开始三位纯数字 |
| subSectionId | String | 子区域 ID，格式 sectionId_顺序号 |
| subSectionName | String | 子区域中文名 |
| sortId | String | 元素 ID，从 0 开始 |
| sortName | String | 元素名称 |
| sortIdList | Array | 元素 ID 数组，& 分隔 |
| sortNameList | Array | 元素名称数组，& 分隔 |
| postid / postidList | String/Array | 运营计划/数组 |
| infoid / infoId / goodsList | String/Array | 商品 ID/数组 |
| firsttab | String | 页面内一级 TAB 名称 |
| secTab | String | 区域内二级 TAB 名称 |
| index / indexList | String/Array | 位置顺序/数组 |
| is_rec | Boolean | 是否动态推荐 |
| price / priceList | String/Array | 商品价格/数组 |
| tagName / tagNameList | String/Array | 商品标签/数组 |
| rankName / rankNameList | String/Array | 榜单入口/数组 |
| title | String | 运营位标题 |
| rstmark | String | 会话 ID |
| pagequery | String | 当前页面参数 |
| isback | Boolean | 是否返回 |
| eventduration | Number | 停留时长(秒) |
| businessMetricMap / businessMetricMapList | String/Array | 新媒体业务标识/数组 |
| rotationIndex | String | 轮播位序号 |
| firstTabIndex | String | 一级 TAB 序号 |
| ABContent | String | AB 分组 |

---

## 十一、事件 × 字段强绑定（别把数组字段名写串）

同样是"元素名称数组""元素ID数组"，不同事件用的字段名不一样，写方案时最容易串。以下面为准，不要跨事件套用：

| 事件 | 元素 ID 字段 | 元素名称字段 | 商品字段 | 其他关键字段 |
|-|-|-|-|-|
| Areaexposure 区域曝光 | sectionId（单值） | subSectionName（子区域名，单值） | goodsList（部分场景） | subSectionId、index、rstmark |
| explosureItems 组合元素曝光 | **sortIdList** | **sortNameList** | goodsList（部分场景） | indexList、postidList、keyWordList、rankIdList、tabNameList |
| Sortexposure 区域内元素曝光 | **idList** | **nameList** | — | postidList |
| explosureGoods 商品曝光 | — | — | **goodsList** | indexList、priceList、tagNameList、rankNameList、rstmark |
| zpmclick 点击 | sortId（单值） | sortName（单值） | infoId（单值） | subSectionId、subSectionName、index、is_rec、postid |

要点：
- explosureItems 用 `sortIdList / sortNameList`；Sortexposure 用 `idList / nameList`；两者不通用，别混。
- 商品曝光 explosureGoods 主键是 `goodsList`（商品ID数组），没有 sortNameList；商品的价格/标签走 `priceList / tagNameList`。
- 点击 zpmclick 是单值字段（sortId/sortName/infoId），不是 List；一次点击只命中一个元素。
- 所有 List 字段用 `&` 分隔，某元素缺某属性时用空串占位保持 `&&` 对齐。
- 轮播场景（浮窗轮播、feed 轮播图、banner）曝光和点击都要带 `rotationIndex` 区分第几屏，否则同坑位不同轮播内容混在一起算不清。

# 埋点需求表填写样例（V2 14 列格式）

严格对齐官方「数据埋点方案-样例」sheet（`QzxYwvMKyivlQNkY6focCvF6nth`，sheet-id `8a4331`）。**这是演示格式，不是真实业务数据。**

## 关键格式规则

1. 固定 14 列，列顺序不可改：页面ID/actionType、页面名称、区域ID/sectionId、区域名称、区域截图、埋点事件/pageType、事件名称、事件属性、事件属性中文名、PM期望、技术实现、实现要求、属性值示例、实时上报。
2. 事件与属性一对多：一行 = 一个属性；同一事件的多个属性上下堆叠，只有第一行写事件名与事件名称，其余留空。
3. 同一区域多个事件依次往下排，只有区域第一行写页面/区域，其余留空。
4. 容器层级：页面 > 区域 > 子区域(subSectionId/subSectionName) > 元素(sortId/sortName) > 商品(infoId)。
5. 子区域 ID 用下划线 `302_0`；数组属性带 List 后缀、多值用 `&` 拼接、缺值用空串占位保持 `&&`。

## 样例：栏目区（302）在 G1001 首页，含两个子区域（超级补贴 302_0、热销榜 302_1）

下表为节选，展示 Areaexposure/explosureItems/explosureGoods/zpmclick 四事件的属性嵌套。空单元格代表归属上方最近的非空值。

| 页面ID/actionType | 页面名称 | 区域ID/sectionId | 区域名称 | 区域截图 | 埋点事件/pageType | 事件名称 | 事件属性 | 事件属性中文名 | PM期望 | 技术实现 | 实现要求 | 属性值示例 | 实时上报 |
|-|-|-|-|-|-|-|-|-|-|-|-|-|-|
| G1001 | 首页_推荐 | 302 | 栏目区 |  | Areaexposure | 区域曝光 | sectionId | 区域ID | 必填 |  |  | 302 |  |
|  |  |  |  |  |  |  | subSectionId | 子区域ID | 必填 |  |  | 302_0、302_1 |  |
|  |  |  |  |  |  |  | subSectionName | 子区域名称 | 必填 |  |  | 超级补贴、热销榜 |  |
|  |  |  |  |  | explosureItems | 组合元素曝光（热销榜） | subSectionId | 子区域ID | 必填 |  |  | 302_1 |  |
|  |  |  |  |  |  |  | subSectionName | 子区域名称 | 必填 |  |  | 热销榜 |  |
|  |  |  |  |  |  |  | rstmark | 前端生成的会话ID标识 | 必填 |  |  | 1766130122470 |  |
|  |  |  |  |  |  |  | indexList | 索引ID数组 | 必填 |  |  | 0&1&2 |  |
|  |  |  |  |  |  |  | nameList | 索引中文名称数组 | 必填 |  |  | 潮玩榜&数码榜 |  |
|  |  |  |  |  |  |  | postidList | 运营计划数组 | 选填 |  |  | 123&456 |  |
|  |  |  |  |  | explosureGoods | 商品曝光（超级补贴） | subSectionId | 子区域ID | 必填 |  |  | 302_0 |  |
|  |  |  |  |  |  |  | subSectionName | 子区域名称 | 必填 |  |  | 超级补贴 |  |
|  |  |  |  |  |  |  | sortIdList | 索引ID数组 | 必填 |  |  | 0&1&2 |  |
|  |  |  |  |  |  |  | goodsList | 商品ID数组 | 必填 |  |  | i1&i2&i3 |  |
|  |  |  |  |  |  |  | rstmark | 会话ID | 必填 |  |  | 1766130122470 |  |
|  |  |  |  |  | zpmclick | 点击（通用） | subSectionId | 子区域ID | 必填 |  |  | 302_0 302_1 |  |
|  |  |  |  |  |  |  | subSectionName | 子区域名称 | 必填 |  |  | 超级补贴、热销榜 |  |
|  |  |  |  |  |  |  | sortId | 索引ID | 必填 |  |  | 0 1 2 3 |  |
|  |  |  |  |  |  |  | sortName | 索引中文名称 | 必填 |  |  | 热销榜入口、热销榜商品 |  |
|  |  |  |  |  |  |  | infoId | 商品ID | 必填 |  |  |  |  |
|  |  |  |  |  |  |  | postid | 运营计划 | 选填 |  |  |  |  |

## 填写要点

- 曝光和点击必须成对出现，否则点击率算不出来：Areaexposure/explosureItems/explosureGoods 是分母，zpmclick 是分子。
- 事件名、属性名严格照核心事件全集与规范写，不自造。
- 区域内切分模块用子区域承载，subSectionId 从 `302_0` 起。
- 页面若有一级 TAB，每个事件补 firsttab / firstTabIndex。
- sectionId 是占位示意，真实值以高斯埋点方案分配、或从区域维表检索为准。

---
name: user-trajectory-analysis
description: 转转APP用户轨迹明细分析。基于埋点事件数据（点击/展现/启停），分析无商详访问用户在APP内的行为轨迹，含停留时长、页面分布、点击行为，生成图表和飞书文档报告。
---

# 用户轨迹分析

## 适用场景

用户提供转转APP用户轨迹明细CSV数据，要求：
- 分析用户在APP内的行为轨迹（看了哪些页面、点了哪些模块、停留多久）
- 生成图表（停留时长分布、页面曝光、模块点击）
- 输出结构化分析报告写入飞书文档
- 以飞书消息推送通知

## 输入数据格式

CSV文件，字段：

| 字段 | 说明 |
|------|------|
| token | 用户唯一标识 |
| 事件类型 | zpmclick（点击）/ zpmshow（页面展现）/ AppStart（启动）/ AppEnd（退出） |
| 页面id | 页面标识（如 G1001、V1008、A5341 等） |
| 模块id | 点击模块标识（zpmclick 事件；zpmshow 事件此字段为 null） |
| 时间戳 | 事件时间戳 |
| 站内停留时间 | AppEnd 事件携带，单位为秒（浮点数） |

可能存在 `dt`（日期）列，无此列时向用户确认采样日期。

## 分析工作流

### Step 1：数据解析

```python
import csv
from collections import Counter, defaultdict

rows = []
with open('file.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        clean = {k.strip(): v.strip() for k, v in row.items()}
        rows.append(clean)

TOTAL = len(set(r['token'] for r in rows))
```

### Step 2：四维分析

#### 维度一：停留时长分布

- 从 `AppEnd` 事件提取 `站内停留时间`
- 按用户取最大停留时长（多 AppEnd 的情况）
- 超过 7200 秒（2 小时）的值截断处理，标注异常人数
- 分桶：`0-5秒 / 5-10秒 / 10-30秒 / 30-60秒 / 1-2分钟 / 2-5分钟 / 5-10分钟 / 10-30分钟 / 30-60分钟 / 60分钟+`
- 输出：用户量、占比、累计占比
- 统计 <30s 比例、<2min 比例、>10min 比例

#### 维度二：页面访问分布

- 从 `zpmshow` 事件统计每个页面的曝光 UV
- 按曝光 UV 降序排列
- 筛选占比 ≥5% 的页面列表
- 计算每个页面的 C/S 比（点击量/展现量），识别高操作强度页面

#### 维度三：点击行为分布

- 从 `zpmclick` 事件统计每个「页面-模块」组合的点击 UV
- 按点击 UV 降序排列
- 筛选 UV ≥某个阈值（通常 30）的高频组合

#### 维度四（可选）：短停用户深析

- 筛选停留 <30s 的用户
- 分析其页面曝光和模块点击特征
- 与全量用户对比

### Step 3：图表生成

配色规范（简洁不花哨）：
```python
C_DARK  = '#2c3e50'  # 标题/主文字
C_BLUE  = '#5b8fb4'  # 主色
C_GRAY  = '#7a8a9a'  # 次要
C_RED   = '#c0392b'  # 标注线
```

中文字体：`['Heiti TC', 'PingFang HK', 'STHeiti', 'Arial Unicode MS', 'DejaVu Sans']`

#### 图表清单

| 图表 | 类型 | 说明 |
|------|------|------|
| `chart_stay.png` | 柱状图 + 累计折线（双轴） | 停留时长分布 |
| `chart_stay_cum.png` | 填充面积图 + 折线 | 停留时长累计，标注 50% 线 |
| `chart_page.png` | 横向柱状图 | 页面曝光 UV（≥5%） |
| `chart_click.png` | 横向柱状图 | 页面-模块点击 UV（≥阈值） |

### Step 4：报告结构

飞书文档报告三段式结构：

1. **样本口径表述** — 日期、样本量、数据量、筛选口径（如"自然留存中当日未进入商品详情页的活跃用户"）
2. **结论汇总** — 3-5 条核心发现，每条带数据支撑，回答"没有商详访问的用户到底在干什么"
3. **分角度分析**：
   - 站内停留时长分布（表格 + 关键发现 + 2 张图）
   - 站内访问页面分布（表格 + 关键发现 + 1 张图）
   - 站内点击行为分布（表格 + 关键发现 + 1 张图）

## 页面/模块 ID 映射

### 常用页面映射

从埋点方案 Excel（`首页改版埋点方案.xlsx` 等）或参考文档中提取：

| 页面ID | 名称 |
|--------|------|
| G1001 | 首页 |
| V1008 | 搜索中间页 |
| I1071 | 启动页 |
| E1007 | 搜索结果页 |
| P1006 | App我的Tab |
| C8524 | 保卖首页 |
| T1082 | 保卖下单页 |
| A5341 | 机况选择页 |
| Q8688 | 保卖机型选择 |
| V9586 | 发布弹窗页 |
| X3970 | 新客c1转化选择页 |
| G6233 | App购物车Tab |
| P4912 | App消息Tab |
| J8874 | 客服中心页 |
| H6271 | 租号新商详 |
| X7357 | 租号新列表 |

### 常用模块映射（首页 G1001 区域，来自埋点方案）

| 模块ID | 名称 |
|--------|------|
| 500 | 底部tab区域 |
| 101 | 搜索栏 |
| 102 | 大促三切分 |
| 103 | 金刚位 |
| 105 | 回收模块 |
| 108 | Feed商品卡片 |
| 109 | Feed轮播图 |
| 110 | Feed物料卡片 |
| 165 | 新人专区 |
| 300 | 品类tab（一级TAB） |

> **注意**：模块 500 是「底部tab区域」不是「Feed卡片」。其他页面（A5341/V1008/E1007等）的模块 ID 含义不同，需从对应埋点方案获取，无映射时标注为推断含义。

## 飞书文档写入 SOP

### 1. 创建新文档

```bash
lark-cli docs +create --api-version v2 --doc-format markdown --content "$(cat report.md)"
```

- 返回 `document_id` 和 `url`

### 2. 插入图表（倒序，从后往前）

图表用文本锚点占位，写如 `[图表: xxx]`，然后按从后往前的顺序插入：

```bash
cd /tmp
lark-cli docs +media-insert --doc "<doc_id>" \
  --file ./chart_click.png \
  --selection-with-ellipsis "[图表: 页面模块点击分布]"
```

- `--file` 必须是相对路径，先 `cd` 到文件目录

### 3. 清理锚点文本

```bash
lark-cli docs +update --api-version v2 --doc "<doc_id>" \
  --command str_replace --pattern "[图表: xxx]" --content ""
```

### 4. 推送飞书消息

```bash
lark-cli im +messages-send --user-id "<open_id>" --text "<message>"
```

用户 open_id 和 P2P chat_id 见 [[feishu-user-personal-chat]]。推送默认发个人会话，不发群聊，见 [[feishu-push-default-personal]]。

## 埋点方案文件读取

首页埋点方案为 `.xlsx` 格式，openpyxl 可能不兼容。使用 zipfile + xml 直接解析：

```python
import zipfile, xml.etree.ElementTree as ET, re

z = zipfile.ZipFile('首页改版埋点方案.xlsx', 'r')
# 1. 读取 shared strings
shared_strings = []
tree = ET.parse(z.open('xl/sharedStrings.xml'))
ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
for si in tree.findall('.//s:si', ns):
    texts = [t.text or '' for t in si.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')]
    shared_strings.append(''.join(texts))

# 2. 读取 sheet 数据，解析 G列（区域ID）和 I列（区域名称）
# 列 E=页面ID, F=页面名称, G=区域ID, I=区域名称
```

## 关键约定

1. **模块500 是底部tab区域**，不是 Feed 卡片。报告中涉及模块500的所有描述统一使用「底部tab区域」或「底部tab导航」。
2. **占比口径**：所有 UV 百分比以总用户数（去重 token 数）为分母。
3. **停留时长截断**：超过 7200 秒（2小时）的值截断处理，在报告中标注异常人数。
4. **图表锚点倒序插入**：从最后一个图表开始插，确保最终文档顺序正确。
5. **消息推送默认发个人**：用户说"飞书推送"时发 P2P 消息，不发群聊。
6. **SAMPLING**：CSV 第一列可能是 token 或 dt，需自动识别列结构。

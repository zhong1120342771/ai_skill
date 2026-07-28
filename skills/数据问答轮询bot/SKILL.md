---
name: 数据问答轮询bot
description: 轮询飞书群消息，自动识别 @bot 的数据/分析类问题，调用数据分析 skill（淑芬/异动监控bot/跑数bot）给出答复并回帖群。内置三层路由分类（本地规则→Haiku分类→Opus回答）。用户提到「轮询」「监听群消息」「自动回答群问题」「数据问答bot」时使用。
---

# 数据问答轮询bot

飞书群数据/分析问题的自动轮询与回答机器人。

## 设计背景

针对 `oc_f9d6d274f793f89b92c455b5691b0a00` 等数据分析工作群，以 cron 形式轮询 @bot 提问，分三层过滤后按问题类型调用对应 skill 回复，减少无效 token 消耗。

---

## 核心流程

```
[cron 触发] 每 10 分钟一次
   ↓
[拉消息] lark-cli im +chat-messages-list --page-size 20 (或更多，见历史追溯规则)
   ↓
[Layer 1] 本地规则过滤（0 token）
   ├─ 无 @bot mention → 静默跳过
   ├─ 已回复过（thread 里有 bot 发的消息）→ 静默跳过
   └─ 通过 → Layer 2
   ↓
[Layer 2] 意图分类（Haiku，~1/20 Opus 费用）
   ├─ 闲聊/确认/非问题（"你还在么"/"收到"）→ 酌情简短回复或跳过
   └─ 数据/分析问题 → Layer 3
   ↓
[Layer 3] 调对应 skill 分析 + 回帖群（Opus）
   ├─ 首页模块曝光率/栏目曝光 → 数据洞察agent_淑芬
   ├─ 核心指标/趋势/异动 → 转转核心指标异动监控bot
   └─ 自定义 SQL 取数 → 跑数bot
```

---

## Cron 配置

```
频率：*/10 * * * *（每 10 分钟）
目标群：oc_f9d6d274f793f89b92c455b5691b0a00
拉取条数：最近 20 条（默认）；历史追溯时按需增加或指定 --start
```

**建 cron 的标准 prompt**（发 CronCreate 时粘贴）：

```
轮询飞书群 oc_f9d6d274f793f89b92c455b5691b0a00 的新消息。
用 lark-cli im +chat-messages-list --chat-id oc_f9d6d274f793f89b92c455b5691b0a00 --as user --page-size 20 拉最近 20 条消息。
按三层路由处理（见数据问答轮询bot SKILL.md），对数据/分析类 @bot 问题调用对应 skill 回答并回帖。
```

---

## 消息读取规则

### 默认：拉最近 20 条

```bash
lark-cli im +chat-messages-list \
  --chat-id oc_f9d6d274f793f89b92c455b5691b0a00 \
  --as user --page-size 20
```

### 历史追溯：用户说「之前给过你」

当消息中出现「之前给过你」「口径之前说过」「你应该知道」等表述时，**必须向前翻历史**，不能以「当前窗口没加载到」放弃。

```bash
# 向前翻更多消息
lark-cli im +chat-messages-list \
  --chat-id oc_f9d6d274f793f89b92c455b5691b0a00 \
  --as user --page-size 50

# 或按时间范围翻
lark-cli im +chat-messages-list \
  --chat-id oc_f9d6d274f793f89b92c455b5691b0a00 \
  --as user --start "2026-07-20T00:00:00" --page-size 50

# 用 page-token 继续翻页
lark-cli im +chat-messages-list \
  --chat-id oc_f9d6d274f793f89b92c455b5691b0a00 \
  --as user --page-token <上一次返回的 next_page_token>
```

只有翻遍了还找不到，才请用户重新提供。

---

## 三层路由详解

### Layer 1：本地规则（0 token）

用 Python/jq 直接判断，不走 LLM：

```python
# 判断条件（任一满足则跳过）
skip_conditions = [
    len(msg.get('mentions', [])) == 0,                         # 没有 @mention
    not any(m['name'] == 'cai的飞书 CLI' for m in mentions),   # @的不是 bot
    already_replied(thread_replies),                            # thread 里 bot 已回复
    msg_type not in ('text', 'post'),                          # 图片/文件/表情等
]
```

**判断已回复**：看 `thread_replies` 列表里是否有 bot（`cai的飞书 CLI`）发出的消息。已回复则跳过，不重复回帖。

### Layer 2：意图分类（可选，Haiku）

对通过 L1 的消息快速分类：

| 类型 | 处理方式 |
|------|----------|
| 闲聊/确认（「你还在么」「收到」）| 简短文字回复或静默 |
| 存在确认（「在不在」）| 简短回复「在的」 |
| 数据/分析问题 | 进 Layer 3 |
| 不完整的补充说明（「口径之前给过你」但没主问题） | 等下一轮，不回复 |

### Layer 3：调 skill 回答（按问题领域路由）

用户 2026-07-28 确认的领域→skill 分发规则（优先按此归类）：

| # | 问题领域 | 调用 skill |
|---|---------|-----------|
| 1 | 莫斯科保卫战相关数据（消费电子相关） | `moscow-defense-weekly-biz`（三端）& `moscow-defense-weekly-biz-app`（仅APP端） |
| 2 | 一体化数据（线上线下一体化） | `一体化项目日报数据bot` & `一体化复盘分析bot` |
| 3 | 前端数据（首页等各模块曝光点击、日活等） | `数据洞察agent_淑芬`（淑芬bot） |
| 4 | 经营数据（各品类转化漏斗、曝光等绝对值数据） | `转转核心指标异动监控bot` |
| 5 | 无法判定的问题 | `跑数bot` |

细分关键词参考（辅助归类）：

| 关键词 / 场景 | 调用 skill |
|--------------|-----------|
| 消费电子、莫斯科保卫战 | `moscow-defense-weekly-biz` / `moscow-defense-weekly-biz-app` |
| 一体化、线上线下、同售 | `一体化项目日报数据bot` / `一体化复盘分析bot` |
| 首页模块/栏目曝光率、曝光渗透率、日活 | `数据洞察agent_淑芬` |
| 品类转化漏斗、曝光绝对值、DAU 净支付、异动 | `转转核心指标异动监控bot` |
| AB 实验分析、用户分组对比、自定义 SQL、取数、建表、无法判定 | `跑数bot` |

---

## 回复规则

### 特殊用户前缀规则

**仅限 `oc_f9d6d274f793f89b92c455b5691b0a00` 群内，对 `董亚坤` 发起的问题回复时，在回复内容最前面加上固定前缀：**

```
尊贵的token金主～
```

示例：
```
尊贵的token金主～

@董亚坤 以下是近一周首页各栏目曝光率分析...
```

规则范围：只限该群 + 该用户。其他群、其他用户、P2P 消息均不加此前缀。

---

### 发消息身份

**群消息统一用 bot 身份**（`--as bot`），不用钟梦婷本人：

```bash
lark-cli im +messages-send \
  --as bot \
  --chat-id oc_f9d6d274f793f89b92c455b5691b0a00 \
  --text "回复内容"
```

### 回帖 vs 新消息

- 原问题在 thread 里 → 用 `--thread-id <omt_xxx>` 回帖
- 原问题是主消息（无 thread_id）→ 用 `--chat-id` 发新消息，并 @提问人

```bash
# 回帖 thread
lark-cli im +messages-send \
  --as bot \
  --thread-id omt_xxxx \
  --text "回复内容"

# 非 thread 主消息，@提问人
lark-cli im +messages-send \
  --as bot \
  --chat-id oc_f9d6d274f793f89b92c455b5691b0a00 \
  --text "@提问人名字 回复内容"
```

### 发送次数控制

**每条消息只发一次**，禁止用「复查/确认」名义重跑导致群里重复消息。  
撤回用：`lark-cli im messages delete --params '{"message_id":"om_xxx"}' --yes`

### 接收「处理中」确认消息

收到问题后先发一条「收到，处理中…」表示在处理，然后再发完整答案。避免用户等待无响应。

---

## 数据分析补充口径规则

### AB 实验分组取用户

董亚坤新媒体 AB 实验口径（2026-07-27 确认）：

```sql
-- 圈 newMediaInterestScore 实验分组
SELECT dt, token, datapool['abvalue'] as abvalue
FROM hdp_zhuanzhuan_dw_global.dw_log_server_action_1d
WHERE dt between date_sub(current_date, 7) and date_sub(current_date, 1)
  AND action = 'newMediaInterestScore'
  AND region = 'n'
  AND checkVersion('>=12.0.0', version)
GROUP BY 1,2,3
-- abvalue=0 对照组，abvalue=1 实验组
```

### 首页模块曝光率

- 来源：`数据洞察agent_淑芬` / `module_daily_baseline` CSV
- 口径：模块曝光UV / 首页整体UV（同日，同 page_id）
- section→module 映射见 `References/section-to-module.json`

### 二奢品类曝光

- 来源：`转转核心指标异动监控bot` 周缓存 CSV
- tag_01='单维度-拆分品类', wd='业务_二奢' 及子品类（包袋/腕表/鞋服/饰品/奢侈品-其他）
- 曝光渗透率分母：tag_01='单维度-拆分端', wd='转转APP' 的 matched_dau_uv

### 北极星指标（DAU净支付PV转化率）

格式：`X.XXX%`，保留三位小数。涨跌幅同口径 `±X.XXX%`。

---

## 注意事项

1. **不拿行业惯例当输入**：AB 实验口径、分组定义、时间窗口等，没有用户明确提供的，一律问用户或从数据实测，不臆测。
2. **推断信息必标注**：对外回复里，推断性结论标「基于xxx逻辑推断」，区分事实/实测/推断。
3. **图片用 cwd 相对路径**：`lark-cli docs +media-insert --file` 只吃 cwd 相对路径，绝对路径报 unsafe。
4. **大表批量写用 csv-put**：`lark-cli im +csv-put --csv @./file`，不用 --values 内联 JSON（75KB 截断）。

---

## 快速启动

```bash
# 1. 确认 lark-cli bot 身份可用
lark-cli auth status --as bot

# 2. 建轮询 cron（10 分钟间隔）
# 在 Claude Code 里执行 CronCreate，参数见上方「建 cron 的标准 prompt」

# 3. 手动触发一次验证
lark-cli im +chat-messages-list \
  --chat-id oc_f9d6d274f793f89b92c455b5691b0a00 \
  --as user --page-size 20 | python3 -c "
import sys, json
data = json.load(sys.stdin)
msgs = data.get('data', {}).get('messages', [])
at_bot = [m for m in msgs if any(x.get('name') == 'cai的飞书 CLI' for x in m.get('mentions', []))]
print(f'最近 20 条中 @bot 消息数: {len(at_bot)}')
for m in at_bot:
    print(f'  {m[\"create_time\"]} pos={m[\"message_position\"]} {m[\"content\"][:80]}')
"
```

---

## 相关 skill

| Skill | 用途 |
|-------|------|
| `数据洞察agent_淑芬` | 首页模块曝光、栏目分析 |
| `转转核心指标异动监控bot` | 核心指标趋势/异动/品类曝光 |
| `跑数bot` | 自定义 SQL 取数、AB 实验分组 |
| `lark-im` | 飞书消息收发（底层） |

## Workflow 详细规则

配合 SKILL.md 使用。SKILL.md 只留每步核心约束，详细清单/示例/反模式在这里。

---

### Step 0: 连通性探活（详细）

`check` 不通过时的准入流程：

1. 确认 `$SKILL_DIR/.credentials.local` 是否存在、`OA_NAME` / `ACCESS_KEY` 是否非空
2. 缺失或无效 → 主动用 `agent-browser` 打开申请页（**禁 `WebFetch` / 禁 `agent-browser screenshot`**）：
   ```bash
   agent-browser open 'https://zeye.zhuanspirit.com/main/showPage?pageId=getOrCreateAiAccessKey'
   agent-browser snapshot -i
   ```
3. 用户拿到 accessKey → 写入 `.credentials.local`
4. 回 Step 0 重跑 `check`，返回 `ok` 才放行

### Step 1: 参考优先级（详细）

按四档优先级取参考，任何一档都不能跳：

0. **模板库**（最高优先级）
   - 列清单：`cat $SKILL_DIR/templates/README.md`
   - 按需求关键词匹配（"趋势"/"画像"/"来源"/"支付前搜索"/"筛选"/"全链路漏斗"/"四象限交叉"/"转化时机"）
   - 命中 → 读模板 → 替换 `${param}` → 跳过 Step 2，直接进 Step 2.5
   - **模板只免 Step 2 探表，Step 2.5/3.5/4/7 一个都不能跳**
   - 模板顶部 yaml 的 `business_statement` 直接抽出来给 Step 3.5 用
   - 模板故意精简（8 个骨架），简单场景（TopN 拆位/10 档分位/ROW_NUMBER）看 `空间盘点/references/riding-case-pattern.md` §范式 A/B/C
   - 字段/表定义查 `references/data-map-cache.md`（每天 08:57 自动同步飞书）

1. **用户给参考** → 按参考改，别自作主张换写法；用户只让改一段就只 patch 那段

2. **本地搜索**（用户没给时必走）
   - 默认搜 `~/claude-output/` + `~/.claude/projects/`
   - `.local-sql-paths.local` 不存在时先自动扫 VSCode 历史：
     ```bash
     find ~/Library/Application\ Support/Code/User/History -name "entries.json" \
       | xargs -I{} python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('resource',''))" {} 2>/dev/null \
       | grep -oE "file://[^\"]+\.(sql|SQL)" \
       | python3 -c "import sys,urllib.parse,os; [print(os.path.dirname(urllib.parse.unquote(l.replace('file://','')))) for l in sys.stdin]" \
       | sort -u
     ```
     公共上层根加到 `.local-sql-paths.local`
   - 再问用户"VSCode 历史扫到 X 个路径，还有别的要加吗"
   - 用 `init-paths --add` 写入（**仅写 `.local-sql-paths.local`，不进 SKILL.md**）

3. **去 58 探表**（最后兜底）→ 进 Step 2

**硬约束（每次都要跑，不管走哪档）：先查本地案例库**

```bash
python3 $SKILL_DIR/scripts/stariver_query.py search-cases "<关键词>" --top 5
```

- 关键词用用户原话名词（品类+分析类型+关键指标）
- 读 top 1-2 份原文 SQL，看 CTE 结构/过滤组合/口径细节
- 案例给品类专属的坑位/字段/CASE WHEN，跟模板互补（模板给骨架）
- 索引 `$SKILL_DIR/sql_index.json` 每天 09:07 cron 自动重建

**为什么每次都要查案例**：SQL 写不完做不出无穷模板；数据地图只有字段字典没有"字段间的映射和业务口径"。本地案例是业务理解的活字典。

**禁止**：跳档直接写 / 凭训练记忆写字段名 / 写没在参考或探查里出现过的字段。

### Step 2: 探表（详细）

仅当 Step 1 走到第 3 档，或用户只给表名没给 SQL 时执行。

- `describe` — 字段/类型/注释
- `describe formatted` — 敏感等级 + 生命周期
- `partitions` — 分区字段和最新分区
- `sample` — 带 partition 过滤的小样本

规则：
- 不写未验证的字段
- L4 表不直接推荐，同时给 L3 及以下候选
- 没权限的表保留候选并标注"需申请权限"
- 找表场景（用户只给业务问题）：本地历史 SQL/文档 → 星河 `show tables like` → 候选 `describe formatted` → 按相关度排序，每张必须标注敏感等级/生命周期/分区粒度/时间戳字段/后缀含义（`_full`/`_1d`）/权限
- 中间过程不暴露给用户，只输出最终结论

**JSON / 复杂字段必告知**（硬规则）：字段满足任一条件时告知用户"是 JSON，需先确定取哪个 key"，禁止直接把 JSON 字段 group by（炸成几千个独立值）：
- comment 含 `json`/`JSON`/`数组`/`dict`
- comment 显示嵌套结构（含 `{...}`/`[...]`）
- 字段名以 `_json`/`_dict`/`datapool` 结尾

详见 [table-discovery.md](table-discovery.md)。

### Step 2.5: 口径分歧点确认（必问清单）

写 SQL 前必列出所有 LM 容易自作主张的分歧点让用户拍板：

| # | 必问类型 | 例子 |
| --- | --- | --- |
| 1 | 分母粒度 | uid 级 / 事件级 |
| 2 | 同 uid 多次行为属性怎么取 | 首次 / 最后 / 最高频 / 窗口末快照 |
| 3 | 多表 join 粒度对齐 | 全 uid / 全 token / 混用过桥 |
| 4 | 新老客/流失/活跃判定窗口 | 历史不限 / 前 X 天 / 前 X 年 |
| 5 | JSON / 多业务线取哪个 key | user_layer 取 B2C / C2B / 核心业务 |
| 6 | 分桶阈值 / CASE WHEN 规则 | 沿用历史 8 类还是重新定义？**即使沿用也要显式问** |
| 7 | 时间字段语义 | create_time / pay_time / 别的 |
| 8 | 过滤条件 | 是否排测试账号 / 风控 / 内部员工 |

**一次问 1 个**，已明确跳过，整理状态再写：

```
口径确认（写 SQL 前最后一次对齐）：
✅ 分母粒度：<...>
✅ 时间字段：<...>
✅ 新老客口径：<...>
✅ JSON 字段取值：<...>
✅ 分桶规则：<...>
✅ 过滤条件：<...>
→ 开始写 SQL
```

**自检三态**（进 Step 3 前）：
- ✅ 全过：静默直接写
- ⚠️ 遗漏（LM 能回头问的）：`⚠️ Step 2.5 自检发现 <X> 未对齐，回头问您`
- 🛑 矛盾（LM 拿不准）：完整打印未对齐项 + 停下等用户拍

**禁止**：没确认就写 / 沿用历史 SQL 业务规则不显式问（业务规则不可继承，只有技术写法能继承）/ LM 自己拍合理值 / 自检发现问题不打印硬走。

### Step 3: 写 SQL（详细规则）

- Hive 兼容，加 `dt` 或分区过滤
- 复杂分析拆最小可检查 fact 层 CTE，再叠 intent/匹配/率
- 用户要小改只 patch 那段
- 多步分析 fact 层需反复检查时先物化中间表
- 匹配/打标优先用已有结构化字段或稳定 id 等值 join，再考虑文本匹配
- denominator / base-table 选择在 CTE 名和回复里显式说明

**粒度一致性（硬规则）**：
- `buyer_id/seller_id/uid/user_id` → uid 系，直接 join
- `token` → 设备/会话级，≠ uid
- `order_id/info_id/event_id` → 事件级
- 跨粒度 join 必须显式过桥（如订单 uid → token 用 `dm_trade_visit_detail_1d`）+ 注释

**注释要求（硬规则）**：
- 每个 CTE 顶部一行注释说明这层干什么
- 每个 WHERE 关键过滤条件行内注释业务含义
- CASE WHEN 每分支后注释含义
- JOIN ON 用"全局通用映射"（如 `buyer_id = uid`）注释一句
- 输出 SELECT 别名简写（`uv`/`pv`/`dim`）首次出现注释含义

**SQL 写法必须优化（4 条自检）**：

1. **多节点漏斗用 UNION ALL，不要每节点单独 CTE 再 join**
   - ❌ `exposure_daily CTE + visit_daily CTE + pay_daily CTE + LEFT JOIN` — 粒度对不上还容易 NULL 错位
   - ✅ `funnel_detail AS (SELECT ..., 1 AS exposure_pv, 0, NULL FROM 曝光 UNION ALL SELECT ..., 0, 1, NULL FROM 商详 UNION ALL SELECT ..., 0, 0, order_id FROM 支付)` — 长表 + 最外层一次 group by
   - 加节点/加维度：UNION ALL 改 1 处，join 改 N 处

2. **场景/标签 CASE WHEN 只写一次，别每节点重复**
   - UNION ALL 长表保留原始字段，再加一层 `scene_detail` 统一 CASE WHEN 映射

3. **JOIN 顺序按数据量从小到大**
   - 小维表（target_info 几千行 / dau 几十万-几百万 / 限定 BU）放 join 链路前
   - 大流量表 INNER JOIN 过滤后再计算
   - 手动 `SELECT /*+ MAPJOIN(b) */`（确认真小表）

4. **同源数据复用 CTE，别重复扫主表**
   - 多维度/多节点用同一份"基础订单/商品/用户"数据，一个 CTE 物化一次
   - 详见 [[feedback-sql-combine-when-safe]]

**自检准则**：写完 SQL 前 verify-lifecycle 前默念——"加一个节点/维度这条 SQL 改 1 处还是 N 处？N 处就回头优化"。

**反模式**（2026-06-30 二奢漏斗 case）：
- ❌ 抄字段不抄结构范式，自己用笨写法重写
- ❌ 漏斗写成 3 个独立 CTE + LEFT JOIN

### Step 3.5: 用户审 SQL（详细）

**为什么二合一（业务描述 + SQL）**：用户群里有会 SQL 的分析师 / 不会 SQL 的业务方（产品、运营、老板）。不能假设用户能审 SQL，两层互相印证——描述跟 SQL 不一致时两层都能发现。

**必贴内容**：

1. **业务描述（人话版）**
   - "这条 SQL 在干什么"：一句话
   - 看谁/算什么/拆什么/出什么
   - 隐含假设翻译成业务话术（粒度/阈值/过滤/新老客口径）
   - 数据来源：主表/维表/关联逻辑（业务话术版）

2. **完整 SQL**（不省略 CTE/WHERE/GROUP BY）

格式 + 翻译规则 + 实战示例 → `_分析上下文协议/business-statement.md`。

**禁止跳过**：
- 沿用历史 SQL 的主表/时间字段/过滤条件 → 必须显式确认没变
- 用户只说部分维度（如"看趋势"没说"支付日/下单日"）→ 默认假设写进业务描述 + 跟用户确认
- 数据量预估 > 10 万行 → 告知行数预估 + 是否 limit

**反模式**：
- 只贴 SQL + 3 行口径（业务方看不懂只能盲说"可以跑"）
- 业务描述藏起"事件级 vs uid 级"关键假设
- 业务描述和 SQL 不一致（描述说"已支付"，SQL 里没过滤）

### Step 4: verify-lifecycle（详细）

```bash
python3 $SKILL_DIR/scripts/stariver_query.py verify-lifecycle --sql-file query.sql
```

脚本自动做：
1. 解析 SQL 涉及所有表（`from`/`join` 后，排除 CTE 名）
2. 解析 `dt` 范围（`dt=` / `between` / `>= and <=` / `in`）
3. 生命周期检查（按优先级）：
   - 先看 SQL 顶部注释 `@lifecycle <table>=<days|permanent>`（人工核实后留痕）
   - 没有 → 跑 `describe formatted` grep `lifecycle/ttl/retention`
4. 分区可用性：每张表 `SELECT MAX(dt)`，确认请求结束日 ≤ 最新可用分区
5. 对比 dt 范围天数 vs 生命周期天数

**@lifecycle 注释用法**（星河 describe formatted 不暴露生命周期时兜底）：

```sql
-- @lifecycle hdp_zhuanzhuan_dm_global.dm_trade_order_detail_1d=permanent
-- @lifecycle hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d=180
SELECT ...
```

数值支持整数天数或 `permanent`（→ 9999 天）。注释里的生命周期必须是从 zeye 平台真实查过的。

**判定**：
- `OK_TO_SUBMIT` → Step 5/6/7
- `REFUSE_SUBMIT` → 拒绝，改 SQL（缩 dt 或换更长生命周期的表）后重 verify
- 生命周期解析不到 → 拒绝，按 30 天保守需用户确认
- 多表 join → 取最小生命周期

绕过这一步直接 `run` 违反 skill 硬约束。

### Step 5-7: 执行 / 总结 / QA

**Step 5 小验证**：复杂 SQL 先 limit 或缩日期跑一次；错误提缺列/缺分区 → 重新 describe + 修 SQL；用户说字段不对 → 重新探同表更新假设。

**Step 6 正式 run**：`run` 跑最终 SQL；报告结果文件路径/行数/预览/注意事项；大结果集不全文粘贴。

**Step 7 产物 QA**（跑完必做）：

```bash
python3 $SKILL_DIR/scripts/result_qa.py \
    --result-path /Users/zz/claude-output/sql_result_xxx.tsv \
    --sql-file <SQL 文件> \
    --task-id <星河 task id>
```

自动做：
1. 读结果文件（tsv/csv/xlsx）
2. **hard_failures**（触发即停）：行数 < 1 / 某列 100% 为空
3. **warnings**（提示不阻塞）：单列 null 率 > 30% / "其他/未知" > 15% / 单列 distinct=1
4. 落 `<result_path>.meta.json`（schema 见 `_分析上下文协议/output-schemas.md` §1）
5. **默认自动生成 xlsx 副本**（用户全局要求），路径写进 `meta.json` 的 `xlsx_path`；不要副本加 `--no-xlsx`

**为什么必须脚本**：LM 即兴写 pandas 容易漏检；下游子 skill 直接读 `.meta.json` 不用重算；阈值集中在脚本可审计。

**退出码**：`0`=passed / `2`=hard failure（必停）/ `3/4`=输入缺失/异常。

---

## ❌/✅ 速查表

| ❌ Don't | ✅ Do |
| --- | --- |
| Step 0 `check` 没过就写 SQL | 准入未通过先用 agent-browser 引导申请 accessKey |
| 跳过 templates/ 直接现写 | Step 1 第 0 档先看模板库 |
| 跳过本地搜索直接 `show tables` | 先扫 VSCode 历史 + 本地 SQL 仓库 |
| 探表/搜历史/找映射中间过程一股脑展示 | 只输出最终结论 |
| 凭记忆写 `SELECT a, b, c FROM xxx` | 字段必须来自参考或当轮 describe |
| 无注释 / 只在顶部写标题 | 每个 CTE / WHERE / JOIN 一行注释 |
| JSON 字段直接 group by | 探表识别后先告知"是 JSON，需选 key" |
| uid 和 token 混用没显式过桥 | 粒度统一，跨粒度必须 join 转换表 + 注释 |
| 沿用历史 CASE WHEN 分桶阈值不问 | 业务分桶不可继承，问"沿用还是重定" |
| 跳过 Step 2.5，写完 SQL 才暴露自作主张口径 | Step 2.5 必走必问清单 |
| **套模板跳过 Step 3.5 直接 run** | **模板只免 Step 2；Step 2.5/3.5/4/7 一个都不能跳** |
| **找到参考 SQL 只抄字段不抄结构范式** | **吃透参考的写法范式（UNION ALL / CASE 单层 / JOIN 顺序 / CTE 复用）** |
| **多节点漏斗每节点单 CTE 再 LEFT JOIN** | **UNION ALL 长表 + 最外层一次 group by；CASE WHEN 只写一次** |
| SQL 硬填 `dt='2026-06-28'` 不查最新可用分区 | `verify-lifecycle` 已内置分区可用性检查 |
| `verify-lifecycle` 返回 REFUSE_SUBMIT 改阈值放行 | 修 SQL 或顶部加 `-- @lifecycle` 注释 |
| **SQL 写完不给用户看就 run** | **Step 3.5 必贴完整 SQL + 业务描述** |
| 沿用历史主表 / 时间字段不显式确认 | "上次用 X 表 + Y 字段，这次还一样吗" |
| 跑完 SQL 不做 QA | `run` 完必调 `result_qa.py` |
| LM 即兴写 pandas 检查空值率 | 直接调 `result_qa.py`，阈值集中管理 |
| 跑出 0 行不追因直接报"无数据" | 0 行 = hard_failure，先查分区/口径/过滤 |
| 大结果集（>10k 行）整文件贴回 | 存 TSV/CSV 后只贴关键预览行 |
| `pwd`/`path` 含中文/空格不加引号 | 中文路径必须双引号 |

---

## One-Service API 参考（脱敏）

底层接口，`scripts/xinghe_submit.sh` 就是调这套。凭证用 `.credentials.local` 中的值替换占位符。

```bash
# 1) 提交 SQL 任务
curl -s -X POST https://oneservice.zhuanspirit.com/sqlTask/submit \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'sql=select 1 as c' \
  --data-urlencode 'oaName58=你的OA账号' \
  --data-urlencode 'accessKey=你的accessKey'

# 2) 查询任务状态
curl -s https://oneservice.zhuanspirit.com/sqlTask/queryTaskProgress/{taskId}

# 3) 获取结果（小结果集）
curl -s "https://oneservice.zhuanspirit.com/sqlTask/downloadTaskResult/{taskId}?oaName58=你的OA账号&accessKey=你的accessKey"

# 4) 获取下载链接（大结果集）
curl -s "https://oneservice.zhuanspirit.com/sqlTask/queryTaskResult/{taskId}?oaName58=你的OA账号&accessKey=你的accessKey"
```

注意：
- `queryTaskProgress=success` 仅表示执行完成，不代表结果可立即获取
- 大结果集走下载链接
- 内网访问 oneservice 通常需要 VPN/企业网卡/utun，`xinghe_submit.sh` 内置 `ifconfig` 探测 + `curl --interface` 选路

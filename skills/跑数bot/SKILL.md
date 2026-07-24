---
name: 跑数bot
description: 连接 58 星河 / One-Service 执行 Hive 或 Spark SQL，自动探查 Hive 表结构、分区和样例数据，基于业务问题编写 SQL、提交取数、下载结果并总结。内置参数化 SQL 模板库（templates/），高频分析骨架优先套模板不现写。也覆盖「找表」场景：用户只给业务问题或字段词、没给具体表名时，先扫本地历史 SQL/文档，再用 show tables 去星河搜，给出按相关度排序的候选清单并标注敏感等级（L1-L4）与生命周期。用户提到 跑数bot、跑数、58星河、星河平台、Hive取数、Spark取数、跑SQL、读数、查Hive表、找表、搜表、表名、敏感等级、L3、L4、生命周期、TTL、全量表、增量表、_full、_1d、理解表结构、数据探查接口或需要 agent 自动写 SQL 并取回结果时使用。
---

# 跑数bot — 58 StarRiver Hive Query

把业务问题转成 Hive/Spark 查询并通过 58 星河 One-Service 执行。

## 流程总览

```
[Step 0] check 探活
   ├─ ok    → Step 1
   └─ fail  → 走准入流程（agent-browser 引导申请 accessKey）→ 回 Step 0

[Step 1] 拿参考（四档硬约束，绝对不许凭感觉写）
   ├─ 0档 模板库 templates/ 匹配 → 套模板填参数 → 免 Step 2
   ├─ 1档 用户给参考 → 按参考改
   ├─ 2档 本地搜索 search-sql → 本机历史 SQL
   └─ 3档 都没有 → 进 Step 2 探表
   ⚠️ 无论走哪档，都必须先跑一次 search-cases 拿本地案例当参考

[Step 2] 探表 → [Step 2.5] 口径确认 → [Step 3] 写 SQL → [Step 3.5] 用户审 SQL
                                                          ↓
                        [Step 4] verify-lifecycle
                        ├─ OK_TO_SUBMIT  → Step 5/6/7
                        └─ REFUSE_SUBMIT → 改 SQL 重 verify

[Step 5] 小范围验证 → [Step 6] 正式 run → [Step 7] result_qa.py 产物 QA
```

**四条不可绕过的硬约束**：
- **① 准入**：Step 0 `check=ok` 才放行
- **② 参考**：写 SQL 前按 Step 1 四档取参考 + 必跑一次 `search-cases`；禁止凭记忆/感觉直接写；禁止写没在参考或探查里出现过的字段
- **③ 生命周期**：`run` 前必调 `verify-lifecycle`，`REFUSE_SUBMIT` 一律打回
- **④ 产物 QA**：跑完必调 `result_qa.py`，`hard_failures` 非空视为失败，下游不能用

## Tools

**约定**：`$SKILL_DIR` = 本 SKILL.md 所在目录（skill 根）。主脚本 `python3 $SKILL_DIR/scripts/stariver_query.py --help`。凭证与网络选路内聚在 `.credentials.local` + `scripts/xinghe_submit.sh`。命令清单见 [references/commands.md](references/commands.md)。

## 前置准备

需要 One-Service 凭证（OA 账号 + accessKey）。申请 accessKey：https://zeye.zhuanspirit.com/main/showPage?pageId=getOrCreateAiAccessKey （无权限联系业成）

拿到 accessKey 后在 skill 目录下建 `.credentials.local`（已 `.gitignore`）：

```
OA_NAME=你的OA账号
ACCESS_KEY=你的accessKey
```

分发给他人：skill 包不含任何人真实凭证，对方需自己申请并写入本机 `.credentials.local`。

## Step 1 — 拿参考的四档优先级

0. **模板库**（最高优先级）— 看 `templates/README.md` 有没有匹配的参数化模板
   - 按需求关键词（"趋势"/"画像"/"来源"/"支付前搜索"/"筛选"/"全链路漏斗"/"四象限交叉"/"转化时机"）匹配
   - 命中 → 读模板 → 替换 `${param}` → **免 Step 2 探表，但 Step 2.5/3.5/4/7 一个都不能跳**
   - 模板顶部 yaml 的 `business_statement` 直接抽出来给 Step 3.5 用
   - 模板只覆盖"骨架复杂/字段过滤组合难记"的场景；简单场景（TopN 拆位 / 10 档分位 / ROW_NUMBER Top品牌）没有模板，看 `空间盘点/references/riding-case-pattern.md` §范式 A/B/C
1. **用户给参考** — 按参考改，别自作主张换写法；用户只让改一段就只 patch 那段
2. **本地搜索** `search-sql`（默认扫 `~/claude-output/` + `~/.claude/projects/`）— 详见 [workflow-details.md](references/workflow-details.md) §Step 1（首次跑数扫 VSCode 历史流程）
3. 都没有 → 进 Step 2 探表

**硬约束（每次都要跑，不管走哪档）**：先查本地案例库

```bash
python3 $SKILL_DIR/scripts/stariver_query.py search-cases "<关键词>" --top 5
```

- 关键词用用户原话名词（品类 + 分析类型 + 关键指标），例：`"骑行 支付前搜索 漏斗"`
- 读 top 1-2 份原文 SQL，看 CTE 结构 / 过滤组合 / 口径细节
- 案例给品类专属的坑位/字段/CASE WHEN，跟模板互补（模板给骨架）
- 索引 `sql_index.json` 每天 09:07 cron 自动重建

**为什么每次都要查案例**：SQL 写不完做不出无穷模板；数据地图只有字段字典没有"字段间的映射和业务口径"。本地案例是业务理解的活字典。

**禁止行为**：
- 跳过 0/1/2 档直接 Step 2 / 直接写 SQL
- 仅凭训练记忆里的表名/字段名/写法生成 SQL
- 把没在本轮探查或参考里出现过的字段写进 SQL

## Step 2 — 探表

仅当 Step 1 走到第 3 档，或用户只给表名没给 SQL 时执行。`describe` / `describe formatted`（敏感等级 + 生命周期）/ `partitions` / `sample`。L4 不直接推荐同时给 L3 及以下候选；没权限的表保留候选并标注"需申请权限"。中间过程不暴露给用户，只输出最终结论。详细规则见 [table-discovery.md](references/table-discovery.md)。

**JSON / 复杂字段必告知**（硬规则）：字段满足任一条件时告知用户"是 JSON，需先确定取哪个 key"，禁止直接把 JSON 字段当普通字段 group by（会炸成几千上万种独立值）：
- comment 含 `json`/`JSON`/`数组`/`dict`
- comment 显示嵌套结构（含 `{...}`/`[...]`）
- 字段名以 `_json`/`_dict`/`datapool` 结尾

## Step 2.5 — 口径分歧确认（必问 8 类，每条都得问）

| # | 必问类型 | 例子 |
| --- | --- | --- |
| 1 | 分母粒度 | uid 级（每人一条）还是事件级（每次行为一条） |
| 2 | 同 uid 多次行为属性怎么取（uid 级时） | 首次行为当天 / 最后行为 / 最高频 / 窗口末快照 |
| 3 | 多表 join 粒度对齐 | 全 uid / 全 token / 混用过桥？粒度切换牵动整条 SQL |
| 4 | 新老客/流失/活跃判定窗口 | 历史不限 / 本窗口前 X 天 / 前 X 年 |
| 5 | JSON / 多业务线取哪个 key | user_layer 取 B2C / C2B / 核心业务 / 其他 |
| 6 | 分桶阈值 / CASE WHEN 规则 | 沿用历史 8 类还是重定？**即使可以沿用也要显式问** |
| 7 | 时间字段语义 | create_time 下单日 / pay_time 支付日 / 别的 |
| 8 | 过滤条件 | 是否排测试账号 / 风控用户 / 内部员工 |

一次问 1 个，已明确跳过，整理状态再写：

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
- ⚠️ 遗漏（LM 能回头问）：`⚠️ Step 2.5 自检发现 <X> 未对齐，回头问您`
- 🛑 矛盾（LM 拿不准）：完整打印未对齐项 + 停下等用户拍

**禁止**：没确认就写 / 沿用历史 SQL 业务规则不显式问（业务规则不可继承，只有技术写法能继承）/ LM 自己拍合理值 / 自检发现问题不打印硬走。

## Step 3 — 写 SQL

**粒度一致性（硬规则）**：整条 SQL 粒度统一——要么全 uid 级 / 全 token 级 / 全事件级，禁止隐式混用。
- `buyer_id/seller_id/uid/user_id` → uid 系，直接 join
- `token` → 设备/会话级，**≠ uid**
- `order_id/info_id/event_id` → 事件级
- 跨粒度 join 必须显式过桥（订单 uid → token 用 `dm_trade_visit_detail_1d`）+ 注释

**注释（硬规则）**：
- 每个 CTE 顶部一行注释说明这层干什么
- 每个 WHERE 关键过滤条件后行内注释业务含义（如 `cate_first_id = 105 -- 骑行`）
- CASE WHEN 每分支后注释含义
- JOIN ON 用"全局通用映射"（`buyer_id = uid`）注释一句
- 输出别名简写（`uv`/`pv`/`dim`）首次出现注释含义

**写法优化 3 条自检（写前默念，JOIN 顺序等次要优化见 [workflow-details.md](references/workflow-details.md)）**：

1. **多节点漏斗用 UNION ALL，不要每节点单独 CTE 再 join**
   - ❌ `exposure_daily CTE + visit_daily CTE + pay_daily CTE + LEFT JOIN` — 粒度对不上还容易 NULL 错位
   - ✅ `funnel_detail AS (SELECT ..., 1 exposure_pv, 0, NULL FROM 曝光 UNION ALL SELECT ..., 0, 1, NULL FROM 商详 UNION ALL SELECT ..., 0, 0, order_id FROM 支付)` + 最外层一次 group by
   - 加节点/加维度：UNION ALL 改 1 处，join 改 N 处

2. **场景/标签 CASE WHEN 只写一次，别每节点重复**
   - ❌ 3 个节点 CTE 各写一遍 CASE WHEN + GROUP BY，改规则要改 3 处
   - ✅ UNION ALL 长表保留原始字段，加一层 `scene_detail AS (SELECT dt, CASE WHEN ... END AS scene, ... FROM funnel_detail)` 统一映射

3. **同源主表 + 同时间窗 + 维度互不相关 → 合并成一条 SQL，别拆多条串行跑**（[[feedback-sql-combine-when-safe]]）
   - ❌ "价格段分布" + "品牌 Top8" 拆成两条 SQL 串行，每条都重新扫主表过滤
   - ✅ 合并样板：
     ```sql
     WITH base AS (SELECT ... FROM 主表 WHERE 共同过滤),  -- 主表只扫一次
          dim_a AS (SELECT '维度A' dim, value, count(...) cnt FROM base GROUP BY ...),
          dim_b AS (SELECT '维度B' dim, value, count(...) cnt FROM base GROUP BY ...)
     SELECT * FROM dim_a UNION ALL SELECT * FROM dim_b ORDER BY dim, cnt DESC
     ```
   - 何时**不能**合：不同主表 / 不同时间窗 / 会产生笛卡尔积 / 一维慢查另一维快（拖累整条）

**自检准则**：写完 SQL 在 verify-lifecycle 前默念——"加一个节点/维度改 1 处还是 N 处？N 处就回头优化"。

**反模式**（2026-06-30 二奢漏斗 case）：抄字段不抄结构范式自己用笨写法重写 / 漏斗写成 3 个独立 CTE + LEFT JOIN（对应参考是 UNION ALL + 单层 CASE + 外层一次 GROUP BY）。

## Step 3.5 — 用户审 SQL（二合一，硬约束）

SQL 写完 `run` 之前，必须按**固定三段顺序**贴给用户：

### 版式（顺序不可变，中间不插分隔线/小标题）

```
1. 完整 SQL（代码块，不省略 CTE/WHERE/GROUP BY）
2. 业务描述（一句话，纯业务话术，讲"看什么 + 输出粒度"）
3. 口径（列表，只列业务上要拍板的关键参数：品类编码、分桶规则、阈值等；
   不写"事件级/分区/不过滤测试账号"这种技术默认）
```

**为什么二合一**：用户里有会 SQL 的分析师 + 不会 SQL 的业务方（产品/运营/老板）。不能假设用户能审 SQL，两层互相印证——描述跟 SQL 不一致时两层都能发现。

**多条 SQL 一起审**：所有 SQL 放一个代码块，`-- ===== SQL N: 标题 =====` 分块；业务描述按 SQL N 编号拆；口径统一列表。多条互不依赖时**默认并行跑**（同一消息发多个 Bash 调用）。

### 禁止跳过的 3 种情况
- 沿用历史 SQL 的主表/时间字段/过滤条件 → 必须显式确认没变
- 用户只说部分维度（如"看趋势"没说"支付日还是下单日"）→ 默认假设写进业务描述 + 跟用户确认
- 数据量预估 > 10 万行 → 告知行数预估 + 是否要 limit

### 反模式（已被用户怒怼过，别再犯）
- ❌ 用"看谁/算什么/拆什么/出什么"四行 bullet 描述 → 切碎业务逻辑
- ❌ SQL 在下、业务描述在上 → 顺序错
- ❌ SQL / 业务描述 / 口径中间硬插分隔线 `---` → 切成三块
- ❌ 只贴 SQL + 3 行口径（业务方看不懂盲说"可以跑"）
- ❌ 业务描述藏起"事件级 vs uid 级"关键假设
- ❌ 业务描述和 SQL 不一致（描述"已支付"，SQL 里没过滤支付状态）

详细样例见 `_分析上下文协议/business-statement.md` + [[feedback-sql-review-format]]。

## Step 4 — verify-lifecycle

```bash
python3 $SKILL_DIR/scripts/stariver_query.py verify-lifecycle --sql-file query.sql
```

脚本自动做：解析表 + `dt` 范围 + 生命周期（先看顶部 `-- @lifecycle <table>=<days|permanent>` 注释，没有再跑 `describe formatted` grep `lifecycle/ttl/retention`）+ 分区可用性（`SELECT MAX(dt)` 确认请求结束日 ≤ 最新可用分区）。

`@lifecycle` 注释语法（星河 describe formatted 不暴露生命周期时兜底，天数必须从 zeye 真实查过）：

```sql
-- @lifecycle hdp_zhuanzhuan_dm_global.dm_trade_order_detail_1d=permanent
-- @lifecycle hdp_ubu_zhuanzhuan_tmp_c2b.tmp_consignment_order_sale_detail_new_full_1d=180
SELECT ...
```

数值支持整数天数或 `permanent`（→ 9999 天）。

**判定**：
- `OK_TO_SUBMIT` → Step 5/6/7
- `REFUSE_SUBMIT` → 改 SQL（缩 dt 或换更长生命周期的表）后重 verify，禁止绕过
- 生命周期解析不到 → 拒绝，按 30 天保守需用户确认
- 多表 join → 取最小生命周期作为整条 SQL 上限

## Step 5/6/7 — 执行 + QA

- **5 小验证**：复杂 SQL 先 `limit` 或缩日期跑一次；错误提缺列/缺分区 → 重新 `describe` 修 SQL
- **6 正式 run**：报告结果路径 / 行数 / 预览 / 注意事项；大结果集不全文粘贴，存 CSV/TSV 后只贴关键行
- **7 产物 QA**：`run` 完必调 `result_qa.py`
  - hard_failures（触发即停）：行数 < 1 / 某列 100% 空
  - warnings（不阻塞）：单列 null 率 > 30% / "其他/未知" > 15% / 单列 distinct=1
  - 落 `.meta.json`（schema 见 `_分析上下文协议/output-schemas.md` §1）
  - 默认自动生成 xlsx 副本（用户全局要求），不要副本加 `--no-xlsx`
  - 退出码：`0` passed / `2` hard failure / `3-4` 输入缺失/异常

## ❌/✅ 速查表（违反就出问题）

| ❌ Don't | ✅ Do |
| --- | --- |
| Step 0 `check` 没过就写 SQL | 先用 agent-browser 引导用户申请 accessKey |
| 跳过 templates/ 直接 LM 现写 | Step 1 第 0 档先看模板库有没有匹配 |
| 跳过 search-cases 直接写 | 无论走哪档都要先跑 search-cases 拿本地案例 |
| 探表/搜历史/找映射中间过程一股脑展示 | 中间过程不暴露，只输出最终结论 |
| 凭记忆写 `SELECT a, b, c FROM xxx` | 字段必须来自参考 SQL 或当轮 describe |
| 无注释 / 只在顶部写标题 | 每个 CTE / WHERE 关键过滤 / JOIN 全局映射注释 |
| JSON 字段直接 group by | 探表识别后先告知用户"是 JSON，需选 key" |
| uid / token 混用没显式过桥 | 粒度统一，跨粒度必须 join 转换表 + 注释 |
| 沿用历史 CASE WHEN 阈值不问 | 业务分桶不可继承，问"沿用还是重定" |
| 跳过 Step 2.5，写完 SQL 才暴露自作主张口径 | Step 2.5 必走 8 类必问清单 |
| **套模板跳过 Step 3.5 直接 run** | **模板只免 Step 2；Step 2.5/3.5/4/7 一个都不能跳** |
| **找到参考只抄字段不抄结构范式** | **吃透参考的 UNION ALL / CASE 单层 / JOIN 顺序 / CTE 复用** |
| **多节点漏斗每节点单 CTE 再 LEFT JOIN** | **UNION ALL 长表 + 最外层一次 group by；CASE WHEN 只写一次** |
| SQL 硬填 `dt='2026-06-28'` 不查最新分区 | `verify-lifecycle` 已内置分区可用性检查 |
| `verify-lifecycle` REFUSE_SUBMIT 改阈值放行 | 修 SQL 或顶部加 `-- @lifecycle` 注释 |
| **SQL 写完不给用户看就 run** | **Step 3.5 必贴完整 SQL + 业务描述** |
| 沿用历史主表 / 时间字段不显式确认 | "上次用 X 表 + Y 字段，这次还一样吗" |
| 跑完 SQL 不做 QA 直接交给下游 | `run` 完必调 `result_qa.py` |
| LM 即兴写 pandas 检查空值率 | 直接 `result_qa.py`，阈值集中管理可审计 |
| 跑出 0 行不追因直接报"无数据" | 0 行 = hard_failure，先查分区/口径/过滤 |
| 大结果集（>10k 行）整文件贴回 | 存 TSV/CSV 后只贴关键预览行 |
| `pwd`/`path` 含中文/空格不加引号 | 中文路径必须双引号 |

## Safety Rules

- 硬约束 ①②③④（流程总览已列）
- 不打印 OA / accessKey / cookies / tokens
- 不 scan 所有库/所有表，除非用户显式要求且范围受限
- 默认 probe 小 + partition-aware
- 只预览新产生的结果文件（`result_is_new`），别把旧 `sql_result_*.tsv` 当当前结果
- 只读，禁止 destructive SQL
- 大结果集加聚合或 `limit`（除非用户显式要全量导出）

## 最小命令清单（高频，全部命令见 [commands.md](references/commands.md)）

```bash
# 探活 / 搜案例 / 跑 / 校验 / QA / 探表
python3 $SKILL_DIR/scripts/stariver_query.py check
python3 $SKILL_DIR/scripts/stariver_query.py search-cases "<关键词>" --top 5
python3 $SKILL_DIR/scripts/stariver_query.py verify-lifecycle --sql-file query.sql
python3 $SKILL_DIR/scripts/stariver_query.py run --sql-file query.sql
python3 $SKILL_DIR/scripts/result_qa.py --result-path /path/to/xxx.tsv --sql-file <SQL> --task-id <id>
python3 $SKILL_DIR/scripts/stariver_query.py describe db.table
python3 $SKILL_DIR/scripts/stariver_query.py sample db.table --where "dt='2026-06-17'" --limit 20
```

## References

- [workflow-details.md](references/workflow-details.md) —— Step 0 准入完整流程 + Step 1 首次跑数扫 VSCode 历史 + JOIN 顺序等次要优化 + One-Service API 参考
- [commands.md](references/commands.md) —— stariver_query.py / build_sql_index.py / result_qa.py 全部命令
- [sql_workflow.md](references/sql_workflow.md) —— 写非平凡 SQL / 调试表结构 / 决定探测顺序
- [table-discovery.md](references/table-discovery.md) —— 只给业务问题/关键词找表 + 评估敏感等级/生命周期/分区/后缀语义
- [business-glossary.md](references/business-glossary.md) —— ID 字段 / 品类 ID / 时间字段 / 场景字段等全局映射**单一事实来源**
- [sql-pitfalls.md](references/sql-pitfalls.md) —— 每次取数前过一遍：`SELECT *` 禁令 / `info_id` 精度 / 中文别名反引号 / UV 不可分组 / `GROUPING SETS` NULL / `\x01` 清洗
- [search-backend-tables.md](references/search-backend-tables.md) —— 搜索链路（搜索词/漏斗/召回/筛选/意图）9 张核心表 + 三键关联 + 宽表字段映射 + `datapool` JSON 结构
- [data-map-cache.md](references/data-map-cache.md) —— 表/字段/口径/关联键**优先看**。飞书数据地图本地缓存，每天 08:57 自动同步
- [apply-access-key.md](references/apply-access-key.md) —— Step 0 准入流程详细规则 + API 参考

---
name: 首页数据洞察
description: 转转 App 首页数据洞察的编排器 skill。每日自动调度,串行执行「代码生成 → 数据分析 → 质量检查 → 洞察结论生成 → 机会计算器」五步,产出首页核心模块的曝光/点击/利用效率分析、机会点结论与「机会点+策略+优先级+优化后收益」四要素飞书推送。当用户提到"首页数据洞察""淑芬",必须调用本 skill。**不要触发**:商详/搜索结果/转化漏斗等非首页主题(走通用 `claude-data-analysis`);单个模块的临时下钻(直接写 SQL,不进流水线);跨业务方的复盘报告(走 `report-writer`)。
metadata:
  type: orchestrator
  schedule:
    cron: "30 9 * * *"
    timezone: Asia/Shanghai
    note: "每天 09:30 触发完整流水线;禁用时改为 disabled: true。2026-07-13 起默认跑四页(G1001-G1004)/11 模块,cron 日常也跑四页。"
  pipeline:
    - 代码生成
    - 数据分析
    - 质量检查
    - 洞察结论生成
    - 机会计算器
---

# 首页数据洞察（编排器）

转转 App 首页每日数据洞察的串行流水线。本 skill 只做编排——通过 `Agent` 工具按顺序调度 5 个子 agent，每个子 agent 拥有独立上下文空间，前一步产物落盘后才进下一步。指标口径、字段定义、失败阈值都在子 agent 的 .md 文件里，本文件不重复。

> **分析范围（2026-07-13 起默认四页 / 11 模块）**：默认覆盖 **G1001 首页 + G1002 奢品馆 + G1003 兴趣圈 + G1004 数码集** 四页，核心模块 **11 个**（较旧版新增 `品类tab`/`品牌墙`）。**首页为主**——`primary_page = G1001`，机会计算器排 P0/P1/P2、conv_aov GMV 折算都以 G1001 为主排页；场馆页(G1002/3/4)效率差异写正文/附录作**结构参考**，不硬给小样本场馆页排 P0。**参数化双模**：把 `References/section-to-module.json` 的 `pages` 改成 `["G1001"]`（或子 agent/脚本传 `--pages`）即可退回单页模式，其余口径不变；单页模式下品类tab/品牌墙首页无曝光，允许缺失（QA 降级 soft，不 hard）。四页对比、page×module 矩阵、page×module×layer 三维、增量拆解走 exploration JSON 的 `pages[]` 块（schema 见 `References/output-schemas.md` §一·补）；`modules[]` 主块仍是 primary_page 的 11 模块（向后兼容）。

## 何时使用

"跑一下今天的首页洞察""首页有没有机会点""首页模块利用效率怎么样""按淑芬的口径出一版首页分析"，以及每日 cron 触发，都走本 skill。其它非首页主题的数据分析走通用 `claude-data-analysis`。

## 入口路由（两线分诊）

淑芬 bot 收到请求后**先分诊**，把它分到两条线之一。分诊在编排器层做（0 成本关键词 + 语义判断），不占子 agent 上下文。

```
[请求进入]
   ↓
[分诊] 这是「问一个数」还是「要一版机会点」？
   ├─ 数据问答线 → 调 agents/数据问答.md 子 agent（整合 5 领域，二次分诊到对应域取数/解读）——不进五步流水线
   └─ 机会点输出线 → 走既有五步流水线（代码生成→数据分析→质量检查→洞察结论生成→机会计算器）
```

**A. 机会点输出线（走全流程，五步串行）** —— 命中任一即归此线：

- 每日 cron（`30 9 * * *`）自动触发
- "跑今天的首页洞察""首页有没有机会点""出一版机会点+策略+优先级+收益""按淑芬口径出首页分析""首页模块利用效率诊断"
- 要的是**成体系的诊断产物**（结论层机会点 + 飞书文档 + P2P 推送），而非单个数值

处理：按下文「流水线契约」串行调度五个子 agent，产物落 `data_storage/`、`analysis_reports/`、`final_report/`、`visualizations/`。

**B. 数据问答线（不走流水线，单点取数/解读）** —— 命中任一即归此线：

- "X 指标是多少""某模块曝光/点击/日活多少""某品类转化漏斗怎样""一体化同城订单量多少""莫斯科消电大盘 DAU 多少""这个数怎么解读""帮我取一下 XX 的数"
- 要的是**一个数 / 一段解读 / 一次性取数**，不需要机会点排序与飞书发布整套编排

处理：调 `Agent` 工具启动**数据问答子 agent**，prompt = `agents/数据问答.md` 完整内容 + 用户原始问题 + dt。该子 agent 内部再做**二次分诊**（莫斯科 / 一体化 / 前端首页 / 经营品类 / 兜底跑数），选对应领域的表和脚本取数后作答。

```
Agent tool:
  subagent_type: general-purpose
  description: "数据问答线 - 二次分诊到5领域取数/解读"
  prompt: "用户问题: ${user_question}
    dt = ${dt}
    你的 agent 定义文件路径: ~/.claude/skills/数据洞察agent_淑芬/agents/数据问答.md
    请完整 Read 该文件并严格按其中的二次分诊与取数手册执行。"
```

**分诊拿不准时的默认**：问题里出现"机会点/优先级/优化收益/跑一版/出报告"等编排信号 → A 线；出现"是多少/查一下/取个数/怎么解读/对比一下"等取值信号 → B 线。两边信号都没有、纯粹一个指标名 → 默认 B 线（先给数，用户要机会点会再说）。**别把 A、B 两线并发跑**——先判定归属，再进对应线。

## 目录布局

```
数据洞察agent_淑芬/
├── SKILL.md                  # 本编排器
├── References/               # 业务规则真源（人读）+ 跨步骤产物契约（机器读）
│   ├── 代码生成要求和说明.md      # 业务规则真源，与飞书文档同步
│   ├── 分析要求和说明.md          # 同上
│   ├── output-schemas.md         # exploration / quality_check / feishu_doc 三套 JSON schema（含四页 pages[] 块）
│   └── section-to-module.json    # 11 模块切分常量 + 四页范围配置（pages/primary_page/strip/cap），sub-agent 不再重切
├── Scripts/                  # SQL 模板 + 维表只读结构 + dau_query.sql + 固化 Python 脚本（同一个目录）
│   ├── *.sql                 # 事件 SQL 模板（四页/10模块）+ 维表映射 + dau_query.sql（全量 DAU，全量推广分母）
│   ├── 商品id和品类业务的映射.sql # 商品表 dw_mysql_info_full_1d 建表结构 + info_id→业务/品类官方映射 CASE（只读参考，涉品类/业务颗粒度时用）
│   ├── qa_check.py           # Step 3 闸口（11 模块 + 四页覆盖校验）
│   ├── render_charts.py      # Step 4 出 5 张基础图 + 4 张四页对比图（单页模式自动跳过后者）
│   ├── feishu_publish.py     # Step 5 飞书 doc + P2P 推送（Step 4 只出本地产物,不调此脚本）
│   └── 新媒承接_*.sql / 新媒承接_出图.py  # 按需查询场景：业务重点名单×平台首次意向流向（不进主流水线，口径见 References/按需查询_新媒承接分析.md）
├── assets/                   # 模板/素材
│   └── report-template.md    # 报告骨架，sub-agent 按此填充
├── agents/                   # 独立子 agent 的 .md 文件
│   ├── 数据问答.md            # 数据问答线：二次分诊 5 领域（莫斯科/一体化/前端首页/经营品类/兜底跑数）取数解读，不进流水线
│   ├── 代码生成.md
│   ├── app体验机会点.md        # Step 1.5 软产物：读飞书 wiki 抽真人体验机会点（可选，缺失不阻断）
│   ├── 数据分析.md
│   ├── 质量检查.md
│   ├── 洞察结论生成.md
│   └── 机会计算器.md
└── _bundled_deps/            # 迁移物料：外部依赖备份 + 还原脚本（运行时不读，任何 sub-agent 都不加载）
    ├── install_deps.sh        # 目标机解压后跑一次，把依赖还原到 ~/.claude 规范位置
    ├── README_迁移部署.md      # 迁移部署步骤 + 部署自查清单
    ├── skills/xinghe-data/    # 主取数通道副本
    ├── skills/humanizer/      # 去 AI 味规范副本
    └── scripts/oneservice_cli.py  # 兜底取数通道副本
```

> **路径大小写硬约束（跨机器有效性）**：磁盘上的真实目录是大写 `References/`、`Scripts/`。所有 skill 内部引用必须用这个大小写，**不要写成 `references/` / `scripts/`**——本机 macOS 大小写不敏感看不出问题，但部署到 Linux / 区分大小写的文件系统会直接找不到文件。唯一例外是全局工具 `~/.claude/scripts/`（如 `oneservice_cli.py`），那是另一个目录，本来就是小写。

> **迁移/打包**：`_bundled_deps/` 是把 skill 迁到别的电脑用的——它按 `~/.claude` 的相对结构备份了 3 个外部依赖（xinghe-data、humanizer、oneservice_cli.py），目标机解压后 `bash _bundled_deps/install_deps.sh` 还原到规范位。`lark-cli`（外部二进制）和环境变量凭证装不进包，目标机自己配，详见 `_bundled_deps/README_迁移部署.md`。打包用 Python `zipfile` 强制 UTF-8 文件名（`flag_bits |= 0x800`），别用 macOS 自带 `zip`/`ditto`——它们不给中文名置 UTF-8 flag，跨系统解压会乱码。

产物落 `~/.claude/` 下的 `data_storage/`、`analysis_reports/`、`visualizations/${dt}/`、`final_report/`。中文文件名含 `&`、空格、`-`，shell 路径要加引号。

## 附：按需查询场景（不进主流水线）

联调群里会有临时的取数需求，跟首页曝光/点击/利用效率的主流水线无关，单独固化在这里。**这些不进「代码生成→分析→质检→结论→机会计算器」五步编排**，直接跑对应脚本取数即可。

| 场景 | 脚本 / SQL | 说明文档 |
|---|---|---|
| 用户活跃指标（DAU/MAU/30日活跃留存，分端） | `Scripts/用户活跃指标_DAU_MAU_留存.py`（参数化，推荐）<br>`Scripts/用户活跃指标_DAU_MAU_留存_分端.sql`（三段模板） | `References/按需查询_用户活跃指标.md` |
| 新媒承接分析（业务重点名单 × 平台首次意向标签 流向分布，整体/仅APP × 大盘/实验组） | `Scripts/新媒承接_{整体版,整体版_实验组,仅app端,仅app端_实验组}.sql`（4 条已验证）<br>`Scripts/新媒承接_出图.py`（匹配率柱状 + 流向堆叠） | `References/按需查询_新媒承接分析.md` |

新增同类按需场景时，按上面的模式加一行：脚本进 `Scripts/`、口径说明进 `References/按需查询_*.md`、在本表登记。

## 流水线契约

### 调度机制

每个步骤通过 **`Agent` 工具** 调度为一个独立子 agent。子 agent 拥有独立上下文空间，**不占用编排器的上下文预算**。编排器只负责：启动子 agent → 校验产物 → 进入下一步。每一步的业务逻辑、校验规则、失败处理由对应子 agent 的 .md 文件定义。

**编排器执行时必须严格遵守以下规则**：

1. **串行执行（指步骤之间）**：五个 step 彼此必须串行，每一步等上一步产物落盘后再启动下一步，**步骤间不要并发**。此规则约束的是 step 与 step 之间；**单个步骤内部的取数可以并发**——如 Step1 取数分两阶段（data1 先跑，其余 6 条并发提交给星河），详见 `agents/代码生成.md`「取数编排」节，不受本条限制。
2. **Agent 隔离**：每一步通过 `Agent` 工具启动，子 agent 的 prompt 为对应 .md 文件的完整内容 + dt 参数
3. **产物校验**：每步完成后，编排器验证预期文件是否存在、是否非空，通过后才进下一步
4. **失败即停**：任一步失败（Agent 返回错误 / 产物缺失 / 硬失败），编排器立即停止，不跳过、不静默重试
5. **日期参数**：`dt` 默认 t-1（YYYY-MM-DD），可由用户覆盖
6. **子 agent 类型固定 `general-purpose`**：本 skill 的每一步都靠「prompt = 对应 .md 文件完整内容」来驱动，业务逻辑全在 .md 里，不依赖任何专用 agent 预设。所以 6 个步骤的 `Agent` 调用**一律传 `subagent_type: general-purpose`**——**不要**猜测或拼接形如 `数据洞察agent_淑芬-xxx`、`首页洞察-xxx` 的类型名（那些要么不存在、要么覆盖不全 6 步，会直接报 "Agent type not found"）。

### 第一步：代码生成

**Agent 调用**：
```
Agent tool:
  subagent_type: general-purpose
  description: "Step 1 代码生成 - 取数脚本生成与执行"
  prompt: "dt = ${dt}
    你的 agent 定义文件路径: ~/.claude/skills/数据洞察agent_淑芬/agents/代码生成.md
    请完整 Read 该文件并严格执行其中的所有指令。"
```

**产物校验**（编排器逐项检查，缺一个即停）：
```bash
# 必须全部存在且行数 > 0
ls -la ~/.claude/data_storage/data1_user_sample_淑芬_${dt}.csv
ls -la ~/.claude/data_storage/data2-2_homepage_exposure_淑芬_${dt}.csv
ls -la ~/.claude/data_storage/data3-2_homepage_click_淑芬_${dt}.csv
ls -la ~/.claude/data_storage/data4-2_page_visit_duration_淑芬_${dt}.csv
ls -la ~/.claude/data_storage/dau_full_淑芬_${dt}.csv  # 全量推广分母
# 同时检查 .meta.json 存在
ls -la ~/.claude/data_storage/*_淑芬_${dt}.meta.json
# 保证产出（2026-07-01 起强制）：四页×11 模块转化率&客单价（含 page_id 列），Step5 单量/GMV 折算的 data-backed 乘数来源（主排页取 G1001）。
# 取数脚本自带 3 次重试 + 近 14 日兜底：当天星河跑不出就自动复用最近一个成功日的乘数（meta.source=fallback_from:YYYY-MM-DD）。
# 因此这张表几乎总应存在；只有近 14 日都无成功产物时脚本才 exit 1。校验：文件必须存在且行数>0。
ls -la ~/.claude/data_storage/淑芬/click_conv_aov/module_click_conv_aov_${dt}.csv || echo "[fail] conv_aov 缺失且近14日无兜底 → 价值折算缺乘数，Step1 失败停流水线，需人工"
# 软产物 data6：近28天(4整周)模块日度基线，喂 Step2 去周期异动判定。软校验——缺失或 meta.status=unavailable 都只 warn 不阻断（Step2 退回 D-1 单基线，无法去周期）
ls -la ~/.claude/data_storage/淑芬/module_daily_baseline/module_daily_baseline_${dt}.csv 2>/dev/null \
  || echo "[warn] data6 模块日度基线缺失 → Step2 退回 D-1 单基线判异动，不阻断"
```

子 agent 文件：[agents/代码生成.md](agents/代码生成.md)

### 第 1.5 步：app 体验机会点（软产物，可选，不阻断）

**前置条件**：第一步 5 个 CSV 全部落盘（本步的下游 Step2 假设检验要拿数据比对，故排在 Step1 之后；本步自身只读飞书 wiki，不依赖 Step1 产物）。

**作用**：读飞书 wiki `CBpNwlvA5iMpMYkqr0zcE5xFnrf`（真人 App 体验聚合机会点报告），抽出「产品机会点」作为数据输入，交给下游走假设检验→洞察→机会计算，让最终文档带上真人体验侧机会点（与数据侧并列区分）。**这是软产物**——读不到 / wiki 未更新 / 解析失败都只 warn 不阻断主流水线。

**Agent 调用**：
```
Agent tool:
  subagent_type: general-purpose
  description: "Step 1.5 app体验机会点 - 读飞书 wiki 抽真人体验机会点（软产物）"
  prompt: "dt = ${dt}
    你的 agent 定义文件路径: ~/.claude/skills/数据洞察agent_淑芬/agents/app体验机会点.md
    请完整 Read 该文件并严格执行其中的所有指令。"
```

**产物校验**（软校验：产物存在即通过，`status` 可为 ok/skipped_no_change/unavailable，**任何 status 都不阻断**）：
```bash
# 软产物：文件存在即可，status 三值都放行；连文件都没有也只 warn 不停
ls -la ~/.claude/analysis_reports/app_experience_opportunities_淑芬_${dt}.json 2>/dev/null \
  || echo "[warn] Step1.5 app体验机会点产物缺失 → 下游轨道 B 写占位，不阻断"
# revision 去重状态（首次不存在正常）
ls -la ~/.claude/data_storage/淑芬/app_exp_state.json 2>/dev/null || true
```

> **revision 去重**：本步用飞书 `revision_id` 去重——wiki 自上次处理无变化则 `status=skipped_no_change`、跳过抽取（不拿陈旧机会点天天刷屏）。**cron 每日触发也跑本步**，靠 revision 去重保证只有 wiki 真更新才重抽，平日近零开销。

子 agent 文件：[agents/app体验机会点.md](agents/app体验机会点.md)

### 第二步：数据分析

**前置条件**：第一步 5 个 CSV 全部落盘。

**Agent 调用**：
```
Agent tool:
  subagent_type: general-purpose
  description: "Step 2 数据分析 - 数据探索、异动根因下钻与机会点假设生成"
  prompt: "dt = ${dt}
    你的 agent 定义文件路径: ~/.claude/skills/数据洞察agent_淑芬/agents/数据分析.md
    请完整 Read 该文件并严格执行其中的所有指令。"
```

**产物校验**：
```bash
ls -la ~/.claude/analysis_reports/exploration_淑芬_${dt}.json
ls -la ~/.claude/analysis_reports/exploration_淑芬_${dt}.summary.md
ls -la ~/.claude/analysis_reports/hypotheses_淑芬_${dt}.md
```

子 agent 文件：[agents/数据分析.md](agents/数据分析.md)

### 第三步：质量检查

**前置条件**：第二步 3 个文件全部落盘 + 第一步 4 个 CSV 仍在。

**Agent 调用**：
```
Agent tool:
  subagent_type: general-purpose
  description: "Step 3 质量检查 - 数据层+结论层质量闸口"
  prompt: "dt = ${dt}
    你的 agent 定义文件路径: ~/.claude/skills/数据洞察agent_淑芬/agents/质量检查.md
    请完整 Read 该文件并严格执行其中的所有指令。"
```

**产物校验**：
```bash
ls -la ~/.claude/analysis_reports/quality_check_淑芬_${dt}.json
# 编排器必须读取该 JSON 的 passed 字段
# passed=false → 立即停止，不进入第四步
# passed=true 但 hard_failures 非空 → 同样停止（hard_failures 非空意味着数据不可信）
python3 -c "import json; q=json.load(open('$HOME/.claude/analysis_reports/quality_check_淑芬_${dt}.json')); exit(0 if q.get('passed') and not q.get('hard_failures') else 1)"
```

子 agent 文件：[agents/质量检查.md](agents/质量检查.md)

### 第四步：洞察结论生成

**前置条件**：第三步 `passed=true` 且 `hard_failures` 为空。

**Agent 调用**：
```
Agent tool:
  subagent_type: general-purpose
  description: "Step 4 洞察结论生成 - 报告撰写、可视化与飞书发布"
  prompt: "dt = ${dt}
    你的 agent 定义文件路径: ~/.claude/skills/数据洞察agent_淑芬/agents/洞察结论生成.md
    请完整 Read 该文件并严格执行其中的所有指令。"
```

**产物校验**：
```bash
ls -la ~/.claude/final_report/首页洞察_淑芬_${dt}.md
ls -la ~/.claude/visualizations/${dt}/module_ctr_rank_淑芬.png
ls -la ~/.claude/visualizations/${dt}/module_exposure_vs_ctr_淑芬.png
ls -la ~/.claude/visualizations/${dt}/user_layer_heatmap_淑芬.png
ls -la ~/.claude/visualizations/${dt}/daily_trend_淑芬.png
ls -la ~/.claude/visualizations/${dt}/feed_depth_distribution_淑芬.png
# 四页对比图（默认四页时产出 4 张；单页模式自动跳过，不参与闸口，缺失只 warn）
for f in page_overall_compare page_module_ctr_matrix incremental_contribution page_module_layer_heatmap; do
  ls -la ~/.claude/visualizations/${dt}/${f}_淑芬.png 2>/dev/null || echo "[warn] 四页图 ${f} 缺失（单页模式属预期，不阻断）"
done
ls -la ~/.claude/final_report/feishu_message_淑芬_${dt}.txt  # P2P 文本骨架(doc_url 留占位)
```

> **飞书文档创建时机（交给 Step 5）**：文档里的优先级/优化后收益要由 Step 5 回填，故文档在 Step 5 回填后才建，Step 4 只出本地报告 md + 5 图 + P2P 骨架（详见「全局约定」与「失败处理」）。所以 Step 4 校验**不要求** `feishu_doc_淑芬_${dt}.json`（那是 Step 5 产物），只校验报告 md + 5 张 png + message 骨架落盘。

子 agent 文件：[agents/洞察结论生成.md](agents/洞察结论生成.md)

### 第五步：机会计算器

**前置条件**：第四步报告 md + 5 张图 + P2P 文本骨架已落盘（飞书文档尚未创建——由本步创建）。

**Agent 调用**：
```
Agent tool:
  subagent_type: general-purpose
  description: "Step 5 机会计算器 - 机会量化、优先级排序、回填报告、建文档并推送"
  prompt: "dt = ${dt}
    你的 agent 定义文件路径: ~/.claude/skills/数据洞察agent_淑芬/agents/机会计算器.md
    请完整 Read 该文件并严格执行其中的所有指令。"
```

Step 5 收口顺序（agent 内部执行）：排优先级 → 回填报告 md（置顶「核心机会汇总」总表 + 结论层优先级+优化后收益）→ `render_charts.py --only-summary` 渲染汇总表配图 → `feishu_publish.py --skip-push` 建含优先级的文档拿 doc_url → 改写 message 为「机会点+策略+优先级+优化后收益」四要素结论 + 替换 doc_url → `feishu_publish.py --skip-doc` 推一条 P2P（文字 + 汇总表配图）。

**产物校验**：
```bash
ls -la ~/.claude/final_report/机会优先级_淑芬_${dt}.md
ls -la ~/.claude/final_report/opportunity_priority_淑芬_${dt}.json
ls -la ~/.claude/final_report/feishu_doc_淑芬_${dt}.json  # 本步建文档+推送,含 doc_url 与 im_push
ls -la ~/.claude/visualizations/${dt}/core_summary_table_淑芬.png 2>/dev/null || echo "[warn] 核心汇总表配图缺失 → 文字 P2P 照常,图片消息跳过,不阻断"
# opportunities[] 按 source 分组，每组内必须已按 P0→P1→P2 排序（两轨道各自有序）
python3 -c "
import json
o=json.load(open('$HOME/.claude/final_report/opportunity_priority_淑芬_${dt}.json'))
order={'P0':0,'P1':1,'P2':2}
ok=True
for src in ('data_flow','app_experience'):
    pr=[x['priority'] for x in o['opportunities'] if x.get('source','data_flow')==src]
    if pr!=sorted(pr,key=lambda p:order[p]): ok=False
exit(0 if ok else 1)"
# 文档已建(含 doc_url) 且 P2P 文字推送至少 1 人成功（图片消息 im_image_push 是补充，不参与闸口判定）
python3 -c "import json; d=json.load(open('$HOME/.claude/final_report/feishu_doc_淑芬_${dt}.json')); ok=sum(1 for p in d.get('im_push',[]) if p.get('status')=='ok'); exit(0 if d.get('doc_url') and ok>0 else 1)"
# 内容级校验（防占位漏填过闸）：置顶总表已回填(报告 md 不再残留 Step5 回填占位串)
grep -q "由 Step5 回填\|优先级/收益由 Step5\|待 Step5 回填" ~/.claude/final_report/首页洞察_淑芬_${dt}.md \
  && { echo "[fail] 报告 md 仍残留 Step5 回填占位串 → 置顶表/结论层未真回填,Step5 失败停,需人工"; exit 1; } || true
# 内容级校验：至少一条提升型机会的收益已带单量/GMV(而非全占位"待业务提供")
python3 -c "
import json
o=json.load(open('$HOME/.claude/final_report/opportunity_priority_淑芬_${dt}.json'))
ups=[x for x in o['opportunities'] if x.get('source','data_flow')=='data_flow' and (x.get('impact_incremental_click_uv_full') or 0)>0]
# 提升型机会存在时,必须至少一条带 data-backed 单量/GMV(module_click_conv_aov 保证产出)
bad = ups and not any((x.get('impact_incremental_orders_full') or x.get('impact_gmv_full')) for x in ups)
exit(1 if bad else 0)" \
  || { echo "[fail] 有提升型机会但收益全无单量/GMV → conv_aov 乘数漏折算,Step5 失败停,需人工"; exit 1; }
```

子 agent 文件：[agents/机会计算器.md](agents/机会计算器.md)

### 流水线状态速查

| 步骤 | 子 agent | 输入（来自上一步） | 输出（落盘产物） | 闸口 |
|---|---|---|---|---|
| 1 | 代码生成 | dt（默认 t-1） | `data_storage/data{1,2-2,3-2,4-2}_*_淑芬_${dt}.csv` + `dau_full_淑芬_${dt}.csv` + `.meta.json`（硬产物）；`淑芬/click_conv_aov/module_click_conv_aov_${dt}.csv`（保证产出，喂 Step5 强制折算单量/GMV，脚本自带重试+近14日兜底）；`淑芬/module_daily_baseline/module_daily_baseline_${dt}.csv`（软产物，近28天模块日度基线，喂 Step2 去周期异动判定） | 5 硬产物行数 > 0 + 命中率 ≥ 95%；conv_aov 必须存在且行数>0（当天失败走兜底，近14日都无才失败停）；data6 基线软校验缺失/unavailable 不阻断 |
| 1.5 | app体验机会点 | dt（读飞书 wiki，不依赖 Step1 产物） | `analysis_reports/app_experience_opportunities_淑芬_${dt}.json`（软产物）+ `.md` + `data_storage/淑芬/app_exp_state.json`（revision 去重态） | **软校验**：产物存在即过，status(ok/skipped/unavailable) 任意都不阻断；缺失也只 warn |
| 2 | 数据分析 | 4 个 CSV（+ 可选 module_daily_baseline 近28天基线、app_experience JSON） | `analysis_reports/exploration_淑芬_${dt}.json`（含 `anomaly_vs_baseline` 去周期异动块）+ `.summary.md` + `hypotheses_淑芬_${dt}.md`（含末尾「app体验机会点验证」小节） | token 子集校验通过 |
| 3 | 质量检查 | 4 CSV + exploration JSON | `analysis_reports/quality_check_淑芬_${dt}.json` | **passed=true 且 hard_failures 为空** |
| 4 | 洞察结论生成 | exploration + hypotheses + quality_check（+ 可选 app_experience JSON） | `final_report/首页洞察_淑芬_${dt}.md`(结论层两轨道 A/B，优先级/收益留位) + 5 张 png + `feishu_message_淑芬_${dt}.txt`骨架（不建文档不推送） | 报告 md（含轨道 A/B）+ 5 图 + message 骨架落盘 |
| 5 | 机会计算器 | 第 4 步报告机会点 + exploration + hypotheses + quality_check（+ 可选 app_experience JSON） | `机会优先级_淑芬_${dt}.md` + `opportunity_priority_淑芬_${dt}.json`(每条带 source) + 回填置顶核心汇总表&两轨道结论层 + `core_summary_table_淑芬.png`配图 + 建飞书文档 + 四要素结论 message + 推 P2P(文字+配图) | 两轨道各自优先级已排序(P0前) + 文档含 doc_url + 文字推送至少 1 人成功(配图为补充不参与闸口) |

## 失败处理

- 前一步是后一步的硬依赖，不要静默重试或跳过。
- 子 agent 返回错误或产物缺失 → 编排器 stdout 打出失败步骤 + 缺失的文件路径，停在那里等人工。
- 步骤 3 `hard_failures` 非空 → 必须停，不进入第 4 步。`passed = (hard_failures 为空)` 是铁律。
- 步骤 4 **不建飞书文档、不推 IM**——只出报告 md + 5 张图 + P2P 文本骨架；任一本地产物缺失 = Step 4 失败，停下等人工。
- 步骤 5 收口飞书：先回填报告 md 结论层（优先级+优化后收益）→ `--skip-push` 建含优先级的文档（创建失败 = 退出码 3 = Step 5 失败，停，不回退发本地路径）→ 改写四要素 message → `--skip-doc` 推 P2P。文档已建但 IM 推送失败 → 仅用 `--skip-doc` 重推、复用已有 `doc_url`，**不要**重建文档、**不要**回退发本地路径。

## 全局约定

- **口径权威副本**：CTR/场馆tab cap/ratio 推广/收益折算这几条跨 agent 复用口径的真源在 [`References/口径真源.md`](References/口径真源.md)。各 agent .md 与下面各条仍写有就地操作细节（隔离上下文要就地可读），**任何冲突以 `References/口径真源.md` 为准**；改口径顺序：飞书文档 → 口径真源.md → 各 agent 就地文案。
- 默认中文输出。
- **报告固定三层结构**：Step 4 产出的洞察报告从上到下固定三层——**第一层「结论」**(机会点 → 对应策略建议 → 优先级 P0/P1/P2 位 → 指标提升 点击UV/单量/GMV) → **第二层「正文」**(分析框架图 → 整体 → 模块 → 分层 → 迁移/坑位下钻，全量量级) → **第三层「附录」**(①抽样原始数据结果 ②抽样方式和样本质量 ③数据源描述)。骨架见 `assets/report-template.md`。结论层「优先级」由 Step 5 机会计算器回填；「指标提升」的**单量/GMV 由 Step5 强制折算**(乘数来自 `module_click_conv_aov`，Step1 保证产出)，提升型机会必带增量点击 UV + 单量 + GMV，绝不硬编。
- **场馆tab（section_id=106）曝光埋点 cap**：`venue_tab.exposure_uv / home_overall.exposure_uv < 90%`（默认触发）时，Step2 把 `venue_tab.exposure_uv` 改记为 `home_overall.exposure_uv`、`uv_ctr` 重算，报告显式标注触发与原始数字。完整替代规则见 [`References/口径真源.md`](References/口径真源.md) §二。
- **CTR 唯一口径 = UV-CTR**（`click_uv / exposure_uv`）；PV-CTR 已废弃，schema/报告/图表/sub-agent 不出现 `pv_ctr` 或"PV-CTR"，`exposure_pv`/`click_pv` 仍采集作量级但不算 CTR。完整定义见 [`References/口径真源.md`](References/口径真源.md) §一。
- **报告正文统一用全量推广量级**：绝对量（曝光/点击 UV·PV、点击次数、覆盖人数、增量点击 UV）呈现全量推广值（样本 × `ratio`，`ratio = dau_full.uv / n_users`）；比例/统计量（UV-CTR/覆盖率/χ²/jaccard）不乘 ratio、正文直接用；样本规模/口径/ratio 及来源放附录。`ratio` 分母来自 `Scripts/dau_query.sql` 当日实跑，**不许硬编码**。完整推广算法见 [`References/口径真源.md`](References/口径真源.md) §三。
- 凭证只走环境变量：星河 `XINGHE_CLIENT_USER` / `XINGHE_CLIENT_SECRET` / `XINGHE_ACCESS_KEY`，One-Service `ONESERVICE_OA` / `ONESERVICE_ACCESS_KEY`，任何脚本都不要硬编码。
- 飞书发布**当前（2026-06-18 起）只推送给钟梦婷一人 P2P**（`ou_5e572adca6deef8ef21c3b18dfade573`），纯文本格式，不推群。**董亚坤（`ou_95979765a4545fa542b0a5ac47e950c8`）已暂停推送，等用户明确放开再恢复双推**——`LARK_INSIGHT_RECEIVERS` 只放钟梦婷的 open_id。如需调整，改 `LARK_INSIGHT_RECEIVERS` 环境变量并相应更新 cron prompt 与本节。文档默认仅创建者可见；发送方应用为「菜的飞书cli」（appId `cli_aa8e16c998b89cc5`），appSecret 由 `lark-cli config` 在本机管理，任何脚本/SKILL 都不写明文。
- 业务规则真源在 `References/`，对应飞书文档：飞书文档先变 → References 同步 → 再改 sub-agent 实现。
- 可视化必须显式设置中文字体（`PingFang SC` / `Heiti SC` / `Arial Unicode MS` / `SimHei`），避免方块乱码。
- **app 体验机会点（轨道 B）来源与去重**：Step 1.5 只读飞书 wiki `CBpNwlvA5iMpMYkqr0zcE5xFnrf`（真人 App 体验聚合机会点报告，`--as user` 身份），**只搬运 wiki 已有结论，不臆造机会点、不改 wiki 的证据强度/优先级**；用飞书 `revision_id` 去重（`data_storage/淑芬/app_exp_state.json` 记上次处理版本，无变化则 `skipped_no_change`）。cron 每日随主流水线一起跑本步，靠 revision 去重保证只有 wiki 真更新才重抽。app 体验来的结论（机会点/策略/优先级/收益）在报告结论层与数据侧**分两并列轨道**（轨道 A 数据洞察 / 轨道 B app 体验），不混排；能映射到 11 模块且有对应指标的走 SQL 量化，映射不到的（商详/搜索结果/跨路径类）保留定性、标「待真人/埋点验证，无法量化收益」。
- **去周期异动判定（排除周期性波动，2026-07-03 起）**：异动判定**不再只跟 D-1 或近 7 天比**——Step1 产出软产物 `module_daily_baseline`（近 28 天=4 整周的模块日度基线，每天在**当天范围内**用 1/339 哈希桶**独立去重**算，绝不跨天去重）。Step2 对这条日序列算双判据：主判据 `z_window`（当天 vs 整窗 28 天均值/标准差）+ 辅判据 `z_dow`（当天 vs 历史**同星期几**，专门扣掉周一~周日的周内周期）。**仅当 `|z_window|≥2` 且 `|z_dow|≥2` 且两者同号才算真异动**（去周期后仍显著），只在周内周期内的波动（如周末自然低点）判为"周期性波动"、不进机会点。落 exploration JSON 的 `anomaly_vs_baseline` 块（schema 见 output-schemas §一）。基线软产物缺失/unavailable → 退回 D-1 单基线并在报告标注"历史窗不可用，无法去周期"。
- **核心汇总表（飞书文档置顶 + 消息末尾配图）**：Step 5 回填优先级/收益后，必须在飞书文档**最前面**放一张核心汇总表，表头固定 `模块 | 机会 | 策略 | 优先级 | 收益`（两轨道机会点合并，按 P0→P1→P2 排，轨道用列内标签区分）；并把这张表渲染成一张 PNG（`Scripts/render_charts.py` 出 `core_summary_table_淑芬_${dt}.png`），作为图片消息**追加在 P2P 文字消息末尾**。表格与配图内容口径完全一致，收益列无 data-backed 参数时写占位不硬编。

## ❌/✅ 速查（关键约束，违反就出问题）

| ❌ Don't | ✅ Do |
|---|---|
| sub-agent 即兴写 QA / 画图 / 飞书发布 Python | 直接调 `Scripts/qa_check.py` / `render_charts.py` / `feishu_publish.py`（`Scripts/` 下脚本是产物契约一部分） |
| sub-agent 重新推断 11 模块的 section_id 切分 / 页面范围 | 读 `References/section-to-module.json` 当常量用（含 pages 四页配置） |
| sub-agent 自创 exploration / quality_check 字段名 | 严格按 `References/output-schemas.md` 的 schema |
| `passed=true` 但有 hard_failures 时硬跳进 Step 4 | 必须停，等人工；`passed = (hard_failures 为空)` |
| Step 4 自己建飞书文档 / 推 IM | Step 4 只出本地报告 md + 5 图 + message 骨架；建文档+推送整段是 Step 5 的事（文档要带 Step 5 回填的优先级） |
| Step 5 文档创建失败回退发本地 md 路径 | 文档失败 = Step 5 失败；路径不能给业务方 |
| Step 5 IM 推送失败时把文档重建一遍 | 复用已建 doc_url，只重推 IM（`Scripts/feishu_publish.py --skip-doc`） |
| 把 P2P 改成群聊或互联网公开 | P2P 是项目级硬规则；文档默认仅创建者可见 |
| 在脚本/SKILL 里写明文 appSecret / 星河密码 | 凭证只走 `lark-cli config` 与 `~/.zshrc` env var |
| 报告只有抽样数字、没有全量量级（业务方读不出业务感） | 正文统一用全量推广量级，样本原始量放附录，**ratio 必须来自当日 dau_query.sql 实跑** |
| 把 CTR / 覆盖率也乘以 ratio 当成"全量 CTR" | 比例指标保持（分子分母同比放大）；只有 UV/PV/次数类绝对量乘 ratio |
| 全量推广用历史/常识 DAU（如"300 万"硬编码） | 跑 `Scripts/dau_query.sql` 拿当日真实 DAU，落 `data_storage/dau_full_淑芬_${dt}.csv` |
| 报告/图表/schema 仍出现"PV-CTR"或 `pv_ctr` 字段 | **PV-CTR 已废弃**，只算 UV-CTR；`exposure_pv` / `click_pv` 仍上报但不再算 PV-CTR |
| 用旧的"PV 中位 4.25%"给机会点定 gap | 唯一口径 UV-CTR，中位取 primary_page(G1001) 有曝光模块中位（剔 capped venue_tab），随天浮动、当日实算不硬编 |
| 只拿 D-1 单基线判异动 / 跨天对 UV 去重当"周期均值" | 用 `module_daily_baseline` 近28天基线，各天单独去重算日序列；z_window + z_dow 双判据，同号且都≥2 才算真异动 |
| 把周末/节假日的自然低点当成异动机会点 | 必看 `z_dow`（同星期几基准）；z_window 显著但 z_dow 不显著 = 周期性波动，判 false 不下钻 |
| 直接拿 `venue_tab.exposure_uv=590` 当真，UV-CTR=60% 当 Top1 | 若 venue_tab 曝光 UV / 首页曝光 UV < 90% 触发 cap：venue_tab.exposure_uv = home_overall.exposure_uv；UV-CTR 重算；报告显式标注修复 |
| 编排器自己写 SQL / 跑分析 / 画图（挤占主流程上下文） | 编排器只调 `Agent` 工具启子 agent，不自己做业务逻辑 |
| 并发执行 4 个步骤 | 严格串行：每步产物落盘校验通过后才进下一步 |
| Step 5 分多条飞书消息 / 建多份文档 | 只建一次文档(`--skip-push`)、推一次 P2P(`--skip-doc`)；那唯一一条就是「机会点+策略+优先级+优化后收益」四要素结论 + 文档链接，一天只推一条 |
| Step 5 把比例指标(UV-CTR/覆盖率)乘 ratio 当"全量机会" | 只有增量点击 UV/次数类乘 ratio；比例保持 |
| Step 5 给搜索框/金刚位等高位模块硬编"提升机会" | 高于 primary_page 有曝光模块中位的是 P2「维持基本盘」，不进提升排序 |
| Step 5 自己拍 GMV 折算参数（转化率/客单价） | 读 `module_click_conv_aov_${dt}.csv` 取 data-backed 乘数（增量订单=增量点击UV×pv_conv_rate_diff，增量GMV=增量订单×笔均客单价，置信度上限MEDIUM 含选择偏差）；这张表由 Step1 保证产出（重试+近14日兜底），**单量/GMV 强制折算，不再有"只给点击UV"的降级**；若 meta.source=fallback_from:X 则报告标注「乘数取自 X 日，非当日」 |
| Step 1.5 即兴臆造 app 机会点 / 改 wiki 的优先级或证据强度 | 只搬运 wiki `CBpNwlvA5iMpMYkqr0zcE5xFnrf` 已有结论，保留 wiki 原 `wiki_priority` / `evidence_strength`；读不到/未更新/解析失败都 `exit 0` 软跳过，不阻断主流水线 |
| 把 app 体验结论与数据洞察结论混排在一起 | 报告结论层分两并列轨道（轨道 A 数据洞察 / 轨道 B app 体验），各一套机会点/策略/优先级/收益；轨道 B 映射不到模块的保留定性标「待验证无法量化」 |
| 飞书文档正文一上来就是分析细节、没有一眼看全的总表 | 文档**最前面**放核心汇总表 `模块 \| 机会 \| 策略 \| 优先级 \| 收益`（两轨道合并按 P0→P1→P2），再接三层报告正文 |
| P2P 只发纯文字、汇总表靠文字堆叠读不动 | 把核心汇总表渲染成 PNG（`core_summary_table_淑芬_${dt}.png`）作为图片消息追加在文字消息**末尾**，注意美观与文字/配图口径一致 |

# 【${dt}】首页数据洞察日报

> 本模板供 agents/洞察结论生成.md 渲染最终报告时填充。占位符用 `${...}` 标记。**报告固定三层结构,从上到下顺序硬约束:第一层「结论」→ 第二层「正文」→ 第三层「附录」**。业务方点开先看结论层(机会点+策略+优先级+指标提升),想追数据再往下看正文,要溯源再翻附录。

> **正文口径:全量推广量级**。正文所有"个数类"指标(曝光 UV/PV、点击 UV/次数、机会点覆盖人数、增量点击 UV 等绝对量)一律只呈现**全量推广值**(样本绝对量 × `ratio`),不再并排样本原始数。**比例/统计量**(UV-CTR、覆盖率、spread、χ²、jaccard 相似度)与样本/全量无关(分子分母同比放大后数值不变),正文直接用即可、不乘 ratio。原始样本层数据(n_users、抽样口径、ratio、关键指标样本绝对量)统一挪到**附录**保留供追溯。

> **CTR 唯一口径 = UV-CTR**(`click_uv / exposure_uv`,看到模块的人里多少点了)。**PV-CTR 已废弃**,本流水线不再产出该指标——`exposure_pv` / `click_pv` 仍上报作量级展示,但不计算"每次曝光转化的点击次数"这一口径。任何旧报告/旧 schema 的 PV-CTR 数据迁移时直接删除该列。

> **GMV 占位铁律**:结论层「指标提升」的 GMV 位,**用户没提供转化率/客单价参数(或无 `module_click_conv_aov` 数据)时不许硬编 GMV**——只给增量点击 UV,GMV 位填占位符 + 一句"GMV/单量折算待业务提供转化率与客单价参数",绝不臆造数字。单量同理:有下单/成交口径可折算才给全量量级,无参数则占位。

> **场馆tab 曝光埋点 cap 修复**:section_id=106 是首页常驻 tab,理论上曝光 UV 应 ≈ 首页曝光 UV;若原始比例 < 90% 触发 cap——exposure_uv 改用 home_overall.exposure_uv,UV-CTR 用新分母重算;exposure_pv / click_pv 保留场馆tab 自身原始 PV(仅作量级展示)。**cap 后的读数默认可信,可直接下业务结论,无需等待 section106 埋点修复**(埋点修复降级为附录一条工程待办,不阻塞结论)。所有报告章节同步:11 模块表加 `(capped)` 标注、附录写 changelog。详见 [`../agents/洞察结论生成.md`](../agents/洞察结论生成.md) 「场馆tab 曝光埋点 cap」专章。

> **分析范围:四页 / 11 模块(2026-07-13 起默认)**:报告覆盖 G1001 首页 + G1002 奢品馆 + G1003 兴趣圈 + G1004 数码集,核心模块 11 个。**首页为主**:结论层机会点、优先级、收益都以 primary_page(G1001) 为主排页;场馆页(G1002/3/4)效率差异写正文「§2.4 四页对比」与附录作**结构参考**,不硬给小样本场馆页排 P0。中位/gap 测算用 **primary_page 有曝光模块 UV-CTR 中位(剔 capped venue_tab)**。单页模式(config `pages=['G1001']`)下 §2.4 与四页图退回单页叙事、可省略。

---

# 核心机会汇总（置顶总表）

> **位置硬约束：这张表必须是整份飞书文档的第一块内容，排在所有分层结论之前**——业务方点开文档一眼看全「哪个模块、什么机会、怎么做、多急、能提升多少」。表头固定五列 `模块 | 机会 | 策略 | 优先级 | 收益`，两轨道（数据洞察 + app体验）机会点**合并进这一张表**，按 P0→P1→P2 排；轨道用「模块」列区分——数据侧填真实模块名，app体验且映射不到模块的填「app体验」。
>
> **本表由 Step5 机会计算器回填**（Step4 阶段先留骨架 + 一句「优先级/收益待 Step5 回填」占位）。收益列口径与结论层完全一致：可量化的给「增量点击 X万/日（+单量/GMV，有 module_click_conv_aov 数据才带）」，`verifiable=false` 的写「待真人/埋点验证，无法量化」，无业务参数的写「待业务参数」，**绝不硬编 GMV**。同一张表同一份数据也会由 `render_charts.py` 渲染成 `core_summary_table_淑芬_${dt}.png`，作为图片消息追加在 P2P 文字末尾，**表与图口径必须一致**。

| 模块 | 机会 | 策略 | 优先级 | 收益 |
|---|---|---|---|---|
| _(Step5 回填：两轨道机会点合并，P0→P1→P2)_ | | | | |

---

# 第一层 · 结论

> 给业务方先看结论。**结论层分两条并列轨道,顺序硬约束:轨道 A「数据洞察机会点」(常规 SQL 数据侧)在前,轨道 B「app体验机会点」(真人 App 体验)在后**。两轨道各自独立成套「①机会点 ②策略建议 ③优先级 ④指标提升」,并各出一张 P0/P1/P2 表——app 体验来的结论与数据侧结论**并列区分、不混排**,让业务方一眼看清哪些是埋点数据挖出来的、哪些是真人体验挖出来的。绝对量给全量推广值(样本 × ratio);比例/统计量(UV-CTR、χ²、倍数)直接用样本值(与全量一致)。

---

# 轨道 A · 数据洞察机会点（常规 SQL 数据侧）

> 来源:10 首页模块 × 四页 × 用户分层的埋点数据（data1~4-2）。以下四块是数据侧机会点的完整结论（首页为主，场馆页作结构参考）。

## A.一、机会点

按优先级排,每条带:模块、现象、**全量量级**。Top 不足 6 条时按实有数量。绝对量给全量推广值(样本 × ratio);比例/统计量(UV-CTR、χ²、倍数)直接用样本值(与全量一致)。

1. **[模块]** 现象一句话
   - 全量量级: 反推到 App DAU=${dau_full.uv} 后,曝光 UV ≈ ${exposure_uv × ratio}、点击 UV ≈ ${click_uv × ratio};UV-CTR=${uv_ctr}、vs 模块均值 ±Y%、z0 是 z4-z5 的 N 倍(比例/倍数与样本一致);对齐到 primary_page(G1001) 有曝光模块 UV-CTR 中位(剔除 capped venue_tab)可日多产出点击 ≈ ${exposure_uv × (uv_ctr_target − uv_ctr_actual) × ratio}
   - 待验证: 引用 hypotheses_淑芬_${dt}.md 中对应假设的反向条件
2. **[模块]** ...

> 受 quality warn 影响的机会点,在条目末尾加 `⚠ 数据待复核`。

## A.二、策略建议(与机会点一一对应)

每个机会点配一条**具体**的产品功能/策略动作,不空泛(不要停在"建议优化")。示例:"大促banner 覆盖广但 CTR 倒一 → 做素材 A/B(动态 vs 静态)+ 按用户分层换活动主题";"z0 新用户停留长但点低位模块 → 给 z0 单独配新人向坑位排序"。这份「机会点 → 策略建议」清单是下游 Step5 机会计算器的主输入(Step5 据此排优先级,不重写建议本身)。

1. **[模块]** 具体动作:改什么功能 / 调什么策略。
2. ...

## A.三、优先级(P0/P1/P2)

> **本节骨架由本 agent 留位,P0/P1/P2 由下游 Step5「机会计算器」追加/回填**。Step5 按「重要 × 紧急」量化排序后写入(仅 `source=data_flow` 的机会点),本 agent 先留下面表格骨架和位置,不自己拍优先级。

| 级别 | 模块 | 机会一句话 | 判定逻辑(重要×紧急) |
|---|---|---|---|
| P0 | _(Step5 回填)_ | | |
| P1 | | | |
| P2 | | | |

## A.四、优化后收益(指标提升:点击 UV / 单量 / GMV)

> 三个量都给。**点击 UV 必给**(全量增量);**单量、GMV 依赖业务参数,无参数则占位,不臆造**(GMV 铁律见顶部)。这三项由下游 Step5 在有 `module_click_conv_aov` 数据时回填单量/GMV;本 agent 阶段无参数则保持占位。

| 提升指标 | 全量量级(增量/日) | 口径与来源 |
|---|---:|---|
| **增量点击 UV** | ${incremental_click_uv × ratio} | 主口径:对齐 primary_page 有曝光模块 UV-CTR 中位后日多产出点击 UV = 曝光UV × (uv_ctr_target − uv_ctr_actual) × ratio(绝对量,全量=样本×ratio) |
| **增量单量** | ${incremental_orders_full 或 占位} | 有下单/成交口径(`module_click_conv_aov` 或业务提供转化率)可折算才填全量;**无参数则填"待业务提供转化率参数"**,由 Step5 有数据时回填 |
| **增量 GMV** | ${incremental_gmv_full 或 占位} | **铁律:无转化率+客单价参数不许硬编**,填"GMV/单量折算待业务提供转化率与客单价参数";有 `module_click_conv_aov` 数据时由 Step5 回填(标 MEDIUM 含选择偏差) |

---

# 轨道 B · app体验机会点（真人 App 体验）

> 来源:飞书 wiki 真人 App 体验聚合机会点报告(按 user-chance 输出规范产出),经 Step1.5 抽取、Step2 交叉验证。**读 `analysis_reports/app_experience_opportunities_淑芬_${dt}.json` + `hypotheses_淑芬_${dt}.md` 的「app体验机会点验证」小节**。
>
> **占位规则**:app_experience JSON 缺失 / `status=skipped_no_change`(wiki 未更新) / `status=unavailable`(读取失败) 时,本轨道四块各写一句占位——「本期 app 体验 wiki 无更新/不可用(status=<值>),无新增体验机会点」,不硬造。
>
> **与轨道 A 的关键区别**:① 每条机会点带 **wiki 优先级 + 证据强度(高/中高/中/低) + round 证据**;② 收益列区分「可量化」(`verifiable=true`,映射到首页模块,Step5 回填增量点击 UV 等)与「定性」(`verifiable=false`,首页埋点覆盖不到,标"待真人/埋点验证,无法量化收益");③ 优先级沿用 wiki 原级,Step5 仅对可量化条目做量化排序。

## B.一、机会点(真人体验)

按 wiki 原优先级排,每条带:机会点标题、解决的问题、**证据强度**、round 证据、是否可量化。

1. **[机会点标题]**（wiki优先级 ${wiki_priority} / 证据强度 ${evidence_strength} / ${verifiable ? "可量化→映射模块 " + mapped_module : "定性·首页埋点覆盖不到"}）
   - 解决的问题: ${problem}
   - 数据侧交叉验证: 引 hypotheses「app体验机会点验证」小节的 APP-H{n} 结论（CONFIRMED/REJECTED/待验证 或 保留定性）
   - 证据: wiki ${evidence_refs}（真人体验，${sample_caveat 摘要：如"4 轮模拟器样本，方向性线索"}）
2. ...

> 全局 caveat（来自 app_experience JSON 的 `sample_caveat`）在本轨道开头统一说明一次：真人侧多为小样本模拟器体验，是方向性线索，高优项进需求前建议真机复核。

## B.二、策略建议(真人体验，与机会点一一对应)

每个体验机会点配 wiki 的「建议方向」（原样带出，不改写）+ 可落地细化。

1. **[机会点标题]** 建议方向: ${suggestion}
2. ...

## B.三、优先级(P0/P1/P2·真人体验)

> **本节骨架留位,由 Step5 回填**。Step5 对 `source=app_experience` 的机会点单独排:`verifiable=true` 的按量化影响×紧急度定级;`verifiable=false` 的沿用 wiki 原优先级(不重新量化)。与轨道 A 的优先级表**分开**。

| 级别 | 机会点 | 证据强度 | 可量化? | 判定逻辑 |
|---|---|---|---|---|
| P0 | _(Step5 回填)_ | | | |
| P1 | | | | |
| P2 | | | | |

## B.四、优化后收益(真人体验)

> 区分可量化与定性两栏。

| 机会点 | 收益(增量/日) | 口径与来源 |
|---|---:|---|
| [可量化机会点] | ${incremental_click_uv × ratio 等} | `verifiable=true`,映射到首页模块,Step5 按增量点击 UV/单量/GMV 公式回填(标 source=app_experience) |
| [定性机会点] | 待真人/埋点验证 | `verifiable=false`,首页埋点覆盖不到,**无法量化收益**,保留真人体验定性,建议真机复核或补埋点 |

---

## 执行摘要

3-5 句。先用一句话讲整体表现(全量量级 + UV-CTR 唯一口径),再用 1-2 句解释数据侧 top 机会点;若本期有 app 体验机会点,再用一句话点出体验侧最高优的那个(带证据强度)。**不要**用"综上所述""总而言之"。

---

# 第二层 · 正文(数据分析结论)

> 数据分析结论,**分层级结构**:整体 → 模块 → 分层 → 迁移/坑位下钻,层级清晰逐层递进。正文所有绝对量用全量推广量级,比例/统计量(UV-CTR/覆盖率/χ²)直接用(不乘 ratio)。正文开头先放一张「分析框架图」交代本报告怎么切分、怎么看。

## 0. 分析框架图

> **此处放分析框架图**——用一张结构化示意说明本报告的分析框架:四页(G1001-G1004)/11 模块切分、用户分层、UV-CTR 口径、样本→全量推广逻辑、坑位下钻路径。**当前实现:用下面的 markdown 结构化框架(表格/列表)承载,不新增 PNG**(新增静态图要动 render_charts.py + 契约,风险大;轻量实现优先)。若后续判断必须出 PNG,则在此处注明"分析框架图(PNG)"占位并说明来源,不硬造。

```
首页数据洞察 · 分析框架
────────────────────────────────────────────
① 数据源      data1(用户分层) + data2-2(曝光) + data3-2(点击) + data4-2(feed) + dau_full(全量DAU)
                       ↓ 1/339 哈希桶抽样 n_users≈9k
② 口径        UV-CTR = click_uv/exposure_uv(唯一口径,PV-CTR 已废弃)
              绝对量 × ratio 推全量;比例/统计量不乘 ratio
              场馆tab section106 曝光 cap:分母用首页 UV(默认可信)
                       ↓
③ 分析层级    整体(四页各自有没有被用) → 模块(11 模块利用效率排行 + 高曝光低转化)
              → 分层(z0/z1-z3/z4-z5 差异 + χ² 显著性) → 四页对比(page×module 矩阵 + 增量拆解 + 分层三维)
              → 迁移/坑位下钻(去周期异动 + 挤压 + 金刚位/栏目区/feed 深度)
                       ↓
④ 推广        样本信号 × ratio → 全量量级;χ²/连续天数作全量数字置信背书
                       ↓
⑤ 收口        机会点 → 策略建议 → (Step5)优先级 → 指标提升(点击UV/单量/GMV)
────────────────────────────────────────────
```

> 说明:这是文字/结构化框架,承载"报告怎么读"的导航;各章节的量化图表见下文 5 张 PNG。

## 1. 首页整体使用情况

回答业务问题 1:首页整体有没有被有效使用?**下表数字均为全量推广量级**(绝对量 = 样本 × ratio;UV-CTR 为比例、与样本一致)。

| 指标 | 全量量级 | 备注 |
| --- | ---: | --- |
| 首页曝光 UV | ${home_overall.exposure_uv × ratio} | 进入首页的用户数(全量) |
| 首页曝光 PV | ${home_overall.exposure_pv × ratio} | 总曝光次数(全量,量级展示,不再算 PV-CTR) |
| 首页点击 UV | ${home_overall.click_uv × ratio} | 点击过任意位的用户数(全量) |
| 首页点击 PV | ${home_overall.click_pv × ratio} | 总点击次数(全量,量级展示,不再算 PV-CTR) |
| **整体 UV-CTR** | ${home_overall.uv_ctr} | = click_uv / exposure_uv,**进入首页的人里有多少点了一下**(比例,与样本一致) |

> 样本原始绝对量与 ratio 见附录。

## 2. 模块结构与用户行为

回答 2-4。绝对量列(曝光/点击 UV·PV)为全量推广值;UV-CTR 为比例、直接用。

### 2.1 11 模块利用效率排行（首页 primary_page）

图: visualizations/${dt}/module_ctr_rank_淑芬.png — 按 `ranked_by_uv_ctr_desc` 列出 Top3 / Bottom3,每条带 UV-CTR 与全量曝光 UV/PV。表中每个模块行包含 UV-CTR 列;全量曝光 PV / 点击 PV 列作量级展示,**不再有 PV-CTR 列**。

> **场馆tab(section_id=106)行**:exposure_uv 列写 `${home_overall.exposure_uv × ratio} (capped)`、备注列写「场馆tab 曝光埋点漏报,本报告用首页曝光 UV 作分母重算其 UV-CTR;**该读数默认可信,据此下业务结论,无需等待 section106 埋点修复**(埋点修复列为附录工程待办)」。

### 2.2 曝光 vs UV-CTR 散点
图: visualizations/${dt}/module_exposure_vs_ctr_淑芬.png — y 轴为 UV-CTR;`high_exposure_low_uv_ctr_candidates` 标注 UV 维度的"高曝光低转化"模块。

### 2.3 各主要模块内部子元素(sortName)拆解

> 读 `exploration.module_subelement_rank`——每个点击 UV≥100 的主要模块（金刚位/搜索框/商卡feed流/回收模块/场馆tab/栏目区等）各出一张子元素排行表，回答"每个区域里各子模块表现如何"。这是**常驻块**，不依赖当日有无异动。

对每个模块，按下表列出该模块内子元素（`sortName`）按点击 UV 降序 Top10（多的截断为"其余 N 个合计"）：

| 子元素(sortName) | 点击 UV(全量) | 曝光 UV(全量) | UV-CTR | 点击 UV 占模块内占比 | 备注 |
|---|---|---|---|---|---|
| ${sortName} | ${click_uv × ratio} | ${exposure_uv × ratio 或 —} | ${uv_ctr 或 —} | ${click_uv_share} | ${sample_warn ? "样本不足,方向参考" : ""} |

规则：
- 点击 UV / 曝光 UV 是绝对量，给全量推广值（× ratio）；UV-CTR / 占比是比例，直接用不乘 ratio。
- 该模块曝光无坑位粒度时，`exposure_uv` / `uv_ctr` 列填"—"并在表下注一句"该模块曝光埋点无子元素粒度，仅给点击 UV 与占比"。
- `sample_warn=true`（子元素点击 UV<30）的行，备注列标"样本不足，方向参考"，不做显著性判定。
- `sortName` 为"未命名"（原始缺失/null/0）的子元素照常列出，不丢弃。
- feed 流深度分布仍附图: feed_depth_distribution_淑芬.png（与子元素表并列，反映商卡 feed 的翻页深度）。

### 2.4 四页对比（G1001-G1004；首页为主，场馆页作结构参考）

> 读 exploration JSON 的 `pages[]` 块 + `incremental` 块。单页模式(config `pages=['G1001']`)下本节退回单页叙事或整节省略。四张对比图配四段结论，每图跟着对应结论段走（勿把图堆到文末）。

**2.4.1 四页整体对比** — 图: visualizations/${dt}/page_overall_compare_淑芬.png
逐页曝光/点击 UV（全量）+ 页内 UV-CTR（剔离场型后的对外口径）。一句话点出四页量级梯度（首页占绝对大头，场馆页量级小）与页内转化效率差异。**离场型 strip 口径**：页面级 §1 CTR 分子剔「离场型」点击——106场馆tab在G1002/3/4剔、G1001不剔；500底部导航四页统一剔（实际只首页有，首页因此从全口径约 92% 降到页内约 70%）。§2.2/§2.4.2/增量用全口径点击。

**2.4.2 page × module UV-CTR 矩阵** — 图: visualizations/${dt}/page_module_ctr_matrix_淑芬.png
11 模块 × 四页的 UV-CTR 热力（`*` 标注场馆tab cap）。点出同一模块在不同页的效率差异（如某模块在场馆页 CTR 明显高/低于首页），作**结构参考**——场馆页样本小，仅方向，不据此单独给场馆页排 P0。

**2.4.3 扩页面增量贡献** — 图: visualizations/${dt}/incremental_contribution_淑芬.png
各模块 G1001 曝光 UV vs G1002+3+4 三页增量曝光 UV 堆叠。读 `incremental`：`net_new`（四页合并去重 union − 首页 home）反映扩三页真正净增了多少人（`incremental.home` 用 G1001 原始全口径点击，不复用 §1 剔后值）。若 net_new 占比很低，说明三页用户与首页高度重叠，扩页面的边际触达增量有限——如实写，不夸大。

**2.4.4 page × module × 分层三维** — 图: visualizations/${dt}/page_module_layer_heatmap_淑芬.png
逐页 × 模块 × 分层（z0/z1-z3/z4-z5）UV-CTR。场馆页各层样本很小（可能每层几十人），仅方向参考、不做 χ² 显著性。点出分层×页面的结构性差异（如某档用户在某页某模块特别活跃）。

## 3. 用户分层差异

回答 5。图: visualizations/${dt}/user_layer_heatmap_淑芬.png — 主热力按 UV-CTR;引用 `chi_square_layer_vs_click` 中 `significant=true` 的模块,每个写一句"X 模块 z0 UV-CTR=A% vs z4-z5 B%(χ²=Y, p<0.05)"。χ²/UV-CTR 均为统计量/比例,与全量一致,直接用(不乘 ratio);χ² 检验本身基于点击次数列联表,UV-CTR 受其显著性背书。

## 4. 结构迁移与挤压(坑位下钻)

回答 6-8。图: visualizations/${dt}/daily_trend_淑芬.png

- D/D-1 异动 Top: `anomaly_vs_d_minus_1` 中 `|delta_pct| > 0.2`(UV-CTR 用比例直接读;曝光 UV/PV、点击次数等绝对量给全量推广值)
- 高曝光低价值: 与 §2.2 呼应
- 模块挤压: `module_co_exposure_jaccard` 中 jaccard > 0.5 的对子(jaccard 为相似度,与全量一致)

## 5. 待验证清单

回答 9-10:当前数据是否足够支持机会判断 / 哪些必须等真实数据或实验验证。

- 需要补充的数据: ...
- 需要做的实验: ...
- 受质量检查影响的结论(如有 warn):
  - ⚠ ${warning.check}: ${warning.details}

---

# 第三层 · 附录

> 三块固定:①抽样的原始数据结果 ②抽样方式和样本质量描述 ③数据源描述(外加 cap changelog 与质量 warn 原文两条工程/审计附件)。正文全量量级 = 样本绝对量 × `ratio`;统计显著性(χ²/连续天数)在样本上验证,是全量数字的置信背书。正文干净用全量、可信度靠本附录背书。

## 附录一、抽样原始数据结果(供追溯)

关键指标的**样本原始绝对量**表(正文用其 × ratio 的全量值):

| 指标 | 样本原始值 | 全量 ≈ (× ratio) |
| --- | ---: | ---: |
| 首页曝光 UV | ${home_overall.exposure_uv} | ${home_overall.exposure_uv × ratio} |
| 首页曝光 PV | ${home_overall.exposure_pv} | ${home_overall.exposure_pv × ratio} |
| 首页点击 UV | ${home_overall.click_uv} | ${home_overall.click_uv × ratio} |
| 首页点击 PV | ${home_overall.click_pv} | ${home_overall.click_pv × ratio} |
| 11 模块曝光/点击 UV·PV | 见 exploration JSON | × ratio |

- **比例/统计量说明**:UV-CTR、覆盖率、spread、χ²、jaccard 与样本/全量无关(分子分母同比放大后数值不变),正文直接用样本计算值,**不乘 ratio**。

## 附录二、抽样方式和样本质量描述

- **抽样口径**:1/339 哈希桶抽样(总桶数 339);指标全部读自 `analysis_reports/exploration_淑芬_${dt}.json`。
- **样本规模**:`n_users = ${n_users}`(z0=${user_layer_distribution.z0} / z1-z3=${user_layer_distribution.z1-z3} / z4-z5=${user_layer_distribution.z4-z5})。健康样本 n_users≈9k。
- **当日 ratio 及来源**:`dau_full.uv = ${dau_full.uv}`(转转 App 当日 distinct token,来源 `Scripts/dau_query.sql` 实跑,落 `data_storage/dau_full_淑芬_${dt}.csv`);`ratio = dau_full.uv / n_users = ${ratio}`(健康范围 [330, 350];超出即在正文全量量级处加"⚠ 抽样代表性偏差,仅作量级感参考")。
- **样本代表性 / 统计显著性(作全量数字置信背书)**:1/339 哈希桶抽样在层级与来源分布上与全量是否一致,用 quality_check 的 `user_layer_distribution` / `user_source_distribution` 对照全量层级表(不可得则记为已知偏差);χ² 显著性 + 连续天数在样本上验证,是全量数字的置信背书;绝对量级 ±5–10% 是合理误差区间;受 quality warn 影响的模块全量量级同样带 ⚠。
- **连续天数**:本次覆盖的连续观察天数(判断信号是单日噪声还是趋势)。

## 附录三、数据源描述

- **事件源与口径**:
  - `data1` — 用户分层源(z0/z1-z3/z4-z5 打标),提供 n_users 抽样口径。
  - `data2-2` — 曝光事件源(exposure_uv / exposure_pv)。
  - `data3-2` — 点击事件源(click_uv / click_pv)。
  - `data4-2` — feed 流事件源(feed 深度分布)。
  - `dau_full` — 全量 DAU,来源 `Scripts/dau_query.sql` **当日实跑**(不硬编码),落 `data_storage/dau_full_淑芬_${dt}.csv`,作全量推广 ratio 分母。
- **平台与 dt 口径**:数据经 star river(StarRocks/Hive)/ one-service 平台执行;分区口径 `dt = ${dt}`(默认 t-1)。
- **数据集元信息**:行数 = ${row_counts}、生成时间、SQL hash、`dau_full.uv` = ${dau_full.uv}、`ratio` = ${ratio}。

## 附录四、场馆tab 埋点 cap 修复 changelog

贴 raw vs capped 对照表(raw_exposure_uv / capped 用首页 UV / raw_uv_ctr / capped_uv_ctr)+ 工程修复 owner / 时间。**说明:cap 后读数默认可信、正文已据此下业务结论,埋点修复仅为工程待办、不阻塞结论。**

## 附录五、质量检查警告原文

完整 quality_check JSON 的 `warnings` 数组。

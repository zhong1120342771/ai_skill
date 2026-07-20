<!-- CONTRACT_START
name: cohort-analysis
description: Perform cohort analysis -- retention curves, cohort comparison, vintage analysis, and cohort LTV -- to reveal how user behavior evolves over time.
inputs:
  - name: COHORT_DIMENSION
    type: str
    source: user
    required: true
  - name: RETENTION_EVENT
    type: str
    source: user
    required: true
  - name: PERIODS
    type: str
    source: user
    required: true
  - name: DATASET
    type: str
    source: system
    required: true
  - name: DATA_INVENTORY
    type: file
    source: agent:data-explorer
    required: false
outputs:
  - path: working/cohort_analysis_{{DATASET}}.md
    type: markdown
  - path: working/charts/retention_heatmap.png
    type: chart
  - path: working/charts/retention_curves.png
    type: chart
  - path: working/charts/ltv_curves.png
    type: chart
depends_on:
  - source-tieout
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: 5
CONTRACT_END -->

# Agent: Cohort Analysis

## 目的
对数据集做同期群分析——留存曲线、同期群对比、批次（vintage）分析和同期群 LTV——以揭示用户行为如何随时间演变、哪些同期群最有价值，产出一份带留存矩阵、LTV 曲线、趋势评估和可视化规格的结构化分析报告。

## 输入
- {{COHORT_DIMENSION}}：用于划分同期群的列（例如 signup_date 截断到月、first_purchase_date 截断到周）。它根据用户的首个合格事件来决定如何把用户分入同期群。
- {{RETENTION_EVENT}}：在每个周期里算作 "留存" 的事件（例如 purchase、login、page_view、session_start）。必须映射到数据中具体的事件或条件。
- {{PERIODS}}：同期群形成后要跟踪的周期数（例如 12 表示 12 个月，26 表示 26 周）。周期粒度与同期群维度粒度一致（月度同期群 = 月度周期）。
- {{DATASET}}：数据源引用。可以是文件路径（CSV、Parquet）、数据库表引用，或 MotherDuck/DuckDB 连接串。若已有 Data Explorer Agent 报告，引用它获取 schema 和质量上下文。
- {{DATA_INVENTORY}}：（可选）Data Explorer Agent 的数据盘点报告。若提供，用它了解可用列、质量问题和连接关系。避免重复的数据画像。

## 工作流

### 预检查（Pre-flight）

写任何 SQL 查询之前：

1. **检查更正** —— 读取 `.knowledge/corrections/index.yaml`。若 `total_corrections > 0`：
   - 扫描 `.knowledge/corrections/log.yaml`，找匹配当前数据集或你计划查询的表的条目
   - 若有相关更正，应用它：用更正后的列名、过滤条件、连接或指标定义
   - 在工作笔记中记下应用了哪些更正

2. **检查 query archaeology** —— 搜索已验证的模式：
   - 对每个计划查询的表，用 `helpers/archaeology_helpers.py` 的 `search_cookbook(table_name)`
   - 用 `search_table_cheatsheet(table_name)` 获取表元数据（粒度、坑、常见连接）
   - 若某 cookbook 条目匹配你的意图，优先用已验证的 SQL 而非从头写
   - 若某表 cheatsheet 有坑，把它们作为约束纳入

3. **为空则静默跳过** —— 若无更正或 archaeology 条目，正常继续，不输出任何关于缺少预检查数据的内容。

### 第 1 步：构建同期群定义
根据 {{COHORT_DIMENSION}} 把每个用户分入同期群。

**1a. 确定同期群归属**
每个用户恰属于一个同期群——其首个合格事件所在的周期。通过把同期群维度列截断到合适粒度来计算。

```python
# Example: Monthly cohorts based on first event
# For each user, find their earliest event timestamp
# Truncate to month → that is their cohort
# Result: a mapping of user_id → cohort_period
```

**1b. 计算同期群规模**
对每个同期群，计数唯一用户数（"起始计数"）。这是所有留存计算的分母。

**1c. 校验同期群定义**
- 确认每个用户恰好出现在一个同期群（无跨同期群重复）
- 检查空同期群（用户数为零的周期）——它们表示数据缺口
- 报告覆盖的日期范围和形成的同期群数量
- 标记用户数少于 50 的同期群——小同期群的结果不可靠

### 第 2 步：构建留存矩阵
对每个同期群，计算在后续每个周期里执行了 {{RETENTION_EVENT}} 的用户百分比。

**2a. 按周期计数留存用户**
对每个 (同期群, period_offset) 对，计数该同期群中在该周期执行了留存事件的不同用户数。

```python
# Example: For cohort "2024-01", period_offset 3
# Count distinct users whose first event was in Jan 2024
# AND who performed the retention event in Apr 2024 (3 months later)
```

**2b. 计算留存率**
把每个周期的留存计数除以该同期群的起始计数。以百分比表示。

| Cohort | Period 0 | Period 1 | Period 2 | ... | Period N |
|--------|----------|----------|----------|-----|----------|
| 2024-01 | 100% | 45% | 32% | ... | 18% |
| 2024-02 | 100% | 48% | 35% | ... | 20% |
| ... | ... | ... | ... | ... | ... |

### 第 3 步：归一化并处理右删失
把所有值表示为同期群起始计数的百分比，并处理较新同期群的不完整数据。

**3a. 归一化**
留存矩阵中每个单元格为：(周期 X 的留存用户) / (同期群起始计数) * 100。Period 0 永远是 100%。

**3b. 处理右删失**
较新同期群尚未到达较后的周期。把这些单元格标为 N/A，而非 0%。

```python
# Example: If today is 2024-06 and the cohort is "2024-04"
# Period 0 and Period 1 have data
# Period 2+ should be N/A (the cohort hasn't had time to reach those periods)
# NEVER fill right-censored cells with 0% — this creates survivorship bias
```

根据数据的日期范围，为每个同期群确定可观测的最大周期。超过此截止点的任何周期为 N/A。

### 第 4 步：计算带置信区间的聚合留存曲线
产出跨所有成熟同期群的 "平均留存曲线"。

**4a. 跨同期群求平均**
对每个 period offset，仅用已到达该周期的同期群（排除 N/A 值）计算平均留存率。这就是聚合留存曲线。

**4b. 加置信区间**
用 `helpers/stats_helpers.py` 的 `confidence_interval()` 为每个周期的平均留存计算 95% 置信区间。

```python
# For each period offset:
# Collect retention rates from all cohorts that have data for this period
# Compute mean and confidence_interval(rates_series, confidence=0.95)
# Result: aggregate curve with error bands
```

**4c. 报告曲线**
把聚合留存曲线以表格呈现：

| Period | Mean Retention | 95% CI Lower | 95% CI Upper | N Cohorts |
|--------|---------------|-------------|-------------|-----------|
| 0 | 100.0% | 100.0% | 100.0% | [all] |
| 1 | 46.2% | 43.1% | 49.3% | [n] |
| ... | ... | ... | ... | ... |

### 第 5 步：对比同期群曲线
判断留存随时间是改善、劣化还是稳定。

**5a. 趋势评估**
对每个 period offset（例如 Period 1 留存、Period 3 留存），按时间顺序把该值在各同期群间作图。是否存在上升或下降趋势？

- **改善：** 较新同期群在相同 period offset 上的留存优于较早同期群
- **劣化：** 较新同期群的留存劣于较早同期群
- **稳定：** 无明显趋势

**5b. 识别离群同期群**
标记任何在任意周期上偏离该周期均值超过 2 个标准差的同期群。这些同期群值得调研——这些用户身上发生了不一样的事。

**5c. 量化趋势**
计算关键周期（Period 1、Period 3、若有则 Period 6）的留存在各同期群间的斜率。报告方向和幅度："过去 6 个月，Period 1 留存每个同期群改善 +1.2 个百分点。"

### 第 5b 步：计算同期群 LTV（若有收入数据）
若数据集含收入或订单数据，按同期群和周期计算人均累计收入。

**5b-i. 检查收入数据**
判断数据是否含收入列（例如 order_total、revenue、transaction_amount）。若没有，跳过本步骤并注明："LTV analysis skipped — no revenue data available."。

**5b-ii. 按同期群计算累计 LTV**
对每个 (同期群, period_offset) 对，计算：
- 该同期群截至该周期的累计总收入
- 除以同期群起始计数得人均 LTV

```python
# Example: Cohort "2024-01" at Period 3
# Sum all revenue from users in that cohort across Periods 0-3
# Divide by cohort starting count
# Result: cumulative LTV per user at Period 3
```

**5b-iii. 按同期群作 LTV 曲线**
每个同期群有一条累计 LTV 曲线。叠加在单张图上以对比。

**5b-iv. 识别 80% 成熟点**
对最成熟的同期群，确定它们在哪个周期达到其最终观测 LTV 的 80%。这告诉业务："一个同期群大约需要 N 个周期才能兑现其大部分生命周期价值。"

**5b-v. 按 LTV 给同期群排序**
识别哪些同期群最有价值、哪些最无价值。与任何已知业务事件（促销、产品发布、季节性效应）交叉对照，假设其原因。

### 第 6 步：计算成熟同期群基准
用最老、最完整的同期群建立基线。

**6a. 选取成熟同期群**
取拥有全部 {{PERIODS}} 个周期数据的 3 个最老同期群（若不足 {{PERIODS}}，则取可得的最大周期数）。

**6b. 平均它们的留存曲线**
对这 3 个同期群在每个周期计算平均留存率。这就是 "成熟同期群基准"。

**6c. 把较新同期群与基准对比**
对每个较新同期群，计算其在每个周期与基准的差异。标记较新同期群偏离基准超过 5 个百分点的周期。

### 第 7 步：产出可视化
生成让留存数据可立即解读的图表。

**7a. 留存热力图**
构建热力图，y 轴为同期群、x 轴为 period offset。颜色深浅代表留存百分比。用 `helpers/chart_helpers.py` 的 `swd_style()` 做样式。

```python
# Apply swd_style() before generating any chart
# Heatmap: rows = cohorts (newest at top), columns = period offsets
# Color scale: dark = high retention, light = low retention
# Annotate each cell with the retention percentage
# Mark N/A cells distinctly (e.g., light gray with no annotation)
```

用 `action_title()` 设一个洞察驱动的标题（例如 "January cohort retains 30% better than average at Month 6"），而非描述性标题。

**7b. 留存折线图叠加**
把每个同期群的留存曲线画成一条线，用 `helpers/chart_helpers.py` 的 `highlight_line()` 高亮聚合曲线。各同期群线条应淡化；聚合曲线应加粗。

**7c. LTV 曲线（若已计算）**
按周期画人均累计 LTV，每个同期群一条线。高亮最有价值和最无价值的同期群。用 `annotate_point()` 标出 80% 成熟点。

**7d. 保存所有图表**
用 `helpers/chart_helpers.py` 的 `save_chart()` 把所有图表保存到 `working/charts/`。

### 第 8 步：验证
跑验证检查以确保分析可靠。

**8a. 幸存者偏差检查**
确认右删失周期被标为 N/A 而非 0%。若任何较新同期群在其尚未到达的周期显示 0% 留存，这是数据错误——修正它。

**8b. 最小同期群规模检查**
标记每个用户数少于 50 的同期群。这些同期群应带注意事项纳入留存矩阵，但从聚合计算和趋势分析中排除。

**8c. 日期范围覆盖检查**
核验数据覆盖了预期的完整日期范围。若有缺口（例如缺月份），标记它们——缺失的数据周期会造成人为的留存下跌。

**8d. 留存单调性检查**
留存通常应随时间下降（或趋平）。若 Period N 的留存显著高于 Period N-1，调研：这可能表示再激活活动、数据质量问题，或留存事件定义问题。

**8e. 同期群规模稳定性检查**
检查同期群规模是否剧烈波动（例如某个同期群是另一个的 10 倍）。同期群规模差异大会扭曲聚合曲线。若差异大，注明哪些同期群主导了聚合、以及这是否影响结论。

**8f. 交叉验证**
对留存矩阵中至少 2 个单元格做抽查：手动跑底层查询，确认计数一致。记录检查了哪些单元格及结果。

## 输出格式

保存到 `working/cohort_analysis_{{DATASET}}.md` 的 markdown 文件，结构如下：

```markdown
# Cohort Analysis Report
**Generated:** {{DATE}}
**Dataset:** {{DATASET}}
**Cohort Dimension:** {{COHORT_DIMENSION}}
**Retention Event:** {{RETENTION_EVENT}}
**Periods Tracked:** {{PERIODS}}

## Executive Summary
[3-5 sentences: the headline retention story. Is retention improving or degrading?
 What is the current steady-state retention? Which cohorts stand out and why?
 If LTV was computed, what is the typical payback period?]

## Cohort Definitions
| Cohort | Starting Count | Date Range |
|--------|---------------|------------|
| [cohort 1] | [n] | [start - end] |
| [cohort 2] | [n] | [start - end] |
| ... | ... | ... |

**Total users:** [n]
**Total cohorts:** [n]
**Cohorts with < 50 users (flagged):** [list or "none"]

## Retention Matrix
[Full retention matrix table with N/A for right-censored cells]

## Aggregate Retention Curve
| Period | Mean Retention | 95% CI Lower | 95% CI Upper | N Cohorts |
|--------|---------------|-------------|-------------|-----------|
| ... | ... | ... | ... | ... |

## Cohort Trend Assessment
**Overall trend:** [Improving / Degrading / Stable]
**Evidence:** [slope at key periods, comparison of recent vs. mature cohorts]
**Outlier cohorts:** [list with brief explanation]

## Mature Cohort Benchmark
**Benchmark cohorts:** [which 3 cohorts]
**Benchmark curve:** [table]
**Newer cohorts vs. benchmark:** [summary of deviations]

## Cohort LTV Analysis (if applicable)
[Cumulative LTV table by cohort and period]
**80% maturity point:** [N periods]
**Most valuable cohort:** [cohort] — [cumulative LTV per user]
**Least valuable cohort:** [cohort] — [cumulative LTV per user]

## Visualization Specs
- **Retention heatmap:** `working/charts/retention_heatmap.png`
- **Retention line overlay:** `working/charts/retention_curves.png`
- **LTV curves (if applicable):** `working/charts/ltv_curves.png`

## Validation Report
| Check | Result | Detail |
|-------|--------|--------|
| Right-censoring handled (no false 0%) | PASS / FAIL | [detail] |
| Minimum cohort size (>= 50 users) | PASS / WARN | [flagged cohorts] |
| Date range coverage complete | PASS / WARN | [gaps found] |
| Retention monotonicity | PASS / WARN | [anomalies] |
| Cohort size stability | PASS / WARN | [variance] |
| Cross-validation spot-check | PASS / FAIL | [cells checked] |

## Data Limitations
- [Limitation 1: what it affects and how]
- [Limitation 2]

## Recommended Next Steps
1. [Specific action based on findings]
2. [Follow-up analysis to run — which agent, what inputs]
3. [Stakeholder conversation to have]
```

## 使用的 Skill
- `.claude/skills/visualization-patterns/skill.md` —— 用于第 7 步的所有图表生成，含主题选择、配色、标注规范和图表类型选择逻辑
- `.claude/skills/triangulation/skill.md` —— 用于第 8 步对留存计算的交叉对照和合理性核对
- `.claude/skills/data-quality-check/skill.md` —— 用于同期群构建前的数据就绪校验，用严重度评定判断分析能否继续

## 验证
在呈现同期群分析报告前，核实：
1. **每个用户恰属一个同期群** —— 各同期群起始计数之和应等于有合格事件的唯一用户总数。若有差异，解释它（例如同期群维度值为 null 的用户）。
2. **Period 0 永远是 100%** —— 按定义，同期群中所有用户在 Period 0 都 "留存"。若任何同期群在 Period 0 显示 < 100%，说明留存事件定义或同期群归属有误。
3. **右删失单元格是 N/A，而非 0%** —— 未到达较后周期的较新同期群必须显示 N/A。右删失位置出现任何 0% 都是会造成幸存者偏差的严重错误。
4. **聚合曲线仅用对该周期有数据的同期群** —— N Cohorts 列应随较后周期递减，因较新同期群退出。若 N Cohorts 在所有周期恒定，说明右删失未被处理。
5. **置信区间随同期群增多而收窄** —— 早期周期（贡献的同期群更多）应比较后周期有更紧的 CI。若此模式反转，说明 CI 计算有问题。
6. **留存（通常）单调不增** —— 留存应随时间下降或趋平。若较后周期出现显著上升，在作为发现报告前先调研。
7. **图表与数据相符** —— 核验热力图或折线图中至少 2 个值与留存矩阵对应单元格一致。讲出与表格不同故事的图表是严重错误。
8. **发现是洞察，而非描述** —— 重读 Executive Summary 和 Trend Assessment。它们应陈述何事重要（"Q1 同期群在 Month 6 留存高 30%，很可能因为新手引导改版"），而非陈述测了什么（"为 12 个同期群计算了留存"）。
9. **小同期群被排除在聚合计算外** —— 任何用户数少于 50 的同期群都应在 Cohort Definitions 表中标记，并从聚合曲线和趋势分析中排除。
10. **LTV 计算使用累计收入** —— 若计算了 LTV，核验同一同期群 Period N 的 LTV 始终 >= Period N-1。LTV 是累计的，必须单调不减。

## 集成
本 agent 是从 `run-pipeline` 调用的流水线步骤。它作为独立分析步骤运行，**不**嵌套在 Descriptive Analytics 内。无 agent 间相互调用——流水线编排器提供输入并收集输出。

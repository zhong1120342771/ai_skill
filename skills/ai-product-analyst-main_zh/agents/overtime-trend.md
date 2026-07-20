<!-- CONTRACT_START
name: overtime-trend
description: Perform time-series analysis to identify trends, detect anomalies, decompose seasonality, and produce annotated timeline charts.
inputs:
  - name: DATASET
    type: str
    source: system
    required: true
  - name: TIME_COLUMN
    type: str
    source: user
    required: true
  - name: METRIC_COLUMNS
    type: str
    source: user
    required: true
  - name: GRANULARITY
    type: str
    source: user
    required: false
  - name: SEGMENTS
    type: str
    source: user
    required: false
  - name: ANALYSIS_CONTEXT
    type: str
    source: user
    required: false
outputs:
  - path: outputs/trend_report_{{DATE}}.md
    type: markdown
  - path: outputs/charts/*.png
    type: chart
  - path: working/timeseries_prepared.csv
    type: markdown
depends_on:
  - source-tieout
knowledge_context:
  - .knowledge/datasets/{active}/schema.md
  - .knowledge/datasets/{active}/quirks.md
pipeline_step: 5
CONTRACT_END -->

# Agent: Overtime / Trend

## 目的
对数据集做时间序列分析，识别趋势、检测异常、分解季节性，并产出带标注的时间线图表，解释什么在何时发生了变化。

## 输入
- {{DATASET}}：要分析的数据源。可以是文件路径（CSV、Parquet）、数据库表引用，或 MotherDuck/DuckDB 连接串。必须至少含一个时间/日期列和一个数值指标列。
- {{TIME_COLUMN}}：含时间维度的列名（例如 `date`、`created_at`、`event_timestamp`）。必须是 date、datetime 或 timestamp 类型——或可被解析为其一的字符串。
- {{METRIC_COLUMNS}}：要随时间分析的一个或多个指标列。多个时逗号分隔（例如 `revenue, active_users, conversion_rate`）。每个都必须是数值列或可聚合字段。
- {{GRANULARITY}}：（可选）分析的时间粒度——取以下之一："daily"、"weekly"、"monthly"、"quarterly"。若未提供，agent 根据日期范围自动选择：<90 天 = 日，90-365 天 = 周，1-3 年 = 月，>3 年 = 季。
- {{SEGMENTS}}：（可选）用于切分时间序列的列（例如 `platform`、`country`、`plan_type`）。若提供，为每个分群分别计算趋势并对比。
- {{ANALYSIS_CONTEXT}}：（可选）业务上下文或一份问题/假设文档，说明团队在趋势中找什么。若提供，agent 把标注和异常评述针对业务上下文定制。

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

### 第 1 步：加载并准备时间序列数据
连接到 {{DATASET}}，为时间序列分析准备数据：

**1a. 校验时间列：**
- 读取 {{TIME_COLUMN}} 并核验它能被解析为 date/datetime
- 检查时间列的空值——标记并排除时间戳为空的行
- 检查时区一致性——若存在混合时区，归一化到单一时区并在报告中注明
- 确定日期范围：最小日期、最大日期、总跨度

**1b. 校验指标列：**
- 对 {{METRIC_COLUMNS}} 中每列，核验它是数值或可聚合（count、sum、mean）
- 检查每个指标列的空值、负值和极端异常值
- 注明任何会影响趋势解读的数据质量问题

**1c. 确定粒度：**
- 若提供了 {{GRANULARITY}}，用它
- 若没有，根据日期范围自动选择：
  - <90 天数据：日
  - 90-365 天：周（聚合到 ISO 周）
  - 1-3 年：月
  - >3 年：季
- 陈述所选粒度及理由

**1d. 聚合数据：**
写并执行 SQL 或 Python，在所选粒度上聚合 {{METRIC_COLUMNS}}：
- 计数类指标：每周期 SUM
- 比率类指标：每周期重算比率（分子 / 分母），**不要**对比率求平均
- 平均类指标：尽量算加权平均
- 若提供了 {{SEGMENTS}}，每周期每分群聚合

```python
# Example: Monthly aggregation of revenue and active_users
# Group by month (from TIME_COLUMN)
# revenue: SUM per month
# active_users: COUNT DISTINCT per month
# If segmented by platform: group by (month, platform)
```

把准备好的时间序列数据集保存到 `working/timeseries_prepared.csv`。

### 第 2 步：计算环比变化
对 {{METRIC_COLUMNS}} 中每个指标，计算：

**2a. 绝对和相对变化：**
- 环比变化（例如月度则为 MoM）：current - previous
- 百分比变化：(current - previous) / previous * 100
- 处理除以零（previous = 0），把它标为 "new" 而非无限增长

**2b. 多周期对比：**
- 若粒度为日或周：另算 Month-over-Month（MoM）
- 若粒度为月：另算 Quarter-over-Quarter（QoQ）和 Year-over-Year（YoY）
- 若粒度为季：另算 YoY
- YoY 是最重要的对比，因为它去除了季节性

**2c. 滚动平均：**
- 计算滚动平均以平滑噪声：
  - 日数据：7 天滚动平均
  - 周数据：4 周滚动平均
  - 月数据：3 月滚动平均
  - 季数据：无滚动平均（点太少）
- 滚动平均揭示日间或周间噪声下的潜在趋势

**2d. 累计指标（如适用）：**
- 若指标天然累计（例如累计注册、累计收入），在周期值旁计算累计总数
- 跨分群或跨年对比累计轨迹

### 第 3 步：识别异常
检测显著偏离预期模式的周期。

**3a. 统计异常检测（用 `control_chart`）：**
用 `helpers/analytics_helpers.py` 的 `control_chart()` 做正式的过程监控：

```python
from helpers.analytics_helpers import control_chart

result = control_chart(metric_series, sigma=3)
if not result['in_control']:
    for v in result['violations']:
        print(f"  {v['rule']}: {v['description']}")
```

控制图应用 Western Electric 规则（规则 1-4）做检测：
- Rule 1：点超出 3-sigma（STRONG ANOMALY）
- Rule 2：3 点中 2 点超出 2-sigma（POTENTIAL ANOMALY）
- Rule 3：5 点中 4 点超出 1-sigma（萌发的模式）
- Rule 4：连续 8 点位于一侧（水平偏移）

辅以简单阈值：把偏离滚动平均 >2 个标准差的周期标为 POTENTIAL，>3 个标准差标为 STRONG。

**3b. 变化率异常：**
- 标记任何环比变化超过平均绝对变化 2 倍的周期
- 即便绝对值在正常范围内，这也能抓出突然的激增或下跌

**3c. 模式断裂检测：**
- 把时间序列前半段与后半段对比
- 若两半之间均值、方差或趋势方向显著改变，标记 STRUCTURAL BREAK
- 检查水平偏移：指标是否永久移到了新基线？

**3d. 上下文标注：**
对每个检测到的异常，尝试解释它：
- 检查异常日期是否对应已知事件（节假日、产品发布、定价改动）
- 若提供了 {{ANALYSIS_CONTEXT}}，把异常与提到的业务事件交叉对照
- 若无可用解释，注明："Anomaly detected on [date] — cause unknown, recommend investigation"

### 第 4 步：分解趋势和季节性
把时间序列拆分为其组成模式。

**4a. 趋势提取：**
- 为每个指标拟合一条简单线性趋势线（最小二乘）
- 报告斜率：指标在增长、下降还是持平？
- 量化趋势："[metric] is growing at approximately [X units] per [period], or [Y%] per [period]"

**4b. 季节性模式识别（用 `detect_seasonality`）：**
用 `helpers/forecast_helpers.py` 的 `detect_seasonality()` 客观检测季节性模式：

```python
from helpers.forecast_helpers import detect_seasonality

result = detect_seasonality(series)
if result['seasonal']:
    print(f"Detected {result['strength']} seasonality with {result['dominant_period']}-period cycle")
```

- 若检测到季节性：报告主导周期、强度和季节振幅
- 若未检测到但至少存在 2 个完整周期：退回到对周期平均值的目视检查
- 若数据不足：明确陈述 "Only [N] months of data — insufficient for seasonal pattern identification"

**4c. 残差分析：**
- 移除趋势和季节成分后，检查残差
- 大残差对应异常——与第 3 步发现交叉对照
- 若残差呈递增模式，说明指标随时间波动加剧

**4d. 分群对比（若提供 {{SEGMENTS}}）：**
- 跨分群对比趋势：所有分群是否同向移动？
- 识别发散的分群："Mobile revenue is growing 15% MoM while desktop is flat"
- 检查异常影响所有分群还是仅一个（分群特定 vs 全局异常）

### 第 5 步：生成时间序列可视化
应用 Visualization Patterns skill（`.claude/skills/visualization-patterns/skill.md`）创建带标注的时间线图表。

**必需图表：**

**图 1：主趋势线**
- X 轴：时间（在所选粒度上）
- Y 轴：主指标值
- 同时展示原始值和滚动平均
- 用标记点和标签标注异常（"Spike: +45% on March 15"）
- 用垂直虚线标注结构断裂
- 含带斜率标注的趋势线

**图 2：环比变化**
- X 轴：时间
- Y 轴：百分比变化（MoM、QoQ 或 YoY——最相关的那个）
- 按正向（绿）vs 负向（红）变化给条形上色
- 在 0% 处加水平参考线
- 标注最大的正向和负向变化

**图 3：季节性模式（如适用）**
- X 轴：季节周期（星期几、一年中的月份等）
- Y 轴：该周期的平均指标值（跨所有年份/周期）
- 用误差棒或区间表示波动性
- 标注峰值和谷值

**图 4：分群对比（若提供 {{SEGMENTS}}）**
- X 轴：时间
- Y 轴：指标值
- 每个分群一条线，颜色各异
- 标注分群发散处
- 若 >4 个分群，含一个 small-multiples 版本

**对每张图：**
- 应用 Visualization Patterns skill 的主题
- 标题是洞察，而非指标名（"Revenue doubled in Q4 driven by holiday demand" 而非 "Revenue over Time"）
- 含带日期范围、粒度和样本量的副标题
- 以 PNG 文件保存到 `working/charts/`

### 第 6 步：三角校验与验证
应用 Triangulation / Sanity Check skill（`.claude/skills/triangulation/skill.md`）：

**一致性检查：**
- 核验各分群值之和等于总数（若提供了分群）
- 核验累计总数单调不减（对累计指标）
- 交叉核对：若收入和交易数都有，平均交易额（收入 / 数量）是否说得通？

**合理性检查：**
- 增长率合理吗？（>100% 的 MoM 增长罕见，值得审视）
- 季节性模式与业务类型一致吗？（例如零售应在 Q4 达峰）
- 异常幅度可信吗？（10 倍激增可能是数据问题，而非真实事件）

**数据完整性检查：**
- 检查时间序列的缺口：是否有周期完全缺失？
- 检查重复周期（同一日期出现两次）
- 核验首末周期数据完整（部分周期会扭曲指标）

记录每项检查及其结果。标记任何未通过合理性检查的发现。

### 第 7 步：编制趋势报告
按下方输出格式，把所有产出汇编成一份结构化报告。

## 输出格式

保存到 `outputs/trend_report_{{DATE}}.md` 的 markdown 文件，图表保存到 `outputs/charts/`。结构：

```markdown
# Trend Analysis Report
**Generated:** {{DATE}}
**Dataset:** {{DATASET}}
**Time range:** [start date] to [end date]
**Granularity:** [daily / weekly / monthly / quarterly]
**Metrics analyzed:** {{METRIC_COLUMNS}}
**Segments:** {{SEGMENTS}} (or "None — total population")

## Executive Summary
[3-5 sentences: the most important trend finding, the biggest anomaly, and the
 overall direction. Written as insights, not descriptions.
 "Revenue grew 34% YoY but growth has decelerated from 8% MoM in Q1 to 2% MoM
 in Q3. A sharp 25% drop in August correlates with the pricing change on Aug 12.
 Mobile revenue is growing 3x faster than desktop, now comprising 55% of total."]

## Key Findings

### Finding 1: [Trend insight headline]
**Evidence:** [specific numbers, comparisons]
**Period:** [relevant time range]
**Confidence:** [HIGH / MEDIUM / LOW]
**Chart:** ![Finding 1](charts/trend_finding_1.png)

### Finding 2: [Anomaly or pattern insight]
[same structure]

### Finding 3: [Segment or seasonal insight]
[same structure]

## Trend Summary

### [Metric 1 Name]
| Period | Value | Change | % Change | Rolling Avg |
|--------|-------|--------|----------|-------------|
| [period 1] | [value] | — | — | — |
| [period 2] | [value] | [+/-X] | [+/-Y%] | [value] |
| ... | ... | ... | ... | ... |

**Overall trend:** [growing / declining / flat] at [X units per period] ([Y% per period])
**Trend line:** [slope and R-squared]

### [Metric 2 Name]
[same structure]

## Period-over-Period Analysis

### Month-over-Month (or applicable period)
| Metric | Latest Period | Previous Period | Change | % Change | Trend Direction |
|--------|--------------|-----------------|--------|----------|----------------|
| [metric 1] | [value] | [value] | [change] | [%] | [up/down/flat] |
| [metric 2] | ... | ... | ... | ... | ... |

### Year-over-Year (if available)
[same structure]

**Chart:** ![Period-over-Period](charts/pop_change.png)

## Anomaly Report

| Date/Period | Metric | Expected | Actual | Deviation | Severity | Likely Cause |
|-------------|--------|----------|--------|-----------|----------|-------------|
| [date] | [metric] | [value] | [value] | [+/-X std dev] | STRONG / POTENTIAL | [cause or "Unknown"] |

**Chart:** ![Annotated Timeline](charts/annotated_timeline.png)

## Seasonal Patterns
[Only present if sufficient data exists for seasonal analysis]

### Annual Seasonality
| Month/Quarter | Average [Metric] | vs. Annual Avg | Characterization |
|---------------|------------------|----------------|-----------------|
| Q1 | [value] | -X% | Trough |
| Q2 | [value] | +Y% | Recovery |
| Q3 | [value] | +Z% | Building |
| Q4 | [value] | +W% | Peak |

**Pattern summary:** "[Metric] shows strong annual seasonality with Q4 peak ([W%] above average) and Q1 trough ([X%] below average)."
**Chart:** ![Seasonal](charts/seasonal_pattern.png)

### Weekly Seasonality (if daily data)
[same structure with day of week]

## Segment Trends
[Only present if {{SEGMENTS}} was provided]

### Segment Comparison: [Segment Dimension]
| Segment | Start Value | End Value | Growth | Growth Rate | Share of Total |
|---------|------------|-----------|--------|-------------|---------------|
| [seg A] | [value] | [value] | [change] | [%] | [% of total] |
| [seg B] | ... | ... | ... | ... | ... |

**Divergence:** [which segments are growing/declining relative to others]
**Chart:** ![Segment Trends](charts/segment_comparison.png)

## Decomposition Summary

| Metric | Trend Component | Seasonal Component | Residual Volatility |
|--------|----------------|-------------------|-------------------|
| [metric 1] | [+X% per period] | [±Y% amplitude] | [low / medium / high] |
| [metric 2] | ... | ... | ... |

## Validation Report
| Check | Result | Detail |
|-------|--------|--------|
| No gaps in time series | PASS / FAIL | [detail] |
| Segment totals = overall total | PASS / FAIL | [detail] |
| Cumulative values non-decreasing | PASS / FAIL | [detail] |
| Growth rates plausible | PASS / FAIL | [detail] |
| Partial periods excluded | PASS / FAIL | [detail] |

## Data Limitations
- [Limitation 1: insufficient history for seasonality, partial periods, etc.]
- [Limitation 2]

## Recommended Next Steps
1. [Investigate the top anomaly — specific agent and inputs]
2. [Deep dive on the fastest-growing or fastest-declining segment]
3. [Set up monitoring for the key trend to track going forward]
```

## 使用的 Skill
- `.claude/skills/visualization-patterns/skill.md` —— 用于第 5 步的所有图表生成，含时间序列专属约定（趋势用折线图、环比变化用条形图）、异常和结构断裂的标注规范，以及主题样式
- `.claude/skills/triangulation/skill.md` —— 用于第 6 步对所有发现的交叉对照和合理性核对，含核验分群总数对得上、增长率合理、异常幅度可信

## 验证
在呈现趋势报告前，核实：
1. **时间序列连续** —— 检查缺口。若粒度为月，范围内每个月都应在场。缺失周期必须被填补（用零或 null 并注明）或显式标记缺口。
2. **环比计算正确** —— 手算至少 3 个百分比变化：(current - previous) / previous * 100。核验它们与报告值一致。
3. **异常是真实的，而非数据假象** —— 对每个 STRONG 异常，检查该日期的底层数据是否有质量问题（例如激增可能是重复记录，下跌可能是数据缺失）。若清洗后异常消失，那是数据问题，而非发现。
4. **季节性模式未过拟合** —— 若报告声称季节性模式，核验它在至少 2 个周期上成立。仅在一年里观察到的模式是单个数据点，而非季节性趋势。
5. **分群值对得上** —— 若提供了分群，核验至少 3 个周期上各分群值之和等于总数。差异表示缺分群或重复计数。
6. **滚动平均用了正确窗口** —— 核验滚动平均窗口与所述粒度一致（日 7、周 4、月 3）。错误窗口会改变平滑并误现趋势。
7. **图表与表格相符** —— 对每张图表抽查至少一个数据点，对照对应表格。视觉表现必须与数字一致。
8. **部分周期已处理** —— 时间序列的首末周期可能数据不完整（例如月中才开始的某月）。这些周期必须从趋势计算中排除，或带注意事项标记。绝不要把部分周期的总数当作有代表性的呈现。

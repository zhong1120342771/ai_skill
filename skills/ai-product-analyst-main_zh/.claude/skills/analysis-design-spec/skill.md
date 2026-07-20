# Skill: Analysis Design Spec

## 用途
确保每次分析在编写任何查询或探索数据之前，都先有一份清晰的计划 —— 它回答什么问题、为什么决策提供依据、需要什么数据、"完成" 长什么样。

## 何时使用
在每次新分析开始时应用本 skill，先于运行 Data Explorer 或任何分析 agent。如果用户让你分析某件事，先产出一份 Analysis Design Spec。仅当用户给出的请求已经覆盖全部七个字段时才跳过（少见）。

## 操作步骤

### Analysis Design Spec

在接触数据之前，填写这份模板。每个字段都是必填。如果某个字段填不出来，问用户。

```markdown
## Analysis Design Spec

### 1. Question
What are we trying to answer?
[A specific, testable question — apply the Question Framing skill]

### 2. Decision
What will this analysis inform?
[A concrete action the team will take based on the answer]
[If the answer is "nothing specific" — this may be reporting, not analysis. Confirm with the user.]

### 3. Data Needed
| Data | Source | Available? | Notes |
|------|--------|-----------|-------|
| [metric/field] | [table/system] | Yes/No/Partial | [gaps, quality concerns] |

### 4. Dimensions
What should we segment or decompose by?
- [Dimension 1]: [why — what would different values tell us?]
- [Dimension 2]: [why]
- [Dimension 3]: [why]

### 5. Time Range & Granularity
- **Period:** [start date — end date]
- **Granularity:** [daily / weekly / monthly]
- **Comparison:** [vs. prior period / vs. same period last year / vs. benchmark]

### 6. Output Format
What deliverable does the user need?
- [ ] Quick answer (1-2 sentences + supporting number)
- [ ] Analysis report (structured findings with charts)
- [ ] Presentation deck (slides for stakeholders)
- [ ] Data table (for further analysis by the user)

### 7. Success Criteria
How will we know the analysis answered the question?
[Specific conditions — e.g., "Identify which segment drove >50% of the decline"
or "Determine whether the change is statistically meaningful at the segment level"]
```

### 如何使用这份 spec

**分析之前：**
1. 填好全部 7 个字段
2. 如果任何字段做了假设，与用户确认
3. 在字段 3 中标记任何数据缺口（如有需要，应用 Tracking Gaps skill）
4. 用字段 4 来决定调用哪些 agent、跑哪些细分

**分析过程中：**
- 每个主要步骤前对照 spec —— 你是否仍在回答既定的问题？
- 如果分析揭示了一个更有意思的问题，记下来，但先把原问题做完
- 用字段 7 来判断何时收手 —— 避免陷入分析的兔子洞

**分析之后：**
- 核对交付物是否匹配字段 6
- 核对字段 7 的成功标准是否达成
- 如果未达成，注明缺了什么、为什么

### 范围标定

不是每个请求都需要同样的深度。用问题来标定：

| Request Type | Depth | Typical Agents | Time |
|-------------|-------|----------------|------|
| **Number pull** | "What was X last month?" | Data Explorer only | Minutes |
| **Monitoring** | "How is X trending?" | Overtime/Trend | 15-30 min |
| **Exploration** | "What's happening with X?" | Descriptive Analytics | 30-60 min |
| **Deep dive** | "Why did X change?" | Full pipeline including Root Cause Investigator | 1-2 hours |

把分析深度匹配到问题上。一次取数不需要完整的调查流水线。

### 写作规则

1. **问题必须具体** —— "用户表现如何？" 不是一个问题。"重设计之后注册的用户，其 7 日留存是否变化了？" 才是。
2. **决策必须可执行** —— "我们会更了解用户" 不是决策。"我们会决定是否回滚重设计" 才是。
3. **维度必须有理由** —— 别什么都拿来细分。每个维度都应有理由："不同设备的 UX 不同，所以转化可能有差异。"
4. **成功标准必须可证伪** —— "好的分析" 不是标准。"找出对变化贡献 >50% 的细分" 才是。
5. **输出格式必须匹配受众** —— 高管要 deck，数据科学家要数据表，PM 要分析报告。

## 示例

### 示例 1：根因调查

```markdown
## Analysis Design Spec

### 1. Question
Why did support ticket volume increase 55% in June compared to the prior 6-month average?

### 2. Decision
If the root cause is a product bug, we'll prioritize a hotfix. If it's seasonal or external, we'll adjust staffing.

### 3. Data Needed
| Data | Source | Available? | Notes |
|------|--------|-----------|-------|
| Support tickets (volume, category, severity) | {schema}.support_tickets | Yes | |
| User device and app version | {schema}.events | Yes | Need to join on user_id |
| Product release dates | Engineering team | Partial | May need to ask |

### 4. Dimensions
- Category: which types of tickets spiked?
- Device/platform: is it isolated to one platform?
- App version: did a specific release cause it?
- Severity: are these critical or minor?

### 5. Time Range & Granularity
- **Period:** Jan 1 – Jul 31 (7 months for baseline + anomaly)
- **Granularity:** Daily for the anomaly month, monthly for baseline
- **Comparison:** June vs. Jan-May average

### 6. Output Format
- [x] Analysis report (structured findings with charts)
- [ ] Presentation deck

### 7. Success Criteria
Identify the specific root cause (what changed, when, affecting whom) and quantify the excess ticket volume attributable to it.
```

### 示例 2：快速取数

```markdown
## Analysis Design Spec

### 1. Question
What was the checkout conversion rate for mobile users last week?

### 2. Decision
Monitoring check — if it dropped below 2.5%, we'll investigate further.

### 3. Data Needed
| Data | Source | Available? | Notes |
|------|--------|-----------|-------|
| Checkout events by device | {schema}.events | Yes | |
| Purchase events | {schema}.orders | Yes | |

### 4. Dimensions
- None needed for the initial pull (just mobile, last week)

### 5. Time Range & Granularity
- **Period:** Last 7 days
- **Granularity:** Single number (weekly total)
- **Comparison:** vs. prior 4-week average

### 6. Output Format
- [x] Quick answer (1-2 sentences + supporting number)

### 7. Success Criteria
A single conversion rate number with context (vs. recent average). If below threshold, flag for investigation.
```

## 反模式

1. **绝不在不知道分析为何种决策服务的情况下开始分析** —— 如果填不出字段 2，你在做无目的的捞数
2. **绝不让 spec 变成阻塞** —— 对于快速取数，每个字段填一句话就往下走。spec 随分析复杂度伸缩。
3. **绝不在分析中途无视 spec** —— 如果发现了更有意思的东西，把它记为后续问题，但先把被要求的事做完
4. **绝不过度扩大范围** —— 如果用户问的是监控类问题，别设计成深度下钻。把深度匹配到请求上。
5. **绝不跳过维度** —— "我把所有东西都细分一遍" 不是计划。挑 2-4 个有理由的维度。

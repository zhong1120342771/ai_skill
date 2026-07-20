# Skill: Tracking Gap Identification

## 目的
评估分析所需的数据是否真的存在、找出缺了什么，并在发现缺口时为工程团队产出按优先级排序的埋点需求。

## 何时使用
在 Data Explorer agent 盘点完可用数据之后、当分析需要可能并不存在的数据时、或当初步查询结果暗示埋点不完整时，应用本 skill。在确定分析方案之前先运行它。

## 操作步骤

### 缺口检测流程

#### 第 1 步：定义数据需求
对每个分析问题，列出所需的每个数据点：

```markdown
| Requirement | Needed For | Granularity | Time Range |
|-------------|-----------|-------------|------------|
| [event/field] | [which analysis step] | [per user/session/event] | [last 30d, 90d, etc.] |
```

#### 第 2 步：盘点可用数据
把每项需求映射到实际存在的数据：

```markdown
| Requirement | Status | Source | Notes |
|-------------|--------|--------|-------|
| [event/field] | AVAILABLE / PARTIAL / MISSING / DERIVABLE | [table.column] | [caveats] |
```

**状态定义：**
- **AVAILABLE**：数据存在、干净，且覆盖所需时间范围
- **PARTIAL**：数据存在但有缺口 —— 缺少时间段、细分不完整或有质量问题
- **MISSING**：完全没有追踪 —— 需要新埋点
- **DERIVABLE**：没有直接数据，但可以从其他可用数据近似推导

#### 第 3 步：为缺口设计变通方案

对每个 PARTIAL 或 MISSING 项，评估变通方案：

```markdown
### Gap: [what's missing]
**Impact on analysis:** [how this gap affects what we can conclude]
**Workaround:** [how to approximate using available data]
**Confidence with workaround:** [High/Medium/Low]
**Workaround limitations:** [what the approximation gets wrong]
```

**常见变通模式：**
- 缺少事件时间戳 → 用相关事件作代理（例如用页面浏览时间代理功能使用时间）
- 缺少用户属性 → 从行为模式推导（例如从功能使用模式推断用户角色）
- 缺少细分数据 → 用可用的代理维度（例如用户自报国家缺失时改用账单国家）
- 时间覆盖不全 → 分析可用窗口，并作为注意事项标记

#### 第 4 步：写埋点需求

对需要工程投入的缺口：

```markdown
### Instrumentation Request: [Event/Property Name]

**Event name:** [snake_case_event_name]
**Trigger:** [Exactly when this event should fire]
**Properties:**
| Property | Type | Required | Description |
|----------|------|----------|-------------|
| [name] | string/int/float/bool | Y/N | [what it captures] |

**Priority:** [P0-Critical / P1-High / P2-Medium / P3-Low]
**Justification:** [Why this is needed — which analysis it unblocks]
**Estimated effort:** [Hours/days — if known]
**Depends on:** [Any prerequisite instrumentation]
```

### 输出格式：埋点缺口报告（Tracking Gap Report）

```markdown
# Tracking Gap Report: [Analysis Name]
## Date: [YYYY-MM-DD]

### Summary
| Status | Count | Items |
|--------|-------|-------|
| AVAILABLE | X | [list] |
| PARTIAL | X | [list] |
| DERIVABLE | X | [list] |
| MISSING | X | [list] |

### Analysis Feasibility
[Can we proceed? What's the confidence level with workarounds?]
- **Full analysis possible:** All critical data available or derivable
- **Partial analysis possible:** Core question answerable, but some segments/dimensions unavailable
- **Analysis blocked:** Critical data missing, no viable workaround

### Gap Details
[For each PARTIAL, DERIVABLE, and MISSING item — details, workaround, and instrumentation request]

### Prioritized Instrumentation Requests
| Priority | Event/Property | Unblocks | Effort |
|----------|---------------|----------|--------|
| P0 | [name] | [which analysis] | [estimate] |
| P1 | [name] | [which analysis] | [estimate] |

### Recommended Analysis Approach
[Given the gaps, here's how to proceed — which workarounds to use, which questions to defer]
```

## 示例

### 示例 1：结账漏斗分析

**分析目标：** 弄清用户在结账漏斗的哪一步流失，以及为什么。

```markdown
### Data Requirements vs. Availability

| Requirement | Status | Source | Notes |
|-------------|--------|--------|-------|
| Page views per checkout step | AVAILABLE | events.page_viewed | All 5 steps tracked |
| Time spent per step | PARTIAL | events.page_viewed | Can derive from timestamps between page views, but doesn't capture tab-switching |
| Payment method selected | AVAILABLE | events.payment_selected | Tracked since Jan 2025 |
| Payment error details | MISSING | — | Only know "payment_failed" event, not the error type |
| Shipping address validation | MISSING | — | No event when address validation fails |
| Cart contents at each step | PARTIAL | events.cart_updated | Cart state only at add/remove, not at each checkout step |
| User device + browser | AVAILABLE | events.properties | All events have device context |

### Gap: Payment error details
**Impact:** Can see WHERE users drop off (payment step) but not WHY (card declined vs. wrong CVV vs. timeout)
**Workaround:** Cross-reference with payment processor logs if accessible via API. Otherwise, can only report "payment failure rate" without root cause.
**Confidence with workaround:** Medium — processor logs may have different user identifiers

### Instrumentation Request: payment_error_details
**Event name:** checkout_payment_error
**Trigger:** When payment processing returns any non-success response
**Properties:**
| Property | Type | Required | Description |
|----------|------|----------|-------------|
| error_code | string | Y | Payment processor error code |
| error_category | string | Y | declined / timeout / validation / fraud |
| payment_method | string | Y | credit_card / paypal / apple_pay |
| retry_count | int | Y | Number of payment attempts in this session |

**Priority:** P1-High
**Justification:** Payment step has 23% drop-off but we can't diagnose the cause without error details. This unblocks targeted fixes.
**Estimated effort:** 4-8 hours (backend event + processor error mapping)
```

### 示例 2：可推导的变通方案

```markdown
### Gap: User role/job title
**Impact:** Can't segment feature adoption by persona (PM vs. Engineer vs. Designer)
**Workaround:** Derive role from feature usage patterns:
- Users who primarily use roadmap features → likely PM
- Users who primarily use code integration features → likely Engineer
- Users who primarily use design review features → likely Designer
**Confidence with workaround:** Low-Medium — users who use multiple feature types will be misclassified
**Workaround limitations:** Only works for active users (can't classify churned users who didn't use enough features). Accuracy estimated at ~65% based on users with known roles.
```

## 反模式

1. **永远不要在没核实的情况下假定数据存在** —— "我们应该有那个"不等于"它在 events 表里"
2. **永远不要在需要 MISSING 数据的情况下还不加标记就推进分析** —— 如果你回答不了问题，就早点说出来
3. **永远不要写没有优先级和理由的埋点需求** —— 工程团队需要知道它能解锁什么
4. **永远不要把 DERIVABLE 当成 AVAILABLE** —— 推导出的指标是近似值；始终注明置信度和局限
5. **永远不要跳过变通方案评估** —— 有时一个好的变通方案能让新埋点变得不必要，省下数周工程时间

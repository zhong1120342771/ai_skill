# Skill: Metric Spec

## 目的
用一套标准化模板把任何指标定义得清晰、完整，让"在测什么、怎么算、如何解读"不存在歧义。

## 何时使用
在定义新指标时、当某个指标被引用却没有明确定义时、或者不同的人用同一个指标名却各指不同含义时，应用本 skill。分析中用到的每个指标都应该有一份 spec。

## 操作步骤

### 指标 Spec 模板

```markdown
## Metric: [Name]

### Definition
**Plain English:** [One sentence a non-technical person can understand]
**Formula:** [Exact calculation]

### Components
| Component | Definition | Source |
|-----------|-----------|--------|
| **Numerator** | [What's being counted/summed in the top] | [Table.column] |
| **Denominator** | [What's being counted in the bottom (if ratio)] | [Table.column] |
| **Unit of analysis** | [What does one row represent?] | [e.g., per user, per session, per order] |

### Segmentation Dimensions
| Dimension | Values | Why |
|-----------|--------|-----|
| [e.g., Device type] | [mobile, desktop, tablet] | [Different UX → different conversion] |
| [e.g., Acquisition channel] | [organic, paid, referral] | [Different intent → different behavior] |
| [e.g., Geography] | [US, EU, APAC] | [Different markets → different baselines] |

### Data Source
- **Primary table:** [schema.table_name]
- **Key columns:** [list]
- **Refresh cadence:** [real-time / hourly / daily / weekly]
- **Latency:** [how delayed is the data?]
- **Reference query:** [SQL query that computes this metric — the canonical implementation]

### Thresholds
| Condition | Value | Action |
|-----------|-------|--------|
| **Healthy** | [e.g., >3.5%] | No action needed |
| **Watch** | [e.g., 2.5-3.5%] | Monitor weekly, investigate if persists >2 weeks |
| **Investigate** | [e.g., <2.5%] | Root cause analysis within 48 hours |
| **Alert** | [e.g., <1.5%] | Escalate to leadership, immediate investigation |

### Known Limitations
- [Limitation 1: e.g., "Does not include guest checkouts — only registered users"]
- [Limitation 2: e.g., "Affected by bot traffic; filter using is_bot flag"]
- [Limitation 3: e.g., "Denominator changes when new markets launch — compare like-for-like"]

### Related Metrics
- [Upstream: what drives this metric?]
- [Downstream: what does this metric drive?]
- [Alternative: other ways to measure the same concept]

### Driver Decomposition (Optional)
If this is a key business metric, decompose it into its drivers to enable faster diagnosis when the metric changes.

**Decomposition type:** [Multiplicative / Additive]

| Driver | Formula | Relationship | Data Source |
|--------|---------|-------------|-------------|
| [driver 1] | [formula] | [× / +] | [table.column] |
| [driver 2] | [formula] | [× / +] | [table.column] |
| [driver 3] | [formula] | [× / +] | [table.column] |

**Diagnostic rule:** If [parent metric] drops, check these drivers in order:
1. [driver 1] — [why this is the most likely cause / highest leverage]
2. [driver 2] — [what changes in this driver would look like]
3. [driver 3] — [least common but possible]

**Verification:** [parent metric] = [driver 1] × [driver 2] × [driver 3] (for multiplicative)
or [parent metric] = [driver 1] + [driver 2] + [driver 3] (for additive)
```

### 写作规则

1. **定义必须无歧义** —— 两个不同的分析师读了这份 spec 应该写出相同的 SQL
2. **始终指明分母** —— "转化率"如果不知道分母是什么（访客？会话？用户？）就毫无意义
3. **始终指明时间窗口** —— 按天计的 "DAU" 和按 7 天平均计的 "DAU" 是两回事
4. **始终指明排除项** —— 哪些用户/事件被过滤掉了？（测试账号、内部用户、机器人）
5. **阈值应基于历史数据** —— 而非凭感觉。要写明依据："基于 6 个月均值 3.8% ± 0.4%"

## 示例

### 示例 1：转化率

```markdown
## Metric: Checkout Conversion Rate

### Definition
**Plain English:** The percentage of users who visit the checkout page and complete a purchase.
**Formula:** (Users who completed purchase) / (Users who viewed checkout page) × 100

### Components
| Component | Definition | Source |
|-----------|-----------|--------|
| **Numerator** | Distinct users with a `purchase_completed` event within 24h of checkout view | events.event_type = 'purchase_completed' |
| **Denominator** | Distinct users with a `checkout_viewed` event | events.event_type = 'checkout_viewed' |
| **Unit of analysis** | Per user per day (deduplicated — a user counts once even with multiple checkout views) |

### Segmentation Dimensions
| Dimension | Values | Why |
|-----------|--------|-----|
| Device type | mobile, desktop, tablet | Mobile checkout has different UX friction |
| Payment method | credit card, PayPal, Apple Pay | Different failure rates by method |
| New vs returning | first purchase, repeat | Different conversion baselines |

### Data Source
- **Primary table:** analytics.events
- **Key columns:** user_id, event_type, event_timestamp, device_type, properties.payment_method
- **Refresh cadence:** Hourly
- **Latency:** ~2 hours from event to availability

### Thresholds
| Condition | Value | Action |
|-----------|-------|--------|
| **Healthy** | >3.5% | No action |
| **Watch** | 2.5-3.5% | Monitor; check if specific segment is dragging |
| **Investigate** | <2.5% | Root cause within 48h; check payment processor, page load times |
| **Alert** | <1.5% | Immediate escalation; likely a bug or outage |

### Known Limitations
- Does not include guest checkouts (only logged-in users)
- 24h attribution window means some slow purchasers are excluded
- Bot filtering depends on `is_bot` flag accuracy (~95% reliable)
```

### 示例 2：营收指标

```markdown
## Metric: Monthly Recurring Revenue (MRR)

### Definition
**Plain English:** The total monthly revenue from all active subscriptions, normalized to a monthly rate.
**Formula:** SUM(active_subscriptions × monthly_equivalent_price) as of the last day of the month

### Components
| Component | Definition | Source |
|-----------|-----------|--------|
| **Numerator** | Sum of monthly-equivalent price for all subscriptions with status='active' on the measurement date | subscriptions.price / (billing_interval_months) |
| **Denominator** | N/A (absolute metric, not a ratio) | — |
| **Unit of analysis** | Per month, measured on last calendar day |

### Segmentation Dimensions
| Dimension | Values | Why |
|-----------|--------|-----|
| Plan tier | free, starter, pro, enterprise | Different ARPU and churn dynamics |
| Billing interval | monthly, annual | Annual has lower churn but deferred revenue |
| Cohort month | signup month | Tracks retention and expansion by cohort |

### Thresholds
| Condition | Value | Action |
|-----------|-------|--------|
| **Healthy** | MoM growth >3% | On track for annual targets |
| **Watch** | MoM growth 0-3% | Dig into new vs expansion vs churn components |
| **Investigate** | MoM growth <0% | Net churn exceeding new business — root cause urgently |

### Known Limitations
- Annual subscriptions are divided by 12 for monthly equivalent; actual cash flow differs
- Does not include one-time fees, implementation fees, or overages
- Enterprise custom pricing may lag in system — verify against finance for board reporting
```

### 示例 3：活跃度指标

```markdown
## Metric: DAU/MAU Ratio (Stickiness)

### Definition
**Plain English:** The percentage of monthly users who use the product on any given day. Higher = more habitual usage.
**Formula:** (Average daily active users in the month) / (Monthly active users) × 100

### Components
| Component | Definition | Source |
|-----------|-----------|--------|
| **Numerator** | Average of daily distinct users with ≥1 meaningful action, averaged across all days in the month | AVG(daily_active_users) where action ∈ meaningful_actions |
| **Denominator** | Distinct users with ≥1 meaningful action in the entire month | COUNT(DISTINCT user_id) for the month |
| **Unit of analysis** | Per month |

### Segmentation Dimensions
| Dimension | Values | Why |
|-----------|--------|-----|
| User tenure | <30d, 30-90d, 90-365d, >365d | New users have different patterns |
| Plan tier | free, paid | Paid users should be stickier |
| Platform | web, iOS, Android | Mobile tends to be stickier |

### Thresholds
| Condition | Value | Action |
|-----------|-------|--------|
| **Healthy** | >25% | Strong daily habit (comparable to social apps) |
| **Watch** | 15-25% | Typical for B2B SaaS; look for improvement opportunities |
| **Investigate** | <15% | Weak daily habit; investigate activation and feature adoption |

### Known Limitations
- "Meaningful action" definition matters enormously — login alone should NOT count
- Weekday/weekend patterns affect daily averages; consider business-day-only variant for B2B
- Bots and automated API calls must be excluded or this metric is inflated
```

### 示例 4：带驱动因子拆解的指标

```markdown
## Metric: Revenue

### Definition
**Plain English:** Total revenue from completed orders in a period.
**Formula:** COUNT(orders) × AVG(order_value)

### Components
| Component | Definition | Source |
|-----------|-----------|--------|
| **Numerator** | Sum of total_amount for orders with status='completed' | orders.total_amount WHERE status='completed' |
| **Denominator** | N/A (absolute metric) | — |
| **Unit of analysis** | Per month |

### Driver Decomposition
**Decomposition type:** Multiplicative

Revenue = Active Users × Orders per User × Average Order Value

| Driver | Formula | Relationship | Data Source |
|--------|---------|-------------|-------------|
| Active Users | COUNT(DISTINCT user_id) with ≥1 order in period | × | orders.user_id |
| Orders per User | COUNT(orders) / COUNT(DISTINCT user_id) | × | orders |
| Average Order Value | SUM(total_amount) / COUNT(orders) | × | orders.total_amount |

**Diagnostic rule:** If Revenue drops, check these drivers in order:
1. Active Users — did fewer users place orders? (acquisition or retention problem)
2. Orders per User — did users buy less frequently? (engagement or value problem)
3. Average Order Value — did users spend less per order? (pricing, mix shift, or promo problem)

**Verification:** Revenue = Active Users × Orders per User × AOV
```

## 在指标字典中自动注册

写完一份指标 spec 后，自动把它注册到指标字典中：

1. 读取 `.knowledge/active.yaml` 获取当前活跃数据集 ID。
2. 检查 `.knowledge/datasets/{active}/metrics/index.yaml` 是否存在。若不存在则创建。
3. 从指标名称生成指标 `id`：小写、用连字符、不含空格（例如 "Checkout Conversion Rate" → `checkout-conversion-rate`）。
4. 如果该指标 ID 已存在于 `index.yaml`，则更新条目。若是新指标，则追加。
5. 按 `.knowledge/datasets/_metric_schema.yaml` 中的 schema，在 `.knowledge/datasets/{active}/metrics/{id}.yaml` 写一个 YAML 文件。把指标 spec 字段映射到 YAML 字段：
   - `definition.formula` ← spec 中的 Formula
   - `definition.unit` ← 从公式推断（%、count、currency、ratio）
   - `definition.direction` ← 从阈值推断（higher_is_better / lower_is_better）
   - `source.tables` ← Data Source 章节中的 Primary table
   - `source.sql` ← 如有提供则用 Reference query
   - `dimensions` ← Segmentation Dimensions 的列名
   - `guardrails` ← Thresholds 章节中的取值
6. 用新增/更新后的条目更新 `index.yaml`。

## 反模式

1. **永远不要在不指明分母的情况下定义指标** —— "转化率"脱离上下文毫无意义
2. **永远不要用一个对不同团队含义不同的指标名** —— 如果市场部的"转化"≠产品部的"转化"，就建两份独立的 spec
3. **永远不要在没有历史数据的情况下设阈值** —— 任意拍脑袋的阈值会导致误报或漏报
4. **永远不要跳过"已知局限"章节** —— 每个指标都有注意事项，藏起来并不会让它们消失
5. **永远不要在不理解分子与分母各自独立变化方式的情况下使用比率** —— "改善"的转化率可能意味着你流失了低意向流量，而不是产品变好了

## 常见指标的参考查询

计算标准指标时使用这些规范的 SQL 模式。把 `{schema}` 替换为当前活跃数据集的 schema（例如 `your_dataset`）。

### 转化率（基于事件）

```sql
-- Conversion rate: % of users who performed action B after action A
SELECT
    COUNT(DISTINCT CASE WHEN b.user_id IS NOT NULL THEN a.user_id END) * 1.0
    / NULLIF(COUNT(DISTINCT a.user_id), 0) AS conversion_rate
FROM {schema}.events a
LEFT JOIN {schema}.events b
    ON a.user_id = b.user_id
    AND b.event_type = '{{TARGET_EVENT}}'
    AND b.timestamp >= a.timestamp
    AND b.timestamp <= a.timestamp + INTERVAL '{{WINDOW}}'
WHERE a.event_type = '{{SOURCE_EVENT}}'
    AND a.timestamp BETWEEN '{{START_DATE}}' AND '{{END_DATE}}';
```

### 营收（基于订单）

```sql
-- Total revenue and order count for a period
SELECT
    COUNT(DISTINCT order_id) AS total_orders,
    SUM(total_amount) AS total_revenue,
    AVG(total_amount) AS avg_order_value,
    COUNT(DISTINCT user_id) AS purchasing_users
FROM {schema}.orders
WHERE status = 'completed'
    AND order_date BETWEEN '{{START_DATE}}' AND '{{END_DATE}}';
```

### 活跃用户（DAU / WAU / MAU）

```sql
-- Daily/Weekly/Monthly active users
SELECT
    DATE_TRUNC('{{GRANULARITY}}', timestamp) AS period,
    COUNT(DISTINCT user_id) AS active_users
FROM {schema}.events
WHERE event_type IN ({{QUALIFYING_EVENTS}})
    AND timestamp BETWEEN '{{START_DATE}}' AND '{{END_DATE}}'
GROUP BY 1
ORDER BY 1;
```

### 留存率（基于队列）

```sql
-- Cohort retention: % of users active in period N after signup
WITH cohorts AS (
    SELECT
        user_id,
        DATE_TRUNC('{{GRANULARITY}}', signup_date) AS cohort
    FROM {schema}.users
),
activity AS (
    SELECT DISTINCT
        user_id,
        DATE_TRUNC('{{GRANULARITY}}', timestamp) AS active_period
    FROM {schema}.events
)
SELECT
    c.cohort,
    DATE_DIFF('{{GRANULARITY}}', c.cohort, a.active_period) AS period_number,
    COUNT(DISTINCT a.user_id) * 1.0
    / NULLIF(COUNT(DISTINCT c.user_id), 0) AS retention_rate
FROM cohorts c
LEFT JOIN activity a ON c.user_id = a.user_id
GROUP BY 1, 2
ORDER BY 1, 2;
```

### NPS（净推荐值）

```sql
-- Net Promoter Score: % promoters - % detractors
SELECT
    COUNT(CASE WHEN score >= 9 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)
    - COUNT(CASE WHEN score <= 6 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0) AS nps,
    COUNT(CASE WHEN score >= 9 THEN 1 END) AS promoters,
    COUNT(CASE WHEN score BETWEEN 7 AND 8 THEN 1 END) AS passives,
    COUNT(CASE WHEN score <= 6 THEN 1 END) AS detractors,
    COUNT(*) AS total_responses
FROM {schema}.nps_responses
WHERE submitted_at BETWEEN '{{START_DATE}}' AND '{{END_DATE}}';
```

**使用说明：**
- 始终把 `{schema}` 替换为当前活跃数据集的 schema 前缀
- 把 `{{VARIABLE}}` 占位符替换为本次分析的实际取值
- 这些只是起步模式 —— 根据你具体的数据模型调整 WHERE 子句和 JOIN
- 在得出结论前，始终先用 Data Quality Check skill 校验输出

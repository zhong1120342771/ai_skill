# Skill: Triangulation / Sanity Check

## 目的
把分析发现与多个数据源、外部基准和常识交叉核对，在它们演变成糟糕决策之前抓住错误。

## 何时使用
在每次分析之后、向利益相关者呈现发现之前、以及任何结果看起来出人意料时，应用本 skill。如果某个发现会改变决策，那它在呈现前**必须**先经过三角验证。

## 操作步骤

### 三角验证框架

每个发现都要过四道透镜的检查 —— 从最常见的误导性结果来源开始：

```
CHECK 0: SEGMENT-FIRST  → Does this hold at the segment level, or is it a Simpson's Paradox?
CHECK 1: INTERNAL        → Do the numbers add up within the analysis?
CHECK 2: CROSS-REFERENCE → Does another data source agree?
CHECK 3: PLAUSIBILITY    → Does this make sense given what we know about the world?
```

### Check 0：分段优先（强制）

**在接受任何聚合发现之前，先做这项检查。** 辛普森悖论是误导性分析结论的头号来源 —— 一个在看分段时会反转的聚合趋势。

**始终要检查的默认分段**（用数据中可用的那些）：
1. 平台/设备（mobile vs. desktop vs. tablet）
2. 用户类型/套餐档位（free vs. paid、套餐级别）
3. 地理/区域（US vs. EU vs. APAC）
4. 获客渠道（organic vs. paid vs. referral）

**对每个聚合发现的处理流程：**
1. 计算该发现指标的聚合值（全部用户/记录）
2. 对至少 2 个默认分段维度的每个取值，计算同一个指标
3. 检查：有没有**任何**分段呈现出与聚合**相反**的趋势？

**如果检测到相反趋势：**
```
⚠️ SIMPSON'S PARADOX DETECTED

The aggregate [metric] shows [aggregate trend].
However, [segment value] shows the OPPOSITE: [segment trend].

The aggregate is misleading because [explanation — e.g., the growing
segment masks the declining segment].

Action: Report segment-level findings instead of aggregate. Flag this
prominently in the Executive Summary.
```

**如果未检测到相反趋势：**
记录："Segment-first check PASSED — aggregate trends are consistent with [dimensions checked] segment-level trends."

**写入校验报告：**
```markdown
| Check | Result | Detail |
|-------|--------|--------|
| Segment-first (platform) | PASS/FAIL | [specifics] |
| Segment-first (user type) | PASS/FAIL | [specifics] |
```

这项检查通常只需 2-3 个查询，却能防住最常见的分析错误。永远不要跳过它。

### Check 1：内部一致性

**算术检查：**
- 百分比加起来是 100% 吗（四舍五入容许 ±1%）？
- 各分段之和等于总量吗？
- 同比/环比变化能重新算对吗？
- 营收 = 单价 × 数量 × (1 - 折扣) 吗？

**逻辑检查：**
- 漏斗是单调递减的吗？（访客多于注册多于购买）
- 各种率都在 0% 到 100% 之间吗？
- 日期是按时间先后排列的吗？
- 分母稳定吗，还是变了？（转化"下降"可能其实是流量激增）

```python
def check_internal_consistency(findings):
    checks = []
    for finding in findings:
        # Segment sum check
        if finding.has_segments:
            segment_sum = sum(finding.segment_values)
            total = finding.total_value
            if abs(segment_sum - total) / total > 0.02:
                checks.append(("FAIL", f"Segments sum to {segment_sum}, but total is {total}"))

        # Rate bounds check
        if finding.is_rate:
            if finding.value < 0 or finding.value > 1:
                checks.append(("FAIL", f"{finding.name} = {finding.value} is outside [0,1]"))

        # Funnel monotonicity
        if finding.is_funnel:
            for i in range(1, len(finding.steps)):
                if finding.steps[i] > finding.steps[i-1]:
                    checks.append(("FAIL", f"Funnel step {i} ({finding.steps[i]}) > step {i-1} ({finding.steps[i-1]})"))
    return checks
```

### Check 2：交叉核对

**用两种不同方式算同一个东西：**
- 从 orders 表算的营收 vs. 从 payments 表算的营收
- 从 events 表算的用户数 vs. 从 users 表算的用户数
- 从漏斗查询算的转化率 vs. 从分别的分子/分母查询算的转化率

**与相关指标对照：**
- 如果转化率上升了，绝对转化数也上升了吗？（分母检查）
- 如果营收增长了，是订单数还是客单价增长了？（哪个分量？）
- 如果流失增加了，新用户注册减少了吗？（这是不是队列效应？）

**基于时间的交叉核对：**
- 日数据加起来等于周数据吗？
- 周数据加起来等于月数据吗？
- 有没有时区相关的差异？

### Check 3：外部合理性

**常见指标的数量级检查：**

| Metric | Typical Range | If Outside Range |
|--------|--------------|------------------|
| SaaS conversion (free → paid) | 2-5% | >10% suspicious; <1% possible but check |
| E-commerce conversion | 1-4% | >8% check for bot filtering issues |
| Email open rate | 15-30% | >50% check for pixel tracking issues |
| Click-through rate (email) | 2-5% | >15% suspicious |
| Monthly churn (SaaS) | 3-8% | <1% check for measurement window; >15% check definition |
| DAU/MAU ratio | 10-25% (B2B SaaS) | >40% unusual for non-social products |
| NPS | 20-50 (good SaaS) | >70 or <-10 check sample methodology |
| Mobile share of traffic | 50-70% (consumer) | <30% check if app traffic is included |
| Bounce rate | 40-60% | <20% check for double-firing analytics |
| Average session duration | 2-5 min (consumer) | >15 min check for session timeout definition |

**基准来源：**
- Mixpanel Product Benchmarks Report（年度，免费）
- Lenny Rachitsky's benchmarks（newsletter，偏 SaaS）
- First Round's State of Startups（年度调查）
- Recurly churn benchmarks（订阅类业务）
- Statista（综合行业基准）
- SimilarWeb（流量基准）

### 需要检查的常见分析错误

#### 辛普森悖论
**它是什么：** 在多个分组中出现的趋势，在合并分组后反转了。
**怎么检查：** 始终同时看聚合视图和分段视图。如果两者不一致，调查各分段的规模。
**例子：** 整体转化上升了，但在每个分段里转化都下降了。原因：转化最高的分段在流量中的占比变大了。

#### 幸存者偏差
**它是什么：** 只分析"幸存"过某个筛选过程的数据，忽略了被过滤掉的部分。
**怎么检查：** 问"这个数据集里没有什么？"检查流失用户、失败交易或已删除账号是否被排除。
**例子：** "人均营收上升了！"—— 但只是因为低消费用户流失了，留下的都是高消费者。

#### 时区问题
**它是什么：** 在不同时区计数的事件，在日界处造成人为的尖峰或低谷。
**怎么检查：** 看小时级分布。如果在 UTC 午夜有个尖峰，检查事件是不是被错误分桶了。
**例子：** "注册在午夜激增"—— 因为移动 app 按本地时间上报，但后端按 UTC 存储。

#### 数据窗口不完整
**它是什么：** 比较两个时间段时，其中一个数据不完整（例如拿整个 1 月跟半个 2 月比）。
**怎么检查：** 始终核实数据范围是否完整。检查最新事件日期。比较口径一致的时间段。
**例子：** "2 月营收暴跌 40%！"—— 但今天才 2 月 15 号，你却拿它跟整个 1 月比。

#### 分母变化
**它是什么：** 一个率发生变化，不是因为行为变了，而是被测量的人群变了。
**怎么检查：** 在解读比率之前，始终分别看分子和分母。
**例子：** "转化率翻倍了！"—— 因为一次营销活动带来了低意向流量（分母激增、分子持平），后来活动结束、分母又回落了。

#### 相关 ≠ 因果
**它是什么：** 两个指标一起变动，但一个并不导致另一个。
**怎么检查：** 找混杂因素。问"同一时间还有什么变了？"检查这个关系在不同分段里是否依然成立。
**例子：** "用了 Feature X 的用户留存高 2 倍"—— 但也许重度用户既用 Feature X 又有高留存，是因为他们本就是重度用户，而非 Feature X 导致了留存。

### 输出格式：校验报告（Validation Report）

```markdown
# Validation Report: [Analysis Name]
## Date: [YYYY-MM-DD]

### Overall Confidence: [HIGH / MEDIUM / LOW]

### Finding-by-Finding Validation

#### Finding 1: [statement]
| Check | Result | Detail |
|-------|--------|--------|
| Internal consistency | PASS/WARN/FAIL | [specifics] |
| Cross-reference | PASS/WARN/FAIL | [specifics] |
| External plausibility | PASS/WARN/FAIL | [specifics] |
| Analytical errors | PASS/WARN/FAIL | [which errors checked, any found] |
| **Confidence** | **HIGH/MEDIUM/LOW** | [summary justification] |

[Repeat for each finding]

### Caveats for Stakeholders
[What should be mentioned when presenting these findings]

### Recommended Additional Validation
[What would increase confidence — more data, different analysis, A/B test]
```

## 示例

### 示例 1：抓住一次分母变化
**发现：** "3 月移动端转化率从 2.1% 升到了 3.4%"
**交叉核对检查：** 分别看分子和分母。
- 移动端购买：1,050 → 1,020（其实略有下降）
- 移动端访客：50,000 → 30,000（显著下降 —— 一次付费推广结束了）
**结论：** WARN —— 转化率"改善"只是因为低意向付费流量消失了。实际购买数减少了。这个发现技术上成立，但具有深度误导性。

### 示例 2：抓住辛普森悖论
**发现：** "本季度整体激活率从 45% 提升到 48%"
**分段检查：**
- Enterprise：62% → 58%（下降）
- SMB：41% → 38%（下降）
- Free tier：32% → 29%（下降）
**但是：** Enterprise 在注册中的占比从 15% 增长到 35%。
**结论：** FAIL —— 每个分段都变差了。这个"提升"完全来自向高激活的 enterprise 分段的结构性迁移。实际的产品体验在退化。

### 示例 3：合理性拦截
**发现：** "邮件营销活动达到了 72% 打开率"
**外部合理性：** 行业均值是 15-30%。72% 属极端。
**调查：** Apple Mail 隐私保护会预取邮件图片，从而抬高 Apple Mail 用户的打开率。名单中 68% 用的是 Apple Mail。
**结论：** WARN —— 在剔除 Apple 隐私预取后，真实打开率大概是 25-35%。在原始数字旁一并报告调整后的数字。

## 反模式

1. **永远不要在不做三角验证的情况下呈现一个出人意料的发现** —— 如果它出人意料，那它要么是突破要么是错误。查清是哪一个。
2. **永远不要跳过分母检查** —— 来自分母变化的分析错误比其他任何原因都多
3. **永远不要只依赖单一数据源** —— 如果这个发现重要，就从另一个角度去验证它
4. **永远不要忽视外部基准** —— 如果你的指标是行业均值的 10 倍，那是危险信号，不是值得庆祝的事
5. **永远不要在没说"我们是这样核对的……"的情况下说"数据显示"** —— 三角验证正是把分析与数据复读区分开来的东西
6. **永远不要把 WARN 发现当成 PASS** —— 一条警告意味着这个发现在向利益相关者呈现时需要附上注意事项

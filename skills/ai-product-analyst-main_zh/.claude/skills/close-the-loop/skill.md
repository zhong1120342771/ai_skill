# Skill: Close-the-Loop

## 用途
确保每次包含建议的分析都以一份清晰的后续计划收尾 —— 谁来决策、用什么指标追踪成效、何时复盘、以及预期结果未出现时怎么办。

## 何时使用
在任何产出建议或行动项的分析结束时应用本 skill。如果分析以 "我们应该做 X" 收尾，本 skill 确保 X 真正被追踪和评估。仅对没有任何建议的纯探索性分析跳过。

## 操作步骤

### Close-the-Loop 清单

把这份清单附在每一份包含建议的分析报告或演示文稿末尾：

```markdown
## Close the Loop

### Decision
- **Recommendation:** [What the analysis recommends]
- **Decision maker:** [Who will approve/reject this — name or role]
- **Decision deadline:** [When this needs to be decided by]
- **Decision made:** [ ] Yes / [ ] No / [ ] Deferred
- **Decision outcome:** [What was actually decided — fill in after]

### Success Tracking
- **Success metric:** [What metric will tell us the recommendation worked?]
- **Current baseline:** [What is the metric today?]
- **Target:** [What value do we expect if the recommendation works?]
- **Measurement window:** [How long after implementation before we evaluate?]
- **Data source:** [Where to pull the metric]

### Follow-Up
- **Check-in date:** [When to evaluate whether the recommendation worked]
- **Owner:** [Who is responsible for the follow-up check]
- **If successful:** [What's the next step — scale it, document it, move to next priority]
- **If unsuccessful:** [What's the fallback — investigate further, try alternative, accept the status quo]
- **If inconclusive:** [What additional data or time is needed before deciding]

### Analysis Provenance
- **Analysis date:** [When this analysis was completed]
- **Analyst:** [Who produced it]
- **Key assumptions:** [1-3 assumptions the recommendation depends on]
- **Confidence level:** [HIGH / MEDIUM / LOW]
- **What would change the recommendation:** [Under what conditions should we revisit]
```

### 每个字段为何重要

| Field | Why It Matters |
|-------|---------------|
| **Decision maker** | 没有负责人，建议就会悬空。必须有人说是或否。 |
| **Decision deadline** | 没有截止日期，决策会被无限推迟。多数分析洞察都有保质期。 |
| **Success metric** | 没有成效指标，就无法判断建议是否奏效。 |
| **Current baseline** | 没有基线，就无法衡量改善。"转化提升了" 在没有 "从多少开始" 的情况下毫无意义。 |
| **Target** | 没有目标值，任何变化看起来都像成功。设一条线。 |
| **Measurement window** | 有些变化要数周才显现成效。明确何时复盘。 |
| **Check-in date** | 后续复盘是最常被跳过的步骤。定一个日期。 |
| **If unsuccessful** | 预先承诺好备选方案，免得事后给失败的建议找借口。 |

### 填写清单

**作为分析师你能填的：**
- 建议（来自分析）
- 成效指标、基线和目标值（来自数据）
- 衡量窗口（基于该指标的典型滞后）
- 关键假设和置信度（来自分析）
- 什么会改变这个建议（如有，来自敏感性分析）

**必须由用户填的（提示他们）：**
- 决策者
- 决策截止日期
- 后续负责人
- 复盘日期

当某些字段必须由用户填写时，明确提示他们：

> This analysis recommends [X]. To close the loop, I need to know:
> 1. Who will decide whether to proceed? (decision maker)
> 2. By when does this need to be decided? (deadline)
> 3. Who will check whether it worked? (follow-up owner)

### 与机会量化（Opportunity Sizing）衔接

如果分析用到了 Opportunity Sizer agent，把成效追踪与量化模型衔接起来：

```markdown
### Success Tracking (from Opportunity Sizing)
- **Success metric:** [same as the primary metric in the sizing model]
- **Current baseline:** [from the base case computation]
- **Target (base case):** [from the base case impact]
- **Target (pessimistic):** [from the pessimistic scenario]
- **Break-even threshold:** [from the break-even analysis — "if improvement < X%, not worth it"]
- **Measurement window:** [long enough to observe the expected impact]
```

这直接把 "值不值得？" 的问题与量化模型的假设联系起来。

## 示例

### 示例 1：Bug 修复建议

```markdown
## Close the Loop

### Decision
- **Recommendation:** Deploy hotfix v2.3.1 to resolve iOS payment processing regression
- **Decision maker:** Engineering lead (Priya)
- **Decision deadline:** End of this sprint (Feb 21)
- **Decision made:** [ ] Yes / [ ] No / [ ] Deferred
- **Decision outcome:** _[pending]_

### Success Tracking
- **Success metric:** Weekly support ticket volume (payment category, iOS)
- **Current baseline:** 89 tickets/week (anomaly period average)
- **Target:** <40 tickets/week (pre-anomaly baseline)
- **Measurement window:** 2 weeks after hotfix deploy
- **Data source:** {schema}.support_tickets, filtered to category='payment' AND device='iOS'

### Follow-Up
- **Check-in date:** 2 weeks after deploy
- **Owner:** _[to be assigned]_
- **If successful:** Document the incident, update monitoring to catch similar regressions earlier
- **If unsuccessful:** Investigate whether the root cause is actually v2.3.0 or a deeper issue; escalate to senior engineering
- **If inconclusive:** Extend measurement window to 4 weeks; check for confounding events

### Analysis Provenance
- **Analysis date:** 2026-02-14
- **Analyst:** AI Product Analyst
- **Key assumptions:** (1) The v2.3.0 release is the sole cause of the ticket spike, (2) The hotfix fully resolves the payment processing issue, (3) No other changes affect payment tickets during the measurement window
- **Confidence level:** HIGH
- **What would change the recommendation:** If the v2.3.0 → ticket spike correlation breaks down when controlling for a third variable, or if the hotfix was already deployed and tickets didn't recover
```

### 示例 2：战略建议

```markdown
## Close the Loop

### Decision
- **Recommendation:** Invest in mobile checkout optimization (projected $480K annual revenue impact)
- **Decision maker:** VP Product
- **Decision deadline:** Q2 planning (Mar 15)
- **Decision made:** [ ] Yes / [ ] No / [ ] Deferred
- **Decision outcome:** _[pending]_

### Success Tracking
- **Success metric:** Mobile checkout conversion rate
- **Current baseline:** 2.1%
- **Target (base case):** 3.4% (+62%)
- **Target (pessimistic):** 2.7% (+29%)
- **Break-even threshold:** 2.3% (+10%) — below this, the investment ROI is negative
- **Measurement window:** 8 weeks after changes ship (4 weeks ramp + 4 weeks measurement)
- **Data source:** {schema}.events (checkout_viewed → purchase_completed, device='mobile')

### Follow-Up
- **Check-in date:** 8 weeks after ship
- **Owner:** _[to be assigned]_
- **If successful:** Expand optimization to tablet; investigate next-largest conversion bottleneck
- **If unsuccessful:** Conduct user research on mobile checkout friction; consider A/B testing specific elements
- **If inconclusive:** Extend to 12 weeks; segment by device model and OS version for more signal

### Analysis Provenance
- **Analysis date:** 2026-02-14
- **Analyst:** AI Product Analyst
- **Key assumptions:** (1) Mobile conversion gap is due to UX friction, not user intent differences, (2) 30% of the gap is closeable through checkout optimization, (3) $47 AOV remains stable
- **Confidence level:** MEDIUM
- **What would change the recommendation:** If mobile users have fundamentally different purchase intent (not just friction), or if the AOV for mobile is significantly lower than desktop, the revenue projection would change
```

## 反模式

1. **绝不以一句建议结束分析** —— 没有后续追踪的建议只是会被遗忘的提议
2. **绝不跳过基线** —— "提升转化" 在没有 "从 2.1% 开始" 的情况下毫无意义
3. **绝不设目标却不设衡量窗口** —— 转化可能 2 天就改善，也可能 2 个月；明确何时复盘
4. **绝不让决策者留空** —— 如果没人对决策负责，就没人会做决策
5. **绝不跳过 "若不成功" 的计划** —— 预先承诺备选方案能防止沉没成本式自我辩护
6. **绝不把复盘日期定得太远** —— 如果衡量窗口是 2 周，复盘就应在上线后 2-3 周，而不是 6 个月后

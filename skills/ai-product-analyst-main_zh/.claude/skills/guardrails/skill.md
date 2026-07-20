# Skill: Guardrails Awareness

## 用途
确保每个成效指标都至少配有一个护栏指标，并且在把正向结论作为 "胜利" 呈现之前，先检查是否存在权衡。

## 何时使用
在两种情形下应用本 skill：
1. **定义指标时** —— 用过 Metric Spec skill 后，检查该指标是否配有护栏
2. **报告正向结论时** —— 在呈现任何改善之前，检查相关护栏指标是否劣化

## 操作步骤

### 什么是护栏？

**护栏指标**是你在优化某个成效指标时不希望它劣化的指标。护栏防止你赢了指标游戏却输了生意。

```
SUCCESS METRIC:  The metric you're trying to improve
GUARDRAIL:       The metric that must not get worse
```

**规则：** 绝不在不检查其护栏的情况下庆祝某个成效指标的改善。护栏劣化的改善是权衡，不是胜利。

### 常见护栏配对

| Success Metric | Guardrail(s) | Why |
|---------------|-------------|-----|
| Conversion rate | Average order value, Return rate | 激进的折扣抬高转化，却侵蚀利润并招致退货 |
| Signup rate | Activation rate, 7-day retention | 降低注册门槛会引入立刻流失的不合格用户 |
| Revenue per user | User satisfaction (NPS/CSAT), Support ticket volume | 变现压力会拉低体验 |
| Feature adoption | Core workflow completion, Session duration | 强推功能使用可能扰乱既有工作流 |
| Time to complete (speed) | Error rate, Quality score | 求快会降低准确性 |
| Cost reduction | Quality, Customer satisfaction | 砍成本会拉低服务 |
| Engagement (DAU, sessions) | Revenue per user, Churn rate | 互动小把戏（通知、暗黑模式）并不转化为价值 |
| Support resolution time | Customer satisfaction, Reopen rate | 关得快≠关得好，如果工单又被重开 |

### 如何应用

#### 定义指标时

用 Metric Spec skill 规定一个指标后，加一个护栏小节：

```markdown
### Guardrails
| Guardrail Metric | Acceptable Range | Check Frequency |
|-----------------|-----------------|-----------------|
| [guardrail 1] | [must stay above X / must not increase by >Y%] | [same cadence as success metric] |
| [guardrail 2] | [threshold] | [cadence] |
```

**选择护栏的规则：**
1. 每个成效指标至少配一个护栏
2. 护栏应衡量价值的另一个维度（例如成效是数量，护栏就是质量）
3. 护栏必须能用现有数据衡量
4. 如果没有明显的护栏，默认用客户满意度或工单量

#### 报告正向结论时

在呈现任何形如 "[metric] improved by X%" 的表述之前，跑一遍这个检查：

```
GUARDRAIL CHECK
□ Identified guardrail metric(s) for [success metric]
□ Computed guardrail metric(s) over the same time period
□ Compared guardrail to baseline / acceptable range
□ Result: [CLEAR / TRADE-OFF / DEGRADED]
```

**判定：**

| Verdict | Guardrail Status | How to Present |
|---------|-----------------|----------------|
| **CLEAR** | 护栏稳定或改善 | 把改善作为胜利呈现 |
| **TRADE-OFF** | 护栏轻微劣化（相对 <10%） | 同时呈现改善与权衡："Conversion improved 15%, but AOV decreased 5%. Net revenue impact is +8%." |
| **DEGRADED** | 护栏显著劣化（相对 >10%） | 不要作为胜利呈现。呈现为："Conversion improved 15%, but return rate doubled. The net impact may be negative — further investigation needed." |

### 护栏升级处理

当护栏劣化时：

1. **量化两端** —— 用相同单位（通常是金额或用户数）计算成效指标的收益与护栏的损失
2. **计算净影响** —— 收益是否大于损失？
3. **标记不确定性** —— 护栏劣化常有滞后效应（例如退货要数周才显现，流失数月后才出现）。注明这一点。
4. **建议进一步调查** —— "The conversion improvement looks positive, but the return rate increase warrants investigation before concluding this is a net win."

### 输出格式

检查护栏后，把这一小节加进分析报告：

```markdown
## Guardrail Check

| Success Metric | Change | Guardrail | Change | Verdict |
|---------------|--------|-----------|--------|---------|
| [metric] | +X% | [guardrail 1] | [no change / +Y% / -Z%] | CLEAR / TRADE-OFF / DEGRADED |
| | | [guardrail 2] | [change] | [verdict] |

**Net assessment:** [The improvement is real / The improvement comes with a trade-off / The improvement may be net negative]
```

## 示例

### 示例 1：明确的胜利

```markdown
## Guardrail Check

| Success Metric | Change | Guardrail | Change | Verdict |
|---------------|--------|-----------|--------|---------|
| Checkout conversion | +12% | Avg order value | +2% (stable) | CLEAR |
| | | Return rate | -1% (improved) | CLEAR |

**Net assessment:** The conversion improvement is a genuine win. Both guardrails are stable or improving.
```

### 示例 2：权衡

```markdown
## Guardrail Check

| Success Metric | Change | Guardrail | Change | Verdict |
|---------------|--------|-----------|--------|---------|
| Signup rate | +25% | 7-day activation | -8% | TRADE-OFF |
| | | 30-day retention | -3% (within normal range) | CLEAR |

**Net assessment:** The signup rate improvement is partially offset by lower activation. The new signups are less qualified. Recommend segmenting the new signups to identify which acquisition channel is bringing lower-quality users.
```

### 示例 3：护栏劣化

```markdown
## Guardrail Check

| Success Metric | Change | Guardrail | Change | Verdict |
|---------------|--------|-----------|--------|---------|
| Resolution time | -40% (faster) | Reopen rate | +85% | DEGRADED |
| | | CSAT score | -22% | DEGRADED |

**Net assessment:** The faster resolution time is coming at the cost of quality. Tickets are being closed prematurely and reopened, and customer satisfaction has dropped significantly. This is NOT a net improvement. Recommend reverting the process change and investigating sustainable ways to reduce resolution time.
```

## 反模式

1. **绝不在不检查护栏的情况下报告成效指标的改善** —— 转化提升 20% 伴随退货率提升 30% 不是胜利
2. **绝不定义没有至少一个护栏的指标** —— 任何指标都能被钻空子；护栏防止这一点
3. **绝不轻视护栏的小幅劣化** —— 小幅劣化会累积，且可能有滞后效应（流失数月后才出现）
4. **绝不把同一个指标既当成效又当护栏** —— 它们必须衡量价值的不同维度
5. **绝不跳过净影响计算** —— "转化升、退货升" 在不知道哪个效应更大之前无法据以行动

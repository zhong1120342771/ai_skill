# Skill: Stakeholder Communication Matrix

## 目的
把分析发现适配到受众 —— 同一个洞察，根据谁来读，采用不同的框架、详略程度和格式。确保高管拿到结论、PM 拿到影响含义、工程师拿到具体细节、数据团队拿到方法论。

## 何时使用
在产出叙事（Storytelling agent）、制作 deck（Deck Creator agent）或用户指定了受众时，应用本 skill。如果没有指定受众，默认用 **Product Team** 格式。

## 操作步骤

### 预备：加载经验（Learnings）
执行前，检查 `.knowledge/learnings/index.md` 中的相关条目：
- 读取该文件。如果不存在或为空，静默跳过。
- 扫描 **"Communication"** 和 **"General"** 标题下的条目（或相关类别，如 "Stakeholder Preferences"）。
- 如有条目，把它们作为本次执行的约束纳入（例如受众特定偏好、格式约定）。
- 如果经验不可用，绝不阻塞执行。

### 利益相关者矩阵

不同受众关心不同的东西。对同一个发现，按以下维度适配：

| Dimension | Executive | Product Team | Engineering | Data Team |
|-----------|----------|-------------|-------------|-----------|
| **Lead with** | Business impact ($, users, risk) | What to do about it (action) | What's broken and where (specifics) | How we found it (methodology) |
| **Detail level** | Bottom line + 1 supporting fact | Findings + implications + next steps | Root cause + technical details + fix scope | Methodology + data quality + caveats |
| **Format** | 3 slides max / 1-paragraph summary | Analysis report with charts | Investigation log with queries/code | Full report with validation section |
| **Metrics language** | Revenue, users, growth rate | Conversion, retention, engagement | Error rate, latency, success rate | Statistical significance, confidence intervals |
| **Time horizon** | This quarter / this year | This sprint / this month | This release / this deploy | This analysis / this dataset |
| **Charts** | 1-2 high-level (big number, trend) | 3-5 focused (funnel, segmentation) | Technical plots (timelines, error logs) | Distribution, correlation, validation |
| **Caveats** | Only if they change the recommendation | Noted alongside findings | Noted with technical implications | Full methodology section |
| **Recommendation style** | "We should X" (decisive) | "I recommend X because Y" (reasoned) | "The fix is X, effort is Y" (scoped) | "The data supports X with caveats Y" (qualified) |

### 如何适配

#### 第 1 步：识别受众

如果用户指定了受众，就用它。如果没有，询问或默认为 Product Team。

常见信号：
- "Prepare this for the leadership team" → Executive
- "What should we do about this?" → Product Team
- "Can you dig into the root cause?" → Engineering
- "How confident are we in this finding?" → Data Team

#### 第 2 步：选择开场重点（Lead）

每次沟通都从对该受众最重要的东西开始：

```
EXECUTIVE:    "This is costing us $X per month."
PRODUCT:      "Mobile checkout conversion dropped 15% — here's what to prioritize."
ENGINEERING:  "iOS app v2.3.0 has a payment processing regression in the checkout flow."
DATA:         "We isolated the root cause through 5 rounds of segment decomposition, controlling for seasonality."
```

同一个发现。不同的第一句话。

#### 第 3 步：校准详略

用金字塔原理 —— 先讲结论，再按受众需要补充细节：

```
Level 1 (Executive):     Conclusion + impact + recommendation
Level 2 (Product):       + key findings + implications + next steps
Level 3 (Engineering):   + root cause details + affected systems + fix scope
Level 4 (Data):          + methodology + validation + caveats + alternative explanations
```

每一层都包含上一层的全部内容，再加更多深度。

#### 第 4 步：适配建议（Recommendation）

| Audience | Recommendation Style | Example |
|----------|---------------------|---------|
| Executive | Decisive, resource-oriented | "Recommend allocating 2 engineers for 1 sprint to fix the iOS payment bug. Expected recovery: $64K/year." |
| Product | Reasoned, prioritized | "Recommend prioritizing the iOS payment fix over the checkout redesign. The bug affects 12% of transactions and has a clear fix, while the redesign has uncertain ROI." |
| Engineering | Specific, scoped | "The regression is in `PaymentProcessor.swift` introduced in v2.3.0 commit `abc123`. Hotfix path: revert the payment tokenization change and deploy v2.3.1." |
| Data | Qualified, methodical | "The data strongly supports a causal link between v2.3.0 and the ticket spike (r²=0.94, controlled for seasonality and mix shift). Recommend confirming with server logs before concluding." |

### 多受众文档

当一份文档要服务多个受众时（分析报告常见）：

1. **从执行摘要开始** —— 3-5 句话，结论先行
2. **给 Product 的关键发现** —— 发生了什么、为什么、该做什么
3. **给 Engineering 的技术细节** —— 根因、受影响系统、修复范围
4. **给 Data 的方法论** —— 分析怎么做的、校验、注意事项

把各章节清晰标注，让读者能跳到自己那一层。

### 输出格式

应用本 skill 时，在交付物顶部注明受众适配：

```markdown
**Audience:** [Executive / Product / Engineering / Data / Multi-audience]
**Adapted for:** [Name or role, if known]
**Detail level:** [Level 1-4]
```

## 示例

### 示例：同一发现，四种受众

**发现：** 6 月支持工单量激增 55%，原因是 app v2.3.0 的 iOS 支付 bug，导致多出 356 张工单、约 $5,340 的支持成本。

**Executive 版本：**
> Support costs increased $5,340/month due to an iOS app bug. Engineering has identified the fix. Recommend deploying the hotfix this sprint — expected to eliminate the excess ticket volume entirely.

**Product 版本：**
> iOS payment failures spiked in June after the v2.3.0 release, driving a 55% increase in support tickets. The bug affects checkout on iOS devices, causing payment processing errors that generate support contacts. Recommend prioritizing the hotfix (v2.3.1) over planned feature work this sprint. After the fix, monitor ticket volume for 2 weeks to confirm recovery.

**Engineering 版本：**
> The payment tokenization change in v2.3.0 (commit `abc123`, deployed Jun 1) introduced a regression in `PaymentProcessor.swift` that causes intermittent failures on iOS 16+ when using Apple Pay. The failure manifests as a timeout in the token exchange, which the client interprets as a generic error. 356 excess support tickets were generated between Jun 1-14. The fix is to revert the tokenization change and use the v2.2.x payment path until the token exchange timeout is resolved. Estimated effort: 2 story points.

**Data 版本：**
> We isolated the root cause through 5 rounds of iterative decomposition: total tickets → monthly anomaly (June) → category isolation (payment issues, 72% of excess) → device isolation (iOS, 89% of payment excess) → version isolation (v2.3.0, 95% of iOS excess). The finding is robust: segment-first checks showed no Simpson's Paradox, the anomaly period aligns precisely with the v2.3.0 release window (Jun 1-14), and the v2.4.0 hotfix on Jun 15 shows immediate recovery. Confidence: HIGH. Caveat: ticket categorization relies on agent tagging, which has ~8% misclassification rate for payment issues.

## 反模式

1. **永远不要给高管一份方法论先行的报告** —— 他们要的是结论，不是你怎么得出来的
2. **永远不要给工程师一份只讲业务影响的摘要** —— 他们需要具体细节才能动手
3. **永远不要跳过建议** —— 每个受众都需要知道下一步该做什么，哪怕表达方式不同
4. **永远不要假定一种格式适合所有人** —— 如果面向混合人群演示，用带标注章节的多受众结构
5. **永远不要对数据团队隐藏注意事项** —— 他们会发现的，然后对分析失去信任
6. **永远不要用注意事项淹没高管** —— 只提那些会改变建议的注意事项

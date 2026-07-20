# Skill: Question Framing

## 目的
用"问题阶梯（Question Ladder）"框架来组织分析问题，让每次分析都从清晰的决策背景、可衡量的成功标准和可检验的假设出发。

## 何时使用
在开始任何新分析时、当用户提出模糊问题（"我们做得怎么样？"）时、或当一个分析请求缺乏决策背景时，应用本 skill。永远先框定，再分析。

## 操作步骤

### 预备：加载经验（Learnings）
执行前，检查 `.knowledge/learnings/index.md` 中的相关条目：
- 读取该文件。如果不存在或为空，静默跳过。
- 扫描 **"Question Framing"** 和 **"General"** 标题下的条目（或相关类别，如 "Business Context"、"Methodology Notes"）。
- 如有条目，把它们作为本次执行的约束或上下文纳入。
- 如果经验不可用，绝不阻塞执行。

### 问题阶梯

每个分析问题都要爬完四级阶梯：

```
GOAL        → What business outcome are we trying to achieve?
DECISION    → What specific decision will this analysis inform?
METRIC      → What will we measure to inform that decision?
HYPOTHESIS  → What do we expect to find, and why?
```

**规则：** 在你能说清全部四级之前，绝不开始分析数据。如果请求方只给了你一个目标（"提升留存"），你的第一项工作就是在碰数据之前先爬完这道阶梯。

### 框定流程

**第 1 步：提取决策**
问："基于这个答案，你会做出什么不同的行动？"
- 如果答案是"什么都不做"或"我只是好奇" → 这是做报表，不是做分析。改去看仪表盘或拉个快速统计。
- 如果答案是一个具体行动 → 你有了决策。继续。

**第 2 步：定义成功标准**
问："你怎么知道这个分析回答了你的问题？"
- 答案应当具体："如果细分人群 X 的转化率下降超过 10%，我们就优先去修"
- 不要含糊："我们会更了解我们的用户"

**第 3 步：形成可检验的假设**
问："你觉得发生了什么，为什么？"
- 好："我觉得移动端转化下降，是因为结账页改版在小屏幕上出了问题"
- 差："我觉得情况很糟"

**第 4 步：识别数据需求**
问："我们需要哪些数据，我们有吗？"
- 把每个假设映射到具体的指标、细分和时间范围
- 尽早标记缺口（见 Tracking Gap Identification skill）

### 好问题 vs. 坏问题

| Bad Question | 问题所在 | Good Question |
|---|---|---|
| "How are our users doing?" | 无决策背景、不可衡量 | "Did the onboarding redesign improve Day-7 retention for new users?" |
| "Analyze our funnel" | 无假设、无范围 | "Where in the signup-to-purchase funnel are we losing the most users, and does it differ by acquisition channel?" |
| "What's our conversion rate?" | 是报表，不是分析 | "Why did conversion rate drop 15% in March, and is it affecting all segments equally?" |
| "Tell me about churn" | 太宽泛、无决策 | "Which user segments have the highest 90-day churn rate, and what behaviors predict churn in the first 30 days?" |
| "Is our product doing well?" | 不可衡量、无对照 | "How does our monthly active user growth compare to Q3, and which features are driving engagement?" |

### 影响 × 可行性优先级

当出现多个问题时，按下图排定优先级：

```
                    HIGH IMPACT
                        │
          ┌─────────────┼─────────────┐
          │   DO FIRST   │   PLAN FOR  │
          │  (Quick win)  │  (Strategic) │
HIGH      │               │              │
FEASIBILITY ──────────────┼──────────────── LOW
          │               │              │ FEASIBILITY
          │   DO IF TIME  │    SKIP     │
          │  (Nice to have)│  (Not worth) │
          └─────────────┼─────────────┘
                        │
                    LOW IMPACT
```

**影响（Impact）标准：**
- 营收/成本影响 >$100K → High
- 影响 >10% 的用户 → High
- 为本季度正在做的决策提供依据 → High
- 出于好奇、无待定决策 → Low

**可行性（Feasibility）标准：**
- 数据已有且干净 → High
- 能在 <4 小时内回答 → High
- 需要新的埋点 → Low
- 需要另一个团队的数据 → Low

### 输出格式：问题简报（Question Brief）

```markdown
# Question Brief: [Title]
## Date: [YYYY-MM-DD]

### Business Context
[2-3 sentences: what's happening, why this matters now]

### The Question Ladder
| Rung | Statement |
|------|-----------|
| **Goal** | [Business outcome] |
| **Decision** | [Specific action this informs] |
| **Metric** | [What we'll measure] |
| **Hypothesis** | [What we expect to find and why] |

### Success Criteria
[How we'll know the analysis answered the question — specific thresholds or conditions]

### Data Requirements
| Data Needed | Source | Available? | Notes |
|-------------|--------|-----------|-------|
| [metric/field] | [table/system] | Yes/No/Partial | [gaps, caveats] |

### Scope
- **Time range:** [specific dates]
- **Segments:** [which user groups, geographies, platforms]
- **Exclusions:** [what we're intentionally leaving out and why]

### Priority
- **Impact:** [High/Medium/Low — with justification]
- **Feasibility:** [High/Medium/Low — with justification]
- **Recommendation:** [Do First / Plan For / Do If Time / Skip]
```

## 示例

### 示例 1：模糊 → 框定良好
**收到的请求：** "Can you look at our signup numbers?"

**重新框定：**
| Rung | Statement |
|------|-----------|
| **Goal** | Increase new user signups by 20% in Q1 |
| **Decision** | Should we invest in fixing the mobile signup flow or increasing top-of-funnel traffic? |
| **Metric** | Signup completion rate by device type + traffic source conversion rate |
| **Hypothesis** | Mobile signup completion rate is <50% of desktop because the form doesn't render properly on small screens. Fixing mobile is higher ROI than more traffic. |

### 示例 2：好奇 → 决策驱动
**收到的请求：** "I'm curious about our power users"

**重新框定：**
| Rung | Statement |
|------|-----------|
| **Goal** | Increase the percentage of users who become power users (>10 sessions/month) |
| **Decision** | Which onboarding interventions should we prioritize to convert casual → power users? |
| **Metric** | Behaviors in first 7 days that predict power user status at Day 30 |
| **Hypothesis** | Users who complete the tutorial AND create a project in their first session are 3x more likely to become power users. The tutorial completion rate is only 23%. |

### 示例 3：宽泛 → 限定范围
**收到的请求：** "Analyze our churn"

**重新框定：**
| Rung | Statement |
|------|-----------|
| **Goal** | Reduce 90-day churn from 35% to 25% |
| **Decision** | Which segment's churn should we tackle first — low-engagement users or users who hit a specific friction point? |
| **Metric** | 90-day churn rate by: (a) engagement tier in first 30 days, (b) last feature used before churning |
| **Hypothesis** | Users who never use Feature X churn at 2x the rate of users who do. Feature X has a discoverability problem, not a value problem. |

## 反模式

1. **永远不要在框定之前就开始分析** —— 没有问题就"先拉点数据"，只会得到有趣但无用的发现
2. **永远不要接受"只是好奇"当作决策** —— 追问"你会做出什么不同的行动？"如果答案确实是什么都不做，就改去看仪表盘
3. **永远不要框定带有预设答案的问题** —— "你能证明 Feature X 有效吗？"不是问题，而是确认偏误。改为"Feature X 对 [指标] 的影响是什么？"
4. **永远不要把问题框定得太宽泛** —— "我们做得怎么样？"需要限定范围。哪个指标？哪段时间？跟什么比？
5. **永远不要跳过假设** —— 假设能防止漫无目的的"捕鱼式"探索，并给你一个具体可检验的东西

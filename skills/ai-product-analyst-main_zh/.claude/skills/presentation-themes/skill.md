# Skill: Presentation Themes

## 目的
生成专业、能讲出连贯分析故事、并遵循与可视化规范一致的主题标准的幻灯片。

## 何时使用
在创建演示、幻灯片或面向利益相关者的结构化输出时，应用本 skill。始终套用当前激活的主题。默认主题：`corporate`。

## 操作步骤

### 幻灯片结构模板

每份演示都遵循这条弧线：

```
Title → Executive Summary → Context → Insight Slides → Synthesis → Recommendations → Appendix
```

#### 幻灯片类型

**1. 标题页（Title Slide）**
```markdown
# [Takeaway headline — not "Q3 Analysis"]
## [Subtitle: scope, date range, audience]
### [Author / Team] | [Date]
```

**2. 执行摘要页（Executive Summary Slide）**
```markdown
# [Key takeaway in one sentence]

- **Finding 1:** [One sentence with key number]
- **Finding 2:** [One sentence with key number]
- **Finding 3:** [One sentence with key number]

**Recommendation:** [One clear action]
```

**3. 背景/铺垫页（Context / Setup Slide）**
```markdown
# [Why we looked at this]

- **Question:** [The business question that triggered this analysis]
- **Data:** [What data we used, time range, scope]
- **Method:** [How we analyzed it — one sentence]
```

**4. 洞察页（Insight Slide，每个发现一页）**
```markdown
# [Finding as a headline — "Mobile conversion dropped 18% in Q3"]

[ONE chart that proves this finding]

- [Supporting detail 1]
- [Supporting detail 2]

**So what:** [Why this matters for the business]
```

**5. 综合页（Synthesis Slide）**
```markdown
# [So what? — The combined story]

[How the findings connect to each other and what they mean together]

- **Pattern:** [What the findings reveal as a whole]
- **Root cause:** [If identified]
- **Magnitude:** [How big is this? Revenue impact, user impact]
```

**6. 建议页（Recommendation Slide）**
```markdown
# [Action to take — imperative verb]

| Action | Owner | Timeline | Expected Impact |
|--------|-------|----------|-----------------|
| [Action 1] | [Team] | [When] | [Quantified if possible] |
| [Action 2] | [Team] | [When] | [Quantified if possible] |

**Next step:** [The one thing to do Monday morning]
```

**7. 附录页（Appendix Slide）**
```markdown
# Appendix: [Topic]

[Supporting data, methodology details, caveats, additional charts]
[This is where you put things that support the story but would slow down the main narrative]
```

### 叙事弧线

每份 deck 都遵循：**Situation → Analysis → Finding → Implication → Recommendation**

| Arc Element | Slide Types | Purpose |
|---|---|---|
| **Situation** | Context slide | Why are we here? What question are we answering? |
| **Analysis** | (Implied — the work happened) | Don't show methodology unless asked |
| **Finding** | Insight slides (1 per finding) | What did we discover? One chart, one headline per finding. |
| **Implication** | Synthesis slide | So what? Why does this matter? |
| **Recommendation** | Recommendation slide | Now what? What should we do? |

### 内容密度规则

1. **每页最多 3 个要点** —— 如果需要更多，就拆成两页
2. **每页一张图** —— 永远不要堆图；每张图都值得有自己的标题
3. **标题是结论，不是标签** —— "Mobile conversion dropped 18%" 而非 "Conversion by Device"
4. **要点里不写完整句子** —— 用带关键数字的短语片段
5. **页数指引**：10 分钟汇报 5-8 页，30 分钟演示 10-15 页
6. **"只读标题"测试**：按顺序只读标题 —— 它们应该能讲出完整的故事

### 主题规格

#### 主题：`corporate`
- 标题字体：Arial Bold, 28pt, #1B2A4A
- 正文字体：Arial, 16pt, #333333
- 强调色：#0066CC
- 背景：白色
- 图表样式：Visualization Patterns skill 中的 `corporate`
- 页眉条：标题下方一条细 #0066CC 线

#### 主题：`minimal`
- 标题字体：Helvetica Bold, 24pt, #333333
- 正文字体：Helvetica, 14pt, #555555
- 强调色：#2563EB
- 背景：白色
- 图表样式：Visualization Patterns skill 中的 `minimal`
- 无装饰元素

#### 主题：`nyt`
- 标题字体：Georgia Bold, 26pt, #000000
- 正文字体：Arial, 14pt, #333333
- 强调色：#D03A2B
- 背景：白色
- 图表样式：Visualization Patterns skill 中的 `nyt`
- 每张图表页底部标注来源

#### 主题：`economist`
- 标题字体：Helvetica Bold, 24pt, #1F2E3C
- 正文字体：Helvetica, 14pt, #333333
- 强调色：#E3120B
- 背景：#D7E4E8
- 图表样式：Visualization Patterns skill 中的 `economist`
- 每页顶部一条红条

#### 主题：`analytics`
- 标题字体：Inter/system sans-serif Bold, 36pt, #1F2937
- 正文字体：Inter/system sans-serif, 16pt, #4B5563
- 强调色：#D97706（琥珀色）
- 背景：#F7F6F2（暖调灰白）
- 表面（Surface）：#FFFFFF（白色卡片 —— 图表自然融入）
- 图表样式：白底图表，配干净边框
- 品牌标识：每页左侧 3px 琥珀色边
- 正向指标：#059669（祖母绿），负向指标：#DC2626（红色）
- Marp CSS 主题：`themes/analytics-light.css`
- 最适合：带图表、数据表和 KPI 指标的分析类演示。为屏幕共享和打印设计。

**Analytics 主题组件：**
- `.metric-callout` —— 单个大数字，配标签和上下文
- `.kpi-row` > `.kpi-card` —— 并排的多个指标（数值、标签、变化量）
- `.finding` —— 洞察卡片，含标题、细节和影响 callout
- `.chart-container` —— 带边框的白色卡片，用于图表图片
- `.rec-row` —— 建议项，含编号、行动、理由、置信度徽章
- `.callout` —— 琥珀色 callout 框，用于关键结论
- `.so-what` —— 琥珀色高亮框，用于洞察页的 "so what"
- `.delta` —— 内联变化指示器（`.up` 绿、`.down` 红、`.flat` 灰）
- `.badge` —— 标签（`.positive`、`.negative`、`.accent`、`.neutral`）
- `.data-source` —— 幻灯片底部的来源标注行

**Analytics 布局变体：**

| Variant | Class Directive | Purpose |
|---------|----------------|---------|
| Insight (full-width) | `<!-- _class: insight -->` | Full-width chart under headline — default for first insight slide |
| Chart-left (60/40) | `<!-- _class: chart-left -->` | Chart on left, text/callout on right — good for chart + so-what pairs |
| Chart-right (40/60) | `<!-- _class: chart-right -->` | Text/callout on left, chart on right — alternates with chart-left |
| Impact | `<!-- _class: impact -->` | Centered statement slide — breathing/pacing between insight runs |

#### 主题：`analytics-dark`
- 背景：#1A1A17（暖调深色）
- 表面（Surface）：#222220
- 抬升层（Elevated）：#2A2A27
- 文字：#F5F5F0（灰白）
- 次级文字：#A8A090（柔和琥珀）
- 弱化文字：#8A8580
- 强调色：#D97706（琥珀橙）
- 浅强调色：#F0A060
- 品牌标识：每页左侧 3px 琥珀色边
- 正向：#22C55E，负向：#EF4444
- Marp CSS 主题：`themes/analytics-dark.css`
- 最适合：工作坊演示、演讲、重度屏幕共享场景、暗光环境

**Analytics-dark 幻灯片变体：**

| Variant | Class Directive | Purpose |
|---------|----------------|---------|
| Default dark | (no class needed) | Standard content slides — warm dark bg, amber accents |
| Dark title | `<!-- _class: dark-title -->` | Opening/hero slides — larger type, centered layout |
| Dark impact | `<!-- _class: dark-impact -->` | Breathing/statement slides — centered, big numbers or single takeaway |
| Two-column | `<!-- _class: two-col -->` | Side-by-side layout (inherits dark styling automatically) |
| Diagram | `<!-- _class: diagram -->` | Extra padding for visual components |
| Insight | `<!-- _class: insight -->` | Compact padding for chart + so-what callout |
| Chart-left | `<!-- _class: chart-left -->` | 60/40 split — chart on left, text/callout on right |
| Chart-right | `<!-- _class: chart-right -->` | 40/60 split — text/callout on left, chart on right |

所有组件（`.kpi-card`、`.finding`、`.rec-row`、`.box-card`、`.before-after` 等）在每种幻灯片变体上都能正确渲染，无需额外的 class 覆盖 —— CSS 在主题层处理暗色样式。

**CSS 作用域警告：** 当用新的组件样式扩展 `analytics-dark.css` 时，如果三个暗色专属变体有各自独特的背景，要确保覆盖规则覆盖到这三者：
```css
section.dark-title .component,
section.dark-impact .component { ... }
```
这能防止浅色模式的颜色在 title 和 impact 幻灯片（它们有不同的背景渐变）上泄漏出来。基础的 `section` 选择器覆盖标准暗色幻灯片。

### 自动主题选择

当没有显式传入 `{{THEME}}` 时，Deck Creator 会根据上下文自动选择主题：

| Condition | Default Theme | Rationale |
|-----------|--------------|-----------|
| `{{THEME}}` explicitly provided | Use as-is | Explicit override always wins |
| `{{CONTEXT}}` is "workshop" or "talk" | `analytics-dark` | Dark themes project better in live settings |
| `{{FORMAT}}` is "marp" (no context) | `analytics` (light) | Analyst deliverables default to light for readability |
| Otherwise | `corporate` | Gamma output default |

传入 `{{THEME}}` 可覆盖任何上下文下的自动选择。

### 演示用字号下限

这些下限确保在屏幕共享和投影时的可读性：

| Element | Minimum Size | Recommended |
|---------|-------------|-------------|
| h1 (title slides) | 48px | 52px |
| h1 (content slides) | 44px | 44px |
| h2 | 36px | 36px |
| h3 | 28px | 28px |
| Body / paragraphs | 24px | 24px |
| List items | 22px | 22px |
| Minimum readable | 16px | — |
| Footer / page numbers | 12-14px | 14px |

除页脚和页码外，任何内容都不应小于 16px。如果文字必须更小，它就该放进附录或演讲者备注。

### 二维码集成模式

在暗色幻灯片上嵌入二维码时，用白色容器包裹以保证可扫描：

```html
<div style="background:#fff; border-radius:10px; padding:6px; display:inline-block;">
  <img src="qr-code.png" style="width:140px; height:140px; display:block;">
</div>
<div style="font-size:14px; color:#8A8580; margin-top:6px;">Scan for [description]</div>
```

尺寸：辅助类二维码 120-160px，主 CTA 二维码 180-220px。

### 工作坊结尾序列模板

供工作坊/演讲 deck 使用的可选幻灯片序列。加在建议页或附录页之后：

1. **课程总览页** —— 简述完整课程，配二维码链接
2. **免费资源页** —— 邮件课程、社群、newsletter，配二维码
3. **免费工作坊页** —— 即将开始的日期和主题
4. **CTA / 优惠页** —— 优惠码、报名链接、联系方式

这个序列遵循**逐步加码的承诺模式**：先给免费资源（低门槛），再给付费产品（更高承诺）。永远不要一上来就推付费 CTA。

### 演讲者备注的互动技巧

用这些互动标记把演讲者备注做得超出标准讲稿：

- **现场投票**：`[POLL] "Drop in chat: 1, 2, or 3 — which scenario is closest to your team?"`
- **举手**：`[HANDS] "Raise your hand if you've ever waited 2+ weeks for an analysis"`
- **反思停顿**：`[PAUSE — let this sink in]`
- **故事分享**：`[ASK] "Has anyone seen something like this at their company?"`
- **过渡提示**：`[ADVANCE]` 或 `[NEXT SLIDE]`
- **聊天互动**：`[CHAT] "Type your biggest analytics pain point in the chat"`

把互动标记放在自然的断点处 —— 揭示一个关键数字之后、过渡到建议之前，或引入一个框架时。

### 导出格式

**Marp PDF（推荐用于 `analytics` 主题）：**

Marp 通过 Chromium 把 markdown 直接转成 PDF。需要自包含 PDF deck 时使用。

```markdown
---
marp: true
theme: analytics
size: 16:9
paginate: true
html: true
footer: "[Organization] | [Author] | [Date]"
---

## Slide Headline

Content here

<!--
Speaker Notes:
"Notes go in HTML comments."
-->

---

## Next Slide Headline

Content here
```

用以下命令生成 PDF：
```bash
# Light theme (analytics)
npx @marp-team/marp-cli --no-stdin --pdf --html --allow-local-files \
  --theme themes/analytics-light.css \
  outputs/deck_name.marp.md \
  -o outputs/deck_name.pdf

# Dark theme (analytics-dark)
npx @marp-team/marp-cli --no-stdin --pdf --html --allow-local-files \
  --theme themes/analytics-dark.css \
  outputs/deck_name.marp.md \
  -o outputs/deck_name.pdf
```

**Gamma 兼容的 Markdown：**
```markdown
---
theme: [theme_name]
---

# Slide Title

Content here

---

# Next Slide Title

Content here
```

**结构化 JSON（供程序化使用）：**
```json
{
  "title": "Deck Title",
  "theme": "corporate",
  "slides": [
    {
      "type": "title",
      "headline": "...",
      "subtitle": "...",
      "speaker_notes": "..."
    }
  ]
}
```

**演讲者备注格式：**
每页幻灯片都包含演讲者备注，含：
- 开场白（这页出现时该说什么）
- 2-3 个讲解要点
- 到下一页的过渡
- 预期的提问

## 示例

### 示例 1：正确的洞察页
```markdown
# Mobile conversion dropped 18% in Q3, erasing gains from the app redesign

[Bar chart: Conversion rate by device, Q2 vs Q3, mobile highlighted in red]

- Desktop conversion stable at 4.2% (±0.1%)
- Mobile fell from 3.8% to 3.1% between July and September
- Drop correlates with iOS 18 update rollout (Aug 12)

**So what:** The app redesign ROI is negative until we fix the iOS 18 compatibility issue. ~$340K/month in lost mobile conversions.
```

### 示例 2：正确的执行摘要
```markdown
# Q3 conversion dropped 12% — mobile is the culprit, and it's fixable

- **Mobile conversion fell 18%** after the iOS 18 update broke checkout flow on iPhones
- **Desktop held steady** at 4.2%, confirming the issue is mobile-specific
- **Fix is scoped** — engineering estimates 2 weeks to patch, recovering ~$340K/month

**Recommendation:** Prioritize the iOS 18 checkout fix over the planned Q4 feature work.
```

## 反模式

1. **永远不要在一页放超过一张图** —— 每个发现都值得有自己的空间
2. **永远不要用标签式标题**（"Revenue by Quarter"）—— 用结论式标题（"Revenue grew 23%"）
3. **永远不要超过 3 个要点** —— 如果需要更多，那就该再开一页
4. **永远不要在主 deck 里展示方法论** —— 把它放进附录
5. **永远不要跳过 "so what"** —— 每张洞察页都必须回答"这为什么重要？"
6. **永远不要做一份没有建议页的 deck** —— 没有行动的分析是浪费
7. **永远不要用完整句子作要点** —— 用带关键数字的短语片段
8. **永远不要按你发现的顺序呈现发现** —— 按最能讲好故事的顺序呈现

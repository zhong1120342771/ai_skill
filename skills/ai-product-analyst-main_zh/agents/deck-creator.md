<!-- CONTRACT_START
name: deck-creator
description: Create a complete slide deck from analysis outputs by combining a storytelling narrative with charts, applying a presentation theme, and generating speaker notes.
inputs:
  - name: NARRATIVE
    type: file
    source: agent:storytelling
    required: true
  - name: CHARTS
    type: file
    source: agent:chart-maker
    required: true
  - name: THEME
    type: str
    source: user
    required: false
  - name: FORMAT
    type: str
    source: user
    required: false
  - name: CONTEXT
    type: str
    source: user
    required: false
  - name: AUDIENCE
    type: str
    source: user
    required: false
  - name: STORYBOARD
    type: file
    source: agent:story-architect
    required: false
  - name: DECK_TITLE
    type: str
    source: user
    required: false
outputs:
  - path: outputs/deck_{{DATASET_NAME}}_{{DATE}}.md
    type: markdown
  - path: outputs/deck_{{DATASET_NAME}}_{{DATE}}.marp.md
    type: markdown
depends_on:
  - storytelling
knowledge_context:
  - .knowledge/datasets/{active}/manifest.yaml
pipeline_step: 16
CONTRACT_END -->

# Agent: Deck Creator

## 目的
把叙事与图表结合、应用演示主题、并为每张幻灯片生成演讲备注，从分析产出创建一套完整的幻灯片 deck。

## 输入
- {{NARRATIVE}}：Storytelling Agent 产出的叙事文档路径。必须含高管摘要、发现、洞察、含义和建议章节。
- {{CHARTS}}：分析过程中产出的图表文件（PNG/SVG）目录或列表路径。每个图表文件都应有描述性文件名。若无可用图表，agent 会生成纯文本幻灯片并标注应插入图表的位置。
- {{THEME}}：（可选）要应用的演示主题——Presentation Themes skill 里的命名主题之一（例如 "nyt"、"economist"、"minimal"、"corporate"、"analytics"、"analytics-dark"）。未指定时默认 "corporate"。
- {{FORMAT}}：（可选）输出格式——"gamma" 表示 Gamma 兼容 markdown（默认），或 "marp" 表示 Marp PDF 就绪 markdown。当选 "marp" 且主题为 "analytics" 时，deck 用 `themes/analytics-light.css`。当为 "analytics-dark" 时，deck 用 `themes/analytics-dark.css`。两者都可直接导出 PDF。
- {{CONTEXT}}：（可选）演示上下文——例如 "workshop"、"talk"、"stakeholder readout"、"team standup"。当上下文为 "workshop" 或 "talk" 时，agent 在正文后加一个带 CTA 幻灯片的可选收尾序列。
- {{AUDIENCE}}：（可选）谁会看这套 deck——例如 "executive team"、"product review"、"board meeting"、"team standup"。默认 "senior stakeholders"。控制内容密度和幻灯片数量。
- {{STORYBOARD}}：（可选）来自 Story Architect 的故事板路径（`working/storyboard_{{DATASET}}.md`）。提供时，用其听众旅程一节做幻灯片框定（听众是谁、之前 vs 之后相信什么、要推动什么决策），用节拍序列做演讲备注的过渡。
- {{DECK_TITLE}}：（可选）覆盖 deck 标题。若未提供，agent 从叙事文档的核心洞察派生标题。

## 不可妥协的默认

### 主题选择（关键）
- 标准分析 → `analytics`（浅色）。拿不准就用浅色。
- Workshop/talk → `analytics-dark`（暗色）。
- 显式 {{THEME}} 覆盖始终优先。
- 绝不为 stakeholder readout、team standup 或任何非演示上下文默认用暗色主题。

### 标题冲突预防
- 幻灯片标题 ≠ 图表烙入的标题。永远如此。
- 幻灯片标题 = 叙事框定（例如 "Payment issues drove the June spike"）。
- 图表标题 = 具体数据主张（例如 "Payment tickets jumped 147% while other categories grew <20%"）。
- 若它们雷同，把幻灯片标题重写为叙事框定。图表标题烙在 PNG 里，做 deck 时无法改。

### 建议排序
- 按置信度排序：High → Medium → Low。始终如此。
- 绝不按字母或主题排序。置信度优先让听众先对最确定的项采取行动。

## MARP 硬性要求（先读这一节）

这些规则覆盖所有其他指令。每套 Marp deck 都必须遵守。

### Frontmatter（逐字——精确复制）

```yaml
---
marp: true
theme: analytics
size: 16:9
paginate: true
html: true
footer: "AI Analyst Lab | [Client/Dataset] | [Month Year]"
---
```

对 analytics-dark，改为 `theme: analytics-dark`。全部 6 个键都是强制的。缺 `html: true` 会禁用所有 HTML 组件。缺 `size: 16:9` 会破坏布局。缺 `footer` 会移除品牌标识。

### 必需的 HTML 组件

每张 insight/content 幻灯片都必须使用主题里的 HTML 组件。deck 必须用至少 3 种不同组件类型。纯 markdown 幻灯片（只有 `##` 标题和要点）对 insight 幻灯片不可接受。

**参考文件（读这些获取片段）：**
- `templates/deck_skeleton.marp.md` —— 含正确 frontmatter 和每种幻灯片类型一个示例的完整骨架
- `templates/marp_components.md` —— 每个 HTML 组件的复制粘贴片段

### 每张幻灯片只做一件事

每张幻灯片只把一件事做好。不要把图表和它的解读放在同一张幻灯片上。改用 `chart-full` 幻灯片放视觉证据，再用 `takeaway` 幻灯片放 so-what。

当故事板为每个节拍提供 `slides` 数组时，把每个 slide 条目直接映射为带指定 class 的 Marp 幻灯片。这是主要的幻灯片构建路径。

### 合法的幻灯片 class

| Class | 用于 |
|-------|---------|
| `title` | 开场标题幻灯片 |
| `section-opener` | 章节分隔 |
| `insight` | 标准分析幻灯片（向后兼容） |
| `impact` | 留白 / 陈述幻灯片 |
| `chart-left` | 60/40 图表 + 文字 |
| `chart-right` | 40/60 文字 + 图表 |
| `two-col` | 并排内容 |
| `diagram` | 给视觉的充裕空间 |
| `chart-full` | 整张图表，最大空间（覆盖 `max-height: 420px`） |
| `kpi` | 2-4 个指标卡，无图表 |
| `takeaway` | 图表之后的解读 / so-what |
| `recommendation` | 带置信度的行动项 |
| `appendix` | 方法论、注意事项、数据源 |

**非法：** `breathing`（用 `impact`）、`hero`（用 `title`）。

### Before / After 示例

**BAD（纯 markdown——无组件、缺 frontmatter 键）：**
```markdown
---
marp: true
theme: analytics-light
paginate: true
---
## The headline: conversion fell 59%
Session-to-purchase rate declined from **7.0%** to **2.9%**.
```

**GOOD（HTML 组件、完整 frontmatter）：**
```markdown
---
marp: true
theme: analytics
size: 16:9
paginate: true
html: true
footer: "AI Analyst Lab | {{DISPLAY_NAME}} | February 2026"
---

<!-- _class: insight -->

## The headline: conversion fell 59% over 2024

<div class="kpi-row">
  <div class="kpi-card">
    <div class="kpi-value negative">-59%</div>
    <div class="kpi-label">Conversion Rate</div>
    <div class="kpi-delta down">Feb → Dec</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value">250K</div>
    <div class="kpi-label">Monthly Sessions</div>
    <div class="kpi-delta up">+28x growth</div>
  </div>
</div>

<div class="so-what">The blended rate is misleading — the denominator changed.</div>
```

---

## 工作流

### 第 1 步：摄入叙事和图表，选择主题
读取 {{NARRATIVE}} 的完整内容。提取：
- 标题 / 核心洞察标题
- 高管摘要（逐字——它成为高管摘要幻灯片）
- 每个发现（标题、支撑数据、图表引用）
- 洞察段落
- 含义段落
- 每条建议（行动、理由、置信度）
- 支撑数据引用和注意事项

盘点 {{CHARTS}} 里的图表文件：
- 列出每个文件及其名称和格式（PNG、SVG）
- 把每张图表与引用它的发现匹配（用文件名或叙事里的图表引用）
- 图表以 (10, 6) figsize / 150 DPI（约 1500x900px）渲染并直接用在幻灯片上。CSS `object-fit: contain` 处理容纳——不需单独的幻灯片变体。
- 标记任何引用了 {{CHARTS}} 中不存在图表的发现
- 标记 {{CHARTS}} 中任何不被任何发现引用的图表（appendix 候选）

**主题选择逻辑：**
1. 若显式提供了 {{THEME}}，用它（显式覆盖始终优先）
2. 若未提供 {{THEME}}：
   - 若 {{CONTEXT}} 为 "workshop" 或 "talk" → 默认 `analytics-dark`
   - 若 {{FORMAT}} 为 "marp" → 默认 `analytics`（浅色主题）
   - 否则 → 默认 `corporate`（Gamma 输出）

**暗色模式幻灯片 class 映射**（当 {{THEME}} 为 `analytics-dark` 时）：

| 幻灯片类型 | 浅色 Class | 暗色 Class |
|-----------|------------|------------|
| 标题 | `title` | `dark-title` |
| 内容 | （默认） | （默认——继承暗色） |
| Impact/留白 | `impact` | `dark-impact` |
| 双栏 | `two-col` | `two-col` |
| 图示 | `diagram` | `diagram` |
| Insight | `insight` | `insight` |
| Chart-left | `chart-left` | `chart-left` |
| Chart-right | `chart-right` | `chart-right` |
| 章节分隔 | `section-opener` | `section-opener` |

**暗色模式组件用法**（当 {{THEME}} 为 `analytics-dark` 时）：
- 所有组件（`.kpi-card`、`.finding`、`.rec-row`、`.box-card`、`.before-after` 等）自动用暗色样式——CSS 处理它
- 表格自动以暗色表头和斑马纹渲染
- 图表应在白底上渲染（它们作为 `<img>` 嵌入暗色幻灯片）
- 嵌入二维码时用 Presentation Themes skill 里的二维码白容器模式

### 第 2 步：应用 Presentation Themes skill
读 `.claude/skills/presentation-themes/skill.md`。加载 {{THEME}} 指定的主题。提取：
- 配色（主色、辅助色、强调色、背景、文字）
- 字体规格（标题字体、正文字体、字号）
- 幻灯片布局规则（边距、图表放置、文字密度上限）
- 所选受众类型的内容密度规则
- 幻灯片结构模板（哪些章节放在哪种幻灯片类型上）

若主题指定了每张幻灯片最大文字量（例如 "insight 幻灯片不超过 40 词"），在后续所有步骤强制执行这些上限。

### 第 3 步：规划幻灯片结构
按此强制结构创建幻灯片大纲：

1. **标题幻灯片**（1 张）
   - deck 标题（来自 {{DECK_TITLE}} 或从叙事派生）
   - 副标题：数据集、日期范围、分析类型
   - 若有，作者/团队署名

2. **高管摘要幻灯片**（1 张）
   - 叙事里的高管摘要，格式化为 3-5 个要点
   - 每个要点最多一句
   - 此幻灯片无图表——纯文本

3. **背景幻灯片**（1 张）
   - 正在回答的业务问题
   - 分析了什么数据（数据集、时间段、范围）
   - 采取了什么方法（1-2 句）

4. **Insight 幻灯片**（每个发现 1 张，通常 3-5 张）
   - 每个发现有自己的幻灯片
   - 幻灯片标题是陈述为要点的发现（而非主题标签）
     - 好："Mobile conversion dropped 23% after the Q3 redesign"
     - 差："Mobile Conversion Analysis"
   - 正文里的支撑数据点（1-2 句）
   - 按主题布局规则放置图表
   - 若此发现无图表，用关键指标标注（大号数字、居中）

4b. **留白 / 陈述幻灯片**（2-3 张，自动插入）
   - **插入规则：** 连续的图表/insight 幻灯片绝不超过 4 张而无节奏间隔。在叙事过渡点插入留白幻灯片。
   - **放置启发：**
     1. Context→Tension 过渡后（例如 "Wait — this isn't organic growth"）
     2. Tension 中点、隔离出主要维度后（例如 "Everything else was normal. This was surgical."）
     3. Resolution 之前（例如 "Now we can quantify the damage"）
   - 用 `impact` class（浅色主题）或 `dark-impact` class（暗色主题）
   - 标题是挑动性的重述或听众的隐含问题——而非发现标题
   - 语气指引：用精确、克制的语言。戏剧性由数据承载——文字不应与之争抢。
     - 禁用词/短语：surgical、devastating、exploded、ticking time bomb、smoking gun、alarm/fire 隐喻、unprecedented（除非字面属实）
     - 偏好：短陈述句（"One device. One category. One version."）、反问（"What did this cost?"）、以精确数字制造戏剧性（"202 lost orders. $16,600 in revenue."）
     - 原则：疑问胜过断言，精确胜过煽情
   - 这些幻灯片不含数据、不含图表、不含证据——它们只是节奏装置
   - 可选正文：最多一句，用辅助色
   - 若 deck 少于 5 张 insight 幻灯片，插入 1-2 张留白幻灯片。若 5+，插入 2-3 张。

5. **综合幻灯片**（1 张）
   - 叙事里的核心洞察——发现合起来意味着什么
   - 这是 "那又怎样？" 幻灯片
   - 一个标题、一段话（最多 3-4 句）
   - **置信度徽章**：若 Validation agent 产出了置信度评分，用 `.kpi-card` 组件展示：`<div class="kpi-card"><div class="kpi-value">{grade}</div><div class="kpi-label">Analysis Confidence ({score}/100)</div></div>`。放在右上角或综合文字旁。
   - 可选：把发现串起来的简单视觉（例如汇总表或前后对比）
   - 综合标题应不用隐喻地陈述发现之间的关系。好："The iOS bug was acute and fixed — the structural quality erosion is ongoing." 差："The iOS bug was the alarm — the structural quality erosion is the fire."

6. **建议幻灯片**（1 张）
   - 每条建议作为编号行动项
   - 含每条的置信度
   - 格式："Action — Rationale (Confidence: High/Medium/Low)"

7. **附录幻灯片**（0-N 张，按需）
   - 支撑发现但对正文太细的详细数据表
   - 产出了但未在主流程中展示的图表
   - 方法论说明
   - 数据质量注意事项
   - 每张附录幻灯片有清晰标题表明其内容

8. **收尾序列**（0-4 张，仅当 {{CONTEXT}} 为 "workshop" 或 "talk" 时）
   - 带二维码的课程概览幻灯片（如适用）
   - 免费资源幻灯片（带二维码的邮件课程、社区、newsletter）
   - 免费 workshop 幻灯片（即将到来的日期）
   - CTA / 折扣幻灯片（折扣码、链接、联系方式）
   - 这些幻灯片在附录**之后**，遵循递进式承诺模式（免费在前，付费在后）
   - 用 `analytics-dark` 主题时，最后的 CTA 幻灯片用 `dark-impact` class

计算总幻灯片数。若 deck 超过 22 张（建议精简）或少于 8 张（建议判断是否有发现需展开），标记。

### 第 3b 步：应用嗓音与语气
所有幻灯片文字（标题、正文、标注）遵循克制、精确的嗓音：
- 标题陈述发现，而非反应
- 正文提供证据，而非评论
- 留白幻灯片用简短、直接的语言——无带主观色彩的隐喻
- 建议具体且可执行，而非戏剧化
完整原则和禁用词列表见 Story Architect 嗓音指南。

### 第 4 步：写每张幻灯片
对大纲里每张幻灯片，产出：

**标题**：传达要点的、要点格式的标题。仅看标题就应能讲出故事——只读标题的读者应能理解完整论点。

**正文内容**：支撑文字，按主题规则格式化。遵守该幻灯片类型的最大字数。列表用要点。insight/综合幻灯片用单段。

**图表放置**：若某图表属于此幻灯片，指定：
- 用哪个图表文件（来自 {{CHARTS}}）
- 放置位置（按主题：左半、右半、整宽、下半）
- 尺寸指引（按主题规格）
- 图表的 alt 文本（无障碍）

**强制：始终把图表嵌入 `<div class="chart-container">` 内。**
绝不对图表图像用裸 markdown 图片语法（`![](...)`）。裸 markdown 图片绕过 CSS 容纳规则，会溢出幻灯片边界。

| 嵌入方式 | 状态 |
|-----------|--------|
| `<div class="chart-container"><img src="charts/foo.png" alt="..." width="100%"></div>` | **正确** |
| `![Chart](charts/foo.png)` | **错误** —— 无容纳，会溢出 |
| `<img src="charts/foo.png" width="100%">` | **错误** —— 缺 `.chart-container` 包裹 |

**幻灯片 class 到布局的映射：**

| 幻灯片 Class | 布局 | 备注 |
|-------------|--------|-------|
| `chart-full` | 整张图表，最大空间 | 覆盖全局 `max-height: 420px`——图表占满幻灯片 |
| `insight`、`diagram` | 整宽内容 | 图表放在 `.chart-container` 内，标准容纳 |
| `chart-left`、`chart-right` | 60/40 分栏 | 图表旁配简短标注 |

对带图表图像的幻灯片：图表烙入的副标题提供描述性上下文（它测什么、时间段、过滤）。**不要**另加 `<div class="data-source">`——那会冗余。只对展示数据的非图表幻灯片（KPI 卡、表格、纯文本数据引用）用 `<div class="data-source">`。非图表幻灯片示例：
```html
<div class="data-source">{{DISPLAY_NAME}}, {{DATE_RANGE}}</div>
```

**视觉标注**：对无图表的幻灯片，指定视觉元素：
- 关键指标标注（大号数字展示）
- 简单表格
- 前后对比
- 图标或概念插图描述

当故事板指定 `visual_format: big_number` 时，用 `.kpi-row` + `.kpi-card` 渲染为原生 HTML，而非嵌入图表 PNG。示例：
```html
<div class="kpi-row">
  <div class="kpi-card">
    <div class="kpi-value accent">202</div>
    <div class="kpi-label">lost orders</div>
    <div class="kpi-delta down">in June</div>
  </div>
  ...
</div>
```

**布局分配**（对带图表的 insight 幻灯片）：
- 第一张 insight 幻灯片用 `insight`（整宽图表）——建立视觉基线
- 后续 insight 幻灯片：当发现有与图表天然并排的 `.so-what`、`.finding` 或 `.metric-callout` 时，用 `chart-left` 或 `chart-right`
- 在 `chart-left` 和 `chart-right` 间交替以制造视觉节奏
- 当图表需要最大宽度（堆叠条、密集时间线、宽表）时保持 `insight`（整宽）
- 连续超过 3 张 insight 幻灯片不要用同一个布局 class

**幻灯片标题 vs 图表标题：** 幻灯片标题和图表标题用途互补——幻灯片标题是叙事节拍（"This is not volume growth"），而图表标题是具体数据主张（"Tickets per 100 orders rose from 14 to 65"）。两者都应在场；它们不冗余。

**内容密度规则（强制）：**
每张幻灯片最多 **2 个主要视觉组件**。组件计数：
- KPI-row = 1 个组件
- chart-container = 1 个组件
- rec-row 组 = 1 个组件
- so-what / callout = 免费（不计）
- data-source = 免费（不计）

若某节拍需要 KPI-row + chart + so-what + callout，拆到 2 张幻灯片（KPI-row 放一张，chart 放下一张）或把 callout 移到演讲备注。绝不微缩组件来塞下——那违背了幻灯片可读性的初衷。

### 第 5 步：为每张幻灯片写演讲备注
对每张幻灯片，写包含以下内容的演讲备注：

1. **开场白**：此幻灯片出现时演讲者说什么（把听众从上一张过渡过来）
2. **要点**：在此幻灯片上要说的 2-4 个要点。它们应在幻灯片内容上展开，而非逐字重复。
3. **图表讲解**：若幻灯片有图表，描述如何带听众走读它（"先看整体趋势，再指出 Q3 下沉，再高亮移动端分群"）
4. **互动标记**：deck 每个章节至少含一个：
   - `[POLL]` —— 通过聊天的听众投票（"在聊天里发 1、2 或 3"）
   - `[HANDS]` —— 举手（"觉得……的请举手"）
   - `[PAUSE]` —— 关键揭示后的反思停顿
   - `[ASK]` —— 邀请听众分享经历（"有人在自己公司见过这个吗？"）
   - `[CHAT]` —— 引导聊天互动（"打出你最大的痛点"）
5. **过渡句**：如何转到下一张（"这把我们带到了该怎么办的问题……"）。含 `[ADVANCE]` 提示。
6. **预想问题**：此幻灯片 1-2 个可能的听众问题及建议回应

演讲备注用第一人称写（"这里我们能看到……" 而非 "演讲者应注意……"）。

### 第 6 步：组装 deck 文档

**若 {{FORMAT}} 为 "marp"（或主题为 "analytics" 或 "analytics-dark"）：**

用带 HTML 组件的 Marp 兼容 markdown 写 deck。以 YAML frontmatter 开头：

```yaml
# For analytics (light) theme:
---
marp: true
theme: analytics
size: 16:9
paginate: true
html: true
footer: "AI Analyst Lab | [Client/Dataset] | [Month Year]"
---

# For analytics-dark theme:
---
marp: true
theme: analytics-dark
size: 16:9
paginate: true
html: true
footer: "AI Analyst Lab | [Client/Dataset] | [Month Year]"
---
```

每张幻灯片用 `---` 分隔。用 CSS 组件 class（两个主题共用相同 class 名）：
- `.metric-callout` 用于大数字，`.kpi-row` 用于多个指标
- `.finding` 用于 insight 卡，`.finding-impact` 用于 "so what"
- `.chart-container` 用于图表图像放置
- `.rec-row` 用于带置信度徽章的建议
- `.so-what` 用于 insight 幻灯片上的琥珀色高亮标注
- `.before-after` > `.panel.before` / `.panel.after` 用于对比
- `.data-source` 用于数据幻灯片底部的署名
- `.delta.up` / `.delta.down` 用于内联指标变化

用 `analytics-dark` 主题时：
- 标题幻灯片用 `<!-- _class: dark-title -->`（而非 `title`）
- impact/留白幻灯片用 `<!-- _class: dark-impact -->`（而非 `impact`）
- 标准内容幻灯片不需 class 指令——它们继承暗色样式
- 所有组件 class 工作方式相同——CSS 处理暗色

演讲备注放在 HTML 注释里：
```html
<!--
Speaker Notes:
"Opening line. Talking points. [PAUSE] Transition. [ADVANCE]"
-->
```

保存为 `outputs/deck_{{DATASET_NAME}}_{{DATE}}.marp.md`

要生成 PDF，运行：
```bash
# Light theme
npx @marp-team/marp-cli --no-stdin --pdf --html --allow-local-files \
  --theme themes/analytics-light.css \
  outputs/deck_{{DATASET_NAME}}_{{DATE}}.marp.md \
  -o outputs/deck_{{DATASET_NAME}}_{{DATE}}.pdf

# Dark theme
npx @marp-team/marp-cli --no-stdin --pdf --html --allow-local-files \
  --theme themes/analytics-dark.css \
  outputs/deck_{{DATASET_NAME}}_{{DATE}}.marp.md \
  -o outputs/deck_{{DATASET_NAME}}_{{DATE}}.pdf
```

**若 {{FORMAT}} 为 "gamma"（默认）：**

用 Gamma 兼容 markdown 格式写完整 deck。每张幻灯片用水平分隔线（`---`）分隔。每张幻灯片的结构：

```
## [Slide Headline]

[Body content]

![Chart alt text](path/to/chart.png)

> **Speaker Notes:**
> [Opening line]
> - [Talking point 1]
> - [Talking point 2]
> [Transition line]
> Likely questions: [Q1], [Q2]
```

应用主题的格式指令：
- 标题 vs 正文用主题的标题层级
- 应用主题的强调模式（关键数字加粗等）
- 在元数据头里注明主题配色（供 Gamma 等支持主题配置的工具用）

### 第 7 步：应用 Visualization Patterns skill 保证图表一致
读 `.claude/skills/visualization-patterns/skill.md`。核验：
- deck 中引用的所有图表都遵循可视化标准
- 图表标题是描述性的（不是 "Chart 1" 这类通用名）
- 坐标轴标签齐备且可读
- deck 中所有图表的颜色使用一致
- 主题要求处用了标注

若任何图表不达标，把问题作为 "Chart improvement recommendations" 记在附录里，而非修改图表文件（修改图表是 Chart Maker Agent 的职责）。

把最终 deck 保存到 `outputs/`。

## 输出格式

**文件：** `outputs/deck_{{DATASET_NAME}}_{{DATE}}.md`

其中 `{{DATASET_NAME}}` 派生自叙事，`{{DATE}}` 为 YYYY-MM-DD 格式的当前日期。

**结构：**

```markdown
# [Deck Title]

**Theme:** {{THEME}}
**Date:** {{DATE}}
**Source analysis:** [Path to {{NARRATIVE}}]
**Slide count:** [N]

---

## [Title Slide Headline]

[Subtitle: dataset, date range]
[Attribution]

> **Speaker Notes:**
> [Welcome, framing, set expectations]

---

## Executive Summary

- [Bullet 1 — question]
- [Bullet 2 — top finding]
- [Bullet 3 — core insight]
- [Bullet 4 — recommendation]

> **Speaker Notes:**
> [Overview of what we'll cover]

---

## [Context Slide Headline]

[Business question. Data analyzed. Approach.]

> **Speaker Notes:**
> [Background context, why this matters]

---

## [Finding 1 Headline — stated as takeaway]

[Supporting data]

![Alt text](path/to/chart1.png)

> **Speaker Notes:**
> [Opening. Talking points. Chart narration. Transition.]

---

[... additional finding slides ...]

---

## [Synthesis Headline — the "so what?"]

[Core insight paragraph]

> **Speaker Notes:**
> [Connect the dots across findings]

---

## Recommended Actions

1. **[Action 1]** — [Rationale] (Confidence: [Level])
2. **[Action 2]** — [Rationale] (Confidence: [Level])
3. **[Action 3]** — [Rationale] (Confidence: [Level])

> **Speaker Notes:**
> [Walk through each recommendation. Anticipated pushback.]

---

## Appendix

### [Appendix Item 1 Title]
[Content — data table, methodology, caveats]

### [Appendix Item 2 Title]
[Content]
```

## 使用的 Skill
- `.claude/skills/presentation-themes/skill.md` —— 用于主题选择、幻灯片布局规则、配色、字体规格和内容密度指引
- `.claude/skills/visualization-patterns/skill.md` —— 用于在 deck 上下文中核验图表质量、一致性和无障碍

## 验证
1. **幻灯片结构完整**：核验 deck 含所有强制幻灯片类型：标题、高管摘要、背景、至少一张 insight、综合、建议。若有缺失，补上。
2. **标题叙事测试**：只按序读幻灯片标题。它们本身应讲出一个连贯故事："We asked X. We found Y. This means Z. We should do W."。若标题序列不流畅，修订标题。
2b. **水平逻辑测试**：只按序读幻灯片标题。每个都必须陈述一个发现或行动（而非标签）。差："Recommended Actions"。好："Three actions to stop ticket rate erosion"。
3. **图表与发现对齐**：幻灯片中引用的每张图表都必须存在于 {{CHARTS}}。每个有对应图表的发现都必须含它。与第 1 步的图表盘点交叉对照。
4. **演讲备注覆盖**：每张幻灯片都必须有演讲备注。任何幻灯片都不应有空白或占位备注。核验每条备注有开场白、至少 2 个要点和一个过渡。
5. **主题合规**：核验每张幻灯片文字密度不超过该幻灯片类型的主题最大字数。核验标题格式符合主题规格（要点标题，而非主题标签）。
6. **幻灯片数量合理**：核验总幻灯片数在 8 到 22 之间。若超出此范围，记录原因（例如 "只有 2 个发现，所以 7 张合适" 或 "发现众多需 24 张——考虑精简"）。
7. **无孤立图表**：核验 {{CHARTS}} 中没有图表既不被主幻灯片引用、又不在附录里。每张图表都应出现在 deck 某处。
8. **标题冲突检查**：对每张带图表的幻灯片，核验幻灯片标题不与图表烙入的标题雷同。图表标题是具体数据主张；幻灯片标题必须是叙事框定。若雷同，重写幻灯片标题以提供叙事上下文（此阶段图表 PNG 无法改）。打印一张对照表以供核验：

   | Slide # | Slide Headline | Chart Title | Match? |
   |---------|---------------|-------------|--------|
   | ... | "..." | "..." | OK / COLLISION |

# Skill: Visualization Patterns

## 目的
确保 Claude Code 产出的每张图表都遵循高质量设计标准：命名主题、一致的样式和清晰的数据表达。

## 何时使用
在生成图表、图形或数据可视化时，应用本 skill。除非用户另有指定，始终套用当前激活的主题。默认主题：`minimal`。

## 操作步骤

### 预备：加载经验（Learnings）
执行前，检查 `.knowledge/learnings/index.md` 中的相关条目：
- 读取该文件。如果不存在或为空，静默跳过。
- 扫描 **"Chart Style"** 和 **"General"** 标题下的条目（或相关类别，如 "Visualization Insights"）。
- 如有条目，把它们作为本次执行的约束纳入（例如偏好的图表类型、颜色覆盖、标注偏好）。
- 如果经验不可用，绝不阻塞执行。

### 核心原则：用数据讲故事（SWD）

每张图表都遵循 Cole Nussbaumer Knaflic 的 SWD 方法论：

> **先把一切都置灰。颜色只留给那个讲出故事的数据点。**

- 每张图最多 **2 种颜色 + 灰色**。Action Amber（`#D97706`）用于主焦点，Accent Red（`#DC2626`）用于次要 callout。其余一切都是灰色。
- **标题陈述结论**，而非描述。"iOS drove the June ticket spike" 而非 "Tickets by Platform."
- 每个视觉元素都必须配得上它的位置 —— 如果它无助于读者理解故事，就删掉。
- 单个数字优先用文字而非图表。横向条形图优先于饼图。直接标注优先于图例。

**实现：** 生成任何图表前，始终先套用 SWD 样式：
```python
from helpers.chart_helpers import swd_style, highlight_bar, highlight_line, action_title, save_chart

colors = swd_style()  # Loads .mplstyle + returns color palette
```

条形图用 `highlight_bar()`（高亮一根条，其余置灰），折线图用 `highlight_line()`（高亮一条序列，其余置灰），所有图表标题用 `action_title()`。

### 去杂乱清单（Declutter Checklist）

在最终确定**任何**图表之前，逐项核对：

- [ ] 图表边框/外框 —— 整个去掉
- [ ] 顶部和右侧坐标轴线（spines）—— 去掉（只保留底部和左侧）
- [ ] 粗重的网格线 —— 去掉或改成很浅的灰（`#E5E7EB`），仅 y 轴
- [ ] 数据点标记 —— 折线图去掉（线本身*就是*数据）
- [ ] 图例 —— 换成数据上的直接标注
- [ ] 旋转的坐标轴文字 —— 如果标签需要旋转，改用横向条形图
- [ ] 多余的零 —— 用 `$45` 而非 `$45.00`；用 `12%` 而非 `12.0%`
- [ ] 3D 效果 —— 永远不要
- [ ] 背景色 —— 始终用暖调灰白（`#F7F6F2`）
- [ ] 冗余的坐标轴标签 —— 如果标题写了 "Revenue ($M)"，y 轴就不需要 "Revenue in Millions of Dollars"
- [ ] 过多的刻度 —— 减到最多 4-6 个刻度
- [ ] 小数精度 —— 让精度匹配决策（`12%` 而非 `12.347%`）

### 图表排序（多图分析）

为深入分析或根因调查产出多张图时，遵循 **Context → Tension → Resolution**：

| Phase | Charts | Purpose | Example |
|-------|--------|---------|---------|
| **Context** | 1-2 | Set the baseline. What does normal look like? | "[Dataset] processes ~4,000 support tickets per month" |
| **Tension** | 2-3 | Reveal the problem. Progressively zoom in. | "June spiked to 6,200" → "The spike was iOS payment issues" |
| **Resolution** | 1-2 | Explain why and recommend action. | "iOS v2.3 introduced a bug → fix eliminates ~2,200 tickets/mo" |

- 每张图都在前一张的基础上递进
- 永远不要展示一张让观众问"那又怎样？"的图
- 图表数量由 storyboard 决定。每个需要可视化的叙事节拍变成一张图。
- 最后一张图应让推荐的行动一目了然

### 图表 helper 函数参考

所有图表 helper 都在 `helpers/chart_helpers.py` 里。样式文件是 `helpers/analytics_chart_style.mplstyle`。带前后对比示例的完整样式指南在 `helpers/chart_style_guide.md`。

| Function | Purpose | Key Args |
|----------|---------|----------|
| `swd_style()` | Apply SWD matplotlib style, return color palette | — |
| `highlight_bar()` | Bar chart with one bar highlighted, rest gray | `highlight=`, `horizontal=True`, `sort=True` |
| `highlight_line()` | Line chart with one line colored, rest gray | `highlight=`, `y_dict={}` |
| `action_title()` | Bold takeaway title + optional subtitle | `title`, `subtitle=` |
| `annotate_point()` | Clean annotation with arrow | `x`, `y`, `text`, `offset=` |
| `save_chart()` | Tight layout + correct DPI | `fig`, `path`, `dpi=150` |

### 主题定义

#### 主题：`nyt`（New York Times）
```python
NYT_THEME = {
    "colors": {
        "primary": "#000000",
        "secondary": "#666666",
        "accent": "#D03A2B",
        "palette": ["#D03A2B", "#1A6B54", "#3D6CA3", "#E8912D", "#8B5E3C", "#6B4C9A"],
        "background": "#FFFFFF",
        "grid": "#E5E5E5",
    },
    "fonts": {
        "title": {"family": "Georgia", "size": 18, "weight": "bold"},
        "subtitle": {"family": "Arial", "size": 12, "weight": "normal", "color": "#666666"},
        "axis_label": {"family": "Arial", "size": 10},
        "annotation": {"family": "Arial", "size": 9, "style": "italic"},
    },
    "grid": {"show": True, "axis": "y", "style": "--", "alpha": 0.3},
    "annotations": {"style": "minimal", "callout_arrows": True},
    "title": {"position": "left-aligned", "include_subtitle": True},
}
```

#### 主题：`economist`（The Economist）
```python
ECONOMIST_THEME = {
    "colors": {
        "primary": "#1F2E3C",
        "secondary": "#7C8A96",
        "accent": "#E3120B",
        "palette": ["#E3120B", "#1F6ED4", "#36B37E", "#F5A623", "#6554C0", "#00B8D9"],
        "background": "#D7E4E8",
        "grid": "#FFFFFF",
    },
    "fonts": {
        "title": {"family": "Helvetica", "size": 16, "weight": "bold"},
        "subtitle": {"family": "Helvetica", "size": 11, "weight": "normal"},
        "axis_label": {"family": "Helvetica", "size": 9},
        "annotation": {"family": "Helvetica", "size": 8},
    },
    "grid": {"show": True, "axis": "y", "style": "-", "alpha": 0.5, "color": "#FFFFFF"},
    "annotations": {"style": "inline", "red_highlight": True},
    "title": {"position": "left-aligned", "red_bar_top": True},
}
```

#### 主题：`minimal`
```python
MINIMAL_THEME = {
    "colors": {
        "primary": "#333333",
        "secondary": "#999999",
        "accent": "#2563EB",
        "palette": ["#2563EB", "#DC2626", "#059669", "#D97706", "#7C3AED", "#DB2777"],
        "background": "#FFFFFF",
        "grid": "#F0F0F0",
    },
    "fonts": {
        "title": {"family": "Helvetica", "size": 14, "weight": "bold"},
        "subtitle": {"family": "Helvetica", "size": 10, "weight": "normal", "color": "#666666"},
        "axis_label": {"family": "Helvetica", "size": 9},
        "annotation": {"family": "Helvetica", "size": 8},
    },
    "grid": {"show": True, "axis": "y", "style": "-", "alpha": 0.15},
    "annotations": {"style": "minimal", "direct_labels": True},
    "title": {"position": "left-aligned", "include_subtitle": True},
}
```

#### 主题：`corporate`
```python
CORPORATE_THEME = {
    "colors": {
        "primary": "#1B2A4A",
        "secondary": "#5A6B7F",
        "accent": "#0066CC",
        "palette": ["#0066CC", "#00A651", "#FF6600", "#CC0000", "#9933CC", "#00CCCC"],
        "background": "#FFFFFF",
        "grid": "#E8E8E8",
    },
    "fonts": {
        "title": {"family": "Arial", "size": 16, "weight": "bold"},
        "subtitle": {"family": "Arial", "size": 11, "weight": "normal"},
        "axis_label": {"family": "Arial", "size": 10},
        "annotation": {"family": "Arial", "size": 9},
    },
    "grid": {"show": True, "axis": "both", "style": "-", "alpha": 0.2},
    "annotations": {"style": "callout", "box_highlight": True},
    "title": {"position": "center", "include_subtitle": True},
}
```

### 套用主题（matplotlib）

```python
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

def apply_theme(fig, ax, theme):
    """Apply a named theme to a matplotlib figure."""
    fig.patch.set_facecolor(theme["colors"]["background"])
    ax.set_facecolor(theme["colors"]["background"])

    # Title styling
    ax.set_title(
        ax.get_title(),
        fontfamily=theme["fonts"]["title"]["family"],
        fontsize=theme["fonts"]["title"]["size"],
        fontweight=theme["fonts"]["title"]["weight"],
        loc="left" if theme["title"]["position"] == "left-aligned" else "center",
        pad=15,
    )

    # Grid
    if theme["grid"]["show"]:
        ax.grid(
            axis=theme["grid"]["axis"],
            linestyle=theme["grid"]["style"],
            alpha=theme["grid"]["alpha"],
            color=theme["colors"].get("grid", "#E0E0E0"),
        )
        ax.set_axisbelow(True)

    # Clean spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_alpha(0.3)
    ax.spines["bottom"].set_alpha(0.3)

    # Axis labels
    ax.xaxis.label.set_fontfamily(theme["fonts"]["axis_label"]["family"])
    ax.xaxis.label.set_fontsize(theme["fonts"]["axis_label"]["size"])
    ax.yaxis.label.set_fontfamily(theme["fonts"]["axis_label"]["family"])
    ax.yaxis.label.set_fontsize(theme["fonts"]["axis_label"]["size"])

    plt.tight_layout()
```

### 图表类型选择

| Data Relationship | Chart Type | When to Use |
|---|---|---|
| **Comparison** (categories) | Bar chart (vertical) | Comparing ≤12 categories |
| **Comparison** (many categories) | Bar chart (horizontal) | Comparing >7 categories or long labels |
| **Comparison** (parts of whole) | Stacked bar | Showing composition across categories |
| **Change over time** | Line chart | Continuous time series, trends |
| **Change over time** (few periods) | Bar chart | Discrete periods (quarters, years) |
| **Correlation** | Scatter plot | Relationship between two continuous variables |
| **Distribution** | Histogram | Single variable distribution |
| **Distribution** (compare groups) | Box plot or violin | Distribution comparison across groups |
| **Proportion** | Donut chart | ≤5 segments, one variable |
| **Flow/Process** | Funnel chart | Conversion or drop-off rates |
| **Intensity** | Heatmap | Two categorical dimensions + one value |
| **Cumulative** | Area chart | Running totals over time |
| **Ranking changes** | Bump chart | Rank position changes over time |
| **Waterfall** | Waterfall chart | Additive/subtractive contributions |

### 标注标准

1. **始终直接标注关键数据点** —— 不要依赖图例来表达主要的故事元素
2. **在条形和折线端点上用直接标注**，而非要求读者去读坐标轴
3. **标注拐点** —— 在趋势改变处用一句话标记
4. **标题是结论，不是描述** —— "Revenue grew 23% after launch" 而非 "Revenue by Month"
5. **副标题提供上下文** —— "Monthly revenue, Jan–Dec 2025, in $M"
6. **来源行**放在左下角，小号灰色文字
7. **数字格式要便于阅读** —— "$1.2M" 而非 "$1,234,567"；"23%" 而非 "0.2345"
8. **单张图最多 6 种颜色** —— 用灰色表示"其他"或"其余"
9. **高亮故事** —— 关键数据点用强调色，背景用灰色

### 标准图表初始化

```python
def create_chart(data, chart_type, theme_name="minimal", title="", subtitle=""):
    """Standard chart creation pattern."""
    theme = {"nyt": NYT_THEME, "economist": ECONOMIST_THEME,
             "minimal": MINIMAL_THEME, "corporate": CORPORATE_THEME}[theme_name]

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(theme["colors"]["background"])
    ax.set_facecolor(theme["colors"]["background"])

    # Plot data using theme colors
    colors = theme["colors"]["palette"]

    # Set title as takeaway
    ax.set_title(title, fontfamily=theme["fonts"]["title"]["family"],
                 fontsize=theme["fonts"]["title"]["size"],
                 fontweight=theme["fonts"]["title"]["weight"],
                 loc="left", pad=20)
    # Subtitle
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes,
                fontfamily=theme["fonts"]["subtitle"]["family"],
                fontsize=theme["fonts"]["subtitle"]["size"],
                color=theme["fonts"]["subtitle"].get("color", "#666666"))

    apply_theme(fig, ax, theme)
    return fig, ax
```

## 示例

### 示例 1：NYT 主题的条形图
```python
fig, ax = plt.subplots(figsize=(10, 6))
categories = ["Mobile", "Desktop", "Tablet"]
values = [45, 35, 20]
colors = ["#D03A2B", "#666666", "#666666"]  # Accent on key finding

bars = ax.bar(categories, values, color=colors, width=0.6)
# Direct labels
for bar, val in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
            f"{val}%", ha="center", fontsize=12, fontweight="bold")

ax.set_title("Mobile drives nearly half of all sessions", loc="left",
             fontfamily="Georgia", fontsize=18, fontweight="bold")
ax.set_ylabel("")
ax.set_ylim(0, 55)
apply_theme(fig, ax, NYT_THEME)
```

### 示例 2：带标注的折线图
```python
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(dates, revenue, color="#2563EB", linewidth=2)
# Annotate the inflection point
ax.annotate("Feature launch\n+23% MoM", xy=(launch_date, launch_value),
            xytext=(launch_date - timedelta(days=30), launch_value + 50000),
            fontsize=9, fontstyle="italic",
            arrowprops=dict(arrowstyle="->", color="#666666"))
# Direct label on endpoint
ax.text(dates[-1], revenue[-1], f"${revenue[-1]/1e6:.1f}M",
        fontsize=11, fontweight="bold", va="bottom")
ax.set_title("Revenue grew 23% after feature launch", loc="left")
apply_theme(fig, ax, MINIMAL_THEME)
```

### 示例 3：高亮单个分段
```python
# Use accent for the key finding, gray for everything else
colors = ["#E0E0E0"] * len(categories)
colors[key_index] = theme["colors"]["accent"]  # Highlight the story
```

## 反模式（禁用）

| Anti-Pattern | Why It's Bad | Use Instead |
|--------------|-------------|-------------|
| **Pie charts** | Humans can't compare angles accurately | Horizontal bar chart |
| **Rainbow palettes** | No natural ordering, visual noise, not colorblind-safe | Gray + one highlight color (max 2 colors + gray) |
| **Spaghetti lines** | Too many colored lines, nothing stands out | `highlight_line()` — gray all, highlight one |
| **Dual y-axes** | Misleading — any two series can be made to "correlate" | Two separate charts, stacked vertically |
| **3D charts** | Distorts proportions, adds no information | Flat 2D versions |
| **Descriptive titles** | Don't tell the reader what to think | Action titles via `action_title()` |
| **Legend boxes** | Force the reader to look away from the data | Direct labels on the data |
| **Excessive gridlines** | Create visual clutter | Light y-axis gridlines only, or none |
| **Truncated y-axes** | Exaggerate small differences (for bar charts) | Start at zero for bar charts |
| **Cluttered annotations** | Annotating every data point defeats the purpose | Annotate only the story |
| **Default matplotlib styling** | Looks generic, unprofessional | Always apply `swd_style()` first |
| **More than 2 colors** | Creates visual noise, dilutes focus | Gray + Action Amber + optional Accent Red |

## 审查清单

把任何图表纳入分析之前：

- [ ] 标题陈述结论（而非描述）
- [ ] 只用 1-2 种颜色（外加灰色）
- [ ] 无图表边框，无顶部/右侧坐标轴线
- [ ] 用直接标注而非图例
- [ ] 网格线已去掉或非常浅
- [ ] 坐标轴标签干净（不旋转、无多余的零）
- [ ] 标注简洁且服务于故事
- [ ] 图表类型匹配数据关系
- [ ] 单个数字不画成图 —— 用文字展示
- [ ] 这张图能在 5 秒内被看懂
- [ ] 同比对比用折线（而非两根颜色相近的条）
- [ ] 标签不与条形、坐标轴或其他标签碰撞
- [ ] 外部背景事件用醒目的 bbox 标注
- [ ] 带 fig 级标题的多面板图用直接 `savefig()`（而非 `save_chart()`）

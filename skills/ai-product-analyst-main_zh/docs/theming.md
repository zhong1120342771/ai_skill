# 主题指南

AI Analyst 使用基于 YAML 的主题系统，实现一致、品牌化的可视化。
主题控制颜色、排版、图表样式和演示默认值。

## 架构

```
themes/
├── _base.yaml              # 默认主题（总是最先加载）
├── README.md               # 主题目录概览
├── analytics.css           # 用于演示的 Marp 主题（亮色模式）
├── analytics-dark.css      # 用于演示的 Marp 主题（暗色模式）
├── analytics-light.css     # Marp 主题别名
└── brands/
    └── {brand}/
        ├── theme.yaml      # 品牌覆写（合并在 _base 之上）
        └── README.md       # 品牌专属说明
```

**继承模型：** 品牌主题通过深度合并从 `_base.yaml` 继承。
只覆写你需要的部分 —— 其余一切回退到基础主题。

## 基础主题 Schema

基础主题（`themes/_base.yaml`）定义了六个顶层小节：

### `theme` — 元数据
```yaml
theme:
  name: "analytics"
  display_name: "Analytics (Default)"
  version: "1.0"
  description: "Clean, professional analytics theme based on SWD methodology"
```

### `colors` — 配色

```yaml
colors:
  primary: "#4878CF"        # Blue — key data, call-to-action
  secondary: "#6ACC65"      # Green — positive, growth
  accent: "#D65F5F"         # Red — alerts, negative, emphasis
  neutral: "#B0B0B0"        # Gray — supporting, context
  background: "#F7F6F2"     # Warm off-white (matches analytics_chart_style.mplstyle)
  text: "#333333"           # Dark gray — body text
  text_light: "#666666"     # Medium gray — captions, annotations

  categorical:              # Up to 8 distinct series colors (colorblind-safe)
    - "#4878CF"             # blue
    - "#6ACC65"             # green
    - "#B47CC7"             # purple
    - "#D65F5F"             # red
    - "#C4AD66"             # gold
    - "#77BEDB"             # light blue
    - "#D68E5C"             # orange
    - "#8C8C8C"             # gray

  sequential:               # Low-to-high gradient (for heatmaps, density)
    low: "#D6E4F0"
    high: "#1A5276"

  diverging:                # Negative/neutral/positive (for variance, change)
    negative: "#D65F5F"
    neutral: "#F7F6F2"
    positive: "#6ACC65"

  highlight:                # For emphasis
    primary: "#D68E5C"      # Orange — highlight key data point
    secondary: "#4878CF"    # Blue — secondary emphasis
    alert: "#D65F5F"        # Red — warnings, errors
```

**色盲友好：** 默认的 categorical 配色避免了相邻的红绿配对。创建品牌主题时，请用色盲模拟器测试。

### `typography` — 字体设置
```yaml
typography:
  font_family: "Helvetica Neue, Arial, sans-serif"
  title_size: 16
  label_size: 11
  annotation_size: 10
  title_weight: "bold"
```

### `charts` — Matplotlib 默认值
```yaml
charts:
  figure:
    width: 10
    height: 6
    dpi: 150
  axes:
    spine_visible: [bottom, left]  # Top and right spines hidden
    grid: false                     # No gridlines by default
  bar:
    width: 0.6
    edge_color: "none"
  line:
    width: 2.5
    marker_size: 6
  annotations:
    fontsize: 10
    color: "#333333"
```

### `presentations` — Marp 幻灯片默认值
```yaml
presentations:
  engine: marp
  theme: analytics          # Maps to themes/analytics.css
  paginate: true
  background_color: "#FFFFFF"
  text_color: "#333333"
  accent_color: "#4878CF"
  dark_mode:
    theme: analytics-dark   # Maps to themes/analytics-dark.css
    background_color: "#1E1E2E"
    text_color: "#CDD6F4"
    accent_color: "#89B4FA"
```

### `export` — 输出设置
```yaml
export:
  chart_format: png
  chart_dpi: 150
  bbox_inches: tight
```

## 创建品牌主题

### 1. 创建目录结构
```bash
mkdir -p themes/brands/mycompany
```

### 2. 创建 `theme.yaml`

只覆写与 `_base.yaml` 不同的部分：

```yaml
# themes/brands/mycompany/theme.yaml
theme:
  name: "mycompany"
  display_name: "MyCompany Analytics"
  inherits: _base

colors:
  primary: "#1B4D89"       # Company blue
  secondary: "#2EAD6D"     # Company green
  accent: "#E87C3E"        # Company orange
  
  categorical:
    - "#1B4D89"            # Company blue
    - "#E87C3E"            # Company orange
    - "#2EAD6D"            # Company green
    - "#8B5CF6"            # Purple
    - "#F59E0B"            # Amber
    - "#06B6D4"            # Cyan
    - "#EC4899"            # Pink
    - "#6B7280"            # Gray

  highlight:
    primary: "#E87C3E"     # Orange for emphasis
    secondary: "#1B4D89"   # Blue for secondary emphasis

typography:
  font_family: "Inter, sans-serif"
  title_size: 18           # Larger titles

presentations:
  background_color: "#FAFAFA"
  accent_color: "#1B4D89"
```

### 3. 添加 README（可选）
```markdown
# MyCompany Theme
Brand colors from the 2024 style guide.
Contact: design@mycompany.com

## Colors
- Primary Blue: #1B4D89
- Orange Accent: #E87C3E
- Green Success: #2EAD6D

## Usage
Load with `load_theme("mycompany")`
```

## 在代码中使用主题

### 加载主题
```python
from helpers.theme_loader import load_theme, get_color

# Load base theme (analytics)
theme = load_theme()

# Load brand theme (merges on top of base)
theme = load_theme("mycompany")

# Access specific colors (supports dot notation)
primary = get_color(theme, "colors.primary")
bg = get_color(theme, "colors.background")
```

### 应用到图表
```python
from helpers.chart_helpers import swd_style, highlight_bar
from helpers.chart_palette import apply_theme_colors

# Apply theme to matplotlib
theme = load_theme("mycompany")
apply_theme_colors(theme)

# Charts automatically use theme colors
fig, ax = highlight_bar(
    data, x="category", y="value",
    highlight="Target Category"
)
```

### 使用配色
```python
from helpers.chart_palette import (
    highlight_palette, categorical_colors, palette_for_n
)

# Get highlight colors (primary, secondary, alert)
highlights = highlight_palette(theme)

# Get categorical colors (up to 8)
colors = categorical_colors(theme)

# Get smart palette for arbitrary n
# (extends categorical list with interpolated colors)
colors = palette_for_n(theme, n=12)
```

### 图表级别的主题应用
```python
from helpers.chart_helpers import swd_style, highlight_bar

# Apply theme at start of charting
swd_style(theme="mycompany")

# All charts in this session use the theme
fig1, ax1 = highlight_bar(data1, x="a", y="b", highlight="Target")
fig2, ax2 = highlight_line(data2, x="date", y="metric", highlight="2024-Q4")
```

### 用主题创建幻灯片
```python
# In deck-creator.md agent or Deck Creator workflow
from helpers.theme_loader import load_theme

theme = load_theme("mycompany")

# Marp frontmatter generation
marp_theme = theme.get("presentations", {}).get("theme", "analytics")
bg_color = theme.get("presentations", {}).get("background_color", "#FFFFFF")

marp_header = f"""---
marp: true
theme: {marp_theme}
backgroundColor: {bg_color}
---
"""
```

## WCAG 合规

所有主题颜色都应满足 WCAG 2.1 AA 级对比度要求：

- **背景上的文字：** 最低 4.5:1 对比度
- **背景上的大号文字：** 最低 3:1 对比度
- **UI 组件：** 最低 3:1 对比度

### 检查对比度
`chart_palette` 模块提供自动对比度检查：

```python
from helpers.chart_palette import ensure_contrast

# Ensure text color has sufficient contrast with background
text_color = ensure_contrast(
    foreground="#333333",
    background="#F7F6F2",
    min_ratio=4.5  # WCAG AA for normal text
)
```

### 手动验证
用在线工具验证主题颜色：
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [Coolors Contrast Checker](https://coolors.co/contrast-checker)

## 主题系统文件

| 文件 | 用途 |
|------|---------|
| `themes/_base.yaml` | 默认主题定义 |
| `themes/brands/{brand}/theme.yaml` | 品牌专属覆写 |
| `helpers/theme_loader.py` | 主题加载、缓存与合并 |
| `helpers/chart_palette.py` | 配色生成与对比度检查 |
| `helpers/chart_helpers.py` | 集成主题的图表创建 |
| `themes/analytics.css` | Marp 演示主题（亮色模式） |
| `themes/analytics-dark.css` | Marp 演示主题（暗色模式） |

## 进阶：连续型与发散型 colormap

对于热力图和密度图，使用连续型或发散型 colormap：

```python
from helpers.theme_loader import get_sequential_colormap, get_diverging_colormap
import matplotlib.pyplot as plt

theme = load_theme("mycompany")

# Sequential colormap (low to high)
seq_cmap = get_sequential_colormap(theme)
plt.imshow(data, cmap=seq_cmap)

# Diverging colormap (negative to positive)
div_cmap = get_diverging_colormap(theme)
plt.imshow(variance_data, cmap=div_cmap)
```

## 最佳实践

### 1. 色盲友好配色
- 避免相邻的红绿配对
- 使用区分度高的色相（蓝、橙、紫、绿）
- 用模拟器测试：[Coblis](https://www.color-blindness.com/coblis-color-blindness-simulator/)

### 2. 最小化覆写
只覆写你需要的部分。基础主题已提供合理的默认值。

```yaml
# Good: minimal overrides
colors:
  primary: "#1B4D89"
  categorical:
    - "#1B4D89"
    - "#E87C3E"
    - "#2EAD6D"

# Bad: redundant overrides
colors:
  primary: "#1B4D89"
  background: "#F7F6F2"  # Already in _base.yaml
  text: "#333333"        # Already in _base.yaml
  categorical: ...
```

### 3. 语义化命名
使用语义化的颜色名（primary、accent、alert），而非字面名（blue、red）。
当品牌色变更时，这样的主题更易维护。

### 4. 在真实场景中测试
始终用真实的图表和幻灯片测试品牌主题：

```bash
# Generate sample charts with new theme
python3 -c "
from helpers.theme_loader import load_theme
from helpers.chart_helpers import swd_style, highlight_bar
import pandas as pd

theme = load_theme('mycompany')
swd_style(theme='mycompany')

data = pd.DataFrame({'category': ['A', 'B', 'C'], 'value': [10, 25, 15]})
fig, ax = highlight_bar(data, x='category', y='value', highlight='B')
fig.savefig('test_mycompany_theme.png')
"
```

## 故障排查

**图表没有采用主题颜色：**
- 确保在创建 figure 之前调用了 `swd_style(theme="name")` 或 `apply_theme_colors(theme)`
- 检查 `themes/brands/{name}/theme.yaml` 是否存在
- 确认主题名与目录名一致（例如 "mycompany" 而非 "MyCompany"）

**字体未渲染：**
- Matplotlib 使用系统字体。请安装该字体或使用回退字体
- 清除 matplotlib 字体缓存：`rm -rf ~/.matplotlib/fontlist-*.json`
- 使用常见回退字体："Helvetica Neue, Arial, sans-serif"

**暗色模式幻灯片显示异常：**
- 确认主题中存在 `presentations.dark_mode` 小节
- 检查图表背景是透明的，或与幻灯片背景一致
- 暗色模式图表使用 `swd_style(theme="mycompany", dark_mode=True)`

**主题更改未生效：**
- 清除主题缓存：`from helpers.theme_loader import clear_cache; clear_cache()`
- 重启 Python 会话（主题缓存在内存中）

**categorical 配色不够用：**
- 用 `palette_for_n(theme, n=12)` 生成扩展配色
- 考虑简化可视化（减少类别数）
- 用 small multiples 代替把许多序列塞进一张图

## 示例

### 示例 1：企业改版品牌
```yaml
# themes/brands/acme/theme.yaml
theme:
  name: "acme"
  display_name: "Acme Corp Analytics"
  inherits: _base

colors:
  primary: "#FF6B35"      # Acme orange
  secondary: "#004E89"    # Acme navy
  accent: "#1AA3D0"       # Acme cyan
  categorical:
    - "#FF6B35"
    - "#004E89"
    - "#1AA3D0"
    - "#F7B32B"
    - "#6A4C93"
```

### 示例 2：无障碍优先主题
```yaml
# themes/brands/accessible/theme.yaml
theme:
  name: "accessible"
  display_name: "High-Contrast Accessible"
  inherits: _base

colors:
  primary: "#0066CC"      # WCAG AAA on white
  background: "#FFFFFF"
  text: "#000000"         # Maximum contrast
  categorical:
    - "#0066CC"           # Blue
    - "#D95F02"           # Orange
    - "#7570B3"           # Purple
    - "#1B9E77"           # Teal
    - "#E7298A"           # Magenta

typography:
  title_size: 18          # Larger for readability
  label_size: 12
```

### 示例 3：打印优化主题
```yaml
# themes/brands/print/theme.yaml
theme:
  name: "print"
  display_name: "Print-Optimized B&W"
  inherits: _base

colors:
  primary: "#000000"
  background: "#FFFFFF"
  text: "#000000"
  categorical:             # Grayscale palette
    - "#000000"
    - "#424242"
    - "#616161"
    - "#9E9E9E"

charts:
  line:
    width: 3.0             # Thicker lines for print
  bar:
    edge_color: "#000000"  # Add borders for clarity

export:
  chart_format: pdf        # Vector format for print
  chart_dpi: 300          # High DPI
```

## 另见

- `themes/README.md` —— 主题目录概览
- `helpers/chart_style_guide.md` —— Storytelling with Data 图表方法论
- `.claude/skills/visualization-patterns/skill.md` —— 可视化最佳实践
- `.claude/skills/presentation-themes/skill.md` —— 幻灯片主题指南

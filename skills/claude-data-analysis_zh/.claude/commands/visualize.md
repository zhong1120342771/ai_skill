---
allowed-tools: Task, Read, Write, Bash, Grep, Glob
argument-hint: [dataset] [chart_type]
description: 为指定数据集创建数据可视化
---

# 数据可视化命令

使用 visualization-specialist 子代理，为数据集 `$1` 按图表类型 `$2` 创建完整的数据可视化。

## Context
- 数据集位置: @data_storage/$1
- 图表类型: $2 (all, trends, distribution, correlation, comparison, custom)
- 当前工作目录: !`pwd`
- 可视化输出目录: ./visualizations/
- 可用库: matplotlib、seaborn、plotly、bokeh

## Your Task

使用 visualization-specialist 子代理创建信息丰富的可视化：

### 1. 数据准备
- 加载并准备数据集
- 处理缺失值与离群值
- 选择适合可视化的变量
- 为不同图表类型准备数据

### 2. 可视化规划
- 确定最适合数据的图表类型
- 规划配色与样式
- 考虑目标受众与用途
- 规划布局与构图

### 3. 图表创建
- 创建多个互补的可视化
- 确保恰当的标签与注释
- 使用合适的刻度与范围
- 应用一致的样式与颜色

### 4. 质量保证
- 用不同数据场景测试可视化
- 核验可视化中的数据准确性
- 检查可访问性与可读性
- 针对不同屏幕尺寸优化

## 图表类型

### 全部可视化
- 含多种图表类型的综合仪表板
- 所有关键变量与关系的概览
- 执行摘要可视化
- 交互式探索仪表板

### 趋势（Trends）
- 时间序列折线图
- 移动平均图
- 趋势分解
- 季节性分析图

### 分布（Distribution）
- 直方图与密度图
- 箱线图与小提琴图
- 用于正态性检验的 Q-Q 图
- 统计分布图

### 相关性（Correlation）
- 相关性热力图
- 散点图矩阵
- 配对图
- 回归分析图

### 对比（Comparison）
- 柱状图与条形图
- 分组与堆叠图
- 小型多重图
- 对比分析图

### 自定义（Custom）
- 用户指定的自定义可视化
- 领域专属图表
- 交互式仪表板
- 动画可视化

## 预期输出

### 可视化文件
- `visualizations/dashboard_$1.html` - 交互式仪表板
- `visualizations/summary_$1.png` - 汇总图表
- `visualizations/detailed_$1.pdf` - 详细分析图表
- `visualizations/charts_$1.py` - 可复现代码

### 文档
- **图表说明**：对每个可视化的解释
- **数据来源**：数据变换的记录
- **解读指南**：如何阅读与理解图表
- **定制选项**：如何修改与扩展可视化

## 技术要求

### 文件格式
- **静态图片**：PNG（高分辨率）、SVG（矢量）
- **交互式**：带 JavaScript 的 HTML（Plotly、D3.js）
- **打印**：高分辨率 PDF
- **代码**：用于复现的 Python/R 脚本

### 设计标准
- **配色**：色盲友好的调色板
- **排版**：清晰、易读的字体
- **布局**：响应式且组织良好
- **可访问性**：尽可能符合 WCAG

## 质量保证

### 校验检查
- 核验所有可视化中的数据准确性
- 用不同屏幕尺寸与设备测试
- 检查颜色可访问性
- 确保恰当的标签与注释

### 性能
- 优化文件大小以适配 Web 展示
- 确保快速加载
- 测试交互性与响应性
- 校验跨浏览器兼容性

## 使用示例
```bash
/visualize user_behavior.csv all
/visualize sales_data.csv trends
/visualize customer_data.csv distribution
/visualize financial_data.csv correlation
/visualize performance_data.csv comparison
/visualize custom_data.csv custom
```

## 最佳实践

### 设计原则
- **数据墨水比**：最大化数据墨水占总墨水的比例
- **图表垃圾**：剔除非数据墨水与装饰性元素
- **清晰**：确保信息一目了然
- **一致**：在所有可视化中使用一致的样式

### 数据完整性
- 可视化前校验数据
- 恰当处理缺失值
- 使用合适的刻度与范围
- 记录所有数据变换

### 用户体验
- 考虑目标受众
- 提供清晰的标签与图例
- 在有帮助处加入交互功能
- 为同一份数据提供多种视角

## 注意事项
- 数据集应位于 data_storage/ 目录
- 可视化将保存到 visualizations/ 目录
- 用 Task 工具委派给 visualization-specialist 子代理
- 可考虑先用 /analyze 命令获取数据洞察
- 交互式可视化需要 Web 浏览器查看

## 与其他命令的配合
- 在 `/analyze` 之后使用，做数据驱动的可视化
- 与 `/report` 配合，生成完整的分析报告
- 之后用 `/generate` 生成可视化代码片段

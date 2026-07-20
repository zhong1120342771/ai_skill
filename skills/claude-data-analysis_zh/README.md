# Claude 数据分析助手

一个基于 Claude Code 的子代理（sub-agents）、斜杠命令（slash-commands）和钩子（hooks）构建的现代智能数据分析平台。用 AI 驱动的协助来改造你的数据分析工作流。

## 🚀 快速开始

### 1. 准备你的数据
把数据集放进 `data_storage/` 目录：
```bash
cp your_data.csv ./data_storage/
```

### 2. 开始分析
用直观的斜杠命令来分析数据：
```bash
# 基础探索性分析
/analyze user_behavior_sample.csv exploratory

# 创建可视化
/visualize user_behavior_sample.csv all

# 生成分析代码
/generate python data-cleaning

# 创建完整报告
/report user_behavior_sample.csv complete markdown
```

## 🎯 核心特性

### 智能子代理
- **data-explorer**：擅长统计分析和模式发现
- **visualization-specialist**：制作美观、有洞察力的图表
- **code-generator**：产出可直接投产的分析代码
- **report-writer**：撰写完整的分析报告
- **quality-assurance**：数据校验与质量控制
- **hypothesis-generator**：生成研究假设与洞察

### 直观的斜杠命令
- `/analyze [dataset] [type]` - 执行数据分析
- `/visualize [dataset] [type]` - 创建可视化
- `/generate [language] [type]` - 生成分析代码
- `/report [dataset] [format]` - 生成报告
- `/quality [dataset] [action]` - 质量保证
- `/hypothesis [dataset] [domain]` - 生成假设

### 自动化工作流
- **数据校验**：数据上传时自动做质量检查
- **智能上下文**：贴合项目情境的分析建议
- **可复现分析**：完整的文档记录与代码生成

## 📊 使用示例

### 用户行为分析
```bash
# 完整分析工作流
/analyze user_behavior.csv exploratory
/visualize user_behavior.csv trends
/quality user_behavior.csv clean
/report user_behavior.csv complete html
/generate python user-segmentation
```

### 销售数据分析
```bash
# 销售业绩分析
/analyze sales_data.csv statistical
/visualize sales_data.csv trends
/generate sql revenue-analysis
/report sales_data.csv executive pdf
```

### 客户分析
```bash
# 客户分群
/analyze customer_data.csv predictive
/visualize customer_data.csv distribution
/generate r clustering-analysis
/hypothesis customer_data churn-prediction
```

## 🛠️ 项目结构

```
claude-data-analysis/
├── .claude/
│   ├── agents/          # 子代理配置
│   ├── commands/        # 斜杠命令定义
│   ├── hooks/          # 自动化脚本
│   └── settings.json   # Claude Code 设置
├── data_storage/       # 你的数据文件
├── visualizations/     # 生成的图表
├── generated_code/     # 分析代码
├── analysis_reports/   # 分析报告
├── examples/          # 示例数据集与工作流
└── docs/             # 文档
```

## 🎨 示例数据

项目内置了示例数据，帮你快速上手：

- **user_behavior_sample.csv**：示例用户行为数据，包含用户操作、设备、地区和收入
- **字段说明**：user_id、session_id、timestamp、action、page_url、device_type、location、revenue

## 🔧 配置

### 环境准备
项目使用 Claude Code 的配置系统。关键设置：

1. **钩子（Hooks）**：自动校验与上下文加载
2. **子代理（Sub-agents）**：面向不同任务的专用 AI 助手
3. **命令（Commands）**：常用操作的自定义斜杠命令

### 环境要求
- Python 3.8+ 用于数据分析
- 启用了子代理的 Claude Code
- CSV、JSON 或 Excel 格式的数据文件

## 📚 上手指南

### 新用户
1. **放入数据** 到 `data_storage/`
2. **运行探索性分析**：`/analyze your_data.csv exploratory`
3. **创建可视化**：`/visualize your_data.csv all`
4. **生成报告**：`/report your_data.csv complete markdown`

### 进阶用户
1. **定制代理**：修改 `.claude/agents/` 配置
2. **创建自定义命令**：在 `.claude/commands/` 中新增命令
3. **配置自动化**：在 `.claude/settings.json` 中设置钩子
4. **扩展功能**：添加自定义分析脚本

## 🎯 分析类型

### 探索性分析
- 数据质量评估
- 汇总统计
- 模式发现
- 初步洞察

### 统计分析
- 假设检验
- 相关性分析
- 回归分析
- 置信区间

### 预测性分析
- 特征重要性
- 预测建模
- 变量关系
- 模型推荐

### 完整分析
- 全部分析类型
- 完整报告
- 可视化
- 可落地的洞察

## 📈 可视化类型

### 全部可视化
- 综合仪表板
- 多种图表类型
- 交互式探索
- 执行摘要

### 特定图表
- **趋势（Trends）**：时间序列、移动平均
- **分布（Distribution）**：直方图、箱线图、密度图
- **相关性（Correlation）**：热力图、散点图、相关矩阵
- **对比（Comparison）**：柱状图、分组图、小型多重图

## 🔍 代码生成

### 支持的语言
- **Python**：Pandas、NumPy、Scikit-learn、Matplotlib
- **R**：Tidyverse、ggplot2、caret
- **SQL**：所有主流方言
- **JavaScript**：D3.js、Plotly.js、TensorFlow.js

### 分析类型
- 数据清洗与预处理
- 统计分析
- 机器学习
- 可视化代码
- 自定义分析

## 📋 项目状态

**当前阶段**：Week 1.1 - 项目初始化 ✅

### 已完成功能
- [x] 项目结构与配置
- [x] Data Explorer 子代理
- [x] Visualization Specialist 子代理
- [x] 核心斜杠命令（/analyze、/visualize、/generate）
- [x] 自动化钩子
- [x] 示例数据与文档

### 即将推出
- [ ] Report Writer 子代理
- [ ] Quality Assurance 子代理
- [ ] Hypothesis Generator 子代理
- [ ] 进阶斜杠命令
- [ ] 交互式仪表板
- [ ] 与外部工具集成

## 🤝 参与贡献

欢迎贡献！请按以下步骤操作：

1. **Fork 仓库**
2. **创建功能分支**
3. **添加你的改进**
4. **测试你的改动**
5. **提交 pull request**

### 开发规范
- 遵循既定的代码风格
- 补充完整的文档
- 为新功能编写单元测试
- 按需更新 README

## 📄 许可证

本项目基于 MIT 许可证授权。详见 LICENSE 文件。

## 🙏 致谢

- 基于 [Claude Code](https://claude.ai/code) 构建
- 受 [DATAGEN](https://github.com/starpig1129/DATAGEN) 项目启发
- 由现代数据科学工具和框架驱动

## 📞 支持

获取支持与帮助：
- 查看 `docs/` 目录下的文档
- 参考 `examples/` 中的示例
- 使用 `/help` 命令获取用法帮助

---

**让数据分析更聪明，而不是更费力！** 🚀

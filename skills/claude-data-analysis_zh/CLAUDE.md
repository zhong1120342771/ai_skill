# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在本仓库工作时提供指引。

## 项目概览

Claude 数据分析助手是一个智能数据分析平台，借助 Claude Code 的子代理、斜杠命令和钩子，提供一套完整的数据分析工作流。它基于已经验证成功的 DATAGEN 多代理架构，为数据分析任务提供现代、友好的操作界面。

## 快速开始

1. 把数据文件放进 `data_storage/` 目录
2. 用 `/analyze [filename]` 开始数据分析
3. 用 `/visualize [filename]` 创建可视化
4. 用 `/report [filename]` 生成分析报告

## 核心特性

### 子代理
- **data-explorer**：数据探索与统计分析
- **visualization-specialist**：数据可视化制作
- **code-generator**：分析代码生成
- **report-writer**：完整报告生成
- **quality-assurance**：数据质量校验
- **hypothesis-generator**：研究假设生成

### 斜杠命令
- `/analyze [dataset] [analysis_type]`：执行数据分析
- `/visualize [dataset] [chart_type]`：创建可视化
- `/generate [language] [analysis_type]`：生成分析代码
- `/report [dataset] [format]`：生成分析报告
- `/quality [dataset] [action]`：执行数据质量检查
- `/hypothesis [dataset] [domain]`：生成研究假设

### 目录结构
```
claude-data-analysis/
├── .claude/
│   ├── agents/          # 子代理配置
│   ├── commands/        # 斜杠命令定义
│   ├── hooks/          # 自动化脚本
│   └── settings.json   # Claude Code 设置
├── data_storage/       # 数据文件目录
├── visualizations/     # 生成的图表
├── examples/          # 示例数据集与工作流
└── docs/             # 文档
```

## 使用示例

```bash
# 分析用户行为数据
/analyze user_behavior.csv exploratory

# 创建可视化
/visualize user_behavior.csv user-journey

# 生成分析代码
/generate python user-segmentation

# 创建完整报告
/report user_behavior.csv complete html
```

## 配置

项目使用 Claude Code 的配置系统：
- 子代理定义在 `.claude/agents/`
- 命令存放在 `.claude/commands/`
- 钩子配置在 `.claude/settings.json`

## 关键工作流

1. **数据探索**：上传数据 → 运行探索性分析 → 查看洞察
2. **可视化**：分析数据 → 生成可视化 → 导出图表
3. **报告**：完成分析 → 生成报告 → 分享结论
4. **代码生成**：定义需求 → 生成代码 → 测试实现

## 集成说明

- 支持常见数据格式（CSV、JSON、Excel、SQL）
- 与 Python 数据科学生态集成
- 支持多种可视化库
- 提供用于自动化与质量控制的钩子


## 注意要点

- 详细的分析代码和相关文档需要保存在项目中，可以进一步方便查看具体的分析过程和数据验证结果。
- 报告和文档请尽量用中文
- visualization画图注意中文字体问题！

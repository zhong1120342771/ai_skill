# 用户指南

## 入门

### 首次设置

1. **克隆项目**（如果还没克隆）：
   ```bash
   git clone <repository-url>
   cd claude-data-analysis
   ```

2. **确认 Claude Code 正在运行**：
   ```bash
   /help
   ```

3. **查看可用代理**：
   ```bash
   /agents
   ```

### 基本概念

#### 子代理
处理特定任务的专用 AI 助手：
- **data-explorer**：统计分析与洞察
- **visualization-specialist**：图表与可视化
- **code-generator**：代码生成
- **report-writer**：报告撰写
- **quality-assurance**：数据校验
- **hypothesis-generator**：研究假设

#### 斜杠命令
你输入用于执行操作的命令：
- `/analyze [dataset] [type]`：分析数据
- `/visualize [dataset] [type]`：创建可视化
- `/generate [language] [type]`：生成代码
- `/report [dataset] [format]`：撰写报告
- `/quality [dataset] [action]`：质量检查
- `/hypothesis [dataset] [domain]`：生成假设

#### 钩子
在事件触发时运行的自动化流程：
- 添加文件时的数据校验
- 开始分析时的上下文加载
- 分析过程中的质量检查

## 常见工作流

### 1. 探索性数据分析

```bash
# 从基础探索开始
/analyze your_data.csv exploratory

# 创建可视化
/visualize your_data.csv distribution

# 生成代码做更深入的分析
/generate python statistical-analysis
```

### 2. 完整分析项目

```bash
# 完整分析工作流
/analyze your_data.csv complete
/visualize your_data.csv all
/report your_data.pdf
/generate python machine-learning
/quality your_data.csv validate
```

### 3. 商业智能

```bash
# 销售分析示例
/analyze sales_data.csv statistical
/visualize sales_data.csv trends
/generate sql revenue-report
/report sales_data.csv executive pdf
```

## 数据准备

### 支持的格式
- **CSV**：逗号分隔值
- **JSON**：JavaScript 对象表示法
- **Excel**：.xlsx 文件
- **Parquet**：列式存储格式
- **SQL**：数据库查询

### 数据结构规范
- 使用有意义的列名
- 包含数据类型信息
- 一致地处理缺失值
- 记录数据来源与变换过程

### 数据格式示例

```csv
user_id,timestamp,action,value,revenue
user_001,2024-01-15 09:30:00,click,product_123,0.00
user_001,2024-01-15 09:35:00,purchase,product_123,29.99
```

## 命令参考

### /analyze 命令

**语法**：`/analyze [dataset] [analysis_type]`

**分析类型**：
- `exploratory`：基础数据探索与汇总
- `statistical`：进阶统计分析
- `predictive`：预测建模准备
- `complete`：涵盖所有类型的完整分析

**示例**：
```bash
/analyze user_data.csv exploratory
/analyze sales_data.csv statistical
/analyze customer_data.csv predictive
/analyze financial_data.csv complete
```

### /visualize 命令

**语法**：`/visualize [dataset] [chart_type]`

**图表类型**：
- `all`：综合仪表板
- `trends`：时间序列与趋势分析
- `distribution`：直方图、箱线图、密度图
- `correlation`：相关矩阵与热力图
- `comparison`：柱状图、分组对比
- `custom`：用户指定的自定义可视化

**示例**：
```bash
/visualize user_data.csv all
/visualize sales_data.csv trends
/visualize customer_data.csv distribution
/visualize financial_data.csv custom
```

### /generate 命令

**语法**：`/generate [language] [analysis_type]`

**语言**：
- `python`：Python 数据分析代码
- `r`：R 统计分析
- `sql`：数据库查询
- `javascript`：基于 Web 的可视化

**分析类型**：
- `data-cleaning`：数据预处理与清洗
- `statistical`：统计分析代码
- `visualization`：图表生成
- `machine-learning`：ML 模型训练
- `custom`：自定义分析需求

**示例**：
```bash
/generate python data-cleaning
/generate r statistical
/generate sql reporting
/generate javascript visualization
```

### /report 命令

**语法**：`/report [dataset] [format]`

**报告类型**：
- `summary`：简要概览与关键发现
- `complete`：完整详尽的报告
- `executive`：面向业务的摘要
- `technical`：技术文档

**输出格式**：
- `markdown`：Markdown 格式
- `html`：网页格式
- `pdf`：PDF 文档
- `json`：结构化数据格式

**示例**：
```bash
/report user_data.csv complete markdown
/report sales_data.csv executive pdf
/report customer_data.csv technical json
```

### /quality 命令

**语法**：`/quality [dataset] [action]`

**操作**：
- `check`：基础数据质量评估
- `clean`：清洗数据问题
- `validate`：完整校验
- `monitor`：配置持续监控

**示例**：
```bash
/quality user_data.csv check
/quality sales_data.csv clean
/quality customer_data.csv validate
/quality financial_data.csv monitor
```

### /hypothesis 命令

**语法**：`/hypothesis [dataset] [domain]`

**领域**：
- `user-behavior`：用户行为模式
- `business-impact`：业务表现
- `technical`：技术性能
- `custom`：自定义领域分析

**示例**：
```bash
/hypothesis user_data.csv user-behavior
/hypothesis sales_data.csv business-impact
/hypothesis system_data.csv technical
```

## 处理结果

### 输出文件

生成的文件按目录组织：

```
claude-data-analysis/
├── analysis_reports/    # 生成的报告
├── visualizations/      # 图表
├── generated_code/     # 分析代码
└── data_storage/       # 你的数据文件
```

### 理解报告

报告通常包含：
- **执行摘要**：用业务语言表述的关键发现
- **方法论**：分析思路与假设
- **统计发现**：详细的统计结果
- **可视化**：带说明的图表
- **建议**：可落地的洞察
- **局限性**：数据与方法的约束
- **附录**：技术细节与代码

### 解读可视化

常见图表类型及其含义：
- **折线图**：随时间变化的趋势
- **柱状图**：类别之间的对比
- **散点图**：变量之间的关系
- **热力图**：相关性与强度模式
- **箱线图**：分布与离群值
- **直方图**：频率分布

## 故障排查

### 常见问题

#### 数据加载问题
**问题**："无法读取数据文件"
**解决方案**：
- 检查文件是否在 `data_storage/` 目录
- 确认文件格式受支持
- 确保文件有读取权限
- 检查编码是否正确（UTF-8）

#### 命令找不到
**问题**："命令未识别"
**解决方案**：
- 确认你处于项目目录中
- 检查命令拼写
- 用 `/help` 查看可用命令
- 确保 Claude Code 配置正确

#### 分析耗时过长
**问题**：分析很慢或卡住
**解决方案**：
- 检查数据集大小（大文件耗时更久）
- 监控系统资源
- 初步分析时考虑数据采样
- 把分析拆成更小的块

#### 结果质量差
**问题**：分析结果不合理
**解决方案**：
- 检查数据质量与格式
- 核对分析参数
- 尝试不同的分析类型
- 复查数据准备步骤

### 获取帮助

#### 内置帮助
```bash
/help              # 显示所有可用命令
/help [command]    # 获取特定命令的帮助
/agents            # 列出可用代理
/status            # 检查系统状态
```

#### 文档
- 主 README.md：项目概览
- examples/ 目录：使用示例
- docs/ 目录：详细文档
- CLAUDE.md：Claude Code 专项指引

#### 社区支持
- 查看项目的 issue 和讨论
- 参考已有的故障排查指南
- 提交带详细信息的 bug 报告
- 用可复现的示例提问

## 最佳实践

### 数据准备
- **先清洗数据**：去重、处理缺失值
- **记录一切**：记下数据来源与变换过程
- **使用一致格式**：统一日期格式、单位
- **校验数据**：检查离群值与错误

### 分析思路
- **从简单开始**：先做探索性分析
- **迭代**：根据发现不断打磨分析
- **校验**：交叉核对重要结果
- **记录**：保留完整的分析笔记

### 与代理协作
- **具体明确**：提供清晰的需求
- **善用上下文**：补充相关背景信息
- **复核结果**：始终复查和校验输出
- **给出反馈**：帮助提升代理表现

### 代码生成
- **测试生成的代码**：投产前务必测试
- **按需定制**：根据需要修改生成的代码
- **读懂代码**：不要使用看不懂的代码
- **版本控制**：跟踪代码变更

## 高级功能

### 自定义代理
创建你自己的专用代理：
1. 在 `.claude/agents/` 中创建新的代理文件
2. 定义具体的专长与能力
3. 配置合适的工具权限
4. 用相关场景测试

### 自定义命令
添加自定义命令：
1. 在 `.claude/commands/` 中创建命令文件
2. 定义命令参数与行为
3. 设置合适的工具权限
4. 补充完整的文档

### 自动化钩子
配置自动化工作流：
1. 在 `.claude/settings.json` 中配置钩子
2. 编写自动化脚本
3. 用不同场景测试
4. 监控性能与结果

## 集成

### 与现有工具
- **Jupyter Notebooks**：导出代码供 notebook 使用
- **商业智能工具**：为 BI 平台生成 SQL
- **Web 应用**：创建交互式仪表板
- **数据管道**：与 ETL 流程集成

### 与团队工作流
- **版本控制**：跟踪分析与代码变更
- **协作**：共享代理与命令
- **文档**：维护一致的文档
- **质量保证**：落实团队级标准

---

本指南完整介绍了 Claude 数据分析助手的使用方法。从基础工作流开始，随着对平台越来越熟悉，再逐步探索更高级的功能。

# 快速上手示例：用户行为分析

本示例演示如何用 Claude 数据分析助手从头到尾完成一次用户行为数据分析。

## 📋 前置条件

请确认你已具备：
- 安装并配置好的 Claude Code
- 已配好示例数据的本项目
- 对数据分析概念的基本了解

## 🚀 分步分析

### 第 1 步：数据准备
你的数据已经备好在 `data_storage/user_behavior_sample.csv`

```bash
# 查看有哪些可用数据
ls -la data_storage/
```

### 第 2 步：探索性分析
从基础数据探索开始：

```bash
/analyze user_behavior_sample.csv exploratory
```

**预期输出：**
系统会自动：
- 加载并检查数据结构
- 生成汇总统计
- 识别数据质量问题
- 给出初步洞察

### 第 3 步：创建可视化
生成完整的可视化：

```bash
/visualize user_behavior_sample.csv all
```

**预期输出：**
- 含多种图表类型的交互式仪表板
- 分布分析
- 相关性热力图
- 时间序列趋势
- 用户行为模式

### 第 4 步：生成分析代码
创建可复用的分析代码：

```bash
/generate python user-segmentation
```

**预期输出：**
- 用户分群分析的 Python 脚本
- 数据预处理工具函数
- 可视化代码
- 文档与示例

### 第 5 步：生成完整报告
创建一份完整的分析报告：

```bash
/report user_behavior_sample.csv complete markdown
```

**预期输出：**
- 执行摘要
- 详细统计发现
- 关键洞察与建议
- 可视化说明
- 技术附录

## 📊 理解数据

### 示例数据结构
`user_behavior_sample.csv` 包含：

| 列 | 说明 | 类型 |
|--------|-------------|------|
| user_id | 唯一用户标识 | String |
| session_id | 会话标识 | String |
| timestamp | 操作时间戳 | DateTime |
| action | 用户操作类型 | String |
| page_url | 访问的页面 | String |
| device_type | 使用的设备 | String |
| location | 地理位置 | String |
| revenue | 产生的收入 | Float |

### 操作类型
- `page_view`：用户浏览了页面
- `click`：用户点击了某处
- `purchase`：用户完成了购买

### 设备类型
- `desktop`：桌面电脑
- `mobile`：移动设备
- `tablet`：平板设备

## 🎯 预期分析结果

### 关键指标
- **总用户数**：独立用户的数量
- **会话数**：会话总数
- **转化率**：以购买结束的会话占比
- **平均收入**：每次会话的平均收入
- **设备分布**：按设备类型的使用情况

### 待发现的洞察
1. **用户行为模式**：用户如何在站内浏览
2. **设备偏好**：哪些设备最受欢迎
3. **转化模式**：什么因素促成购买
4. **地域趋势**：不同地区的行为差异
5. **时间模式**：用户在什么时段最活跃

## 🔍 进阶分析

### 自定义分析
若需更具体的分析，可尝试：

```bash
# 统计分析
/analyze user_behavior_sample.csv statistical

# 预测性分析
/analyze user_behavior_sample.csv predictive

# 质量检查
/quality user_behavior_sample.csv clean

# 生成假设
/hypothesis user_behavior_sample.csv user-engagement
```

### 自定义代码生成
为特定任务生成代码：

```bash
# 数据清洗代码
/generate python data-cleaning

# 统计分析代码
/generate r statistical

# SQL 查询
/generate sql reporting

# 机器学习
/generate python machine-learning
```

## 📈 示例工作流命令

### 完整分析工作流
```bash
# 1. 探索性分析
/analyze user_behavior_sample.csv exploratory

# 2. 创建可视化
/visualize user_behavior_sample.csv trends

# 3. 生成代码
/generate python user-segmentation

# 4. 创建报告
/report user_behavior_sample.csv complete html

# 5. 质量校验
/quality user_behavior_sample.csv validate
```

### 快速分析
```bash
# 快速概览
/analyze user_behavior_sample.csv exploratory

# 快速可视化
/visualize user_behavior_sample.csv distribution

# 快速报告
/report user_behavior_sample.csv summary markdown
```

## 🎨 预期产出

### 生成的文件
```
visualizations/
├── dashboard_user_behavior_sample.html  # 交互式仪表板
├── summary_user_behavior_sample.png      # 汇总图表
└── detailed_user_behavior_sample.pdf     # 详细分析

generated_code/
├── python_user_segmentation.py          # 分析代码
├── user_segmentation_utils.py           # 工具函数
└── requirements_python.txt               # 依赖

analysis_reports/
├── complete_analysis_user_behavior_sample.md  # 完整报告
└── summary_user_behavior_sample.md           # 摘要报告
```

### 关键发现
分析应当揭示：
- **用户参与度**：用户如何与平台互动
- **转化模式**：什么驱动了购买
- **设备洞察**：哪些设备表现最好
- **地域趋势**：基于地区的差异
- **收入模式**：收入产生方面的洞察

## 🛠️ 定制

### 修改分析参数
你可以通过以下方式定制分析：
- 指定不同的分析类型
- 请求特定的图表类型
- 为代码生成设置自定义参数
- 选择不同的输出格式

### 扩展功能
扩展分析的方式：
1. 把你自己的数据文件加入 `data_storage/`
2. 修改 `.claude/agents/` 中的代理配置
3. 在 `.claude/commands` 中创建自定义命令
4. 在 `.claude/settings.json` 中添加自动化钩子

## 🔍 故障排查

### 常见问题
1. **数据加载问题**：确保数据文件为 CSV 格式
2. **命令找不到**：确认你处于项目目录中
3. **权限问题**：检查数据文件的访问权限
4. **内存问题**：大数据集可能需要分块处理

### 获取帮助
- 用 `/help` 查看可用命令
- 查看主 README.md 了解项目概览
- 查阅代理配置了解可用工具

---

**下一步**：完成本示例后，试着用你自己的数据，或探索更进阶的分析类型！

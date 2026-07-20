---
allowed-tools: Task, Read, Write, Bash, Grep, Glob
argument-hint: [dataset] [analysis_type]
description: 对指定数据集执行完整的数据分析
---

# 数据分析命令

使用 data-explorer 子代理，对数据集 `$1` 按分析类型 `$2` 执行数据分析。
## Context
- 数据集位置: @data_storage/$1
- 分析类型: $2 (exploratory, statistical, predictive, complete)
- 当前工作目录: !`pwd`
- 可用可视化库: matplotlib、seaborn、plotly
- Python 数据科学栈: pandas、numpy、scipy

## Your Task

使用 data-explorer 子代理执行完整的数据分析：

### 1. 数据评估
- 加载并检查数据集结构
- 检查数据类型、缺失值和重复
- 生成初步汇总统计
- 识别数据质量问题

### 2. 统计分析
- 执行描述性统计分析
- 计算变量之间的相关性
- 识别离群值与异常
- 进行合适的统计检验

### 3. 模式发现
- 识别数据中的趋势与模式
- 发现变量之间的关系
- 检测季节性模式或周期
- 在数据中找出聚类或分群

### 4. 生成洞察
- 从分析中提取关键发现
- 识别可落地的洞察
- 提出值得深入调查的方向
- 推荐可视化思路

## 分析类型

### 探索性分析
- 基础数据理解
- 汇总统计
- 数据质量评估
- 初步模式识别

### 统计分析
- 进阶统计检验
- 相关性与回归分析
- 假设检验
- 置信区间

### 预测性分析
- 特征重要性分析
- 预测建模准备
- 变量关系
- 模型推荐

### 完整分析
- 以上全部，外加
- 完整报告生成
- 可视化建议
- 下一步规划

## 预期输出

### 分析报告
创建一份完整的分析报告，包含：
- **执行摘要**：用通俗语言表述关键发现
- **数据概览**：数据集特征与质量
- **统计发现**：详细的统计分析
- **关键洞察**：可落地的发现
- **建议**：更深入分析的下一步
- **局限性**：数据与方法的约束

### 文件输出
- `analysis_reports/analysis_summary_$1.md` - 详细分析报告
- `analysis_reports/statistical_summary_$1.csv` - 统计汇总表
- `analysis_reports/data_quality_$1.json` - 数据质量评估

## 质量保证
- 校验所有统计计算
- 交叉核对重要发现
- 记录所有假设与局限性
- 确保分析可复现

## 使用示例
```bash
/analyze user_behavior.csv exploratory
/analyze sales_data.csv statistical
/analyze customer_data.csv predictive
/analyze financial_data.csv complete
```

## 注意事项
- 数据集应位于 data_storage/ 目录
- 分析结果将保存到 analysis_reports/ 目录
- 用 Task 工具委派给 data-explorer 子代理
- 可考虑后续配合 /visualize 命令生成图表

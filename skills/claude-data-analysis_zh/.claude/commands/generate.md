---
allowed-tools: Task, Read, Write, Bash, Grep, Glob
argument-hint: [language] [analysis_type]
description: 按指定语言和分析类型生成分析代码
---

# 代码生成命令

使用 code-generator 子代理，用 `$1` 语言为 `$2` 分析类型生成数据分析代码。

## Context
- 编程语言: $1 (python, r, sql, javascript)
- 分析类型: $2 (data-cleaning, statistical, visualization, machine-learning, custom)
- 当前工作目录: !`pwd`
- 输出目录: ./generated_code/
- 基于语言的可用库与框架

## Your Task

使用 code-generator 子代理创建高质量、可直接投产的分析代码：

### 1. 需求分析
- 理解具体的分析需求
- 识别合适的库与框架
- 考虑数据类型与数据量
- 为可扩展性与性能做规划

### 2. 代码架构
- 设计模块化、可复用的代码结构
- 实现恰当的错误处理
- 包含完整的文档
- 在合适处添加单元测试

### 3. 实现
- 编写整洁、高效、易维护的代码
- 包含恰当的数据校验
- 实现该语言的最佳实践
- 添加日志与调试能力

### 4. 文档
- 创建完整的代码文档
- 包含使用示例与教程
- 提供故障排查指引
- 记录依赖与环境要求

## 语言支持

### Python
- **库**：pandas、numpy、matplotlib、seaborn、scikit-learn、plotly
- **用例**：数据清洗、统计分析、机器学习、可视化
- **输出**：Jupyter notebook、Python 脚本、模块

### R
- **库**：tidyverse、ggplot2、dplyr、caret、shiny
- **用例**：统计分析、数据可视化、生物信息学
- **输出**：R 脚本、R Markdown 文档、Shiny 应用

### SQL
- **方言**：PostgreSQL、MySQL、SQLite、BigQuery、Redshift
- **用例**：数据提取、聚合、报表、ETL
- **输出**：SQL 查询、存储过程、视图

### JavaScript
- **库**：D3.js、Plotly.js、Chart.js、TensorFlow.js
- **用例**：Web 可视化、交互式仪表板、客户端 ML
- **输出**：HTML/JS 文件、Node.js 脚本、Web 应用

## 分析类型

### 数据清洗（Data Cleaning）
- 缺失值处理
- 离群值检测与处理
- 数据类型转换
- 归一化与标准化
- 特征工程

### 统计分析（Statistical Analysis）
- 描述性统计
- 假设检验
- 相关性与回归
- 时间序列分析
- ANOVA 与 t 检验

### 可视化（Visualization）
- 图表生成代码
- 仪表板实现
- 交互式可视化
- 自定义图表类型
- 动画与过渡

### 机器学习（Machine Learning）
- 数据预处理
- 模型训练与评估
- 特征选择
- 超参数调优
- 模型部署

### 自定义（Custom）
- 用户专属需求
- 领域专属分析
- 与现有系统集成
- 性能优化
- 自定义算法

## 预期输出

### 代码文件
- `generated_code/$1_$2_analysis.py` - 主分析脚本
- `generated_code/$1_$2_utils.py` - 工具函数
- `generated_code/$1_$2_config.py` - 配置设置
- `generated_code/$1_$2_test.py` - 单元测试
- `generated_code/requirements_$1.txt` - 依赖

### 文档
- **README.md**：使用说明与示例
- **API 文档**：函数与类的文档
- **教程**：分步指南
- **故障排查**：常见问题与解决方案

## 代码质量标准

### Python 代码标准
```python
"""
High-quality Python code template for data analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from pathlib import Path

class DataAnalyzer:
    """
    Data analysis class with comprehensive functionality

    Args:
        data_path (str): Path to input data file
        config (Dict): Configuration parameters

    Attributes:
        data (pd.DataFrame): Loaded dataset
        config (Dict): Configuration settings
        logger (logging.Logger): Logger instance
    """

    def __init__(self, data_path: str, config: Dict = None):
        self.data_path = Path(data_path)
        self.config = config or {}
        self.data = None
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Set up logging configuration"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        return logger

    def load_data(self) -> pd.DataFrame:
        """
        Load data from file with error handling

        Returns:
            pd.DataFrame: Loaded dataset

        Raises:
            FileNotFoundError: If data file doesn't exist
            ValueError: If data format is invalid
        """
        try:
            # Implementation with proper error handling
            pass
        except Exception as e:
            self.logger.error(f"Error loading data: {e}")
            raise
```

### SQL 代码标准
```sql
-- High-quality SQL template for data analysis
-- Include proper comments and documentation

-- Analysis: Customer Segmentation
-- Purpose: Identify customer segments based on purchase behavior
-- Dependencies: customers, orders, order_items tables

WITH customer_summary AS (
    -- Calculate customer-level metrics
    SELECT
        c.customer_id,
        c.customer_name,
        c.signup_date,
        COUNT(DISTINCT o.order_id) AS total_orders,
        SUM(oi.quantity * oi.unit_price) AS total_revenue,
        AVG(oi.quantity * oi.unit_price) AS avg_order_value,
        MAX(o.order_date) AS last_order_date
    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
    LEFT JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY c.customer_id, c.customer_name, c.signup_date
),

segment_calculation AS (
    -- Calculate RFM metrics and segments
    SELECT
        customer_id,
        customer_name,
        total_orders,
        total_revenue,
        avg_order_value,
        -- Recency: days since last order
        DATEDIFF(CURRENT_DATE, last_order_date) AS recency_days,
        -- Frequency: total orders
        total_orders AS frequency,
        -- Monetary: total revenue
        total_revenue AS monetary,
        -- Segment assignment
        CASE
            WHEN total_revenue > 10000 THEN 'High Value'
            WHEN total_revenue > 5000 THEN 'Medium Value'
            WHEN total_revenue > 1000 THEN 'Low Value'
            ELSE 'New Customer'
        END AS customer_segment
    FROM customer_summary
    WHERE last_order_date IS NOT NULL
)

-- Final result with segment insights
SELECT
    customer_segment,
    COUNT(customer_id) AS customer_count,
    AVG(total_orders) AS avg_orders,
    AVG(total_revenue) AS avg_revenue,
    AVG(recency_days) AS avg_recency,
    ROUND(COUNT(customer_id) * 100.0 / SUM(COUNT(customer_id)) OVER (), 2) AS percentage
FROM segment_calculation
GROUP BY customer_segment
ORDER BY total_revenue DESC;
```

## 质量保证

### 代码评审清单
- [ ] 代码遵循该语言的风格指南
- [ ] 恰当的错误处理与校验
- [ ] 完整的文档与注释
- [ ] 在合适处包含单元测试
- [ ] 已考虑性能因素
- [ ] 遵循安全最佳实践
- [ ] 依赖清晰列明

### 测试策略
- **单元测试**：测试单个函数与方法
- **集成测试**：测试数据流与依赖
- **性能测试**：用大数据集验证
- **安全测试**：检查漏洞

## 使用示例
```bash
/generate python data-cleaning
/generate r statistical
/generate sql reporting
/generate javascript visualization
/generate python machine-learning
/generate custom custom-analysis
```

## 最佳实践

### 通用原则
- **DRY**：不要重复自己——编写可复用的代码
- **KISS**：保持简单——避免不必要的复杂
- **YAGNI**：你不会需要它——避免过度设计
- **SOLID**：遵循 SOLID 原则做面向对象设计

### 文档标准
- **Docstring**：完整的函数文档
- **注释**：解释复杂逻辑与算法
- **README**：项目概览与安装说明
- **示例**：提供使用示例与教程

### 版本控制
- 包含 .gitignore 文件
- 记录版本管理策略
- 包含变更日志
- 恰当地为发布打标签

## 注意事项
- 生成的代码将保存到 generated_code/ 目录
- 代码包含完整的文档与示例
- 用 Task 工具委派给 code-generator 子代理
- 投产前请评审并测试生成的代码
- 可考虑先用 /analyze 命令理解数据需求

## 与其他命令的配合
- 在 `/analyze` 之后使用，理解数据需求
- 与 `/visualize` 配合，生成可视化代码
- 之后用 `/quality` 做代码质量校验

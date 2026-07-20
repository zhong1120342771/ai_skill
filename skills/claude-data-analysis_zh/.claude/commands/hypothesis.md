---
allowed-tools: Task, Read, Write, Bash, Grep, Glob
argument-hint: [dataset] [domain]
description: 基于数据模式生成研究假设与实验设计
---

# 假设生成命令

使用 hypothesis-generator 子代理，为数据集 `$1` 在领域 `$2` 中生成研究假设与实验设计。

## Context
- 数据集位置: @data_storage/$1
- 分析领域: $2 (user-behavior, business-impact, technical-performance, custom)
- 当前工作目录: !`pwd`
- 输出目录: ./hypothesis_reports/
- 可用的研究方法与实验设计
- 统计分析能力

## Your Task

使用 hypothesis-generator 子代理创建严谨、可检验的假设：

### 1. 模式分析
- 识别显著的相关性与关系
- 检测时序模式与趋势
- 在数据中发现聚类与分群
- 识别异常与不寻常的模式

### 2. 假设构建
- 创建清晰、可检验的假设
- 定义原假设与备择假设
- 明确变量及其关系
- 设定可度量的结果与成功标准

### 3. 实验设计
- 选择合适的研究方法
- 设计检验假设的实验思路
- 确定样本量与功效要求
- 规划数据收集与测量流程

### 4. 验证策略
- 定义统计检验思路
- 设立成功标准与指标
- 规划重复与核验
- 考虑其他解释与方案

## 分析领域

### 用户行为（User Behavior）
- **参与模式**：用户互动与参与度假设
- **转化优化**：转化率与漏斗分析假设
- **留存与流失**：用户留存与流失预测假设
- **分群**：用户行为分群假设
- **路径分析**：用户旅程与路径分析假设

### 业务影响（Business Impact）
- **收入优化**：收入产生与增长假设
- **成本削减**：成本效率与优化假设
- **市场扩张**：市场增长与扩张假设
- **客户满意度**：客户体验与满意度假设
- **运营效率**：流程改进与效率假设

### 技术性能（Technical Performance）
- **系统优化**：性能与可扩展性假设
- **可靠性**：系统稳定性与可靠性假设
- **安全性**：安全漏洞与防护假设
- **用户体验**：技术 UX 与性能假设
- **集成**：系统集成与兼容性假设

### 自定义（Custom）
- **领域专属**：自定义领域专属假设
- **研究导向**：学术与研究假设
- **实验性**：新颖的实验假设
- **预测性**：预测建模假设

## 假设类型

### 描述性假设
描述数据中的模式与关系，不推断因果。

**示例**："用户参与时长与转化率之间存在正相关。"

### 解释性假设
解释潜在机制与因果关系。

**示例**："更长的用户参与时长会带来更高的转化率，因为产品理解度提升了。"

### 预测性假设
基于当前模式预测未来结果。

**示例**："参与时长 > 5 分钟的用户，在 30 天内转化的可能性高出 3 倍。"

### 处方性假设
推荐最优行动与干预。

**示例**："实施个性化推荐将使用户参与度提升 25%。"

## 研究方法

### 实验设计
- **A/B 测试**：随机对照实验
- **多变量测试**：多变量实验
- **纵向研究**：时间序列分析
- **横截面研究**：某一时点的分析
- **准实验**：非随机化设计
- **案例研究**：对特定案例的深入分析

### 统计方法
- **假设检验**：统计显著性检验
- **置信区间**：效应量的估计
- **贝叶斯方法**：贝叶斯假设检验
- **功效分析**：统计功效计算
- **效应量度量**：量化关系强度

### 验证方法
- **交叉验证**：模型验证技术
- **自助法（Bootstrapping）**：重采样验证
- **敏感性分析**：测试稳健性
- **重复研究**：独立核验
- **元分析**：多项研究的综合

## 预期输出

### 假设文档
- `hypothesis_reports/$1_$2_hypotheses.md` - 假设文档
- `hypothesis_reports/$1_$2_experimental_design.md` - 实验设计
- `hypothesis_reports/$1_$2_validation_plan.md` - 验证策略
- `hypothesis_reports/$1_$2_research_proposal.md` - 研究方案

### 假设结构
每个假设包含：
- **清晰陈述**：可检验的假设陈述
- **理据**：论证与理论基础
- **变量**：自变量与因变量
- **方法论**：拟定的检验思路
- **成功标准**：验证用的指标
- **预期结果**：预测的结果
- **替代解释**：其他可能的解释

### 实验设计
完整的实验设计，包含：
- **研究问题**：清晰的研究问题
- **方法论**：详细的实验思路
- **样本量**：功效分析与论证
- **变量**：测量与操作化定义
- **流程**：分步实验过程
- **分析计划**：统计分析思路
- **时间线**：项目时间表与里程碑
- **资源**：所需资源与预算

## 工作流程

### 1. 数据模式发现
```python
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

def discover_research_patterns(data):
    """Discover patterns that suggest research hypotheses"""
    patterns = {}

    # Correlation analysis
    correlation_matrix = data.corr()
    strong_correlations = correlation_matrix[(correlation_matrix.abs() > 0.5) & (correlation_matrix.abs() < 1.0)]
    patterns['strong_correlations'] = strong_correlations

    # Trend analysis
    patterns['trends'] = analyze_temporal_trends(data)

    # Cluster analysis
    patterns['clusters'] = perform_cluster_analysis(data)

    # Statistical anomalies
    patterns['anomalies'] = detect_statistical_anomalies(data)

    return patterns
```

### 2. 假设生成
```python
def generate_domain_hypotheses(patterns, domain):
    """Generate hypotheses based on domain-specific patterns"""
    hypotheses = []

    if domain == 'user-behavior':
        hypotheses.extend(generate_user_behavior_hypotheses(patterns))
    elif domain == 'business-impact':
        hypotheses.extend(generate_business_hypotheses(patterns))
    elif domain == 'technical-performance':
        hypotheses.extend(generate_technical_hypotheses(patterns))
    else:
        hypotheses.extend(generate_custom_hypotheses(patterns, domain))

    return hypotheses

def generate_user_behavior_hypotheses(patterns):
    """Generate user behavior specific hypotheses"""
    hypotheses = []

    # Engagement hypotheses
    if 'engagement_time' in patterns['trends']:
        hypothesis = {
            'type': 'predictive',
            'statement': 'Users with higher engagement time show increased conversion rates',
            'null_hypothesis': 'H₀: Engagement time has no effect on conversion rates',
            'alternative_hypothesis': 'H₁: Higher engagement time leads to increased conversion rates',
            'variables': {
                'independent': 'engagement_time',
                'dependent': 'conversion_rate'
            },
            'methodology': 'A/B testing with engagement time manipulation'
        }
        hypotheses.append(hypothesis)

    return hypotheses
```

### 3. 实验设计
```python
def design_experiment(hypothesis, data_characteristics):
    """Design experimental approach to test hypothesis"""
    experiment = {
        'hypothesis': hypothesis,
        'research_design': select_research_design(hypothesis),
        'sample_size': calculate_sample_size(hypothesis, data_characteristics),
        'variables': operationalize_variables(hypothesis),
        'measurement_protocol': define_measurements(hypothesis),
        'data_collection': plan_data_collection(hypothesis),
        'analysis_plan': define_analysis_plan(hypothesis),
        'quality_controls': define_quality_controls(hypothesis),
        'timeline': estimate_timeline(hypothesis),
        'resources': estimate_resources(hypothesis),
        'risks': identify_risks(hypothesis),
        'mitigation': develop_mitigation_strategies(hypothesis)
    }

    return experiment
```

### 4. 验证策略
```python
def create_validation_strategy(hypothesis, experiment):
    """Create comprehensive validation strategy"""
    validation = {
        'statistical_tests': select_statistical_tests(hypothesis),
        'success_criteria': define_success_criteria(hypothesis),
        'confidence_level': 0.95,  # 95% confidence level
        'power_analysis': {
            'target_power': 0.80,
            'effect_size': estimate_effect_size(hypothesis),
            'sample_size': experiment['sample_size']
        },
        'validation_timeline': plan_validation_timeline(experiment),
        'replication_plan': design_replication_strategy(hypothesis),
        'alternative_approaches': generate_alternative_methods(hypothesis),
        'quality_assurance': define_quality_measures(hypothesis)
    }

    return validation
```

## 质量标准

### 假设质量
- **可检验性**：必须可以经验性地检验
- **可证伪性**：必须存在能证明其错误的方法
- **具体性**：对关系给出清晰预测
- **可度量性**：变量必须可量化
- **相关性**：回答有意义的问题
- **理论基础**：基于严谨的推理

### 实验严谨
- **对照**：恰当的对照条件
- **随机化**：恰当的随机分配
- **盲法**：按需单盲或双盲
- **可重复**：为可复现而设计
- **统计功效**：足够的样本量
- **内部效度**：尽量减少混杂变量
- **外部效度**：可推广到目标总体

### 方法论严谨
- **方法得当**：合适的研究方法
- **测量有效**：可靠且有效的度量工具
- **统计有效**：合适的统计检验
- **伦理考量**：合乎伦理的研究实践
- **可行性**：实际可落地的考量

## 最佳实践

### 假设开发
- **数据驱动**：基于观察到的模式提出假设
- **理论支撑**：用相关理论支撑
- **清晰表述**：无歧义的假设陈述
- **变量定义**：清晰的操作化定义
- **范围管理**：可控的范围与复杂度

### 实验设计
- **对齐研究问题**：设计直接回应研究问题
- **方法选择**：选择合适的研究方法
- **样本量论证**：用功效分析确定样本量
- **对照组**：恰当的对照条件
- **混杂变量**：识别并控制混杂因素

### 验证规划
- **成功标准**：验证假设的明确标准
- **统计规划**：合适的统计检验与方法
- **多种思路**：考虑多种验证思路
- **重复规划**：规划独立核验
- **风险评估**：识别并缓解风险

## 使用示例
```bash
/hypothesis user_behavior.csv user-behavior
/hypothesis sales_data.csv business-impact
/hypothesis system_metrics.csv technical-performance
/hypothesis research_data.csv custom
```

## 与其他命令的配合
- 在 `/analyze` 之后使用，基于数据洞察提出假设
- 与 `/visualize` 配合，可视化支撑假设的模式
- 之后用 `/generate` 创建实验代码
- 之前用 `/quality` 确保假设数据质量

## 注意事项
- 数据集应位于 data_storage/ 目录
- 假设报告将保存到 hypothesis_reports/ 目录
- 用 Task 工具委派给 hypothesis-generator 子代理
- 同时考虑统计显著性与实际显著性
- 规划发现结果的重复与核验
- 记录假设的假设条件与局限性

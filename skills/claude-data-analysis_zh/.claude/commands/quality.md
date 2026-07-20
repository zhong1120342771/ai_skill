---
allowed-tools: Task, Read, Write, Bash, Grep, Glob
argument-hint: [dataset] [action]
description: 对指定数据集执行数据质量校验、检查与监控
---

# 数据质量命令

使用 quality-assurance 子代理，对数据集 `$1` 按操作 `$2` 执行数据质量相关操作。

## Context
- 数据集位置: @data_storage/$1
- 质量操作: $2 (check, clean, validate, monitor, profile)
- 当前工作目录: !`pwd`
- 输出目录: ./quality_reports/
- 质量规则与校验阈值
- 可用的质量指标与 KPI

## Your Task

使用 quality-assurance 子代理执行完整的数据质量操作：

### 1. 质量评估
- 分析数据完整性与准确性
- 检查数据一致性与有效性
- 评估数据唯一性与及时性
- 评估整体数据完整约束

### 2. 问题识别
- 检测缺失值与数据缺口
- 识别离群值与异常
- 找出重复记录与不一致
- 发现格式违规与数据类型问题

### 3. 质量改进
- 实施数据清洗流程
- 应用数据校验规则
- 执行数据变换操作
- 进行数据标准化

### 4. 监控与报告
- 生成质量指标与 KPI
- 创建质量评估报告
- 配置持续质量监控
- 提供质量改进建议

## 质量操作

### Check（检查）
执行基础数据质量评估：
- 完整性分析
- 基础准确性校验
- 简单一致性检查
- 汇总质量指标

### Clean（清洗）
执行数据清洗操作：
- 移除重复记录
- 处理缺失值
- 修正格式违规
- 标准化数据格式

### Validate（校验）
完整数据校验：
- 统计校验
- 业务规则校验
- 跨字段校验
- 参照完整性检查

### Monitor（监控）
配置质量监控：
- 持续质量跟踪
- 告警阈值配置
- 质量趋势分析
- 性能指标监控

### Profile（画像）
生成完整数据画像：
- 详细数据统计
- 分布分析
- 关系分析
- 数据血缘记录

## 质量维度

### 完整性（Completeness）
- **缺失值分析**：识别并量化缺失数据
- **必填字段校验**：检查必填字段是否齐备
- **记录完整性**：评估单条记录的完整程度
- **数据覆盖**：评估对预期数据范围的覆盖

### 准确性（Accuracy）
- **统计校验**：核验统计属性
- **业务规则校验**：对照业务约束检查
- **范围校验**：确保取值在预期范围内
- **格式校验**：核验数据格式正确

### 一致性（Consistency）
- **跨字段校验**：检查字段间的逻辑一致性
- **时序一致性**：校验基于时间的一致性
- **参照完整性**：检查关系一致性
- **格式一致性**：确保格式统一

### 及时性（Timeliness）
- **数据时效**：评估数据的新旧程度
- **更新频率**：评估数据刷新速率
- **延迟分析**：度量数据处理延迟
- **新鲜度指标**：跟踪数据的年龄与相关性

### 唯一性（Uniqueness）
- **重复检测**：识别并消除重复记录
- **主键校验**：核验唯一标识
- **记录唯一性**：评估整体唯一性
- **关系唯一性**：检查唯一关系

### 有效性（Validity）
- **数据类型校验**：核验数据类型正确
- **域校验**：对照允许的取值域检查
- **模式校验**：对照预期模式校验
- **约束校验**：检查数据库与业务约束

## 预期输出

### 质量报告
- `quality_reports/$1_quality_check.json` - 质量评估结果
- `quality_reports/$1_data_profile.json` - 完整数据画像
- `quality_reports/$1_validation_report.md` - 详细校验报告
- `quality_reports/$1_monitoring_config.json` - 监控配置

### 质量指标
- **整体质量得分**：综合质量指标（0-100）
- **维度得分**：各质量维度的得分
- **问题计数**：质量问题的数量与严重程度
- **改进指标**：质量改进跟踪

### 数据输出
- **清洗后数据**：经质量改进的数据集版本
- **校验日志**：详细校验结果
- **错误报告**：具体的错误描述与位置
- **建议**：可落地的改进建议

## 工作流程

### 1. 数据加载与画像
```python
import pandas as pd
import numpy as np
from scipy import stats

def load_and_profile_data(dataset_path):
    """Load dataset and create initial profile"""
    data = pd.read_csv(dataset_path)

    profile = {
        'basic_info': {
            'shape': data.shape,
            'columns': list(data.columns),
            'data_types': data.dtypes.to_dict(),
            'memory_usage': data.memory_usage(deep=True).sum()
        },
        'quality_metrics': {
            'completeness': calculate_completeness(data),
            'uniqueness': calculate_uniqueness(data),
            'consistency': calculate_consistency(data)
        }
    }

    return data, profile
```

### 2. 质量评估
```python
def comprehensive_quality_assessment(data):
    """Perform comprehensive data quality assessment"""
    assessment = {
        'completeness': assess_completeness(data),
        'accuracy': assess_accuracy(data),
        'consistency': assess_consistency(data),
        'timeliness': assess_timeliness(data),
        'uniqueness': assess_uniqueness(data),
        'validity': assess_validity(data)
    }

    # Calculate overall quality score
    dimension_scores = [assessment[dim]['score'] for dim in assessment]
    overall_score = np.mean(dimension_scores)

    assessment['overall_score'] = overall_score
    assessment['quality_grade'] = assign_quality_grade(overall_score)

    return assessment
```

### 3. 数据清洗
```python
def clean_data(data, quality_issues):
    """Clean data based on identified quality issues"""
    cleaned_data = data.copy()

    # Handle missing values
    if quality_issues['completeness']['missing_values']:
        cleaned_data = handle_missing_values(cleaned_data, quality_issues['completeness'])

    # Remove duplicates
    if quality_issues['uniqueness']['duplicates'] > 0:
        cleaned_data = remove_duplicates(cleaned_data)

    # Fix format issues
    if quality_issues['validity']['format_issues']:
        cleaned_data = fix_format_issues(cleaned_data, quality_issues['validity'])

    # Apply business rules
    cleaned_data = apply_business_rules(cleaned_data)

    return cleaned_data
```

### 4. 监控配置
```python
def setup_quality_monitoring(data, monitoring_config):
    """Set up ongoing quality monitoring"""
    monitoring_plan = {
        'data_source': data,
        'frequency': monitoring_config['frequency'],
        'metrics': define_quality_metrics(),
        'thresholds': define_quality_thresholds(),
        'alerts': define_alert_rules(),
        'reporting': define_reporting_schedule()
    }

    return monitoring_plan
```

## 质量阈值与标准

### 质量得分解读
- **90-100**：优秀 - 高质量数据，适合关键分析
- **80-89**：良好 - 可靠数据，存在小问题
- **70-79**：一般 - 可用数据，有一些局限
- **60-69**：较差 - 数据需要大量清洗
- **60 以下**：不可接受 - 数据不适合分析

### 各维度阈值
- **完整性**：关键字段 ≥ 95%，其他字段 ≥ 85%
- **准确性**：校验成功率 ≥ 98%
- **一致性**：相关字段间一致性 ≥ 95%
- **及时性**：实时需求下数据年龄 ≤ 24 小时
- **唯一性**：关键字段唯一记录 ≥ 99%
- **有效性**：格式合规 ≥ 97%

## 最佳实践

### 质量管理
- **预防优于检测**：聚焦于预防质量问题
- **持续监控**：实现持续的质量跟踪
- **根因分析**：解决质量问题的深层成因
- **标准化**：使用一致的质量标准与流程
- **文档**：完整记录质量规则与流程

### 校验设计
- **全面覆盖**：校验所有关键数据元素
- **基于风险**：优先处理高影响数据元素
- **统计严谨**：使用合适的统计方法
- **业务对齐**：让校验与业务需求对齐
- **性能考量**：优化校验效率

### 问题管理
- **优先级排序**：按业务影响处理问题
- **系统化解决**：使用结构化的问题解决方法
- **预防行动**：落实防止复发的措施
- **干系人沟通**：让干系人保持知情
- **持续改进**：持续打磨质量流程

## 错误处理与恢复

### 常见质量问题
1. **缺失数据**：识别模式并实施恰当处理
2. **离群值**：恰当检测与处理异常取值
3. **格式问题**：标准化格式并校验合规
4. **一致性违规**：解决逻辑不一致
5. **参照完整性**：修复关系违规

### 恢复策略
```python
class QualityRecoveryManager:
    def __init__(self):
        self.recovery_strategies = {
            'missing_data': self.recover_missing_data,
            'outliers': self.handle_outliers,
            'format_issues': self.fix_format_issues,
            'consistency_violations': self.resolve_inconsistencies
        }

    def recover_missing_data(self, data, missing_pattern):
        """Recover missing data based on identified patterns"""
        if missing_pattern['mechanism'] == 'MCAR':
            # Use mean/median imputation for MCAR
            return self.impute_mcar(data, missing_pattern)
        elif missing_pattern['mechanism'] == 'MAR':
            # Use model-based imputation for MAR
            return self.impute_mar(data, missing_pattern)
        else:
            # Use specialized techniques for MNAR
            return self.impute_mnar(data, missing_pattern)
```

## 与其他系统集成

### 数据管道集成
- **预处理校验**：在分析前校验数据
- **实时监控**：监控流式数据质量
- **批处理**：校验批处理结果
- **数据湖治理**：确保数据湖质量标准

### 商业智能集成
- **仪表板中的质量指标**：纳入质量指示
- **数据置信水平**：展示数据洞察的可靠性
- **决策支持**：为决策提供质量背景
- **性能跟踪**：监控质量趋势随时间的变化

## 使用示例
```bash
/quality user_behavior.csv check
/quality sales_data.csv clean
/quality customer_data.csv validate
/quality financial_data.csv monitor
/quality inventory_data.csv profile
```

## 与其他命令的配合
- 在 `/analyze` 之前使用，确保数据质量
- 与 `/visualize` 配合，做质量可视化
- 之后用 `/report` 做质量报告
- 之前用 `/generate` 做质量感知的代码生成

## 注意事项
- 数据集应位于 data_storage/ 目录
- 质量报告将保存到 quality_reports/ 目录
- 用 Task 工具委派给 quality-assurance 子代理
- 设定质量阈值时考虑业务情境
- 分析前先了解并理解质量问题
- 为关键数据实现持续质量监控

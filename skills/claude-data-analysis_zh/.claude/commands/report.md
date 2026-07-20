---
allowed-tools: Task, Read, Write, Bash, Grep, Glob
argument-hint: [dataset] [report_type] [format]
description: 为指定数据集生成完整的分析报告
---

# 报告生成命令

使用 report-writer 子代理，为数据集 `$1` 按报告类型 `$2`、以 `$3` 格式生成完整的分析报告。

## Context
- 数据集位置: @data_storage/$1
- 报告类型: $2 (summary, complete, executive, technical, custom)
- 输出格式: $3 (markdown, html, pdf, json, docx)
- 当前工作目录: !`pwd`
- 输出目录: ./analysis_reports/
- 可用模板与排版选项

## Your Task

使用 report-writer 子代理创建专业、完整的分析报告：

### 1. 报告规划
- 根据类型与受众确定合适的报告结构
- 汇集所有相关的分析结果与可视化
- 规划叙事流与讲故事的方式
- 选择合适的技术细节深度

### 2. 内容生成
- 撰写有说服力的执行摘要（用于执行型报告）
- 创建详细的方法论章节（用于技术型报告）
- 用支撑证据呈现关键发现
- 纳入带说明的数据可视化
- 提供可落地的建议

### 3. 质量保证
- 核验所有统计与论断的准确性
- 确保报告通篇逻辑一致
- 检查清晰度与可读性
- 校验来源与方法的恰当引用

### 4. 排版与交付
- 为选定的输出格式应用合适的排版
- 创建专业的文档结构
- 添加必要的元数据与参考
- 生成最终交付文件

## 报告类型

### 摘要报告（Summary）
- 关键发现的简要概览
- 核心统计与洞察
- 高层建议
- 篇幅 1-2 页

### 完整报告（Complete）
- 完整的分析文档
- 详细的方法论与结果
- 完整的统计分析
- 大量可视化与说明
- 技术附录与参考

### 执行报告（Executive）
- 面向业务的摘要
- 关键绩效指标
- 战略建议
- 行动项与实施路线图
- 财务影响评估

### 技术报告（Technical）
- 详细的方法论文档
- 统计分析结果
- 技术附录
- 代码与算法文档
- 可供同行评审的格式

### 自定义报告（Custom）
- 用户自定义的结构与内容
- 贴合具体需求
- 灵活的排版选项
- 自定义章节与侧重

## 输出格式

### Markdown (md)
- 对 Web 友好的格式
- 利于版本控制
- 易于转换为其他格式
- 适合文档与协作

### HTML (html)
- 交互式 Web 格式
- 内嵌可视化
- 响应式设计
- 可通过 Web 浏览器访问

### PDF (pdf)
- 专业的打印格式
- 固定版式
- 高质量输出
- 可直接分发

### JSON (json)
- 结构化数据格式
- 机器可读
- 对 API 友好
- 利于集成

### DOCX (docx)
- Microsoft Word 格式
- 商务标准
- 可编辑格式
- 适合企业使用

## 预期输出

### 报告文件
- `analysis_reports/$1_$2_report.$3` - 主报告文件
- `analysis_reports/$1_appendix.$3` - 技术附录
- `analysis_reports/$1_visualizations.$3` - 可视化汇编
- `analysis_reports/$1_metadata.json` - 报告元数据

### 内容结构
- **标题页**：报告标题、作者、日期、版本
- **执行摘要**：关键发现与建议
- **引言**：背景与目标
- **方法论**：分析思路与方法
- **结果**：详细发现与统计
- **讨论**：解读与含义
- **结论**：总结与下一步
- **参考文献**：来源与引用
- **附录**：技术细节与补充材料

## 质量标准

### 内容质量
- **准确性**：所有统计与论断必须经过核验
- **清晰**：清晰、简洁、易懂的语言
- **完整性**：覆盖分析的所有重要方面
- **相关性**：聚焦受众相关的信息
- **客观性**：均衡、无偏的呈现

### 技术质量
- **统计有效**：恰当的统计方法与解读
- **方法严谨**：扎实的分析方法论
- **数据完整**：准确呈现数据
- **可复现**：足够详细以供复现
- **文档完善**：对方法的完整记录

### 呈现质量
- **专业排版**：行业标准的排版
- **图文整合**：可视化的无缝整合
- **可读性**：清晰的排版与布局
- **可访问性**：可访问的设计与内容
- **一致性**：通篇一致的样式

## 报告模板

### 执行摘要模板
```markdown
# Executive Summary: $1 Analysis

## Key Findings
- **Primary Insight**: [Key statistical finding]
- **Business Impact**: [Business-relevant implication]
- **Performance Metrics**: [KPIs and measurements]

## Recommendations
1. **Immediate Action**: [Specific action item with timeline]
2. **Strategic Initiative**: [Long-term recommendation]
3. **Investment Priority**: [Resource allocation recommendation]

## Next Steps
- **Phase 1 (0-30 days)**: [Immediate actions]
- **Phase 2 (30-90 days)**: [Medium-term initiatives]
- **Phase 3 (90+ days)**: [Long-term strategic actions]
```

### 技术报告模板
```markdown
# Technical Analysis Report: $1

## Abstract
Brief summary of analysis objectives, methods, and key findings.

## 1. Introduction
### 1.1 Background and Objectives
Context and purpose of the analysis.

### 1.2 Data Description
Source, structure, and characteristics of the dataset.

## 2. Methodology
### 2.1 Data Preparation
Data cleaning, transformation, and preprocessing steps.

### 2.2 Analytical Methods
Statistical methods and algorithms used in the analysis.

## 3. Results
### 3.1 Descriptive Statistics
Summary statistics and data characteristics.

### 3.2 Inferential Statistics
Hypothesis testing results and confidence intervals.

### 3.3 Key Findings
Detailed presentation of analysis results.

## 4. Discussion
### 4.1 Interpretation
Explanation of what the findings mean.

### 4.2 Limitations
Constraints and limitations of the analysis.

## 5. Conclusions
### 5.1 Summary
Recap of key insights and discoveries.

### 5.2 Recommendations
Actionable recommendations based on findings.

## 6. References
Citations to relevant literature and methods.

## 7. Appendices
### 7.1 Technical Details
Additional technical information.
### 7.2 Data Dictionary
Detailed variable descriptions.
### 7.3 Code Listings
Relevant code snippets.
```

## 最佳实践

### 报告写作
- **了解受众**：根据受众的专业水平定制内容
- **讲好故事**：营造从数据到洞察的叙事流
- **简洁**：只纳入相关信息
- **善用视觉**：用合适的可视化支撑文字
- **提供情境**：说明发现的意义

### 数据呈现
- **使用合适图表**：按数据类型选择图表
- **清晰标注**：确保所有图表与表格标注清晰
- **包含单位**：始终标明度量单位
- **突出要点**：强调重要发现
- **确保可访问**：让内容对所有用户可访问

### 建议
- **具体**：提供具体、可落地的建议
- **排序**：按重要性与影响对建议排序
- **包含时间线**：说明何时采取行动
- **指派责任**：明确由谁负责行动
- **衡量成功**：定义如何衡量成功

## 使用示例
```bash
/report user_behavior.csv complete markdown
/report sales_data.csv executive pdf
/report customer_data.csv technical html
/report financial_data.json summary json
/report custom_data custom docx
```

## 与其他命令的配合
- 在 `/analyze` 之后使用，使报告有分析结果可用
- 与 `/visualize` 配合，把可视化纳入报告
- 之后用 `/quality` 校验报告数据质量
- 之前用 `/hypothesis` 纳入研究发现

## 注意事项
- 数据集应位于 data_storage/ 目录
- 报告将保存到 analysis_reports/ 目录
- 用 Task 工具委派给 report-writer 子代理
- 选择报告类型时考虑目标受众
- 生成报告前确保所有数据分析已完成
- 最终分发前评审并定制报告

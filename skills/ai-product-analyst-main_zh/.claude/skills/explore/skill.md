# Skill: Explore Data

## 用途
快速、交互式的数据探索，无需走完整流水线。让用户在投入正式分析之前，先翻看当前激活数据集 —— 预览表、查看分布、发现模式、形成假设。

## 何时使用
- 用户说 `/explore` 或 "让我探索一下数据" 或 "这个数据集里有什么？"
- 连接新数据集后、任何正式分析之前
- 当用户想了解数据形态但没有具体问题时

## 调用方式
`/explore` —— 探索当前激活的数据集
`/explore {table}` —— 聚焦某张表
`/explore {table} {column}` —— 下钻某个字段

## 操作步骤

### 第 1 步：加载上下文
读取 `.knowledge/active.yaml` 确定当前激活的数据集。
读取 `.knowledge/datasets/{active}/schema.md` 作为表/字段参考。
读取 `.knowledge/datasets/{active}/quirks.md` 了解已知的坑。

如果没有激活的数据集，提示："No dataset connected. Use `/connect-data` to add one."

### 第 2 步：选择探索模式

**模式 A：数据集概览**（未指定表）
- 列出所有表，含行数和日期范围
- 突出 3-5 张分析价值最高的表（行数最多、join 最多）
- 展示关键实体及它们如何关联
- 基于可用数据，建议 3 个起步问题

**模式 B：表探索**（指定了表）
- 展示字段列表，含类型和空值率
- 随机抽样 5 行
- 数值字段：min、max、mean、median
- 类别字段：前 5 个取值及计数
- 日期字段：范围和覆盖度
- 标记任何质量问题（>5% 空值、低基数、可疑值）

**模式 C：字段下钻**（指定了表 + 字段）
- 完整分布：数值用直方图，类别用条形图
- 空值分析：计数、模式（随机 vs 系统性）
- 异常值检测：IQR 方法，标记极端值
- 如果是日期字段：按周的覆盖度热力图
- 建议可做交叉分析的相关字段

### 第 3 步：交互式跟进
展示结果后，提供 2-3 个情境化的下一步动作：
- "Want to see how {column} varies by {dimension}?"
- "This looks like a good candidate for funnel analysis. Want to try `/run-pipeline`?"
- "There are quality issues in {column}. Want to run `/data-profiling`?"

### 第 4 步：保存探索笔记
把简短的探索摘要写到 `working/explore_notes_{DATE}.md`：
- 检查过的表
- 关键观察
- 质量标记
- 建议的下一步

该文件供后续 agent 使用（例如 Question Framing 可参考探索笔记来指导假设生成）。

## 规则
1. 保持快速 —— 每个探索步骤不超过 3-4 个查询
2. 若生成任何图表，始终应用 `swd_style()`
3. 探索期间绝不修改数据
4. 输出中始终标注表名和字段名
5. 如果数据源是 CSV 回退，向用户提及这一点

## 边界情况
- **空表：** 报告行数 = 0，建议检查数据加载
- **表未找到：** 对 schema 做模糊匹配，建议最接近的匹配
- **字段全为空值：** 标记为 BLOCKER，建议检查数据管道
- **表非常宽（>50 列）：** 按类别分组，展示摘要而非完整列表

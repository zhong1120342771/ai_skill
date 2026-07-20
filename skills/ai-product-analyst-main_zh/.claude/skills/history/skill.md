# Skill: History

## 用途
浏览和搜索分析归档中的历史分析。帮助用户回顾此前分析过什么、查找过往结论，并在以往工作的基础上继续推进。

## 何时使用
- 用户说 `/history` 或 "我以前分析过什么？"
- 会话开始时，提供过往工作的背景
- 在框定新问题时，检查是否已有类似分析

## 调用方式
`/history` —— 列出最近的分析（最近 10 条）
`/history {id}` —— 展示某条分析的完整明细
`/history search={term}` —— 按标题、问题或标签搜索
`/history --all` —— 列出所有数据集的全部分析
`/history dataset={id}` —— 筛选到指定数据集

## 操作步骤

### 第 1 步：加载归档
1. 读取 `.knowledge/analyses/index.yaml`
2. 如果为空："No analyses archived yet. Complete an analysis and it will appear here."

### 第 2 步：执行命令

**列出最近（`/history`）：**
- 筛选到当前激活的数据集（除非带 `--all` 标志）
- 按日期降序排序
- 用表格展示最近 10 条：日期、标题、级别、关键结论数量、数据集
- 显示总数："Showing 10 of {total} analyses."

**展示某条（`/history {id}`）：**
- 在 index 中按 ID 查找条目
- 展示：标题、日期、问题、级别、全部关键结论、所用指标、所用 agent、输出文件、标签、置信度、建议
- 如果输出文件存在，提示："Want to review the full analysis?"

**搜索（`/history search={term}`）：**
- 在以下范围搜索：标题、问题、key_findings、标签（大小写不敏感）
- 用表格展示匹配的条目
- 如果无匹配："No analyses match '{term}'. Try broader terms."

**全部数据集（`/history --all`）：**
- 在输出中加入 dataset_id 列
- 跨所有数据集按日期降序排序

### 第 3 步：情境化建议
展示历史记录后：
- "Want to re-run this analysis with fresh data?"
- "Want to build on finding #{n}?"
- 如果最近一次分析是部分完成的："This analysis was incomplete. Resume with `/resume-pipeline`."

## 边界情况
- **无激活数据集：** 展示所有分析，或提示连接数据集
- **归档文件缺失：** 创建空 index
- **分析输出文件已被删除：** 标注 "output files no longer available"
- **历史记录非常长（>100）：** 分页，每次展示 20 条

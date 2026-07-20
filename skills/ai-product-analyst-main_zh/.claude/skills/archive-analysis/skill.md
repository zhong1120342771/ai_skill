# Skill: Archive Analysis

## 用途
把完成的分析保存到知识系统的分析归档中，以便日后回顾。记录关键结论、
所用指标、调用过的 agent，以及输出文件路径，使过往工作能在未来会话中被引用。

## 何时使用
- 完成 L3+ 分析后（验证完成后）
- `/run-pipeline` 成功完成后
- 用户说 "save this analysis" 或 "archive this"
- 在第 18 步（Close the Loop）结束时自动触发

## 操作步骤

### 第 1 步：收集分析元数据
从当前会话收集：

1. **标题：** 从原始问题或业务背景推导
2. **问题：** 用户的原始问题
3. **问题级别：** 来自 Question Router 的分类（L1-L5）
4. **数据集 ID：** 来自 `.knowledge/active.yaml`
5. **关键结论：** 从分析输出或验证报告中提取前 3-5 条结论
6. **所用指标：** 列出分析中引用的指标 ID（若有指标字典则与之比对）
7. **所用 agent：** 列出被调用的 agent 名称
8. **输出文件：** 列出 `outputs/` 和 `working/` 中文件的路径
9. **标签：** 从问题关键词 + 指标名自动生成
10. **置信度：** 若有，取自验证 agent 的置信度评分

### 第 2 步：创建归档条目
生成唯一 ID：`analysis_{YYYYMMDD}_{HHMMSS}`

按 `.knowledge/analyses/_schema.yaml` 构建条目 dict。

### 第 3 步：追加到 index
1. 读取 `.knowledge/analyses/index.yaml`
2. 把新条目追加到 `analyses` 列表
3. 递增 `total_analyses`
4. 把 `last_updated` 更新为当前日期
5. 写回 `index.yaml`

### 第 4 步：更新数据集统计
1. 读取 `.knowledge/datasets/{active}/manifest.yaml`
2. 递增 `analysis_count`
3. 把 `last_used` 更新为当前日期
4. 写回

### 第 5 步：确认
向用户报告：
```
Analysis archived: {title}
ID: {id}
Findings: {count} key findings captured
Use `/history` to browse past analyses.
```

### 第 6 步：沉淀到 Query Archaeology（可选）

归档后，检查该分析是否产出了值得保存到
`.knowledge/query-archaeology/curated/` 的可复用模式，通过 `helpers/archaeology_helpers.py` 进行。

1. **SQL 模式** —— 如果已验证的 SQL 查询可用于未来分析：
   - 提议通过 `capture_cookbook_entry(title, sql, dataset, tables, tags)` 沉淀
   - 只沉淀通过对账或验证检查的查询

2. **表知识** —— 如果分析揭示了有用的表元数据：
   - 提议通过 `capture_table_cheatsheet(table_name, dataset, grain, primary_key, common_filters, gotchas, common_joins)` 沉淀/更新
   - 包含 grain、主键、常用过滤、gotchas 和常用 join

3. **Join 模式** —— 如果分析用到了非显而易见的 join：
   - 提议通过 `capture_join_pattern(tables, join_sql, cardinality, validated, dataset)` 沉淀
   - 记录基数（cardinality）以及该 join 是否经过验证

**本步骤的规则：**
- 询问用户："Would you like to save any SQL patterns from this analysis?"
- 如果用户拒绝，或没有可复用模式，静默跳过
- 只从置信度等级 B 或更高的分析中沉淀模式
- 未经用户确认绝不自动沉淀

## 规则
1. 绝不覆盖已有的归档条目 —— 始终追加
2. 关键结论每条一句话，基于事实，带数字
3. 标签用小写，不带空格（用连字符）
4. 如果未运行验证，把置信度设为 null 并注明
5. 即使是部分完成的分析也归档 —— 标记为 `partial: true`

## 边界情况
- **无输出：** 仅用元数据归档，注明 "no output files"
- **流水线被中断：** 归档可用部分，标记为部分完成
- **重复问题：** 仍然归档 —— 不同运行可能发现不同的东西
- **分析 index 不存在：** 从模板创建

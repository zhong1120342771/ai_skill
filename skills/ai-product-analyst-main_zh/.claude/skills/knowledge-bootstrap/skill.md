# Skill: Knowledge Bootstrap

## 用途
为新会话初始化全部 7 个知识子系统。把配置状态、数据集、用户画像、集成项、组织上下文、纠正记录、经验、query archaeology 和分析归档加载进工作记忆。

## 何时使用
- 任何会话开始时
- `/connect-data` 或 `/switch-dataset` 之后
- 当系统检测到知识文件缺失或陈旧时

## 操作步骤

按顺序加载每个子系统。每次文件读取都必须优雅降级：如果
文件不存在，静默跳过，并在摘要中注明 "not yet populated"。
绝不因某个子系统缺失而阻塞会话。

### 第 1 步：配置状态
读取 `.knowledge/setup-state.yaml`。
- 解析 `setup_complete`，统计 `status: "complete"` 的阶段数。
- 如果 `setup_complete: false`，注明未完成的阶段以便建议 `/setup`。
- **如果缺失：** 注明 "Setup: not initialized -- offer /setup"。

### 第 2 步：激活数据集
读取 `.knowledge/active.yaml`。
- 如果 `active_dataset` 为 null 或缺失，注明 "No active dataset" 并继续。
- 如果已设置，从 `.knowledge/datasets/{active}/` 加载：

| File | Required | If Missing |
|------|----------|------------|
| `manifest.yaml` | Yes | 注明 "manifest missing -- not usable" |
| `schema.md` | Yes | 通过 `schema_to_markdown()` 或剖析生成 |
| `quirks.md` | No | 创建空模板 |
| `metrics/index.yaml` | No | 计为 0 |

若 `schema.md` 缺失，生成 schema：
1. 检查 `data/schemas/{active}.yaml` —— 若找到则用 `schema_to_markdown()`。
2. 否则回退到 `get_connection_for_profiling()`。
3. 陈旧判断：如果 `last_profile.md` 更新，则重新生成。

从 manifest 提取系统变量：`{{SCHEMA}}`、`{{DISPLAY_NAME}}`、
`{{DATE_RANGE}}`、`{{DATABASE}}`。

### 第 3 步：用户画像
读取 `.knowledge/user/profile.md`。
- **如果存在：** 应用 `Detail level`、`Chart preference`、`Narrative style`。
- **如果缺失：** 从模板创建（见下），注明 "Profile: new"。

会话中遇到用户的明确纠正时，更新画像：
向 Corrections Log 小节追加 `YYYY-MM-DD | Assumed [X] | User prefers [Y]`。绝不从沉默中推断。

### 第 4 步：用户集成项
读取 `.knowledge/user/integrations.yaml`。
- 提取 `preferred_export_format`、`communication.detail_level`。
- 统计已配置的渠道（`configured: true`）。
- **如果缺失：** 注明 "Integrations: not configured -- defaults apply"。

### 第 5 步：组织上下文
在 `setup-state.yaml`（`phases.phase_3_business.data.organization_id`）
或激活数据集 manifest 的 `organization` 字段中查找组织 ID。

如果存在组织 ID 且不是 `_example`：
- 读取 `.knowledge/organizations/{org_id}/manifest.yaml` 获取名称、行业。
- 读取 `.knowledge/organizations/{org_id}/business/index.yaml` 获取各小节计数
  （术语、产品、指标、目标、团队）。
- **如果组织目录缺失：** 注明 "Org: linked but not found"。

如果未关联组织：注明 "Org: not configured"。

### 第 6 步：纠正记录
读取 `.knowledge/corrections/index.yaml`。
- 提取 `total_corrections` 和 `by_severity` 计数。
- 如果 `total_corrections > 0`，突出 critical/high 的计数，让 agent 在写 SQL 前
  检查完整日志。
- **如果缺失：** 注明 "Corrections: not yet populated"。

### 第 7 步：经验
读取 `.knowledge/learnings/index.md`。
- 扫描类别标题（`### N. Category Name`）。
- 注明哪些类别有内容条目、哪些为空。
- 不要加载全部内容 —— 只看类别是否存在。
- **如果缺失：** 注明 "Learnings: not yet populated"。

### 第 8 步：Query Archaeology
读取 `.knowledge/query-archaeology/curated/index.yaml`。
- 提取 `cookbook_entries`、`table_cheatsheets`、`join_patterns` 计数。
- **如果缺失：** 注明 "Archaeology: not yet populated"。

### 第 9 步：分析归档
读取 `.knowledge/analyses/index.yaml`：
- 提取 `total_analyses` 和最近 5 条（标题、日期、结论数、级别）。
- 如果最近一次分析在 24 小时内，标记以便延续。

读取 `.knowledge/analyses/_patterns.yaml`：
- 统计 `patterns[]` 条目数，若有则注明模式名称。
- **如果缺失：** 注明 "Patterns: not yet populated"。

### 第 10 步：报告就绪度

汇编一份 **内部上下文摘要**（保存在工作记忆中，不直接展示原文）：

```
Setup: {complete (N/M phases) | incomplete (list missing) | not initialized}
Dataset: {display_name} ({source_type}, {N} tables, ~{rows} rows, {date_range}) | not configured
Profile: {role}, {detail_level} | new
Integrations: {preferred_format}, {N} channels | not configured
Org: {company} ({industry}), {N} glossary, {N} products, {N} metrics | not configured
Corrections: {N} logged ({N} critical, {N} high) | none
Learnings: {N}/{6} categories populated | not yet populated
Archaeology: {N} cookbook, {N} cheatsheets, {N} join patterns | not yet populated
Archive: {N} analyses, {N} recurring patterns | none
```

然后输出 **面向用户的状态**：

```
Dataset: {display_name} ({source_type})
Tables: {N} tables, ~{row_count} rows
Date range: {date_range}
Metrics: {M} defined
Profile: {loaded | new}
Status: Ready for analysis
```

如果某个关键子系统缺失（无数据集、无 manifest），调整状态
并建议 `/connect-data` 或 `/setup`。

---

## 用户画像模板

```markdown
# User Profile

Auto-created by knowledge bootstrap. Updated as the system learns preferences.

## Role & Expertise
- **Role:** _[auto-detected or user-specified]_
- **Technical level:** _[beginner | intermediate | advanced]_
- **SQL comfort:** _[none | basic | intermediate | advanced]_
- **Statistics comfort:** _[none | basic | intermediate | advanced]_
- **Domain:** _[e-commerce | fintech | saas | marketplace | other]_

## Communication Preferences
- **Detail level:** _[executive-summary | standard | deep-dive]_
- **Chart preference:** _[minimal | standard | chart-heavy]_
- **Narrative style:** _[bullet-points | prose | mixed]_

## Corrections Log
_Records of times the user corrected the system's assumptions._
<!-- Format: YYYY-MM-DD | What was wrong | What was right -->
```

## 边界情况
- **无 `.knowledge/` 目录：** 创建完整目录树并提示 `/connect-data`。
- **schema.md 为空：** 通过剖析重新生成。
- **无数据文件：** 建议检查连接或回退到 CSV。
- **多个数据集：** 报告激活的那个，并提醒 `/switch-dataset`。
- **配置未完成：** 注明阶段，不阻塞。建议 `/setup`。

## 反模式
1. **绝不跳过 bootstrap。** 始终读取 manifest —— 细节可能已变。
2. **绝不硬编码数据集名。** 从 `active.yaml` 解析。
3. **绝不在 bootstrap 期间修改 manifest。** Bootstrap 只读。
4. **绝不向用户倾倒原始 YAML。** 展示简短状态，不展示加载过程。
5. **绝不因某个子系统缺失而阻塞。** 始终优雅降级。

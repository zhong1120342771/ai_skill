# Skill: Query Archaeology Retrieval

## 用途
从 query archaeology 库中检索经过验证的 SQL 模式、表速查表和 join 模式，让
agent 复用已验证的成果，而不是从零写 SQL。

## 何时使用
- **自动地** 在任何分析 agent 写 SQL 之前（预检步骤）
- **手动地** 当用户询问某张表或某个 join 的已知模式时

## 操作步骤

### 第 1 步：检查 index

读取 `.knowledge/query-archaeology/curated/index.yaml`。解析计数器：
`cookbook_entries`、`table_cheatsheets`、`join_patterns`。

**如果三者都为零（或文件缺失），到此为止。** 不返回任何内容，
也不向用户提及 archaeology。

### 第 2 步：确定搜索词

从当前分析上下文中提取：
- agent 即将查询的 **表名**（例如 `orders`、`events`）
- **查询意图标签**（例如 `funnel`、`retention`、`revenue`、`cohort`）

### 第 3 步：搜索三个库

搜索每个有条目的库（按 index 计数）。匹配用
**大小写不敏感的子串** —— `order` 匹配 `orders`、`order_items`。

#### 3a. Cookbook（`curated/cookbook/*.yaml`）
对每个文件，检查：
- `tables` 数组 —— 任一元素是否包含某个搜索表名作为子串？
- `tags` 数组 —— 任一元素是否匹配某个查询意图标签？

匹配时提取：`title`、`sql`、`tables`、`tags`，以及任何 `caveats`/`notes`。

#### 3b. 表速查表（`curated/tables/*.yaml`）
对每个文件，检查：
- `table_name` 是否包含某个搜索表名作为子串？

匹配时提取：`table_name`、`grain`、`primary_key`、`common_filters`、
`gotchas`、`common_joins`。

#### 3c. Join 模式（`curated/joins/*.yaml`）
对每个文件，检查：
- `tables` 数组 —— 是否至少有两个元素匹配搜索表名？
- 如果只有一个搜索表，则当 `tables` 包含它作为子串时匹配。

匹配时提取：`tables`、`join_sql`、`cardinality`、`notes`、`validated`。

### 第 4 步：格式化结果

把匹配的条目作为围栏式上下文块返回。省略无匹配的小节。

```
--- QUERY ARCHAEOLOGY CONTEXT ---

## Cookbook Patterns
### {title}
Tables: {tables}  |  Tags: {tags}
```sql
{sql}
```
Caveats: {caveats or "none"}

## Table Cheatsheets
### {table_name}
- Grain: {grain}
- Primary key: {primary_key}
- Common filters: {common_filters}
- Gotchas: {gotchas}
- Common joins: {common_joins summary}

## Join Patterns
### {tables[0]} <-> {tables[1]}
Cardinality: {cardinality}  |  Validated: {validated}
```sql
{join_sql}
```
Notes: {notes}

--- END ARCHAEOLOGY CONTEXT ---
```

### 第 5 步：交接给 agent

把格式化后的块作为附加上下文传给分析 agent。该
agent 应优先使用 archaeology 的 SQL 而非从零编写，遵守列出的任何
gotchas，并在工作文件中标注使用了某个 archaeology 模式。

## 反模式

1. **库为空时绝不提及 archaeology** —— 静默跳过
2. **绝不要求精确匹配** —— 始终用子串，让 `order` 能找到 `orders`
3. **绝不一次性贪婪加载所有文件** —— 先检查 index 计数，跳过为零的库
4. **绝不修改 archaeology 文件** —— 该 skill 只读
5. **检索失败时绝不阻断分析** —— archaeology 是增益项，不是关卡

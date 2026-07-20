# /setup-dev-context — 开发者上下文设置

> 面向把 AI Analyst 集成进开发工作流的团队的独立 skill。
> 大多数用户（PM、高管、DS）永远用不到 —— 只有做代码库集成的团队才需要。

## 触发
调用方式为 `/setup-dev-context`

## 目的
收集代码库相关的上下文，帮助 AI Analyst 理解你的开发环境。这能让 SQL 生成更准确、对 schema 有感知，并能与你现有的数据基础设施集成。

## 前置条件
- 必须先完成 `/setup` 访谈（第 1–2 阶段）
- 读取 `.knowledge/setup-state.yaml` 确认 `phase_2.status: complete`
- 如果 setup 未完成，告知用户："Run `/setup` first to configure your profile and data connection."

## 访谈流程

### 第 1 步：代码库结构
向用户询问：
```
I'll ask a few questions about your development environment to provide better support.

1. **Repository type:** What kind of codebase is this?
   - [ ] Analytics/data warehouse (dbt, SQL files, ETL)
   - [ ] Application backend (API, services)
   - [ ] Full-stack application
   - [ ] Data science / ML project
   - [ ] Other: ___
```

把回答记录到 `.knowledge/user/dev-context.yaml` 的 `codebase.type` 下。

### 第 2 步：数据层
向用户询问：
```
2. **Data layer:** How is your data organized?
   - Database type: (Postgres, BigQuery, Snowflake, DuckDB, other)
   - Schema naming convention: (e.g., `analytics.`, `public.`, `dbt_prod.`)
   - Key tables location: (path to schema definitions, dbt models, etc.)
```

记录到 `codebase.data_layer` 下。

### 第 3 步：SQL 约定
向用户询问：
```
3. **SQL conventions:** Does your team follow specific patterns?
   - Naming: snake_case / camelCase / other
   - Date handling: timezone-aware? Default timezone?
   - NULL handling: COALESCE patterns? Default values?
   - Any team-specific SQL style guide? (path or URL)
```

记录到 `codebase.sql_conventions` 下。

### 第 4 步：集成点
向用户询问：
```
4. **Integration points:** Where does AI Analyst fit in your workflow?
   - [ ] Ad-hoc analysis only (no integration needed)
   - [ ] Reads from dbt models
   - [ ] Connects to production replica
   - [ ] Uses exported CSV/Parquet files
   - [ ] Accesses data warehouse directly
   - Other: ___
```

记录到 `codebase.integration` 下。

### 第 5 步：文件约定
向用户询问：
```
5. **File conventions:** (optional)
   - Where do analysis outputs go? (default: `outputs/`)
   - Any naming conventions for SQL files?
   - Git branch strategy for analysis work?
```

记录到 `codebase.file_conventions` 下。

## 输出

把收集到的上下文保存到 `.knowledge/user/dev-context.yaml`：

```yaml
schema_version: 1
created: "{{DATE}}"
last_updated: "{{DATE}}"

codebase:
  type: null           # analytics | backend | fullstack | data-science | other
  data_layer:
    database: null     # postgres | bigquery | snowflake | duckdb | other
    schema_prefix: null
    models_path: null  # path to dbt models or schema definitions
  sql_conventions:
    naming: snake_case
    timezone_aware: false
    default_timezone: UTC
    null_handling: null
    style_guide: null
  integration:
    mode: null         # adhoc | dbt | replica | exported | direct
    details: null
  file_conventions:
    output_dir: outputs/
    sql_naming: null
    git_strategy: null
```

更新 `.knowledge/setup-state.yaml`：
```yaml
dev_context:
  status: complete
  completed_at: "{{DATE}}"
```

## 完成提示
```
Developer context saved. AI Analyst will now:
- Use your schema prefix ({{schema_prefix}}) in SQL queries
- Follow your team's SQL conventions
- Output files to {{output_dir}}

You can update this anytime with `/setup-dev-context`.
```

## 重置
`/setup-dev-context reset` —— 清空 dev-context.yaml 并重置为默认值。

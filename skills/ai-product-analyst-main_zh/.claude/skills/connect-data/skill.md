# Skill: Connect Data

## 用途
引导式向导，用于连接新数据集。带用户走完选择连接类型、配置凭证、验证连接、剖析 schema、搭建知识 brain 的全流程。

## 何时使用
- 用户说 `/connect-data` 或 "连接我的数据库" 或 "添加一个新数据集"
- 首次运行欢迎流程建议连接数据
- `/switch-dataset` 后，目标数据集尚不存在时

## 调用方式
`/connect-data` —— 启动连接向导
`/connect-data type=postgres` —— 跳过类型选择

## 操作步骤

### 第 1 步：选择连接类型
呈现选项：
1. **CSV files** —— "I have CSV files in a local directory"
2. **DuckDB** —— "I have a local DuckDB database file"
3. **MotherDuck** —— "I have a MotherDuck cloud database"
4. **PostgreSQL** —— "I have a PostgreSQL database"
5. **BigQuery** —— "I have a Google BigQuery dataset"
6. **Snowflake** —— "I have a Snowflake warehouse"

### 第 2 步：收集连接详情

**对 CSV：**
- 询问："What's the path to your CSV directory? (relative to this repo)"
- 验证目录存在且包含 .csv 文件
- 列出找到的文件并请用户确认

**对 DuckDB：**
- 询问："Path to your .duckdb file?"
- 验证文件存在
- 用 `SELECT 1` 测试连接

**对 MotherDuck：**
- 询问："Database name and schema?"
- 提示："MotherDuck connects via MCP. Make sure your token is configured."

**对 PostgreSQL / BigQuery / Snowflake：**
- 从 `connection_templates/` 复制相应模板
- 请用户填写必填字段
- **重要：** 绝不直接索要或存储密码。引导用户使用环境变量（例如 `$PG_PASSWORD`）。

### 第 3 步：创建数据集 brain
1. 从展示名生成 dataset_id（小写，连字符）
2. 创建 `.knowledge/datasets/{id}/` 目录
3. 用连接模板 + 用户输入写入 `manifest.yaml`
4. 创建带小节标题的空 `quirks.md`
5. 创建空的 `metrics/index.yaml`

### 第 4 步：测试连接
使用 `helpers/connection_manager.py` 的 `ConnectionManager`：
1. 用新配置实例化
2. 调用 `test_connection()`
3. 如果失败：展示错误，提供重试或编辑配置
4. 如果通过：继续

### 第 5 步：剖析 schema
1. 调用 `list_tables()` 枚举表
2. 对每张表：通过 `get_table_schema()` 获取字段名和类型
3. 用 `helpers/data_helpers.py` 的 `schema_to_markdown()` 生成 `schema.md`
4. 写入 `.knowledge/datasets/{id}/schema.md`
5. 提议运行完整数据剖析："Want me to deep-profile this dataset?"

### 第 6 步：设为激活
1. 更新 `.knowledge/active.yaml` 指向新数据集
2. 确认："Connected! **{display_name}** is now your active dataset."
3. 展示：表数量、估计行数、日期范围（若检测到）
4. 建议下一步：`/explore` 浏览、`/metrics` 定义指标，或直接提问

## 规则
1. 绝不在 manifest 文件中以明文存储凭证
2. 在宣布成功前始终测试连接
3. 始终生成 schema.md —— 它是分析的必需项
4. 即使剖析失败，也要创建完整的 `.knowledge/datasets/{id}/` 树
5. 如果用户已有这个数据集，覆盖前先询问

## 边界情况
- **目录不存在：** 提议创建
- **未找到 CSV 文件：** 检查其他格式（.parquet、.json）
- **连接反复失败：** 建议检查凭证、防火墙、VPN
- **schema 过大（>100 张表）：** 仅剖析，跳过逐表明细
- **数据集名冲突：** 追加数字（例如 "mydata-2"）

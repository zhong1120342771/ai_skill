# AI Analyst 安装指南

## 前置条件

- **Python 3.10+** 以及 pip
- 已安装 **Claude Code** CLI（[文档](https://docs.anthropic.com/en/docs/claude-code)）
- 你的数据为 CSV、DuckDB，或受支持的数据仓库（Postgres、BigQuery、Snowflake）

## 快速开始

### 1. 克隆并安装

```bash
git clone <repo-url> ai-analyst
cd ai-analyst
pip install -e ".[dev]"
```

### 2. 启动 Claude Code

```bash
claude
```

### 3. 接入你的数据

首次启动时，Claude 会检测到全新安装并启动交互式安装访谈。它会引导你完成：

1. **你的角色和团队** —— 让 Claude 调整沟通风格
2. **你的数据源** —— CSV 目录、DuckDB 文件或仓库连接
3. **你的业务背景** —— 公司做什么、核心指标、团队结构
4. **你的偏好** —— 输出格式、图表风格、导出渠道

你也可以随时手动运行安装：

```
/setup
```

### 4. 开始分析

安装完成后，直接提问即可：

```
What's our conversion rate by device type?
```

或运行完整分析流水线：

```
/run-pipeline
```

## 接入数据源

### CSV 文件

把 CSV 文件放进一个目录（例如 `data/my_dataset/`），并在安装时告诉 Claude。每个 `.csv` 文件都会成为一张可查询的表。

### 本地 DuckDB

在安装时把 Claude 指向一个 `.duckdb` 文件。DuckDB 能对本地数据提供快速的 SQL 查询。

### 外部数据仓库

对于 Postgres、BigQuery 或 Snowflake 连接，你需要配置 MCP（Model Context Protocol）服务。运行 `/connect-data` 并按提示操作。

## 重置

要重新开始：

```
/setup reset
```

- **Tier 1 重置** —— 清除你的画像和偏好
- **Tier 2 重置** —— 清除所有内容，包括数据集连接

## 运行测试

```bash
python -m pytest tests/ -v
```

## 项目结构

```
ai-analyst/
  .claude/skills/     -- Claude skill 定义（自动应用的行为）
  .knowledge/         -- 知识系统（由安装和使用过程填充）
  agents/             -- agent 提示词模板（多步骤工作流）
  helpers/            -- Python 工具模块
  tests/              -- Pytest 测试套件
  data/               -- 你的数据集（已 gitignore）
  docs/               -- 文档
  outputs/            -- 分析产物（图表、幻灯片、叙事）
  working/            -- 中间工作文件
```

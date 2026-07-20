# 更新日志

本文件记录该项目所有值得关注的变更。

## [2.0.0] - 2026-02-23

### 新增
- 交互式上手引导：`/setup` 访谈了解你的角色、数据源和业务背景
- 知识基础设施：纠错记录、经验沉淀、查询考古、组织知识
- 自学习闭环：反馈采集、纠错记录、经验证 SQL 模式检索
- 基于 YAML 的品牌主题，配套符合 WCAG 标准的配色（`themes/brands/`）
- 流水线运行跟踪：`/runs` 可列出、查看、对比和清理运行记录
- 用于 Slack/邮件/高管摘要输出的 comms drafter agent
- 业务背景体系：按组织维护术语表、指标、产品、团队
- Notion ingest skill，从 Notion 工作区导入业务背景
- 跨数据集消歧的 entity resolver
- 8 个新 slash 命令：`/setup`、`/runs`、`/business`、`/log-correction`、`/architect`、`/notion-ingest`、`/setup-dev-context`、`/compare-datasets`
- 9 个新 skill：archaeology、feedback-capture、log-correction、setup、setup-dev-context、runs、business、notion-ingest、architect
- 606 个测试，使用合成 fixture（不依赖外部数据）
- 用于数据连通性诊断的健康检查系统
- 用于知识文件版本管理的 schema 迁移辅助工具

### 变更
- 完全与数据集解耦：agent 从激活的 manifest 解析表/列，不再使用硬编码名称
- 移除内置的 NovaMart 数据集 —— 用 `/connect-data` 接入你自己的数据
- 移除遗留的 setup 脚本（`download-data.sh`、`build-duckdb.sh`）和相关文档
- 更新 CLAUDE.md，纳入 V2 工作流、agent 索引和 skill 表
- Python 要求提升到 3.10+

### 修复
- 通过持久化状态管理，提升流水线恢复的可靠性
- chart palette 现在会校验 WCAG 对比度

## [1.0.0] - 2026-02-19

### 新增
- 首个公开版本
- 17 个专用分析 agent，支持基于 DAG 的并行执行
- 30 个自动应用的 skill（问题框定、数据质量、可视化、校验）
- 14 个供交互使用的 slash 命令
- 示例电商数据集 schema（13 张表）
- 分层数据体系：Tier 1 入 git，Tier 2 通过 GitHub Releases
- setup 脚本：`setup.sh`、`download-data.sh`、`build-duckdb.sh`
- 多仓库支持：DuckDB、MotherDuck、Postgres、BigQuery、Snowflake
- 带碰撞检测的 SWD 风格图表生成
- 带品牌化 HTML 组件的 Marp 幻灯片制作
- 带 A-F 置信度评分的四层校验框架
- 用于跨会话记忆的知识系统
- 带标准化定义的指标词典
- 带模式抽取的分析归档

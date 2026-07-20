# 历史沿革

## 来源

本仓库于 2026-02-19 从 `ai-analytics-for-builders` 单体仓库中抽取而来。

- **来源：** 从原始私有单体仓库抽取
- **抽取方式：** `git archive`（干净快照，不含历史记录）
- **开发周期：** 2026 年 2 月 13 日至 19 日
- **贡献者：** Shane Butler，AI 结对编程伙伴为 Claude Code（Opus）
- **原始背景：** Shane Butler 的 AI Analyst 项目

## 为什么没有 git 历史？

该单体仓库包含多个产品（课程、邮件流水线、播客工具、市场营销）。如果只为 AI Analyst 子目录抽取 git 历史，会带入其他项目的无关提交，并泄露内部文件路径。一个干净的快照能得到更小、更整洁的仓库。

完整的开发历史保留在私有的 `ai-analytics-for-builders` 单体仓库中，用于溯源。

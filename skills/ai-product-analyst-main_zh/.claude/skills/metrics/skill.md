# Skill: Metrics

## 目的
浏览、搜索并展示当前活跃数据集的指标字典中的指标定义。提供快速入口，了解指标是如何定义、计算和校验的。

## 何时使用
- 用户说 `/metrics` 或"给我看看指标"或"我们追踪哪些指标？"
- 分析过程中，在计算某个指标前确认其定义
- 编写指标 spec 时，检查是否已有定义

## 调用方式
`/metrics` —— 列出当前活跃数据集的所有指标
`/metrics {id}` —— 显示某个指标的完整 spec
`/metrics category={cat}` —— 按类别筛选（例如 monetization）
`/metrics search={term}` —— 搜索指标名称和描述

## 操作步骤

### 第 1 步：加载指标字典
1. 读取 `.knowledge/active.yaml` 确定活跃数据集。
2. 读取 `.knowledge/datasets/{active}/metrics/index.yaml` 获取指标列表。
3. 如果不存在 metrics 目录："No metric dictionary for this dataset. Use the metric-spec skill to define metrics."

### 第 2 步：执行命令

**列出全部（`/metrics`）：**
- 以表格展示：id、name、category、direction、validation_status
- 按 category 分组
- 显示总数

**显示指定指标（`/metrics {id}`）：**
- 读取 `.knowledge/datasets/{active}/metrics/{id}.yaml`
- 展示：name、category、owner、完整定义（formula、unit、direction、granularity）、源表、维度、guardrails、典型区间、校验状态
- 如果找不到该指标：从索引中给出最接近的匹配建议

**按类别筛选（`/metrics category=monetization`）：**
- 按 category 字段过滤索引
- 展示过滤后的表格

**搜索（`/metrics search=revenue`）：**
- 搜索指标名称和描述（不区分大小写的子串匹配）
- 展示匹配的指标

### 第 3 步：上下文相关建议
展示指标后，给出相关操作建议：
- "Want to validate {metric} against the current data? Use the data-profiling skill."
- "Need to define a new metric? Use the metric-spec skill."
- "Want to see how {metric} trends over time? Ask me to analyze it."

## 边界情况
- **没有活跃数据集：** 提示连接一个
- **指标字典为空：** 建议使用 metric-spec skill
- **被引用但不在字典中的指标：** 主动提出创建它
- **校验过期：** 标记 last_validated 距今超过 30 天的指标

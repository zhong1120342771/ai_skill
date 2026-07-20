# Skill: Compare Datasets

## 用途
跨两个或更多已连接的数据集对比指标、结论和模式。帮助识别跨数据集的共性模式（例如 "两条产品线的转化漏斗行为相似"）以及单个数据集特有的异常。

## 何时使用
- 用户说 `/compare-datasets` 或 "跨数据集对比"
- 分析多个数据集后，寻找共性
- 当用户问 "这个模式是该数据集独有的吗？"

## 调用方式
`/compare-datasets` —— 把当前激活数据集与其他所有数据集对比
`/compare-datasets {id1} {id2}` —— 对比两个指定的数据集
`/compare-datasets metric={name}` —— 跨数据集对比某个指定指标

## 操作步骤

### 第 1 步：确定要对比的数据集
1. 读取 `.knowledge/datasets/` 枚举所有已连接的数据集。
2. 如果指定了具体数据集，验证它们存在。
3. 如果未指定数据集，使用当前激活的 + 其他所有的。
4. 至少需要 2 个数据集。如果只有 1 个："Only one dataset connected. Use `/connect-data` to add another."

### 第 2 步：加载指标字典
对每个数据集：
1. 读取 `.knowledge/datasets/{id}/metrics/index.yaml`
2. 构建跨数据集所有指标 ID 的并集
3. 区分共享指标（同 ID 或同名）与数据集特有指标

### 第 3 步：对比共享指标
对每个存在于 2 个以上数据集的指标：
1. 从每个数据集加载该指标的 YAML
2. 对比：定义是否一致？（同公式、同单位）
3. 对比：典型取值范围是否重叠？（数据集是否有相近的基线？）
4. 对比：护栏是否一致？（阈值是否一致？）
5. 标记差异："conversion_rate is defined differently in {dataset_a} vs {dataset_b}"

### 第 4 步：对比分析历史
对每个数据集：
1. 读取 `.knowledge/analyses/index.yaml`
2. 从近期分析中提取关键结论
3. 寻找跨数据集模式：
   - 同一结论出现在多个数据集
   - 相反结论（指标在一个里升、在另一个里降）
   - 独立得出的相同根因

### 第 5 步：生成跨数据集观察
把结论写入 `.knowledge/global/cross_dataset_observations.yaml`：
- 共享模式：跨数据集都出现的行为
- 分歧：数据集表现不同之处
- 指标一致性：哪些指标定义保持一致
- 建议进一步调查：对比所引出的问题

### 第 6 步：展示结果
显示对比表：

```
Cross-Dataset Comparison: {dataset_a} vs {dataset_b}

Shared Metrics: {N} ({M} with matching definitions)
Metric Discrepancies: {list}

Shared Patterns:
  - {pattern description} (seen in both datasets)

Divergences:
  - {metric} is {direction} in {dataset_a} but {direction} in {dataset_b}

Suggested Next:
  - "Investigate why {pattern} differs between datasets"
  - "Align {metric} definitions across datasets"
```

## 边界情况
- **只有 1 个数据集：** 无法对比 —— 建议连接另一个
- **无共享指标：** 报告此情况 —— 数据集可能服务于不同目的
- **无分析历史：** 仅对比 schema 和指标定义
- **数据集很多（>5）：** 仅与当前激活数据集做两两对比

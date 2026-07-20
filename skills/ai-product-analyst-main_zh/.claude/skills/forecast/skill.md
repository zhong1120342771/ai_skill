# Skill: Forecast

## 用途
用 forecast_helpers 库为关键指标生成时间序列预测。支持朴素基线、季节性检测和指数平滑 —— 足以回答 "接下来应该预期什么？"，无需复杂建模。

## 何时使用
- 用户问 "下个月收入会怎样？" 或 "预测 DAU"
- 趋势分析揭示了值得外推的模式之后
- 在量化一个依赖未来值的机会时
- 以 `/forecast` 调用

## 调用方式
`/forecast {metric}` —— 预测指定指标
`/forecast {metric} periods=30` —— 指定预测期数
`/forecast {metric} method=holt_winters` —— 指定方法

## 操作步骤

### 第 1 步：准备数据
1. 从指标字典（`.knowledge/datasets/{active}/metrics/`）或用户指定中
   确定指标及其源表。
2. 按合适的粒度（日/周/月）聚合查询数据。
3. 创建带 DatetimeIndex 的 pandas Series。
4. 清洗：前向填充 NaN，去掉开头的空值。
5. 至少需要 14 个数据点。如果更少："Not enough history for forecasting."

### 第 2 步：检测季节性
运行 `helpers/forecast_helpers.py` 的 `detect_seasonality()`：
- 如果检测到季节性，报告："Found {strength} {period}-day seasonality."
- 存下主导周期供第 3 步使用。

### 第 3 步：生成预测
运行多个方法并对比：

1. **朴素（末值）：** `naive_forecast(series, periods, method='last')`
2. **朴素（季节性）：** 若检测到季节性：`naive_forecast(series, periods, method='seasonal_naive')`
3. **指数平滑（自动）：** `exponential_smoothing(series)`
4. **Holt-Winters：** 若检测到季节性且数据充足：`exponential_smoothing(series, seasonal_period=dominant_period)`

对比各方法的 MSE。选出拟合最佳的方法。

### 第 4 步：生成图表
使用 `chart_helpers`：
1. 调用 `swd_style()`
2. 把历史数据画成实线
3. 把预测画成虚线，alpha 更浅
4. 加置信带（残差的 ±1 个标准差）作为阴影区
5. 用一条垂直虚线标出历史/预测的边界
6. 用 `action_title()` 配一个前瞻性标题
7. 用 `save_chart()` 保存到 `working/forecast_{metric}_{DATE}.png`

### 第 5 步：展示结果
报告：
- 最佳方法及原因（MSE 最低）
- 关键期次的预测值（未来 7/14/30 天）
- 季节性摘要
- 置信度（基于残差大小）
- 注意事项："Forecasts assume past patterns continue. External factors not modeled."

## 规则
1. 始终至少跑 2 个方法以便对比
2. 绝不在不声明假设的情况下给出预测
3. 始终包含一个朴素基线，让用户看出模型是否带来增益
4. 如果残差显示出系统性模式，提示（模型可能设定有误）
5. 如果数据存在结构性断点，警告预测可能不可靠

## 边界情况
- **常数序列：** 报告 "No variation — forecast is the constant value"
- **强趋势 + 无季节性：** 用 Holt's（二次）指数平滑
- **历史很短（<30 点）：** 只用朴素方法，提示精度有限
- **数据有缺口：** 视缺口大小，插值或警告

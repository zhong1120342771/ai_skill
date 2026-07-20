# Skill: Feedback Capture

## 用途
路由前拦截器，在每条用户消息上先于 Question Router 运行。检测纠正信号、方法论经验和正向反馈，把它们沉淀到 `.knowledge/`，然后透传到正常路由。

## 何时使用
- 在每条进来的用户消息上，先于 Question Router 分类
- 静默运行 —— 用户不应察觉本 skill 在执行

## 操作步骤

### 第 0 步：拦截（先于 Question Router 运行）

把全部检测和沉淀逻辑包在 try/except 里。如果有任何失败，
什么都不记，把消息原样透传给 Question Router。绝不
阻断流水线。

### 第 1 步：检测反馈类型

在用户消息中扫描以下信号模式：

**纠正信号**（用户指出某处错了）：
- "that's wrong"、"that's incorrect"、"actually it's..."、"it should be..."
- "the column is X not Y"、"that number should be..."、"you used the wrong..."
- "off by..."、"overcounted"、"undercounted"、"double-counted"
- "that join is wrong"、"missing a filter"、"forgot to exclude..."

**经验信号**（用户传授可复用的方法论）：
- "next time..."、"always use..."、"never use..."、"prefer X over Y"
- "the convention here is..."、"our team uses..."、"don't forget to..."
- "a better approach would be..."、"going forward..."、"remember that..."

**正向信号**（用户确认正确）：
- "that's right"、"exactly"、"perfect"、"good analysis"、"looks good"

**无信号**：没有模式匹配。如果有多个匹配，优先级：纠正 > 经验 > 正向。

### 第 2 步：按检测结果处理

#### 若检测到纠正：

1. 读取 `.knowledge/corrections/index.yaml` 获取 `last_correction_id`。
2. 计算下一个 ID：把数字后缀加一（例如 `CORR-001` -> `CORR-002`）。
   如果 `last_correction_id` 为 null，从 `CORR-001` 开始。
3. 从上下文估计严重度：
   - **critical**：向干系人呈现了错误结论
   - **high**：输出中数字有误、影响结果的 join 错误
   - **medium**：用错了字段、过滤或指标定义
   - **low**：轻微的标签、格式或命名问题
4. 分类类别：`join_error` | `filter_missing` | `metric_definition` |
   `date_range` | `aggregation` | `schema` | `logic` | `other`
5. 读取 `.knowledge/corrections/log.yaml`。
6. 向 `corrections` 列表追加一个新条目：
   ```yaml
   - id: "CORR-{N}"
     date: "{TODAY}"
     severity: "{estimated}"
     category: "{classified}"
     dataset: "{active dataset or null}"
     tables: []
     description: "{what the user said was wrong}"
     fix: "{what the user said is correct}"
     sql_before: null
     sql_after: null
     prevented_by: null
   ```
   仅当用户消息含足够细节时才填 `tables`、`sql_before`、`sql_after` 和
   `prevented_by`。否则留 null。
7. 写入更新后的 `log.yaml`。
8. 更新 `.knowledge/corrections/index.yaml`：递增 `total_corrections`，
   递增对应的 `by_severity` 和 `by_category` 计数，设置
   `last_correction_id` 和 `last_updated`。
9. 简短确认："Got it, logged as {ID}." 然后正常继续处理
   用户的实际请求。

#### 若检测到经验：

1. 读取 `.knowledge/learnings/index.md`。
2. 归入六个类别之一：
   - Data Patterns | Query Techniques | Business Context |
     Stakeholder Preferences | Visualization Insights | Methodology Notes
3. 在匹配的 `### {N}. {Category}` 标题下追加一个要点。
   格式：`- {concise learning} (source: user feedback, {TODAY})`
4. 写入更新后的 `index.md`。
5. 简短确认："Noted for future analyses." 然后正常继续处理
   用户的实际请求。

#### 若检测到正向反馈：

简短确认（"Thanks!" 或类似的一句话）并正常继续处理
消息的其余部分。无需写文件。

#### 若未检测到信号：

静默透传。不要说 "I didn't detect feedback."。直接
进入 Question Router。

### 错误处理

全部检测和沉淀逻辑都必须包在 try/except 里。如果文件读
写失败，完全跳过沉淀并继续路由。分析师的
首要职责是回答问题，不是记账。

## 反模式

1. **绝不阻断流水线** —— 如果沉淀失败，静默透传
2. **绝不让用户确认反馈类型** —— 静默分类
3. **绝不宣布 "no feedback detected"** —— 不加评论地透传
4. **绝不做重处理** —— 模式匹配并写入，仅此而已
5. **绝不覆盖已有的纠正** —— 始终追加
6. **绝不编造纠正细节** —— 推断不出的字段用 null

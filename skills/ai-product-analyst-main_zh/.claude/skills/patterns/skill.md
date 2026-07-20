# Skill: Patterns

## 目的
浏览并搜索跨多次分析发现的重复出现的模式（pattern）。模式在每次分析归档后自动抽取，代表数据中持续出现的行为。

## 何时使用
- 用户说 `/patterns` 或"我们见过哪些模式？"
- 分析过程中，检查某个发现是否匹配已知模式
- 会话开始时，提醒用户已确立的行为规律

## 调用方式
`/patterns` —— 列出当前活跃数据集的模式
`/patterns --global` —— 列出所有数据集的模式
`/patterns search={term}` —— 按关键词搜索模式
`/patterns {id}` —— 显示某个模式的完整细节

## 操作步骤

### 第 1 步：加载模式
1. 读取当前活跃数据集的 `.knowledge/analyses/_patterns.yaml`。
2. 如果带 `--global` 标志：同时读取 `.knowledge/global/cross_dataset_observations.yaml`。
3. 如果为空："No patterns recorded yet. Complete a few analyses and patterns will emerge."

### 第 2 步：执行命令

**列出模式（`/patterns`）：**
- 过滤到当前活跃数据集（除非带 `--global`）
- 按出现次数降序排序（最确立的排在前）
- 以表格展示：type、description、occurrences、confidence、last seen
- 显示总数

**显示指定模式（`/patterns {id}`）：**
- 展示：description、type、所有证据（含分析 ID）、维度、
  指标、建议的调查方向
- 提出："Want to investigate this pattern further?"

**搜索（`/patterns search={term}`）：**
- 在 description、维度、指标、标签中搜索
- 以表格展示匹配的模式

**全局（`/patterns --global`）：**
- 在各数据集模式之外，纳入跨数据集观察
- 标注每个模式是在哪个数据集中观察到的

### 第 3 步：上下文相关建议
展示模式后：
- "Want to check if {pattern} still holds in the current data?"
- "Want to use {pattern} as context for a new analysis?"
- "This pattern was last seen {N} days ago — may need revalidation."

## 模式抽取（自动）

每次分析归档后（由 archive-analysis skill 触发），扫描新分析以寻找潜在模式：

1. 把新发现与已有模式比对：
   - 如果某发现匹配已有模式 → occurrences 加一，更新 last_seen
   - 如果某发现是新的但能扩展某个模式 → 作为证据加入
2. 寻找全新模式：
   - 同一指标行为出现在 2 次以上分析中 → 候选模式
   - 同一细分人群持续表现更好 → 候选模式
   - 在相近时间反复出现的异常 → 候选模式
3. 把更新后的模式写回 `_patterns.yaml`

至少出现 2 次才能创建一个模式。只出现一次的发现就只是发现，不是模式。

## 边界情况
- **没有模式：** 建议多做几次分析
- **过期模式（last_seen >60 天）：** 标记为可能已过时
- **相互矛盾的模式：** 标记并建议调查
- **模式过多（>50）：** 按出现次数显示前 20 条，提供分页

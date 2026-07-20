# Skill: Export

## 用途
针对不同受众，以不同格式导出分析结果。把流水线输出转换成可直接分享的交付物。

## 何时使用
- 用户说 `/export` 或 "把这个导出为..." 或 "把这个发给..."
- 完成一次分析或流水线运行后
- 当用户需要特定格式的结果时

## 调用方式
`/export slides` —— 从最新分析生成/刷新 Marp 幻灯片
`/export email` —— 写一封高管摘要邮件（markdown）
`/export slack` —— 写一条简洁的 Slack 更新（markdown）
`/export brief` —— 写一页式决策简报（markdown）
`/export data` —— 把分析数据表导出为 CSV
`/export all` —— 生成所有文本格式 + 数据

## 操作步骤

### 第 1 步：寻找源材料
按优先级顺序检查已完成的分析输出：
1. `outputs/slides_*.md` —— 最新的 deck
2. `outputs/analysis_*.md` —— 最新的叙述
3. `working/pipeline_summary.md` —— 流水线摘要
4. `working/storyboard_*.md` —— 故事板

如果没有任何输出：
- 检查 `working/` 中是否有部分结果
- 如果什么都没找到："No analysis results to export. Run an analysis first or use `/run-pipeline`."

### 第 2 步：生成所请求的格式

**格式：slides**
- 如果 deck 已存在，询问："Deck found at {path}. Regenerate or export as-is?"
- 如果没有 deck，用最新叙述 + 图表调用 Deck Creator agent
- 输出：`outputs/slides_{DATE}.md`

**格式：email**
- 结构：主题行 + 三段正文（背景、关键结论、建议）
- 语气：面向高管、无术语、行动导向
- 包含：1-2 个关键数字、"所以呢"、以及明确的诉求
- 输出：`outputs/email_summary_{DATE}.md`

**格式：slack**
- 结构：加粗标题 + 3-5 个要点 + 适合发到 thread
- 控制在 300 词以内
- 谨慎使用 emoji（仅勾选符号、箭头）
- 包含：关键指标、方向、建议动作
- 输出：`outputs/slack_update_{DATE}.md`

**格式：brief**
- 结构：标题 + 执行摘要（三句话）+ 关键结论（编号）+ 建议 + 下一步 + 附录（数据源、方法论）
- 目标一页（约 500 词）
- 输出：`outputs/decision_brief_{DATE}.md`

**格式：data**
- 把 `working/` 中所有 DataFrame 导出为 CSV 到 `outputs/data/`
- 附一个 README，列出每个文件及其内容
- 输出：`outputs/data/` 目录

**格式：all**
- 依次运行 email + slack + brief + data
- 如果 slides 已存在则跳过

### 第 3 步：导出之后
- 列出所有导出文件及路径
- 建议："Copy the email to your clipboard?" 或 "Want to adjust the tone?"

## 规则
1. 绝不编造结论 —— 只用实际分析输出中的数据
2. 始终标注源分析的日期和数据集
3. 按格式自适应详细程度（email = 高层、brief = 中等、data = 原始）
4. 对所有文本输出应用 Stakeholder Communication skill
5. 如果分析有置信度评分，在 brief 格式中包含它们

## 边界情况
- **部分完成的分析：** 导出可用部分，注明缺口："Note: validation step was not completed."
- **outputs/ 中有多份分析：** 取日期最新的，或询问用户用哪一份
- **图表缺失：** 文本格式仍可用，注明："Charts not available for this export."
- **用户请求未知格式：** 列出可用格式并请其选择

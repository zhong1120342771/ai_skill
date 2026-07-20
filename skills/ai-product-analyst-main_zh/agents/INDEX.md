# Agent 索引

## 系统变量（自动解析）
| 变量 | 取值 | 使用位置 |
|----------|-------|---------|
| `{{DATE}}` | 当前日期，YYYY-MM-DD | 所有 agent 的输出文件名 |
| `{{DATASET_NAME}}` | 从数据路径或用户输入派生的短名称 | 文件命名、报告标题 |
| `{{BUSINESS_CONTEXT_TITLE}}` | 从 `{{BUSINESS_CONTEXT}}` 派生的简短标题 | 问题简报标题 |
| `{{RUN_ID}}` | 唯一运行标识（YYYY-MM-DD_question-slug） | Run Pipeline、Resume Pipeline |
| `{{RUN_DIR}}` | 每次运行的输出目录路径 | 流水线运行期间的所有 agent |
| `{{SQL_PATTERNS}}` | 由 archaeology 检索出的 SQL 模式 | 分析类 agent |
| `{{CORRECTIONS}}` | 当前上下文已记录的更正 | 分析类 agent |
| `{{LEARNINGS}}` | 特定类别的经验 | Question Framing、Storytelling |
| `{{ENTITY_INDEX}}` | 消歧索引 | Question Router |
| `{{ORG_CONTEXT}}` | 业务上下文（术语表、产品、团队） | Question Framing、Storytelling |
| `{{THEME}}` | 当前主题名称 | Chart Maker、Deck Creator |
| `{{CONTEXT}}` | 演示上下文（workshop/talk/analysis） | Story Architect、Deck Creator |
| `{{STORYBOARD}}` | Story Architect 的输出 | Chart Maker、Storytelling |
| `{{FIX_REPORT}}` | Visual Design Critic 的反馈 | Chart Maker（修复轮次） |
| `{{DECK_FILE}}` | 生成的 deck 路径 | Visual Design Critic |
| `{{CONFIDENCE_GRADE}}` | 验证置信度评分（A-F） | Storytelling、Deck Creator |

## Agents
| Agent | 路径 | 何时调用 |
|-------|------|-------------|
| Question Framing | `agents/question-framing.md` | 用户提供一个待分析的业务问题 |
| Hypothesis | `agents/hypothesis.md` | 问题已框定，需要可验证的假设 |
| Data Explorer | `agents/data-explorer.md` | 需要了解某个数据源里有哪些数据 |
| Descriptive Analytics | `agents/descriptive-analytics.md` | 需要分析数据集（分群、漏斗、驱动因素） |
| Overtime / Trend | `agents/overtime-trend.md` | 需要时间序列分析或趋势识别 |
| Cohort Analysis | `agents/cohort-analysis.md` | 需要同期群留存曲线、LTV 分析或不同批次对比 |
| Root Cause Investigator | `agents/root-cause-investigator.md` | 初步分析发现异常——需要逐层下钻找到具体根因 |
| Opportunity Sizer | `agents/opportunity-sizer.md` | 已识别根因或机会点——用敏感性分析量化业务影响 |
| Experiment Designer | `agents/experiment-designer.md` | 需要验证因果假设——设计 A/B 测试或准实验分析，含功效估计与决策规则 |
| Story Architect | `agents/story-architect.md` | 分析已完成——在任何制图之前设计故事板（叙事节拍 + 视觉映射）。为 workshop/talk 的收尾序列传入 `{{CONTEXT}}`。 |
| Chart Maker | `agents/chart-maker.md` | 需要生成某张具体图表。 |
| Visual Design Critic | `agents/visual-design-critic.md` | Chart Maker 生成图表之后——对照 SWD 清单审查。Deck Creator 之后——用 `{{DECK_FILE}}` 和 `{{THEME}}` 做幻灯片级别的设计审查。 |
| Narrative Coherence Reviewer | `agents/narrative-coherence-reviewer.md` | Story Architect 产出故事板之后、制图之前——审查故事流程、节拍结构，以及存在的收尾节拍 |
| Storytelling | `agents/storytelling.md` | 分析和图表均已完成，需要一段叙事 |
| Source Tie-Out | `agents/source-tieout.md` | Data Explorer 之后、分析之前——通过对比 pandas 直读与 DuckDB SQL 在基础指标上的结果来校验数据加载完整性。不一致则 HALT。 |
| Validation | `agents/validation.md` | 在呈现之前需要核验结论 |
| Deck Creator | `agents/deck-creator.md` | 需要从分析生成演示。支持 `{{THEME}}`（analytics-dark）和 `{{CONTEXT}}`（workshop/talk 收尾序列）。 |
| Comms Drafter | `agents/comms-drafter.md` | 需要面向干系人的沟通材料（Slack 摘要、邮件简报、高管摘要）。非关键——若失败流水线继续。 |

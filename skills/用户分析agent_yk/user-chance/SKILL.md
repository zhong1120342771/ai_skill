---
name: user-chance
description: Use when 用户要通过 Agent 在真实 App 或转转 App 中模拟真实用户完成任务、发现体验问题、寻找产品机会点、运行真机或模拟器体验实验、导出体验报告、复盘 mobile-mcp 执行过程或调优 user-chance 行为模型。
---

# user-chance

## 定位

`user-chance` 是 Agent 用户体验实验 Skill。它让 Agent 扮演指定用户，在真实 App 中自主完成任务，并基于全过程证据输出体验问题和产品机会点。

核心原则：

```text
Agent 行动像用户，复盘像研究员。
```

它不是自动化测试、固定脚本、页面巡检清单，也不是过程流水账。默认主交付是体验报告；截图、UI 树、录屏、路径、候选、弹窗处理和动作记录都是支撑结论的证据。

## 输入契约

少爷只需要提供最小任务信息：

| 字段 | 必填 | 说明 |
|---|---|---|
| 用户角色 | 是 | Agent 要扮演谁 |
| 任务目标 | 是 | 用户想完成什么、判断什么 |
| 禁止边界 | 是 | 本轮不能做什么 |
| 可选条件 | 否 | App、城市、登录态、设备、最大步数、是否复测、是否重点体验某条路径、报告重点、是否用于批量或竞品对比 |

不要要求少爷指定入口、点击顺序、关键词、筛选策略、弹窗处理方式或判断规则；这些由 Agent 基于角色、目标、品类 / 行业语境、页面信息、安全边界和行为模型自主决定。

### 自然语言优先

少爷不需要手写 `experiment_mode`、`path_spec`、`path_policy`、`report_intent`、`export_profile` 这类内部字段。少爷可以直接说：

- “这次自由探索，看用户会怎么找。”
- “这次重点体验首页活动入口这条路径。”
- “大致经过首页、活动入口、活动承接页、商品列表、商品详情。”
- “中途允许像真实用户一样处理弹窗、看优惠、滑动列表、看图、返回修正。”
- “如果这条路径明显不支持目标，或者快碰到下单 / 支付 / 客服 / 资料修改边界，就停并说明。”
- “报告重点看体验问题和机会点。”
- “这轮结果后续要进入批量分析 / 竞品对比。”

Agent 要把这些自然语言内部归一化为稳定字段，用于执行和报告；除非少爷要求查看配置、调试 Skill 或复制给其他 Agent，否则不要把 YAML 配置当成少爷必须输入的话术。

内部字段含义：

| 内部字段 | 人话含义 |
|---|---|
| `experiment_mode` | 本轮是自由目标探索，还是重点体验一条指定路径 |
| `path_spec` | 指定路径的大致节点、允许的自然绕路、可以停下或脱离路径的条件 |
| `path_policy` | 路径约束强度：严格按路径、大致经过关键节点、允许自然脱离 |
| `report_intent` | 报告重点：机会点、体验过程或调研洞察 |
| `export_profile` | 是否额外输出给批量聚合或竞品对比使用的结构化摘要 |

`report_intent` 只影响最终报告表达重点，不能改变用户行为逻辑。`export_profile` 只决定是否额外输出给批量聚合或竞品对比使用的结构化摘要，不等于报告意图。

## 默认环境

除非少爷指定其他 App，本 Skill 默认体验转转 App。

| 字段 | 默认值 |
|---|---|
| App | 转转 |
| Android 包名 | `com.wuba.zhuanzhuan` |
| 工具 | `mobile-mcp` + ADB |
| 设备 | 不静态默认；先做可启用端判断 |
| 实验对象 | 转转真实 App 的购物 / 交易相关体验 |

包名、版本、设备类型必须以本轮真实设备返回为准。包名变化、测试包、灰度包、渠道包、分身应用都要先说明并请求确认。

## 文件分工

按需读取，不要把所有引用一次性加载。

| 文件 | 负责 | 何时读取 |
|---|---|---|
| `references/behavior-model.md` | 用户模拟心智、行为生成、结果契约、报告证据链 | 运行体验实验、判断行为真实性、调优行为模型 |
| `references/path-constrained-mode.md` | 指定路径体验模式、自然语言路径输入、路径策略、锚点、偏离和路径合规输出 | 少爷要求重点体验某条路径，或内部归一化为 `experiment_mode=path_constrained` |
| `references/android-tool-layer.md` | 真机 / 模拟器、ADB、mobile-mcp、转转 APK、工具失败边界 | 涉及设备接入、模拟器、MCP、ADB、包名或工具排查 |
| `scripts/check_skill_contract.sh` | Skill 结构、关键契约和脚本语法校验 | 重构、调优或覆盖本 Skill 后 |

如果要真正跑体验实验，必须读取 `behavior-model.md`。如果涉及真机、模拟器、MCP 或 ADB，必须读取 `android-tool-layer.md`。
如果少爷用自然语言要求“重点体验某条路径”“按这条链路走”“从某入口开始体验”，或内部归一化为 `experiment_mode=path_constrained`，必须读取 `path-constrained-mode.md`。

## 工具层要求

正式实验必须依赖真实工具层执行，不能用纯对话或想象替代。

最低能力：

| 能力 | 要求 |
|---|---|
| 端发现 | 能识别在线真机 / 模拟器，或发现可启动 AVD |
| App 启动 | 能启动目标 App，并校验前台包名 |
| 页面观察 | 每步保存截图，并尽量获取 UI 树 / 元素快照 |
| 操作执行 | 能点击、输入、滑动、横滑、返回 |
| 状态识别 | 能检查当前包名、页面文本、敏感页和遮挡层 |
| 证据保存 | 每步保存截图、UI 树、动作、动作理由、结果 |
| 安全拦截 | 命中硬红线时停止或请求确认 |

端选择规则和模拟器启动细节见 `references/android-tool-layer.md`。常用脚本：

```bash
/Users/liangkun/.codex/skills/user-chance/scripts/resolve_android_endpoints.sh
/Users/liangkun/.codex/skills/user-chance/scripts/start_android_avd.sh user_chance_api35
/Users/liangkun/.codex/skills/user-chance/scripts/check_zhuanzhuan_android_env.sh emulator-5554
node /Users/liangkun/.codex/skills/user-chance/scripts/mobile_mcp_healthcheck.mjs --device emulator-5554 --save-to <path>
```

工具层失败不能写成产品体验问题。

## 用户模拟内核

每轮实验先建立 `User Simulation Kernel`，再生成动作。完整定义见 `references/behavior-model.md`。

| 模块 | 作用 |
|---|---|
| `persona_priors` | 用户角色、目标强度、知识水平、价格敏感、风险敏感、耐心、信任基线 |
| `goal_parameter_map` | 拆解用户给定目标，区分固定约束和可变目标实体参数 |
| `decision_concern_map` | 识别真实用户在角色、品类、行业和页面语境下会关心什么 |
| `evidence_seeking_behavior` | 判断用户会用什么自然方式验证这些关注点 |
| `media_action` | 当看图、视频、图集会影响判断时，记录具体媒体取证动作或未执行原因 |
| `route_hypothesis` | 用户可能自然尝试的路径和行为策略 |
| `attention_filter` | 操作层判断用户当前会注意到什么、可能自然忽略什么 |
| `dynamic_user_state` | 持续更新候选、信心、信任、摩擦、未解问题和下一意图 |
| `local_information_maturity` | 判断当前候选池、页面或对比组是否足以支持下一步 |
| `target_entity_shift` | 记录目标实体是否发生升级、降级或横向替代，并分析产品含义 |
| `decision_policy` | 判断用户是否愿意买、明确不买、暂缓、放弃或未形成判断 |
| `decision_closure` | 判断关键候选、显著对比和关键证据是否闭合，防止过早 `buy_ready` |
| `friction_response` | 处理弹窗、权益、筛选、排序、保障、评价、低价卡片、无反馈等摩擦 |
| `stop_proof` | 证明停止是用户自然状态或边界导致，不是 Agent 偷懒 |
| `path_compliance` | 路径约束模式下记录锚点是否到达、是否偏离、路径是否支持用户目标 |
| `start_state_validity` | 判断实验起点是否匹配角色；新用户不能默认从历史详情页、搜索页或列表页开始 |
| `mode_lock` | 锁定本轮真实执行模式，指定路径测试不能事后写成自由探索结果 |
| `tool_friction` | 隔离中文输入失败、点击无反馈、UI 树缺失等工具摩擦，防止伪装成用户自然换路 |
| `stop_decision_split` | 拆分用户状态和停止触发，避免安全边界把用户判断误包装成自然暂缓 |
| `evidence_strength` | 给体验问题和机会点标注证据强度，区分强证据、单次线索、Agent 推断和工具限制 |

关键原则：

- 用户给定目标就是目标，不要替用户猜隐藏需求。
- 真实用户不只受显性目标驱动，也受角色、品类、行业风险、页面线索和交易心理驱动。
- `性价比` 不能简化为价格；它通常包含价格、状态、风险、保障、信任和使用场景匹配。
- 二手、高客单、非标商品等场景中，图片、实拍、瑕疵、成色、配件、质检和保障都可能是关键证据。
- 路径不只是入口；弹窗、活动、权益、筛选、排序、对比、行情、保障、看图、返回修正、放弃路径，都可能是自然行为。

## 双视角

每轮实验同时维护两种视角：

| 视角 | 用途 |
|---|---|
| `user_action_view` | 决定下一步怎么操作，只能基于当前视窗、已注意信息、角色目标和自然行为 |
| `research_analysis_view` | 实验后复盘，可以使用截图、UI 树、完整路径、未被注意但实际存在的信息 |

操作不能开全知视角；分析不能降级成普通用户视角。报告应表达为“信息存在，但当前路径下不容易被用户注意到”，不要写成“页面没有”。

## 运行流程

每轮按以下流程推进：

1. **Endpoint Resolution**：如果未指定设备，先判断可启用端，必要时自动启动模拟器或请少爷确认。
2. **Preflight**：校验输入、设备、App、账号、证据目录、停止规则；保存首张截图和 UI 树。
3. **Start State Validation**：判断起点是否匹配用户角色和实验目的；首次/新用户若落在历史详情、搜索、列表或推荐污染状态，必须回到自然起点，或明确标记未覆盖发现/进入阶段并降级结论。
4. **Mode Resolution**：先用自然语言复述本轮实验方式，再内部确认 `experiment_mode`、`path_spec`、`report_intent`、`export_profile`；路径约束模式先建立路径锚点和偏离规则。
5. **Mode Lock Check**：锁定 `requested_mode`、`resolved_mode` 和 `execution_mode`。若少爷要求指定路径，但实际跑成自由探索，本轮必须标记 `mode_validity=invalid | partial`，不能把 `path_compliance=not_applicable` 当作有效路径结论。
6. **User Simulation Kernel**：建立用户先验、目标参数、决策关注点、取证方式、路径假设、注意力、动态状态和决策策略。
7. **Observe**：工具层观察截图、UI 树、页面文本、前台包名。
8. **Notice**：判断当前用户大概率注意到什么。
9. **Interpret**：判断用户如何理解、困惑、犹豫或建立信任。
10. **Update State**：更新候选、关注点覆盖、证据覆盖、信心、信任、摩擦和下一意图。
11. **Assess Tool Friction**：若出现输入失败、点击无反馈、UI 树缺失、截图缺失、MCP/ADB 异常，先记录 `tool_friction`，判断它是否改变路径；工具摩擦导致的替代路径不能直接当作自然用户路径。
12. **Assess Maturity**：判断当前候选池、页面、媒体证据或对比组是否足以支持下一步。
13. **Assess Decision Closure**：在输出 `buy_ready`、`reject_ready` 或强 `defer_ready` 前，检查关键候选、显著替代候选、关键媒体/报告/保障证据是否闭合；未闭合则只能继续探索、暂缓或降级。
14. **Assess Target Entity Shift**：若出现升级、降级或横向替代信号，判断是否只作参考、轻量探索或允许转向。
15. **Choose Action**：选择符合角色、关注点、注意力和自然取证方式的动作。
16. **Safety Check**：检查动作是否触碰安全边界或少爷设定边界。
17. **Act & Evidence**：执行安全动作，保存动作前后证据。
18. **Stop Check**：先判断用户状态，再判断停止触发；如果接近边界，必须说明抛开边界用户是否仍会买、暂缓、拒绝或继续探索。
19. **Research Review**：用全局证据复盘体验问题和机会点，并给每个问题和机会点标注证据强度。
20. **Report**：按 `report_intent` 输出体验报告；若 `export_profile` 不是 `default`，同时输出结构化摘要。

不要用固定入口、固定路径、固定动作数量证明“探索充分”。是否继续由用户状态、关注点缺口、证据缺口、摩擦成本、信任变化和停止证明决定。

## 硬门槛

这些门槛优先于报告完整性。触发后必须影响行动或结论，不能只在报告末尾补字段。

| 门槛 | 要求 |
|---|---|
| 模式锁 | 指定路径实验如果跑成自由探索，标记 `mode_validity=invalid | partial`，本轮不能证明指定路径有效 |
| 起点硬门槛 | 首次/新用户起点污染时必须尝试回首页、冷启动或自然入口；无法校正时不能输出完整新用户结论，也不能给产品问题强结论 |
| 工具失败隔离 | 中文输入失败、点击无反馈、UI 树缺失等必须写入 `tool_friction`；若改变路径，`tool_constraint_impact` 至少为 `major` |
| 决策闭合 | 未自然检视显著替代候选、关键媒体/报告/保障证据或价格差异时，不能输出 `buy_ready`，最多 `defer_ready` 或 `not_formed` |
| 成熟度枚举 | `local_information_maturity.maturity` 只能是 `low` / `medium` / `high`；禁止 `medium-high`、`low-medium`、`high enough for detail`、`medium for defer` 等混合值 |
| 路径合规降级 | `self_correction_cost=high`、目标漂移或用户多次想逃离时，不能写 `path_compliance.status=followed` |
| 证据强度分层 | 流程证据强不等于决策证据强；单轮样本默认是线索，除非多步骤、多证据和用户状态变化共同支撑 |

## 安全边界

默认硬红线：

- 不真实支付。
- 不提交真实订单。
- 不购买或开通付费会员。
- 不修改隐私资料、实名信息、银行卡、地址、手机号等敏感信息。
- 不发布评价、评论、问答、笔记。
- 不发起售后、退款、投诉。
- 不联系真实客服，除非明确接入测试客服队列。
- 不操作非测试账号。
- 命中验证码、支付页、提交订单页、实名认证页、银行卡页、隐私资料页、外部支付 App 时立即停止或请求确认。

不要扩大解释安全红线。普通运营弹窗、活动、优惠、领券、补贴、筛选、排序、对比、行情、保障说明默认不是红线，由 Agent 按角色和目标判断。查看优惠、打开券说明、比较券后价、领取普通可放弃权益，默认属于体验路径；只有少爷明确禁止、会消耗高价值不可逆权益、要求支付 / 下单 / 绑卡 / 实名 / 开通会员，或进入真实履约链路时，才停止或请求确认。

系统权限弹窗默认不授权，除非任务明确依赖且不触碰隐私红线。

## 结果契约

主结果不使用任务型的“成功 / 失败”二分法。顶层结果必须使用：

```yaml
decision_status: reached | not_reached | not_applicable
user_decision: buy_ready | reject_ready | defer_ready | abandon | not_formed | not_applicable
stop_reason: decision_threshold_met | effort_exhausted | safety_boundary | user_boundary | tool_failure | observation_failure | max_steps | no_progress
stop_trigger: natural_decision | safety_boundary_near | user_boundary_near | tool_limit | observation_limit | max_steps_reached | no_progress
boundary_influence: none | possible | material | blocking
observation_quality: full | degraded | failed
conclusion_level: formal_finding | directional_signal | tool_failure_record
tool_constraint_impact: none | minor | major | blocking
start_state_validity: clean | contaminated | unknown
entry_coverage: covered | partial | not_covered
mode_validity: valid | partial | invalid | not_applicable
tool_friction_impact: none | minor | path_changed | blocking
decision_closure: closed | partial | open | not_applicable
stop_proof:
  decision_status:
  user_decision:
  stop_reason:
  stop_basis:
  what_user_knows:
  what_user_still_does_not_know:
  why_stopping_is_natural:
  why_not_agent_laziness:
  counterfactual_without_boundary:
  evidence_refs:
```

字段关系：

- `buy_ready`、`reject_ready`、`defer_ready`、`abandon` 都表示用户已经形成状态，`decision_status=reached`。
- `not_formed` 表示尚未形成可解释判断，`decision_status=not_reached`。
- `not_applicable` 只用于工具失败或观察失败导致用户模拟没有有效发生。
- `tool_failure` 必须对应 `conclusion_level=tool_failure_record` 和 `tool_constraint_impact=blocking`。
- `safety_boundary` 或 `user_boundary` 不一定代表用户没有形成判断；边界可能发生在用户形成判断前或后。
- `stop_reason` 说明结果类型，`stop_trigger` 说明直接停止触发；二者不能混写。接近下单、支付、客服或资料修改边界时，必须输出 `boundary_influence` 和 `counterfactual_without_boundary`。
- `abandon` 是有价值的用户状态，不是失败，必须说明体验成本、信任损失或路径挫败。
- `start_state_validity=contaminated` 或 `entry_coverage=not_covered` 时，不能把本轮写成完整新用户体验结论；默认降级为 `directional_signal`。
- 如果少爷要求指定路径，但真实执行为自由探索，必须输出 `mode_validity=invalid`，不能用 `path_compliance=not_applicable` 掩盖模式错配。
- 如果 `tool_friction_impact=path_changed | blocking`，本轮路径、候选和用户判断必须降级；工具摩擦只能作为工具问题或样本限制，不能包装成自然用户偏好。
- 如果 `decision_closure=open | partial`，不能输出强购买建议；`buy_ready` 需要关键关注点和显著替代候选达到闭合，或明确限定为“只愿意进入购买前确认”。
- `run_outcome` 和 `legacy_goal_result` 只能作为派生摘要或兼容附录，不能放进主摘要，也不能驱动行为。

## 报告契约

默认输出体验报告，不输出完整过程流水账。

单轮报告必须包含：

| 模块 | 要求 |
|---|---|
| 一句话结论 | 用户最终状态、最关键体验问题或机会点 |
| 运行结果 | `decision_status`、`user_decision`、`stop_reason`、`stop_proof` |
| 工具与环境 | 设备、App 版本、登录态、MCP/ADB 状态、模拟器证据说明 |
| 样本有效性 | 输出 `sample_validity`，说明角色、账号、设备、App 状态是否匹配实验目标 |
| 起点有效性 | 输出 `start_state_validity` 与 `entry_coverage`，说明是否覆盖用户发现/进入阶段 |
| 实验配置 | `experiment_mode`、`path_policy`、`report_intent`、`export_profile` |
| 模式有效性 | 输出 `mode_validity`，说明本轮真实执行是否符合少爷指定的自由探索或指定路径模式 |
| 用户模拟内核 | `persona_priors`、`goal_parameter_map`、`decision_concern_map`、`evidence_seeking_behavior`、动态状态 |
| 探索与决策 | 实际路径、候选、关注点覆盖、取证方式、局部信息成熟度、关键缺口 |
| 工具摩擦 | 输出 `tool_friction` 与 `tool_friction_impact`，说明输入、点击、截图、UI 树或 MCP/ADB 问题是否改变路径 |
| 媒体取证 | 若外观、瑕疵、配件或实物可信度影响判断，说明是否看封面、横滑、开图集、看视频或为什么没做 |
| 决策闭合 | 输出 `decision_closure`，说明最终用户状态是否已由关键候选、对比候选和关键证据支撑 |
| 路径合规 | `path_constrained` 时输出 `path_compliance`，说明锚点、偏离和路径适配 |
| 停止拆分 | 输出 `stop_decision_split`，区分用户状态、停止触发、边界影响和无边界反事实 |
| 目标实体变更 | 若发生升级、降级或横向替代，说明理由、证据、固定约束是否保留、产品问题和机会点 |
| 行为真实性评估 | `behavior_assessment` 与兼容 `behavior_fidelity` |
| 关键步骤 | 只展示关键步骤；完整 `step_record` 放过程审计 |
| 过程体验点 | 困惑、犹豫、信任变化、打断、决策成本等 |
| 双证据 | `noticed_evidence` 与 `global_evidence` |
| 体验问题 | 最多 5 个，按影响排序，每个绑定体验点、证据和 `evidence_strength` |
| 产品机会点 | 每个机会点说明解决哪个体验问题和证据强度 |
| 需真人验证 | Agent 判断但仍需真实用户研究或实验确认 |
| 证据索引 | 截图、UI 树、步骤编号、录屏或日志位置 |
| 结构化摘要 | `export_profile=aggregate_input | benchmark_input` 时输出 `structured_summary` 或 `summary.json` |

证据链必须成立：

```text
证据 -> 过程体验点 -> 体验问题 -> 产品机会点
```

## 输出校验

输出前做三层校验：

### Output Contract

- 主摘要必须包含 `decision_status`、`user_decision`、`stop_reason`、`stop_proof`。
- 每个停止结果必须解释用户知道什么、还不知道什么、为什么停止自然，并输出 `stop_basis`。
- 必须区分用户状态和停止触发；安全边界只能作为停止触发，不能自动等同于用户自然暂缓。
- 每个核心体验问题必须回链到体验点和证据。
- 每个机会点必须关联体验问题。
- 每个体验问题和机会点必须标注 `evidence_strength`。
- 工具失败、观察失败、超步数、无进展、安全停止必须显式说明。
- 样本有效性不足时，不能把结果当作强结论。
- 新用户角色若未覆盖发现/进入阶段，必须显式降级并建议冷启动复跑。
- 旧 `legacy_goal_result` 只能出现在兼容附录或给少爷摘要中。
- `report_intent` 只能改变报告重点，不能改变用户行动。
- `export_profile` 不能把批量或竞品逻辑塞进单轮行为循环。
- 若模式错配，必须明确本轮无效或部分有效，不能用自评“通过”覆盖。
- 若工具摩擦改变路径，必须降级样本有效性，并从产品体验问题中隔离。
- `buy_ready` 必须有 `decision_closure=closed`，或明确写成“只愿意进入购买前确认且仍有未闭合问题”并降级。
- `path_constrained` 必须输出 `path_compliance`。
- `path_constrained` 的 `path_compliance` 不能只写锚点到达，还要判断路径是否自然服务目标、用户自我修正成本和路径决策支持度。
- `self_correction_cost=high`、目标漂移或多次逃离冲动出现时，`path_compliance.status` 不能是单纯 `followed`。

### Behavior Critic

- 是否由用户先验、决策关注点、自然取证方式、注意力、状态变化和摩擦反应驱动行动。
- 是否过度走最短路径。
- 是否直接用 UI 树全知视角跳转。
- 是否过早形成强结论。
- 是否区分了用户已注意信息和全局证据。
- 是否把模拟器证据当作高优结论。
- 是否记录工具化动作和复跑建议。
- `behavior_fidelity=高` 是否真的有足够自然比较、取证和停止理由；若存在关键候选未看、重大工具改路或高捷径风险，不能给高。

### Report Critic

- 是否把工具失败误判成体验问题。
- 是否把普通弹窗、优惠、权益误判成红线。
- 是否忽略截图可见但 UI 树不可读的信息。
- 是否遗漏用户自然会核验的关键关注点，例如二手商品的瑕疵、状态、配件、质检或保障。
- 是否把流程证据强误写成决策证据强。
- 是否把单轮样本或污染样本写成强产品结论。
- 机会点是否真的对应体验问题。
- 结论是否可能被未查看关键证据推翻。

## 审计导出

少爷要求“导出过程”“复盘是否跑偏”“判断这轮跑得对不对”时，输出过程审计。若存在以下文件，按它的口径导出：

```text
/Users/liangkun/Documents/产品工作/user-chance_test_process_export_prompt.md
```

少爷要求“导出结果”“输出报告”时，按以下文件口径导出：

```text
/Users/liangkun/Documents/产品工作/user-chance_test_result_export_prompt.md
```

默认主交付始终是体验报告和机会点。

## Skill 维护校验

少爷要求重构、调优或覆盖本 Skill 时，改完运行：

```bash
/Users/liangkun/.codex/skills/user-chance/scripts/check_skill_contract.sh
```

该脚本只校验 Skill 结构、关键契约和脚本语法，不替代真实 App 实验。

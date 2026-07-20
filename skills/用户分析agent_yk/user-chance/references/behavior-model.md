# Behavior Model

本文档用于 `user-chance` 的真实用户行为模拟。运行真实 App 体验实验、复盘 Agent 是否像真实用户、或调优行为策略时读取；只做工具接入检查时不需要读取。

核心原则：

```text
Agent 行动像用户，复盘像研究员。
```

`user-chance` 不是让 Agent 用最短路径完成任务，而是让 Agent 在工具真实执行的基础上，模拟一个具体用户如何注意、理解、犹豫、比较、信任、放弃或形成判断。

## 双视角

| 视角 | 用途 | 约束 |
|---|---|---|
| `user_action_view` | 决定下一步怎么操作 | 只能基于当前视窗、已注意信息、角色目标、品类语境和自然行为 |
| `research_analysis_view` | 实验后分析体验问题和机会点 | 可以使用截图、UI 树、完整路径、未被用户注意但实际存在的信息 |

操作不能开全知视角；分析不能降级成普通用户视角。

正确表达：

| 不严谨表达 | 推荐表达 |
|---|---|
| 页面没有质检信息 | 质检信息存在，但当前路径下不容易被用户注意到 |
| 用户没看到优惠，所以没有优惠 | 优惠入口存在，但没有进入用户注意范围或未形成可理解价值 |
| Agent 直接点报告入口 | 需要先说明用户是否已经注意到报告入口，以及这个动作是否自然 |
| 用户没滑图，所以图片不重要 | 图片可能是关键证据，但本轮没有进入用户自然取证路径 |

## User Simulation Kernel

每轮实验先建立 `User Simulation Kernel`。它是行动生成的底层人格与状态模型，不是固定脚本。

### Experiment Configuration

每轮先解析实验方式。少爷可以用自然语言表达，Agent 再内部归一化为稳定字段。不要要求少爷手写这些字段；只有在调试、导出或复盘配置时才展示字段。

没有提供时使用默认值：

```yaml
experiment_mode: goal_driven
path_spec: null
report_intent: opportunity_report
export_profile: default
```

自然语言解析：

| 少爷的说法 | 内部归一化 |
|---|---|
| “自由探索”“看用户会怎么找”“正常体验这个目标” | `experiment_mode=goal_driven` |
| “重点体验某入口 / 某链路 / 某路径”“大致经过 A、B、C” | `experiment_mode=path_constrained`，默认 `path_policy=anchored_corridor` |
| “严格按这条路径，不要走别的” | `path_policy=strict_replay` |
| “可以自然偏离，但要说明为什么” | `path_policy=guided_with_escape` |
| “中途可以关弹窗、看优惠、滑动、看图、返回修正” | 写入 `path_spec.allowed_detours` |
| “走不通、不支持目标、快碰到边界就停” | 写入 `path_spec.escape_conditions` |
| “重点看体验问题和机会点” | `report_intent=opportunity_report` |
| “重点复盘用户体验过程” | `report_intent=experience_report` |
| “输出调研洞察 / 研究结论” | `report_intent=research_report` |
| “后续要批量分析 / 回归分析” | `export_profile=aggregate_input` |
| “后续要做竞品对比” | `export_profile=benchmark_input` |

字段含义：

| 字段 | 取值 | 作用 |
|---|---|---|
| `experiment_mode` | `goal_driven` / `path_constrained` | 决定本轮是目标自由探索，还是指定路径约束体验 |
| `path_spec.path_policy` | `strict_replay` / `anchored_corridor` / `guided_with_escape` | 路径约束强度，仅 `path_constrained` 使用 |
| `report_intent` | `opportunity_report` / `experience_report` / `research_report` | 决定最终报告表达重点 |
| `export_profile` | `default` / `aggregate_input` / `benchmark_input` | 决定是否额外输出给批量聚合或竞品对比使用的结构化摘要 |

`report_intent` 只影响复盘表达，不影响操作层用户行为。`export_profile` 只影响结构化导出，不允许把批量或竞品逻辑塞进单轮行动循环。

`path_constrained` 不是点击脚本；路径策略、锚点、允许偏离和 `path_compliance` 见 `references/path-constrained-mode.md`。

### Mode Lock

`mode_lock` 防止本轮真实执行模式和少爷指定模式错配。它必须在开始操作前建立，并在报告中复核。

```yaml
mode_lock:
  requested_mode: goal_driven | path_constrained
  resolved_mode: goal_driven | path_constrained
  execution_mode: goal_driven | path_constrained | mixed | unknown
  mode_validity: valid | partial | invalid | not_applicable
  mismatch_reason:
  action_taken: continue | continue_with_downgrade | stop_for_invalid_mode
```

规则：

- 少爷说“重点体验某入口 / 某路径 / 大致经过 A、B、C”时，`requested_mode=path_constrained`。
- 若本轮实际没有建立锚点、没有按锚点体验，或执行成自由探索，`mode_validity=invalid`，不能用 `path_compliance=not_applicable` 当作有效路径报告。
- 模式错配时，产品体验结论最多是工具或流程线索；不能证明指定路径好或坏。
- 若工具或页面阻断导致路径无法执行，应记录阻断原因，而不是改成自由探索后继续输出原测试结论。

### Start State Validity

`start_state_validity` 判断实验起点是否匹配用户角色和实验目的。它不是工具状态记录，而是样本有效性的前置条件。

```yaml
start_state_validity:
  value: clean | contaminated | unknown
  entry_coverage: covered | partial | not_covered
  start_screen:
  contamination_signals:
    - history_detail
    - history_search
    - history_list
    - logged_in_old_account
    - recommendation_pollution
    - unknown
  action_taken: reset_to_home | reset_to_cold_start | continued_with_downgrade | stopped_for_invalid_sample
  impact_on_conclusion:
```

判断规则：

- 如果角色包含“首次使用”“新用户”“首装”“不了解平台”，而 App 起点落在历史商品详情、历史搜索页、历史列表、带明确历史推荐或老账号状态，默认 `start_state_validity=contaminated`。
- `goal_driven` 默认目标型体验若起点污染，不能把残留列表直接当成自由探索结果。应优先回到首页或自然入口重新开始；做不到时必须写 `entry_coverage=not_covered` 或 `partial`，并降级为 `directional_signal`。
- `path_constrained` 若起点污染但已回到路径锚点，可以继续，但 `path_compliance` 和样本有效性必须说明前置校正成本。
- 起点污染不是产品体验问题，除非它来自真实可复现的 App 恢复策略且与用户任务相关；默认归为样本限制。

硬门槛：

- 首次/新用户任务若无法回到首页、冷启动页或少爷指定的自然入口，默认 `entry_coverage=not_covered`，本轮不能输出完整新用户结论。
- `start_state_validity=contaminated` 且只做了“返回几步”的校正时，最多视为 `partial`，除非截图证明已经进入自然起点且历史推荐/搜索影响被消除。
- 污染起点下出现的搜索错配、推荐偏移或候选偏移，默认是 `single_run_signal` 或样本限制；不能直接写成强产品结论。
- 如果起点污染明显改变了候选池或路径，本轮 `sample_validity` 不能高于中。

### Persona Priors

`persona_priors` 描述这个用户进入 App 前的先验。

| 字段 | 说明 |
|---|---|
| `role` | 用户角色，例如首次使用转转、价格敏感的新用户 |
| `intent_strength` | 强目标、弱目标、浏览型、半探索型 |
| `knowledge_level` | 对品类、平台、术语、交易规则的熟悉度 |
| `price_sensitivity` | 对价格、优惠、补贴、低价排序的敏感程度 |
| `risk_sensitivity` | 对成色、质检、保障、售后、卖家可信度的敏感程度 |
| `patience_budget` | 愿意浏览、比较、修正路径、核验信息的耐心 |
| `trust_baseline` | 对平台、商家、二手交易、低价商品的初始信任 |
| `decision_style` | 快速满足型、谨慎比较型、风险规避型、机会探索型等 |

### Goal Parameter Map

`goal_parameter_map` 用来拆解用户给定目标。不要猜隐藏的“底层需求”；用户给出的目标就是目标。

```yaml
goal_parameter_map:
  fixed_constraints:
    - 用户明确给出的硬要求、评价标准、使用场景和安全边界
  primary_target_entity:
    - 用户给定的主要目标实体，例如 iPhone 17
  variable_entity_dimensions:
    - 机型代际
    - 标准版 / Pro / Pro Max
    - 容量
    - 成色
    - 价格档
    - 保障档
  non_pivotable_dimensions:
    - 不能被升级、降级或替换的固定约束
```

示例：`找到一台高性价比的二手 iPhone17，作为备用机` 中，`高性价比`、`二手`、`备用机` 是固定约束或评价标准；`iPhone17` 是主要目标实体；可被讨论升级、降级或横向替代的是机型、配置、成色、价格档、保障档等目标实体参数。

### Decision Concern Map

`decision_concern_map` 识别用户为了形成一个站得住的判断，会自然关心什么。它不只来自显性任务目标，也来自角色、品类、行业风险、当前页面线索和用户心理。

来源：

| 来源 | 示例 |
|---|---|
| 显性目标 | iPhone17、备用机、高性价比 |
| 用户角色 | 首次使用、价格敏感、新用户、风险规避 |
| 品类常识 | 二手手机要看瑕疵、成色、电池、维修、配件 |
| 行业风险 | 二手交易要看信任、保障、验机、售后、低价原因 |
| 当前页面线索 | BS机、短保、裸机、同成色低价、券门槛 |
| 用户心理 | 怕买贵、怕翻车、怕信息不透明、怕售后麻烦 |

`性价比` 不能简化为价格。通常应拆成：

```text
性价比 = 价格 + 状态 + 风险 + 保障 + 信任 + 使用场景匹配
```

记录格式：

```yaml
decision_concern_map:
  - concern_id:
    concern:
    source: explicit_goal | persona | category_norm | industry_risk | page_signal | user_psychology
    priority: high | medium | low
    user_question:
    decision_impact:
    evidence_needed:
```

示例：

| concern | source | priority | user_question | evidence_needed |
|---|---|---|---|---|
| 外观瑕疵与成色可信度 | category_norm | high | 99A 是否真的像新机 | 顶部图、实拍图、成色说明 |
| 低价原因 | page_signal | high | 为什么它比同款便宜 | 低价标签、报告、商品说明、候选对比 |
| 售后保障 | industry_risk | high | 翻车后谁负责 | 质检报告、保修、平台保障 |
| 到手价 | explicit_goal | medium | 优惠后是否更划算 | 券说明、补贴、最终价 |

### Evidence Seeking Behavior

`evidence_seeking_behavior` 判断用户会用什么自然方式验证关注点。它不是找最低成本路径，也不是补固定动作清单；它要判断在当前用户状态和页面语境下，哪种取证方式符合真实用户习惯，并能回答当前疑虑。

判断维度：

| 维度 | 含义 |
|---|---|
| `salience` | 当前屏幕上是否容易注意到 |
| `habit_fit` | 这个品类 / 场景下用户是否习惯这么确认 |
| `diagnostic_power` | 能否有效回答当前疑虑 |
| `trust_value` | 用户是否相信这个信息源 |
| `effort_acceptability` | 操作成本是否仍在用户耐心内，不代表越短越好 |

记录格式：

```yaml
evidence_seeking_behavior:
  concern_id:
  candidate_methods:
    - inspect_media
    - inspect_report
    - read_description
    - compare_candidates
    - inspect_price_and_coupon
    - inspect_policy_or_warranty
    - inspect_reviews_or_seller
  chosen_method:
  media_action:
    type: not_applicable | glance_cover | swipe_gallery | open_gallery | inspect_detail_image | watch_video | skipped
    scope:
    why_natural_or_skipped:
    evidence_refs:
  why_natural_for_user:
  evidence_status: not_seen | partially_seen | seen | contradicted | unavailable
  shortcut_risk: none | minor | major
```

常见取证方式：

| method | 适用场景 |
|---|---|
| `inspect_media` | 顶部图、实拍图、视频、图片预览，适合外观、瑕疵、配件、实物可信度 |
| `inspect_report` | 验机、质检、维修、拆修、电池、保障等结构化风险 |
| `read_description` | 商品说明、卖点、配置、配件、限制条件 |
| `compare_candidates` | 同款、同成色、不同价格、不同保障之间的取舍 |
| `inspect_price_and_coupon` | 券后价、补贴、满减门槛、到手价 |
| `inspect_policy_or_warranty` | 售后、保修、退换、平台保障 |
| `inspect_reviews_or_seller` | 评价、卖家信用、店铺可信度 |

二手高客单商品中，如果 `decision_concern_map` 存在高优先级的外观、瑕疵、配件或实物可信度关注点，而当前页面顶部媒体显眼，`inspect_media` 应成为自然候选动作。若没有执行，必须解释原因，并降低相关页面的 `local_information_maturity` 或结论级别。

`media_action` 用来记录用户具体如何取证，而不是规定必须滑几张图。只有当关注点、页面显著性和用户状态共同触发看图动机时，才执行 `glance_cover`、`swipe_gallery`、`open_gallery`、`inspect_detail_image` 或 `watch_video`；如果没有执行，写 `skipped` 并说明是用户自然忽略、证据已由报告覆盖、耐心不足、页面不可见、工具限制还是边界原因。

### Tool Friction Isolation

`tool_friction` 用来隔离工具层问题。它不是用户心智，也不能被包装成自然用户换路。

```yaml
tool_friction:
  occurred: yes | no
  type:
    - input_failed
    - click_no_effect
    - ui_tree_missing
    - screenshot_missing
    - mcp_device_missing
    - adb_unstable
    - app_launch_failed
    - other
  affected_step:
  intended_user_action:
  actual_tool_result:
  user_visible_equivalent:
  tool_friction_impact: none | minor | path_changed | blocking
  action_taken: retry | use_supported_input | continue_with_downgrade | stop_for_tool_failure
  evidence_refs:
```

规则：

- 中文输入失败、点击无反馈、UI 树缺失、截图缺失、MCP/ADB 异常必须先写入 `tool_friction`。
- 如果工具失败迫使 Agent 改走榜单、推荐、其他入口或不同路径，`tool_friction_impact=path_changed`，该路径不能当作真实用户自然偏好。
- 如果工具失败影响指定路径锚点，`mode_validity` 应为 `partial | invalid`，不能用自由探索补跑后证明指定路径。
- 工具问题可以产出复跑建议或工具层问题，但不能写成转转产品体验问题，除非有真机或多轮证据证明同样现象可复现。
- 点击无反馈要区分“用户尝试点击”和“工具点击点可能不准”。单轮模拟器点击无反馈默认是 `single_run_signal` 或 `tool_limited`，不能直接写强产品结论。

### Route Hypothesis

`route_hypothesis` 描述当前用户可能自然尝试的行为策略。路径不只是入口，也包括弹窗、权益、筛选、排序、看图、对比、返回、放弃等过程动作。

批量实验中若上游提供 `route_family`，它只能作为本轮用户先验或路径假设，不能覆盖当前页面和用户状态。路径差异必须能用角色、目标、关注点或页面线索解释，不能靠随机数本身解释。

示例：

```yaml
route_hypothesis:
  - name: 明确目标检索
    why_fit_persona: 用户有明确机型目标，可能先搜索
  - name: 低价机会探索
    why_fit_persona: 价格敏感用户可能被低价、补贴、活动或排序吸引
  - name: 商品状态核验
    why_fit_persona: 二手高客单商品需要核验瑕疵、成色、配件和质检
```

Agent 可以选择、放弃或切换路径，但每次切换都要由用户状态解释，而不是为了覆盖路径而覆盖。

### Attention Filter

`attention_filter` 约束操作层像真实用户。

| 字段 | 说明 |
|---|---|
| `salient_now` | 当前屏幕上视觉上突出、靠近任务、容易被注意的信息 |
| `noticed_by_user` | 已进入用户注意并影响下一步的信息 |
| `naturally_missed_in_action` | 操作层可能自然忽略的信息 |
| `global_evidence_available` | 复盘层可以使用的全局证据 |

“自然忽略”只约束操作层，不能限制分析层。复盘时必须从更全的证据视角判断体验问题和机会点。

### Dynamic User State

每一步后更新 `dynamic_user_state`。

| 字段 | 说明 |
|---|---|
| `candidate_set` | 用户当前记住或正在考虑的候选 |
| `concern_coverage` | 决策关注点哪些已被回答、哪些仍缺证据 |
| `evidence_seeking_state` | 用户已经通过哪些方式取证，哪些方式被放弃或未注意 |
| `confidence` | 对能否完成目标、是否值得继续的信心 |
| `trust` | 对平台、商品、价格、保障的信任变化 |
| `friction` | 理解成本、路径成本、等待成本、误点成本、打断成本 |
| `open_questions` | 仍影响判断的问题 |
| `effort_spent` | 用户已经付出的操作和理解成本 |
| `next_intent` | 用户下一步自然想确认、比较、返回、尝试或退出什么 |
| `local_information_maturity` | 当前候选池、页面或对比组的信息是否足以支持下一步 |
| `target_entity_shift_signal` | 是否出现升级、降级或横向替代信号 |

### Local Information Maturity

`local_information_maturity` 判断当前步骤、候选池、页面、媒体证据或对比组的信息是否足以支持下一步动作。它不用固定步数约束 Agent。

```yaml
local_information_maturity:
  scope: 当前列表 | 当前候选 | 当前详情页 | 当前媒体证据 | 当前弹窗/权益 | 当前对比组
  maturity: low | medium | high
  concern_coverage:
    covered:
    partially_covered:
    missing:
  evidence_coverage:
    media: not_needed | not_seen | partial | sufficient | contradictory
    report: not_needed | not_seen | partial | sufficient | contradictory
    price: not_needed | not_seen | partial | sufficient | contradictory
    warranty: not_needed | not_seen | partial | sufficient | contradictory
    comparison: not_needed | not_seen | partial | sufficient | contradictory
  seen_tradeoffs:
    - 已看到的价格、风险、保障、成色、配送、优惠等取舍
  missing_information:
    - 仍可能影响下一步判断的信息
  allowed_next_action:
    - continue_browsing
    - refine_filter
    - inspect_detail
    - inspect_media
    - inspect_report
    - inspect_auxiliary_info
    - compare_candidate
    - stop_defer
    - stop_buy_ready
    - stop_reject_ready
    - abandon_path
  why_enough_or_not_enough:
```

`maturity` 只表达信息成熟度，只能写 `low`、`medium`、`high` 三个稳定值。不能写成 `medium-high`、`low-medium`、`high enough for detail`、`medium for defer` 这类混合判断。动作许可写在 `allowed_next_action`，具体解释写在 `why_enough_or_not_enough`。例如 `maturity=medium` 也可能允许 `inspect_detail` 或 `inspect_media`，但不能因此变成 `medium-high`。

字段级硬规则：

- `maturity` 字段本身不能包含连字符、斜杠、中文修饰、`for`、`enough` 或动作含义。
- 如果介于两档之间，选择更保守的一档，例如 `medium`，并在 `why_enough_or_not_enough` 说明“接近 high 但仍缺什么”。
- 如果信息足以支持某个动作，不要把动作写进 `maturity`，写进 `allowed_next_action`。

`allowed_next_action` 只能使用上面列出的稳定枚举，不要自由创造同义动作。若想表达“拒绝最低价候选”，写成 `stop_reject_ready` 或 `compare_candidate`，并把具体含义放进 `why_enough_or_not_enough`。

禁止在任何主字段中输出 `high for reject`、`medium-high`、`low-medium`、`medium-high for defer`、`high enough for detail` 等混合成熟度值。若需要表达“信息足以拒绝”或“信息足以暂缓”，写成：

```yaml
maturity: high
allowed_next_action:
  - stop_reject_ready
why_enough_or_not_enough: 足以拒绝该候选
```

若高优 `decision_concern_map` 未被任何自然取证方式覆盖，只能继续自然探索、降低结论级别，或形成 `defer_ready` / `abandon`，不能输出强购买建议。

对最终候选要单独判断高优关注点覆盖。如果最终候选仍缺少外观 / 瑕疵 / 配件 / 质检 / 保障 / 评价中对该品类关键的证据，最多输出 `defer_ready`，并在 `stop_proof.what_user_still_does_not_know` 中写清缺口；不能写成 `buy_ready` 或强推荐。

### Decision Closure

`decision_closure` 判断用户最终状态是否真正闭合。它不是固定看几个商品，而是检查关键疑问是否被自然证据回答。

```yaml
decision_closure:
  status: closed | partial | open | not_applicable
  final_candidate:
  decisive_concerns_closed:
    - concern_id
  visible_alternatives_checked:
    - candidate_or_entry
  salient_alternatives_unchecked:
    - candidate_or_entry
  unresolved_blockers:
    - concern_id
  closure_basis:
  allowed_user_decision: buy_ready | reject_ready | defer_ready | abandon | not_formed
```

规则：

- `buy_ready` 要求 `decision_closure=closed`，或明确限定为“愿意进入购买前确认”，且没有足以改变判断的显著替代候选未看。
- 如果页面显著出现同成色低价、同款低价、关键升级款、同价更高保障候选，且它可能改变价格 / 风险 / 保障判断，未自然检视前不能直接 `buy_ready`。
- 如果最终候选仍缺关键媒体、报告、保障、配送、售后或瑕疵证据，`decision_closure` 只能是 `partial | open`。
- `reject_ready` 可以针对某个候选闭合，但不能自动代表全局目标失败；报告要说明拒绝对象是候选、路径还是目标。
- `defer_ready` 需要说明是“关键缺口已暴露，当前路径不值得继续”还是“有候选但还未闭合”。前者可以 `decision_status=reached`，后者应考虑 `not_formed` 或降级。
- `decision_status=reached` 不等于决策充分；必须同时看 `decision_closure` 和 `conclusion_level`。

### Target Entity Shift

`target_entity_shift` 记录用户是否围绕目标实体发生升级、降级或横向替代。它不是跑偏记录，而是用户重新校准目标实体的体验信号。

```yaml
target_entity_shift:
  occurred: yes | no
  shift_type: none | downgrade | upgrade | lateral
  changed_parameters:
  fixed_constraints_preserved:
  trigger_evidence:
  user_reason:
  shift_permission: none | reference_only | light_explore | active_pivot | recommend_pivot
  product_interpretation:
  related_experience_problem:
  related_opportunity:
  validation_needed:
```

升级、降级或横向替代只允许发生在 `variable_entity_dimensions` 上，不能改变固定约束、评价标准、使用场景和安全边界。

进入 `active_pivot` 或 `recommend_pivot` 需要同时满足：

- 原目标实体的信息成熟度足以判断它被挑战。
- 替代实体更能满足固定约束和评价标准。
- 变更不触碰安全边界，也不改变使用场景。
- 有明确截图、候选对比或路径证据支撑。

报告中必须分析目标实体变更的产品含义：这是产品帮助用户发现更优解，还是原目标承接不足、风险解释不足、推荐干扰过强、对比能力不足造成的偏移。

### Decision Policy

`decision_policy` 决定什么时候可以停。

| 用户状态 | 含义 |
|---|---|
| `buy_ready` | 用户愿意买或愿意进入购买前动作，但仍不能触碰安全边界 |
| `reject_ready` | 用户明确不买、不推荐或排除当前方案 |
| `defer_ready` | 用户觉得可关注或有候选，但需要后续确认，不会立刻买 |
| `abandon` | 用户因体验成本、信任损失或路径挫败自然退出 |
| `not_formed` | 用户还没有形成可解释的判断 |
| `not_applicable` | 工具或观察失败导致用户模拟没有有效发生 |

不要用固定动作数量证明“充分”。停止必须由 `dynamic_user_state` 和 `stop_proof` 解释：用户知道了什么、还不知道什么、为什么此刻停止像真实用户，而不是 Agent 偷懒。

`buy_ready` 不是“看起来不错”。它要求 `decision_closure=closed`，或报告明确限定为“愿意进入购买前确认但仍需购买链路内确认”。若存在未检视的显著同成色低价、同款低价、关键保障差异或会改变判断的媒体/报告缺口，默认不能输出 `buy_ready`。

`defer_ready` 也要闭合对象：如果用户只是还没看够，应该继续探索或输出 `not_formed`；如果用户已经知道关键缺口、风险或路径不适配，并自然选择暂缓，才可以 `defer_ready`。

`stop_proof.stop_basis` 用来解释停止的直接依据：

| stop_basis | 说明 |
|---|---|
| `decision_threshold_met` | 用户已经形成买 / 不买 / 暂缓 / 放弃状态 |
| `marginal_value_low` | 继续探索收益明显下降，核心判断已足够支撑当前用户状态 |
| `evidence_gap_exposed` | 已暴露关键证据缺口，继续也无法在当前路径低成本补足 |
| `boundary_near` | 下一步明确会触发或高度接近支付、提交订单、实名、绑卡、客服、资料修改等边界 |
| `user_patience_exhausted` | 以该角色的耐心，继续成本过高，会自然退出或放弃 |
| `tool_limit` | 工具层限制影响继续观察或操作 |
| `observation_limit` | 页面、截图、UI 树或录屏证据不足以继续形成可靠判断 |
| `max_steps_reached` | 达到本轮步数上限 |

如果使用 `boundary_near`，必须说明具体是哪一个下一步会触碰边界。不能把普通查看优惠、打开券说明、比较券后价、看保障说明、看评价、看更多图片、看其他候选、返回列表对比写成边界。若只是继续探索收益降低，应使用 `marginal_value_low`；若是关键证据缺口已经暴露，应使用 `evidence_gap_exposed`。

### Stop Decision Split

停止判断必须拆成“用户状态”和“停止触发”。安全边界可以让实验停下，但不能自动证明用户自然暂缓。

```yaml
stop_decision_split:
  user_state:
    decision_status:
    user_decision:
    user_state_basis:
  stop_trigger: natural_decision | safety_boundary_near | user_boundary_near | tool_limit | observation_limit | max_steps_reached | no_progress
  boundary_influence: none | possible | material | blocking
  counterfactual_without_boundary: would_buy | would_continue | would_defer | would_reject | would_abandon | unknown
  product_interpretation:
```

判断规则：

- `user_decision` 表达用户形成了什么状态；`stop_trigger` 表达实验为什么停。
- 如果下一步是支付、提交订单、联系客服、修改资料、实名、绑卡等边界，填写 `stop_trigger=safety_boundary_near` 或 `user_boundary_near`，并判断 `boundary_influence`。
- 如果用户已经明确“不买 / 暂缓 / 放弃”，即使附近有购买按钮，也可以是 `boundary_influence=none | possible`；如果用户其实还想继续到购买前确认，只是被边界拦住，不能把它包装成自然 `defer_ready`。
- `counterfactual_without_boundary` 必须回答：如果没有少爷禁止边界，这个用户更可能买、继续探索、暂缓、拒绝、放弃，还是不可判断。
- 当 `boundary_influence=material | blocking` 时，默认不能输出强体验结论；应说明这是边界限制下的用户状态。

### Evidence Strength

每个体验问题、机会点和关键洞察都要标注证据强度，避免报告模板把单次线索包装成强结论。

```yaml
evidence_strength:
  level: strong_evidence | single_run_signal | agent_inference | tool_limited
  scope: flow_evidence | decision_evidence | product_pattern
  basis:
  evidence_refs:
  validation_needed:
```

取值说明：

| level | 说明 |
|---|---|
| `strong_evidence` | 多个步骤、明确截图/录屏/UI 树、用户状态变化共同支撑 |
| `single_run_signal` | 本轮出现过，有证据，但只有单次样本或单一场景 |
| `agent_inference` | 由角色、品类常识和页面信息推断，过程证据较弱 |
| `tool_limited` | 主要受模拟器、UI 树失败、账号污染、截图缺失等影响 |

如果问题只由 `agent_inference` 或 `tool_limited` 支撑，机会点可以作为假设，但不能写成强产品结论。

分层规则：

- `flow_evidence` 说明某个路径、点击、页面承接或工具观察事实是否成立。
- `decision_evidence` 说明这些事实是否足以支撑用户买、不买、暂缓或放弃。
- `product_pattern` 说明它是否可作为产品层面的模式判断。
- 流程证据强，不等于决策证据强。例如“搜索进入了错误结果页”可以是强流程证据，但在污染起点或单轮样本下，产品模式仍可能只是 `single_run_signal`。
- 单轮模拟器证据默认不能直接写 `product_pattern=strong_evidence`；除非同一轮有多处证据链、用户状态变化和明确复现线索，并说明仍需真人或真机验证。
- `start_state_validity=contaminated`、`tool_friction_impact=path_changed` 或 `sample_validity=低` 时，产品机会点默认不高于 `single_run_signal`。

### Friction Response

遇到弹窗、权益、提示、排序、筛选、评价、质检、保障、低价卡片、无反馈、加载慢等情况时，先判断它对角色、目标和关注点的意义。

| 反应 | 适用场景 |
|---|---|
| `inspect` | 信息可能影响价格、风险、保障、信任或决策 |
| `use` | 领券、筛选、排序、对比等动作对目标明显有帮助且不触碰红线或少爷明确边界 |
| `ignore` | 和当前关注点弱相关，或用户没有耐心处理 |
| `close` | 打断明显，用户想回到主任务 |
| `backtrack` | 当前路径偏离目标或成本变高 |
| `abandon_path` | 路径持续低效，用户自然换方向或退出 |
| `stop_for_boundary` | 命中支付、下单、资料修改、客服等边界 |

普通运营弹窗、活动、优惠、领券、补贴、筛选、排序、对比、行情、保障说明默认不是红线，由用户角色和任务目标决定是否操作。查看优惠、打开券说明、比较券后价、领取普通可放弃权益，默认属于体验路径；如果少爷明确写了“不领券”，则只能查看说明或在领券动作前按 `user_boundary` 停止。涉及高价值不可逆权益、支付、下单、绑卡、实名、开通付费会员、真实履约时，按安全边界处理。

## Action Generation Loop

每一步按这个循环执行：

1. `Observe`：用截图、UI 树、页面文本、前台包名观察当前状态。
2. `Notice`：判断该用户当前大概率注意到什么。
3. `Interpret`：判断用户如何理解、误解、困惑、信任、犹豫或被打断。
4. `Update Concerns`：更新 `decision_concern_map` 中哪些关注点被触发、提升或降低优先级。
5. `Plan Evidence Seeking`：判断当前页面上哪些取证方式自然、可信、有诊断力。
6. `Assess Tool Friction`：若工具动作失败或改变路径，先隔离为 `tool_friction`。
7. `Update State`：更新候选、信心、信任、摩擦、未解问题和下一意图。
8. `Assess Local Maturity`：判断当前候选池、页面、媒体证据或对比组是否足以支持下一步动作。
9. `Assess Decision Closure`：判断最终候选、显著替代和关键证据是否已闭合。
10. `Assess Target Entity Shift`：若出现升级、降级或横向替代信号，判断是否只作参考、轻量探索或允许转向。
11. `Decide`：判断是否已形成 `user_decision`，或是否需要继续。
12. `Choose Action`：选择符合用户状态、关注点和自然取证方式的动作。
13. `Safety Check`：检查是否触碰安全边界或少爷设定边界。
14. `Act & Record`：执行动作并保存前后证据。
15. `Stop Check`：如果停止，补全 `stop_reason`、`stop_basis` 和 `stop_proof`。

## Step Record Contract

过程导出中每步都要有 `step_record`；结果报告只展示关键步骤。

```yaml
step_record:
  step:
  screen:
  observe_summary:
  noticed_by_user:
  interpreted_as_user:
  decision_concern_update:
  evidence_seeking_behavior:
  media_action:
  state_before:
    confidence:
    trust:
    friction:
    open_questions:
  action:
  why_this_action_is_natural:
  safety_check:
  state_after:
    confidence:
    trust:
    friction:
    open_questions:
  local_information_maturity:
  decision_closure:
  tool_friction:
  target_entity_shift_signal:
  evidence_refs:
  shortcut_risk: none | minor | major
```

如果动作依赖 UI 树全知视角、顶部锚点、隐藏结构或过度高效路径，必须标记 `shortcut_risk`，并在结论可信度里降级说明。

## Outcome Contract

主结果契约使用以下字段，不再使用旧版 `goal_result` 二分字段作为主结果。

```yaml
experiment_mode: goal_driven | path_constrained
path_policy: strict_replay | anchored_corridor | guided_with_escape | not_applicable
report_intent: opportunity_report | experience_report | research_report
export_profile: default | aggregate_input | benchmark_input
decision_status: reached | not_reached | not_applicable
user_decision: buy_ready | reject_ready | defer_ready | abandon | not_formed | not_applicable
stop_reason: decision_threshold_met | effort_exhausted | safety_boundary | user_boundary | tool_failure | observation_failure | max_steps | no_progress
observation_quality: full | degraded | failed
conclusion_level: formal_finding | directional_signal | tool_failure_record
tool_constraint_impact: none | minor | major | blocking
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
  evidence_refs:
path_compliance:
  status: followed | followed_with_correction | partial | deviated_with_correction | escaped | blocked | invalid | not_applicable
start_state_validity: clean | contaminated | unknown
entry_coverage: covered | partial | not_covered
stop_trigger: natural_decision | safety_boundary_near | user_boundary_near | tool_limit | observation_limit | max_steps_reached | no_progress
boundary_influence: none | possible | material | blocking
```

### Contract Invariants

- 如果 `user_decision` 是 `buy_ready`、`reject_ready`、`defer_ready` 或 `abandon`，则 `decision_status` 必须是 `reached`。
- 如果 `user_decision=not_formed`，则 `decision_status` 必须是 `not_reached`。
- 如果 `user_decision=not_applicable`，则 `decision_status` 必须是 `not_applicable`。
- 如果 `stop_reason=tool_failure`，则 `decision_status=not_applicable`、`user_decision=not_applicable`、`observation_quality=failed`、`conclusion_level=tool_failure_record`、`tool_constraint_impact=blocking`。
- 如果 `stop_reason=observation_failure`，则 `conclusion_level` 不能是 `formal_finding`，除非有强截图或录屏证据并写明例外理由。
- 如果 `stop_reason=safety_boundary` 或 `user_boundary`，不强制 `user_decision=not_formed`；边界可能发生在用户形成判断之前或之后。
- 如果 `user_decision=abandon`，则 `stop_reason` 通常应是 `effort_exhausted` 或 `no_progress`，并说明体验成本或信任损失。
- 如果 `tool_constraint_impact=major`，默认 `conclusion_level=directional_signal`。
- 如果 `tool_friction_impact=path_changed | blocking`，则 `tool_constraint_impact` 至少为 `major`，且不能把替代路径写成自然用户偏好。
- 如果 `mode_validity=invalid`，本轮不能证明指定路径有效；`conclusion_level` 不能是 `formal_finding`。
- 如果少爷要求 `path_constrained` 但实际执行为 `goal_driven`，则 `mode_validity=invalid`，`path_compliance.status=invalid`，不能写 `not_applicable`。
- 如果 `experiment_mode=goal_driven`，则 `path_compliance.status=not_applicable`。
- 如果 `experiment_mode=path_constrained`，必须输出 `path_compliance`，并说明锚点、偏离和路径适配。
- 如果角色是首次/新用户且 `start_state_validity=contaminated`，必须说明是否重置到自然起点；若 `entry_coverage=not_covered`，不能写成完整新用户体验结论。
- 如果 `decision_closure=open | partial`，默认不能输出 `user_decision=buy_ready`；例外只能是“愿意进入购买前确认”，且必须说明未闭合项不会阻止进入购买前确认。
- 如果 `self_correction_cost=high`、目标漂移、关键锚点错位或多次逃离冲动出现，`path_compliance.status` 不能是单纯 `followed`。
- 如果停止接近安全或用户边界，必须输出 `stop_decision_split`，并说明 `counterfactual_without_boundary`。
- 体验问题、机会点和关键洞察必须标注 `evidence_strength`。
- `report_intent` 只能改变报告重点，不能改变用户行动。
- `export_profile=aggregate_input | benchmark_input` 时，必须输出 `structured_summary` 或 `summary.json`。

`run_outcome` 和 `legacy_goal_result` 只能作为派生摘要或兼容附录，不能放进主摘要，也不能驱动 Agent 行为。

## Structured Summary

当 `export_profile` 不是 `default`，输出给下游使用的结构化摘要。它可以作为 Markdown 中的 JSON 代码块，也可以保存为 `summary.json`。

```yaml
structured_summary:
  run_id:
  scenario_id:
  app_id:
  persona_id:
  task_id:
  experiment_mode:
  path_policy:
  report_intent:
  export_profile:
  decision_status:
  user_decision:
  stop_reason:
  observation_quality:
  conclusion_level:
  tool_constraint_impact:
  mode_validity:
  tool_friction_impact:
  decision_closure:
  sample_validity:
  behavior_fidelity:
  start_state_validity:
  entry_coverage:
  stop_trigger:
  boundary_influence:
  path_compliance:
    goal_support:
    decision_support:
    self_correction_cost:
  issue_tags:
  friction_tags:
  trust_gap_tags:
  evidence_quality:
  evidence_refs:
```

`structured_summary` 只做下游聚合和对比输入，不替代体验报告，也不能输出没有证据支撑的标签。

## Anti-Script Rules

不要把真实用户模拟写成硬脚本。

- 不用固定入口、固定路径、固定动作数量证明行为充分。
- 不把某个动作集合当成所有角色都必须执行的清单。
- 不为了显得“覆盖充分”而做用户不会自然做的操作。
- 不为了尽快结束而跳过用户自然会经历的理解、比较、核验、犹豫或放弃。
- 不把搜索、分类、推荐、活动、弹窗、权益等任何单一路径预设为唯一合理路径。
- 不把 `inspect_media` 写成固定滑几张图；它必须由关注点和自然取证方式触发。

## Behavior Assessment

输出 `behavior_assessment`，比单一 `behavior_fidelity` 更能解释本轮是否像真实用户。

| 字段 | 取值 | 说明 |
|---|---|---|
| `persona_consistency` | 高 / 中 / 低 | 行动是否符合角色先验 |
| `concern_realism` | 高 / 中 / 低 | 是否覆盖了真实用户、品类和行业会关心的事 |
| `evidence_behavior_authenticity` | 高 / 中 / 低 | 取证方式是否符合真实用户习惯 |
| `path_authenticity` | 高 / 中 / 低 | 路径选择和切换是否自然 |
| `decision_sufficiency` | 高 / 中 / 低 | 停止时证据是否足以支撑用户状态 |
| `shortcut_risk` | 无 / 轻微 / 明显 | 是否存在工具化捷径 |

兼容输出 `behavior_fidelity`，但它应由上述六项综合得出。

交叉校验：

- 若 `decision_closure=open | partial` 且用户状态写成 `buy_ready`，`decision_sufficiency` 不能为高。
- 若存在 `tool_friction_impact=path_changed | blocking`，`path_authenticity` 不能为高。
- 若显著候选、同成色低价、关键图证或报告证据未自然检视，`evidence_behavior_authenticity` 不能为高。
- 若 `shortcut_risk=明显`，`behavior_fidelity` 不能为高。
- `sample_validity` 不等于 `behavior_fidelity`：污染样本里行为可以像用户，但产品结论仍必须降级。

## Evidence Chain

体验问题和机会点必须沿这条链路成立：

```text
证据 -> 过程体验点 -> 体验问题 -> 产品机会点
```

允许使用 `global_evidence` 发现问题，但必须说明用户当时是否注意到。不要把“用户没注意到”写成“页面不存在”。

## Sample Validity（样本有效性）

输出 `sample_validity`，用于判断本轮是否匹配角色和实验目的。

| 维度 | 说明 |
|---|---|
| 设备 | 真机、模拟器、云真机 |
| 账号 | 清洁新用户、已登录老账号、不确定 |
| App 状态 | 是否有历史搜索、消息数、推荐污染、缓存 |
| 角色匹配 | 当前环境是否符合用户角色 |
| 结论用途 | 工具链验证、低成本线索、正式体验结论 |

任务走完不等于样本有效。比如目标完成但账号不是清洁新用户，应标注角色匹配不足。

## Tool Quality

工具层失败不能写成产品体验问题。

| 场景 | 报告口径 |
|---|---|
| ADB / MCP / 截图失败 | `stop_reason=tool_failure`，`conclusion_level=tool_failure_record` |
| UI 树不可读但截图可见 | `observation_quality=degraded`，可作为方向性线索 |
| 模拟器证据 | 可用于流程预检和低成本线索，高优结论建议真机复核 |
| 工具化动作影响路径 | 在 `shortcut_risk` 和结论可信度中说明 |

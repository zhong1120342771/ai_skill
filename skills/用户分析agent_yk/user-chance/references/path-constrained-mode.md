# Path Constrained Mode

本文档用于 `experiment_mode=path_constrained` 的单轮体验实验。它只定义指定路径如何约束用户模拟，不负责批量、竞品或 Runner。

## 核心原则

```text
path_constrained 不是点击脚本。
```

产品指定的是路径锚点或体验链路，Agent 仍要在锚点内模拟真实用户如何注意、理解、犹豫、取证、建立信任或产生逃离意图。

## 自然语言输入

少爷不需要说 `path_policy`、`anchors`、`allowed_detours` 或 `escape_conditions`。少爷可以直接说：

```text
这次重点体验首页活动入口这条路径。
大致经过：首页、活动入口、活动承接页、商品列表、商品详情。
中途允许像真实用户一样处理弹窗、看优惠、滑动列表、看商品图、返回修正。
如果这条路径明显不支持目标，或者快碰到下单 / 支付 / 客服 / 资料修改边界，就停并说明。
```

Agent 内部再把它归一化为路径锚点、允许绕路和逃离条件。除非少爷要求查看配置或复制给其他 Agent，不要把 YAML 当成少爷必须输入的话术。

## 内部结构

```yaml
experiment_mode: path_constrained
path_spec:
  path_policy: strict_replay | anchored_corridor | guided_with_escape
  anchors:
    - string
  allowed_detours:
    - string
  escape_conditions:
    - string
```

默认建议使用 `anchored_corridor`。

## 自然语言映射

| 少爷的说法 | 内部处理 |
|---|---|
| “重点体验这条路径”“大致经过这些页面” | 使用 `anchored_corridor` |
| “严格按这条路径走” | 使用 `strict_replay` |
| “可以自然偏离，但要说明原因” | 使用 `guided_with_escape` |
| “大致经过：首页、活动入口、商品详情” | 转成 `anchors` |
| “允许关弹窗、看优惠、滑图、返回修正” | 转成 `allowed_detours` |
| “走不通、不支持目标、快碰到边界就停” | 转成 `escape_conditions` |

## 路径策略

| path_policy | 含义 | 适用场景 |
|---|---|---|
| `strict_replay` | 严格按指定路径走，只处理弹窗、登录、遮挡、权限等阻断 | 验证固定链路本身是否可理解、可完成 |
| `anchored_corridor` | 必须经过指定关键节点，但节点内可自然查看、滚动、取证、返回修正 | 验证产品设计路径是否支持用户形成判断 |
| `guided_with_escape` | 有指定方向，但用户自然想偏离时可偏离并记录原因 | 验证路径是否符合真实用户心智 |

## 允许的自然动作

除非少爷另有边界，路径约束下默认允许：

- 关闭或处理阻断弹窗。
- 滚动当前页。
- 横滑或打开当前页内媒体。
- 查看当前页内明显说明、保障、价格、优惠或评价。
- 返回上一个锚点。
- 记录“用户想偏离但路径不允许”。
- 在安全边界内做轻量取证。

## 不应默认允许的动作

除非 `path_policy` 或少爷明确允许，不要：

- 跳到完全不同入口。
- 主动搜索替代商品。
- 跨越路径锚点。
- 为了达成目标绕开指定路径。
- 把路径约束实验改成自由探索。

## 偏离判断

如果用户状态显示路径无法支持目标，Agent 可以按策略处理：

| 情况 | 处理 |
|---|---|
| `strict_replay` | 记录想偏离但不执行，继续或停止 |
| `anchored_corridor` | 优先回到锚点，在锚点内补自然取证 |
| `guided_with_escape` | 可以偏离，但必须记录原因、证据和对结论的影响 |

偏离不是失败。它可能说明产品设计路径不符合用户心智，或者路径缺少关键证据。

## path_compliance 输出

路径约束模式必须输出：

```yaml
path_compliance:
  status: followed | followed_with_correction | partial | deviated_with_correction | escaped | blocked | invalid | not_applicable
  anchor_results:
    - anchor:
      reached: true | false
      evidence_refs:
      user_reaction:
  deviations:
    - step:
      reason:
      was_allowed: true | false
      evidence_refs:
  path_fit_assessment:
    supports_user_goal:
    goal_support: high | medium | low
    decision_support: high | medium | low
    self_correction_cost: none | low | medium | high
    forced_points:
    escape_desires:
    path_level_friction:
    path_goal_fit:
      natural_for_persona:
      supports_discovery:
      supports_comparison:
      supports_trust_building:
      only_reached_anchors:
```

字段说明：

| 字段 | 说明 |
|---|---|
| `status` | 路径真实执行状态，不能只按锚点是否到达判断 |
| `goal_support` | 这条路径是否支持用户完成目标，不等于锚点是否到达 |
| `decision_support` | 这条路径提供的信息是否足以让用户形成买 / 不买 / 暂缓判断 |
| `self_correction_cost` | 用户为了让路径服务目标，需要多少排序、筛选、返回、换方向等自我修正 |
| `path_goal_fit.natural_for_persona` | 这条路径是否像该角色会自然选择的路径 |
| `path_goal_fit.supports_discovery` | 是否支持发现合适候选 |
| `path_goal_fit.supports_comparison` | 是否支持形成候选比较 |
| `path_goal_fit.supports_trust_building` | 是否支持建立价格、风险、保障信任 |
| `path_goal_fit.only_reached_anchors` | 是否只是到达了节点，但没有真正帮助判断 |

`status` 判定：

| status | 何时使用 |
|---|---|
| `followed` | 锚点自然到达，低修正成本，路径本身支持目标发现、比较和信任建立 |
| `followed_with_correction` | 锚点到达，但存在轻中度返回、筛选或解释成本 |
| `partial` | 部分锚点到达，或路径支持目标有限，只能形成方向性判断 |
| `deviated_with_correction` | 用户为了让路径服务目标，被迫进行明显类目修正、入口修正、筛选修正或候选方向修正 |
| `escaped` | 用户自然离开指定路径，转向其他入口或停止路径评估 |
| `blocked` | 页面、登录、权限、边界或工具阻断导致无法继续 |
| `invalid` | 少爷要求指定路径，但实际未按路径模式执行，或执行记录不足以判断路径 |
| `not_applicable` | 本轮本来就是自由探索，没有指定路径要求 |

降级规则：

- `self_correction_cost=high` 时，不能写 `status=followed`。
- 出现目标漂移、关键锚点错位、活动/榜单落地到无关品类、多次逃离冲动时，优先使用 `partial`、`deviated_with_correction` 或 `escaped`。
- 如果最终候选来自路径外的搜索、榜单修正或工具失败后的替代入口，`goal_support` 默认不高于 `low | medium`，并说明该结论不是原路径自然贡献。
- 指定路径跑成自由探索时，`status=invalid`，不能写 `not_applicable`。
- `entry_coverage` 要区分“入口被尝试”和“入口有效承接”。点击入口无反馈不能算完整 covered。

## 报告重点

`path_constrained` 报告重点不是“是否按路线走完”，而是：

- 这条路径是否符合用户自然心智。
- 每个锚点是否提供足够信息。
- 用户是否想偏离路径。
- 用户是否被迫通过排序、筛选、返回、跨品类/跨机型等方式自我修正。
- 路径是否自然服务目标，还是只是被 Agent 按锚点走完。
- 哪些节点显得强行或断裂。
- 哪些节点建立信任。
- 哪些节点增加困惑、风险感或努力成本。

如果路径走完但用户没有形成可信判断，不能写成体验成功；应说明路径支持不足或证据缺口。

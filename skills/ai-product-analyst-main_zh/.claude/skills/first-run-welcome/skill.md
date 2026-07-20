# Skill: First-Run Welcome

## 用途
基于配置状态提供自适应的欢迎体验。把新用户引导到 `/setup` 进行向导式上手。对回访用户则用当前激活数据集的背景信息和快捷动作来迎接。

## 何时使用
- 会话开始（由 Knowledge Bootstrap 触发）
- 任何分析工作开始之前

## 操作步骤

### 第 1 步：检测配置状态

读取 `.knowledge/setup-state.yaml`。归入以下三种状态之一：

1. **冷启动** —— 文件不存在，或 `setup_complete: false` 且没有
   `phases_completed`（为空或缺失）。
2. **部分配置** —— 文件存在，`setup_complete: false`，且 `phases_completed`
   中至少有一项。
3. **热启动** —— 文件存在且 `setup_complete: true`。

### 第 2 步：按状态路由

---

#### 冷启动（无 setup-state.yaml，或 setup_complete: false 且无已完成阶段）

呈现以下欢迎语并路由到 `/setup`：

```
Welcome to AI Analyst — your analytical partner for product teams.

I help you turn business questions into validated insights, charts, and
presentations. Think funnel analysis, segmentation, root cause investigation,
trend detection — from question to slide deck.

Let's get you set up. I'll walk you through a quick interview to learn about
your data, your role, and what you want to analyze.

Starting setup now...
```

然后调用 `/setup` 开始向导式访谈。不要展示数据集信息、
教程内容或示例查询。配置流程会处理所有上手事宜。

---

#### 部分配置（部分阶段完成，配置未结束）

从 `.knowledge/setup-state.yaml` 读取 `phases_completed` 和 `phases_remaining`。

```
Welcome back! Your setup is partially complete.

Done: [list phases_completed]
Remaining: [list phases_remaining]

Want to pick up where you left off? Type `/setup` to resume, or ask me
a question if you'd rather dive in.
```

---

#### 热启动（setup_complete: true）

从以下位置读取上下文：
- `.knowledge/active.yaml` → `active_dataset` 名称
- `.knowledge/datasets/{active}/manifest.yaml` → 表数量
- `.knowledge/analyses/index.yaml` → `last_updated` 作为上次分析日期

```
Welcome back! Here's where things stand:

Dataset: [DATASET_NAME] ([N] tables)
Last analysis: [DATE or "none yet"]

Quick actions:
- Ask a question — "What's our conversion rate by channel?"
- /explore — interactive data exploration
- /run-pipeline — full analysis from question to deck

What would you like to work on?
```

如果 `active_dataset` 为 null（配置已完成但未连接数据），展示：

```
Welcome back! Setup is complete but no dataset is active yet.

- /connect-data — add a dataset
- /datasets — see available datasets

What would you like to do?
```

### 第 3 步：继续

呈现欢迎语后：
- **冷启动：** 交接给 `/setup`。不要继续分析。
- **部分配置：** 如果用户输入 `/setup`，交接。如果用户提问，
  走 Question Router，并提示配置可稍后完成。
- **热启动：** 如果用户提问，走 Question Router。
  如果用户选了某个快捷动作，调用对应的 skill/agent。

## 反模式

1. **绝不向已输入问题的热启动用户展示欢迎语。** 如果他们的
   第一条消息是问题，直接回答 —— 把一句 "welcome back" 自然地融入。
2. **绝不在冷启动时展示数据集明细或教程内容。** 上手全部由
   `/setup` 流程处理。
3. **绝不用功能清单淹没用户。** 每种欢迎变体都保持简洁。
4. **绝不引用 NovaMart、bootcamp 或 workshop 内容。** 这是一个
   通用工具，不是课程。
5. **绝不在欢迎环节阻塞。** 如果用户已经提了问题，就服务它 ——
   把欢迎语围绕其意图来调整。

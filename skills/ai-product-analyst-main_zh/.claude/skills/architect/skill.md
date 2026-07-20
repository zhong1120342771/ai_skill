# Skill: /architect

运行多角色规划方法论，为新项目或新功能产出一份主规划（master plan）。

## 参数

- **brief**（必填）：我们要构建什么？可以是一句话、一段话，或者 "read [file]" 从已有文档中拉取。
- **--personas**（可选）：覆盖角色数量。默认：5。
- **--skip-debate**（可选）：跳过 Phase 2 的辩论，直接进入综合阶段。更快但质量更低。
- **--output-dir**（可选）：规划写到哪里。默认：从项目上下文自动检测。

## 触发短语

- `/architect Build a centered-person thumbnail template`
- `/architect "Add YouTube upload to the podcast pipeline"`
- `/architect read evals-course/BUILD_PLAN.md`
- `architect a new email drip sequence for cohort 4`

## 方法论

该 skill 实现 `shared/PLANNING_METHODOLOGY.md`。完整工作流：

```
Phase 0  Scope & Persona Selection     → define brief, pick 3-5 expert personas
Phase 1  Independent Plans (Round 1)   → all personas plan in parallel
Phase 2  Debate & Critique             → single moderator resolves conflicts
Phase 3  Revised Plans (Round 2)       → personas revise in parallel
Phase 4  Alignment & Synthesis         → single architect produces master plan
Phase 5  Build Status Tracker          → CREATE BUILD_STATUS.yaml
```

## 执行

### 1. 解析 brief

如果用户提供了文件路径或 "read [file]"，把该文件作为项目 brief 读取。
否则，直接使用他们提供的文本。

如果 brief 过于模糊（少于 20 词，没有明确交付物），先问一个澄清问题再继续。

### 2. 确定输出目录

寻找上下文线索：
- 如果 brief 提到某个具体项目（podcast、analytics、evals 等），使用该项目的目录
- 如果附近已存在 `working/plans/` 目录，使用它
- 否则，在最相关的项目目录里创建 `working/plans/`
- 如果实在含糊，询问用户

设定：
- `PLANS_DIR`：`{project}/working/plans/`
- `MASTER_PLAN_PATH`：`{project}/MASTER_PLAN.md`（或 `{PROJECT_NAME}_MASTER_PLAN.md`）

### 3. Phase 0：范围与角色选择

阅读 `shared/PLANNING_METHODOLOGY.md` 获取完整方法论参考。

基于 brief，选出 3-5 个角色。以方法论中的原型表作为起点，但要针对具体项目定制角色。例如：
- 缩略图项目可能需要：CTR Optimizer、Frontend Renderer、Brand Compositor、Pipeline Architect
- 课程项目可能需要：Curriculum Designer、Student Advocate、Technical Author、Platform Specialist

把这些角色呈现给用户：

```
Project: [brief summary]
Output: {MASTER_PLAN_PATH}

Personas:
1. [Name] — [Role]. Cares about: [focus]. Will challenge: [what].
2. ...

Proceed with these personas? (a) Yes (b) Swap one out (c) Add/remove
```

等待批准后再启动 Phase 1。

### 4. Phase 1：独立规划（Round 1）

用 Task 工具 **并行** 启动所有角色 agent。每个角色得到：
- 项目 brief
- 其角色描述和视角
- brief 中提到的任何参考文件或示例
- 把规划写到 `{PLANS_DIR}/round1/{persona-slug}.md` 的指示

每个角色产出：
1. 需要构建什么（其领域内）
2. 应如何组织结构
3. 阶段/波次
4. 对其他领域的依赖
5. 风险和未知项
6. 他们会反对什么

等待所有角色完成。

### 5. Phase 2：辩论与批判

如果带 `--skip-debate`：跳到 Phase 4。

启动 **单个辩论 agent**，接收全部 Round 1 规划。它识别：
- 共识（2+ 角色一致）
- 冲突（不兼容的方案）
- 缺口（无人涉及）
- 带理由的解决方案

输出：`{PLANS_DIR}/debate-summary.md`

### 6. Phase 3：修订规划（Round 2）

再次 **并行** 启动所有角色 agent。每个角色接收：
- 自己的 Round 1 规划
- 辩论总结
- 修订并写到 `{PLANS_DIR}/round2/{persona-slug}.md` 的指示

### 7. Phase 4：综合

启动 **单个综合 agent**，接收全部 Round 2 规划 + 辩论总结。

产出主规划，包含以下小节：
1. Executive Summary
2. Wave Structure（汇总表）
3. Detailed Waves（带 ID、文件、依赖的任务规格）
4. Dependency Graph
5. Files Changed Summary
6. Open Questions

输出：`{MASTER_PLAN_PATH}`

### 8. Phase 5：构建状态追踪器

用户批准主规划后，按 `shared/PLANNING_METHODOLOGY.md` 中的 schema 生成 `BUILD_STATUS.yaml`。

### 9. 报告

```
=== PLANNING COMPLETE ===

Master Plan:    {MASTER_PLAN_PATH}
Build Tracker:  {project}/BUILD_STATUS.yaml
Persona Plans:  {PLANS_DIR}/round1/ (5 files)
Revised Plans:  {PLANS_DIR}/round2/ (5 files)
Debate Summary: {PLANS_DIR}/debate-summary.md

Waves: [N]
Tasks: [N]
Ready to execute: "produce wave 0" or read the master plan first
```

## 快捷方式

- `/architect --quick [brief]`：用 3 个角色，跳过辩论（仅 Phase 0-1-4）。适合较小的项目，更快。
- `/architect --resume`：重新读取 `working/plans/` 中已有的规划，从上次中断处继续。

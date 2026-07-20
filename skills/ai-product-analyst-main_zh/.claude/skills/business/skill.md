# /business — Business Context Browser

> 你所在组织知识系统的交互式浏览器。探索术语、产品、指标、目标和团队结构。

## 触发
以 `/business` 或 `/business {subcommand}` 调用

## 前置条件
- 组织上下文必须存在于 `.knowledge/organizations/{org}/`
- 读取 `.knowledge/setup-state.yaml` 找到当前激活的组织
- 如果未配置组织："No organization context found. Run `/setup` Phase 3 to configure business context, or create one manually at `.knowledge/organizations/{name}/`."

## 子命令

### `/business`（无参数）—— 概览
展示可用业务上下文的摘要：

```
📊 Business Context: {org_name}

  Glossary:    {n} terms defined
  Products:    {n} products cataloged
  Metrics:     {n} metrics specified
  Objectives:  {n} OKRs/goals tracked
  Teams:       {n} teams mapped

Type /business {category} for details.
```

**实现：**
1. 读取 `.knowledge/organizations/{org}/manifest.yaml` 获取组织名
2. 使用 `helpers/business_context.py` → `load_business_context(org_path)`
3. 统计各类别条目数
4. 展示摘要表

### `/business glossary` —— 浏览术语
展示所有业务术语定义：

```
📖 Glossary ({n} terms)

  Term              | Definition                          | Category
  ──────────────────|─────────────────────────────────────|──────────
  Active User       | User with ≥1 session in last 30d    | Engagement
  Churn             | No activity for 60+ days            | Retention
  ...
```

**实现：**
1. 从 `business/glossary/terms.yaml` 加载
2. 按字母排序
3. 展示前 20 个术语；若更多则提供 "Show all"
4. 如果为空："No glossary terms defined. Add terms to `.knowledge/organizations/{org}/business/glossary/terms.yaml`."

### `/business products` —— 查看产品目录
展示产品层级：

```
📦 Products ({n} total)

  Product           | Category    | Status    | Key Metrics
  ──────────────────|─────────────|───────────|────────────
  Core Platform     | SaaS        | Active    | MAU, Revenue
  Mobile App        | Mobile      | Active    | DAU, Retention
  ...
```

**实现：**
1. 从 `business/products/index.yaml` 加载
2. 以表格形式展示
3. 如果为空："No products defined. Add products to `.knowledge/organizations/{org}/business/products/index.yaml`."

### `/business metrics` —— 查看指标定义
展示指标字典：

```
📏 Metrics ({n} defined)

  Metric            | Type        | Formula/Definition        | Owner
  ──────────────────|─────────────|───────────────────────────|──────
  Conversion Rate   | Ratio       | signups / visitors        | Growth
  MRR               | Currency    | SUM(active_subscriptions) | Finance
  ...
```

**实现：**
1. 从 `business/metrics/index.yaml` 加载
2. 若有，则与 `.knowledge/datasets/{active}/metrics/` 交叉引用
3. 展示定义、类型、负责人
4. 如果为空："No metrics defined. Use `/metrics add` to define metrics, or add to `.knowledge/organizations/{org}/business/metrics/index.yaml`."

### `/business objectives` —— 查看 OKR/目标
展示当前目标：

```
🎯 Objectives ({n} active)

  Objective                      | Key Results              | Status
  ───────────────────────────────|──────────────────────────|────────
  Increase activation rate       | +15% by Q2               | On Track
  Reduce churn                   | <5% monthly by Q3        | At Risk
  ...
```

**实现：**
1. 从 `business/objectives/index.yaml` 加载
2. 展示状态标识（On Track / At Risk / Behind）
3. 如果为空："No objectives defined. Add OKRs to `.knowledge/organizations/{org}/business/objectives/index.yaml`."

### `/business teams` —— 查看团队结构
展示团队组织：

```
👥 Teams ({n} mapped)

  Team              | Lead        | Focus Area        | Analysts
  ──────────────────|─────────────|───────────────────|──────────
  Growth            | Jane D.     | Acquisition       | 2
  Product           | John S.     | Core Experience   | 3
  ...
```

**实现：**
1. 从 `business/teams/index.yaml` 加载
2. 展示团队摘要
3. 如果为空："No teams defined. Add team structure to `.knowledge/organizations/{org}/business/teams/index.yaml`."

### `/business lookup {term}` —— 搜索
跨所有类别搜索某个术语：

1. 搜索术语表（精确 + 模糊匹配）
2. 搜索产品名
3. 搜索指标名
4. 搜索目标文本
5. 展示所有匹配，带类别标签

如果无匹配："No results for '{term}'. Try a different search term or browse categories with `/business`."

**实现：**
1. 使用 `helpers/business_context.py` → `get_glossary()`、`get_products()` 等
2. 跨所有类别做大小写不敏感的子串匹配
3. 排序：精确匹配 > 以此开头 > 包含
4. 展示前 10 条结果，带类别标识

## 错误处理
- 缺少组织目录 → 建议 `/setup` Phase 3
- 类别为空 → 展示有帮助的 "如何添加" 提示，附文件路径
- YAML 格式错误 → 展示解析错误，建议检查文件语法
- 上下文不完整（部分类别为空）→ 展示已有部分，注明缺口

## 展示规则
- 结构化数据用表格（对齐列）
- 初始展示限制在 20 行；提供分页
- 始终展示文件路径，让用户知道去哪里编辑
- 自适应详细程度：`/business` 给摘要，子命令给明细

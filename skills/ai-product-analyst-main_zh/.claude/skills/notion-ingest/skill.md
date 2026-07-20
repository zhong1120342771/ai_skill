# /notion-ingest — Notion 工作区爬取器

> 爬取一个 Notion 工作区，抽取业务术语、指标、产品文档和团队结构。
> 填充组织知识系统。

## 触发
调用方式为 `/notion-ingest` 或 `/notion-ingest {workspace_url}`

## 前置条件
- 在 `.knowledge/user/integrations.yaml` 中配置好 Notion 集成令牌
- 组织目录存在于 `.knowledge/organizations/{org}/`
- 如果没有令牌："Notion integration token not found. Add it to `.knowledge/user/integrations.yaml` under `notion.token`. See [Notion Integration Guide](https://developers.notion.com/docs/create-a-notion-integration) for setup."

## 概览

本 skill 用广度优先（BFS）爬取策略系统地遍历一个 Notion
工作区，把页面转换成结构化的知识条目。它**不**需要
外部 Python 包 —— 所有 Notion API 调用都用内联 HTTP 请求。

## 第 1 步：鉴权检查

```python
import yaml, os

# Load integration config
integrations_path = ".knowledge/user/integrations.yaml"
with open(integrations_path) as f:
    config = yaml.safe_load(f)

notion_token = config.get("notion", {}).get("token")
if not notion_token:
    print("❌ No Notion token found. Add to .knowledge/user/integrations.yaml")
    # HALT
```

用一次简单的 API 调用验证令牌可用：
```
GET https://api.notion.com/v1/users/me
Authorization: Bearer {token}
Notion-Version: 2022-06-28
```

## 第 2 步：工作区探测

向用户询问爬取范围：
```
Notion workspace connected. How would you like to crawl?

1. **Full workspace** — Crawl all accessible pages (may be slow for large workspaces)
2. **Specific database** — Provide a database URL to crawl
3. **Specific page tree** — Provide a root page URL to crawl its children
4. **Search by keyword** — Search for pages matching specific terms
```

## 第 3 步：BFS 爬取策略

```
Algorithm: Breadth-First Search (BFS)

Queue ← [root_page_id]
Visited ← {}
Results ← []

WHILE Queue is not empty:
    page_id ← Queue.dequeue()
    IF page_id IN Visited: CONTINUE
    Visited.add(page_id)

    page ← fetch_page(page_id)        # GET /v1/pages/{id}
    children ← fetch_children(page_id) # GET /v1/blocks/{id}/children

    result ← convert_to_knowledge(page, children)
    Results.append(result)

    # Enqueue child pages and linked databases
    FOR child IN children:
        IF child.type == "child_page" OR child.type == "child_database":
            Queue.enqueue(child.id)

    rate_limit_pause()  # See Step 4
```

### 页面拉取
```
GET https://api.notion.com/v1/pages/{page_id}
Authorization: Bearer {token}
Notion-Version: 2022-06-28
```

### 块子级拉取（分页）
```
GET https://api.notion.com/v1/blocks/{block_id}/children?page_size=100
Authorization: Bearer {token}
Notion-Version: 2022-06-28
```

通过 `has_more` 和 `next_cursor` 处理分页。

## 第 4 步：限流

Notion API 限制：集成令牌每秒 3 个请求。

```python
import time

class RateLimiter:
    """Simple token-bucket rate limiter for Notion API."""

    def __init__(self, requests_per_second=2.5):
        self.min_interval = 1.0 / requests_per_second
        self.last_request = 0

    def wait(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request = time.time()
```

**退避策略：**
- 遇到 429（被限流）：等待 `Retry-After` 头指定的秒数，最少 1s
- 遇到 5xx：指数退避（1s、2s、4s），最多重试 3 次
- 遇到 4xx（非 429）：记录错误，跳过该页，继续爬取

## 第 5 步：页面转 Markdown

把 Notion 块类型转换成 markdown：

| Notion Block Type | Markdown Output |
|-------------------|-----------------|
| paragraph | Plain text |
| heading_1 | `# Title` |
| heading_2 | `## Title` |
| heading_3 | `### Title` |
| bulleted_list_item | `- Item` |
| numbered_list_item | `1. Item` |
| code | ` ```lang\ncode\n``` ` |
| quote | `> Quote` |
| callout | `> ℹ️ Callout` |
| table | Markdown table |
| divider | `---` |
| toggle | Treat as heading + nested content |
| child_page | `[Page Title](notion://page_id)` |
| child_database | `[Database Title](notion://db_id)` |

**富文本抽取：**
- Bold → `**text**`
- Italic → `*text*`
- Code → `` `text` ``
- Links → `[text](url)`
- Mentions → `@{mention_name}`

## 第 6 步：知识抽取

对每个爬取到的页面，尝试分类并抽取结构化知识：

### 自动分类规则
| Page Contains | Classification | Target File |
|---------------|---------------|-------------|
| Term definitions, glossary entries | Glossary term | `business/glossary/terms.yaml` |
| KPI, metric, formula | Metric definition | `business/metrics/index.yaml` |
| Product name, feature list | Product entry | `business/products/index.yaml` |
| OKR, objective, key result | Objective | `business/objectives/index.yaml` |
| Team name, org chart | Team entry | `business/teams/index.yaml` |
| SQL query, data pattern | Query archaeology | `.knowledge/query-archaeology/raw/` |

### 分类启发式规则
- **Glossary：** 页面标题含 "glossary"、"definitions"、"terms"，或
  内容有类定义模式（"X is defined as"、"X means"）
- **Metrics：** 内容含 "KPI"、"metric"、"formula"、"calculated as"，
  或有数值目标/阈值
- **Products：** 内容含 "product"、"feature"、"roadmap"，或位于
  具有产品类属性的数据库中
- **Objectives：** 内容含 "OKR"、"objective"、"key result"、"goal"、
  "target"，或有季度引用
- **Teams：** 内容含 "team"、"squad"、"org chart"，或有角色/人员
  属性

### 原始存储
所有爬取到的页面以原始 markdown 保存到：
```
.knowledge/query-archaeology/raw/notion_{page_id_short}.md
```

带 YAML frontmatter：
```yaml
---
source: notion
page_id: {full_page_id}
title: {page_title}
url: {page_url}
crawled_at: {timestamp}
classification: {auto_class or "unclassified"}
---
```

## 第 7 步：进度报告

爬取期间，展示进度：
```
🔄 Crawling Notion workspace...

  Pages crawled:    45/~120 (estimated)
  Terms extracted:  12
  Metrics found:    5
  Products found:   3
  Errors:           1 (skipped)

  Current: "Q4 2025 OKR Tracker"
```

## 第 8 步：爬取后摘要

爬取完成后：
```
✅ Notion ingest complete!

  Pages crawled:     127
  Pages skipped:     3 (errors logged)

  Knowledge extracted:
    Glossary terms:  23 → business/glossary/terms.yaml
    Metrics:         8  → business/metrics/index.yaml
    Products:        5  → business/products/index.yaml
    Objectives:      12 → business/objectives/index.yaml
    Teams:           4  → business/teams/index.yaml

  Raw pages saved:   127 → .knowledge/query-archaeology/raw/

  Review extracted knowledge with `/business` to verify accuracy.
  Auto-classifications may need manual correction.
```

## 第 9 步：捕获到 Query Archaeology

对含 SQL 查询或数据模式的页面，创建 cookbook 条目：

```python
from helpers.archaeology_helpers import capture_cookbook_entry

# For each page with SQL content
capture_cookbook_entry(
    title=page_title,
    sql=extracted_sql,
    description=f"From Notion: {page_title}",
    tags=["notion-import", classification],
    source=f"notion:{page_id}"
)
```

## 错误处理

| Error | Response |
|-------|----------|
| Invalid token | "Notion token is invalid or expired. Update in `.knowledge/user/integrations.yaml`." |
| Permission denied (403) | "Cannot access page '{title}'. Check integration permissions in Notion." |
| Rate limited (429) | Auto-retry with backoff (transparent to user) |
| Network error | Retry 3x, then skip page and continue |
| Empty workspace | "No accessible pages found. Verify the integration has access to your workspace." |
| Large workspace (500+) | "Large workspace detected (~{n} pages). This may take several minutes. Continue? [Y/n]" |

## 增量更新

后续运行时，支持增量模式：
```
/notion-ingest --incremental
```

1. 读取 `.knowledge/organizations/{org}/notion_sync_state.yaml` 获取上次同步时间戳
2. 使用 Notion 搜索 API 的 `filter.timestamp.last_edited_time.after` 参数
3. 只处理自上次同步以来修改过的页面
4. 完成后更新同步状态

## 重置
`/notion-ingest reset` —— 清除所有原始 Notion 页面和同步状态。**不会**移除
已抽取的知识条目（那些必须通过 `/business` 或手动清理）。

# Skill: Data Inspect

## 用途
展示当前激活数据集的 schema —— 表、字段、行数和表间关系。可选地下钻到某张具体的表。

## 何时使用
以 `/data` 调用查看完整 schema 概览，或以 `/data {table}` 调用查看某张表的字段明细。

## 操作步骤

### 模式 1：`/data`（完整 schema 概览）

1. 读取 `.knowledge/active.yaml` 获取当前激活的数据集
2. 读取 `.knowledge/datasets/{active}/schema.md`
3. 展示精简摘要：

```
Active Dataset: {display_name}
Connection: {type} ({database}.{schema})

Tables:
  users          ~50,000 rows   8 columns   user_id (PK)
  products           500 rows   7 columns   product_id (PK)
  events        ~6.5M rows     9 columns   event_id (PK)
  sessions       ~1.4M rows    8 columns   session_id (PK)
  orders        ~30-50K rows   6 columns   order_id (PK)
  order_items         — rows   4 columns   order_id + product_id
  memberships         — rows   4 columns   user_id
  support_tickets ~20K rows    7 columns   ticket_id (PK)
  nps_responses   ~8K rows     5 columns   user_id
  experiment_assignments ~20K  4 columns   user_id + experiment_id
  promotions          5 rows   7 columns   promo_id (PK)
  experiments         2 rows   8 columns   experiment_id (PK)
  calendar          366 rows   4 columns   date (PK)

Use `/data {table}` for column details.
```

### 模式 2：`/data {table}`（表明细）

1. 读取 `.knowledge/datasets/{active}/schema.md`
2. 找到所请求表对应的段落
3. 展示完整的字段清单，含类型和说明
4. 展示关键关系（指向/来自这张表的外键）

### 模式 3：无激活数据集

如果 `.knowledge/active.yaml` 没有 `active_dataset`，或者 brain 不存在：
- 显示："No active dataset. Run `/connect-data` to connect one, or `/datasets` to see available options."

## 反模式

1. **绝不为了展示 schema 而查询数据库** —— 为提速，应从缓存的 schema.md 文件读取
2. **绝不直接展示 schema.md 原文** —— 始终格式化成精简的表格视图

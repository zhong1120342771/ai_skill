# SQL 避坑清单（每次取数必看）

> 来源：海仓 `zhuanzhuan-data-query` skill 的 pitfalls，多个看板实战踩坑归纳。每次写 SQL 前逐条对照。
> 与 `sql_workflow.md` 的关系：本文件列具体陷阱和现象，`sql_workflow.md` 列写法原则。

## ⚠️ 坑1：脱敏规则禁止 SELECT *

**现象**：提交返回 `"命中脱敏规则时禁止使用 select *，请显式指定查询字段"`
**原因**：安全策略，**CTE 内的 `SELECT *` 也不行**
**规避**：显式列出所有字段

```sql
-- 错误
WITH cte AS (SELECT * FROM table)
-- 正确
WITH cte AS (SELECT col1, col2, col3 FROM table)
```

## ⚠️ 坑2：商品ID等大整数精度丢失

**现象**：`info_id` / `order_id` 是 19 位整数（如 `2062908865348469761`），Python/JS 读出来末位变 0（`...760`）
**原因**：超过 IEEE 754 双精度浮点安全整数范围（2^53-1 ≈ 9×10^15）
**规避**：SQL 里必须 `cast(info_id AS string)`，JSON 解析时当字符串处理

```sql
SELECT cast(info_id AS string) AS `商品ID`, ...
```

**下游读结果时**：pandas 读 tsv/csv 建议 `dtype={'商品ID': str, '订单ID': str}`；xlsx 大整数会被 Excel 自动转科学计数法，也建议保持字符串。

## ⚠️ 坑3：中文列别名必须反引号

```sql
-- 错误
SELECT col AS 商品名称
-- 正确
SELECT col AS `商品名称`
```

## ⚠️ 坑4：整体 UV 不能用「分组求和」

**现象**：`使用筛选UV + 未使用筛选UV` 算出的整体 UV 比真实值虚高
**原因**：同一用户可能在不同请求里跨组（既有使用也有未使用），求和重复计数
**规避**：整体 UV 必须 SQL 全集 `count(distinct token / user_id)` 去重，**禁止分组相加**

```sql
-- 正确
SELECT count(distinct token) AS 整体UV FROM ...
-- 错误
SELECT sum(使用筛选UV) + sum(未使用筛选UV)  -- 会虚高
```

推广规则：**任何"整体级去重指标"都不能靠分组求和拼出来**，必须 SQL 全集算一次。

## ⚠️ 坑5：GROUPING SETS 的 NULL 处理

**现象**：`GROUPING SETS` 返回的聚合层级，某些维度为 `NULL` 或 `'NULL'` 字符串
**规避**：判断时同时检查 `is None` 和 `== 'NULL'` 字符串

```python
if c3id and c3id != 'NULL':
    lvl = 3
elif c2id and c2id != 'NULL':
    lvl = 2
```

## ⚠️ 坑6：类目字段可能为空或 'NULL' 字符串

商品表的 `cate_third_name` 等可能为空（商品挂在一/二级或四五级），需用 `COALESCE` 或三级类目 + 一/二级补充。

## ⚠️ 坑7：搜索词字段含 \x01 分隔符

`datapool['orikeyword']` 或宽表 `query` 常含 `\x01` 分隔符，需清洗：

```sql
regexp_replace(query, unhex('01'), '')
-- 或
regexp_replace(datapool['orikeyword'], '', ' ')
```

## 其他易错点

- `orikeyword` 是搜索词字段，`keyword` 常为空**勿用**
- f-string 中不能含反斜杠，遇到先赋值变量再引用
- 列名大小写不一致（如 `SKU` vs `sku`），读取时先确认
- 后台 heredoc 写 SQL 文件在某些 harness 下会失败——本 skill 通过 `stariver_query.py --sql-file` 已规避

# 找表工作流

用户给的是业务问题或字段名，不是表名时使用本流程。目标是定位一张或多张可以承接业务问题的 Hive 表，并在交付候选前评估好生命周期与敏感等级。

## 顺序

1. **本地优先**：先扫历史 SQL 和文档里出现过的表名，命中就直接用，不要再问。
   - `rg -INo --no-messages '\b[a-z][a-z0-9_]+\.[a-z][a-z0-9_]+\b' ~/ai/project ~/claude-output 2>/dev/null | sort -u`
   - 用业务关键词过滤：再 `| grep -i '<关键词>'`。
   - 命中后仍要走第 3 步评估，本地表名只能证明用过，不能证明现在还能用。

2. **星河搜表**：本地无命中或要扩面才搜。用 `show tables` + `like` 通配，覆盖有权限/无权限。
   - 先猜库：常见前缀走 `show-databases --like '%<词>%'`。
   - 库内搜：`show-tables <db> --like '%<词>%'`。
   - 关键词要拆，例如「订单+发货」拆成 `%order%`、`%ship%` 两轮，再求交集。
   - 不要一次性扫所有库。

3. **候选评估**：每张候选都跑 `describe formatted`，提取以下字段后再判断是否推荐。
   - `python3 .../stariver_query.py describe <db.table> --formatted`
   - 提取项见下方「候选必看字段」。

4. **输出候选清单**：按相关度排序，每行带元数据，让用户自己挑。不要替用户决定。

## 候选必看字段

每张候选表交付前必须确认：

| 字段 | 看哪里 | 用途 |
| --- | --- | --- |
| 敏感等级（L1/L2/L3/L4） | `describe formatted` 的 `TBLPROPERTIES` 或 `Comment`，关键词 `sensitivity` / `security_level` / `安全等级` | L3 及以下可用；L4 必须找替代表，不要直接用 |
| 生命周期（TTL/留存天数） | `TBLPROPERTIES` 中 `lifecycle` / `ttl` / `life_cycle` / `retention` | 后续写 SQL 时 `dt` 跨度不可超过这个天数 |
| 分区粒度 | `Partition Information` 里的 `dt` 等字段；`show partitions` 看最新分区 | 决定查询日期范围如何拼 |
| 时间戳字段 | `describe` 的列名，关注 `*_time` / `*_ts` / `timestamp` / `event_time` / `ctime` / `utime` | 增量表必须有；全量表也常带，决定能不能做时序分析 |
| 有无 select 权限 | 直接 `sample` 一次小 limit；权限拒绝会报错 | 无权限的表仍保留为候选，附「需申请权限」标记，不要悄悄丢掉 |

## 表名后缀约定

读表名先判类型，能省一轮 describe：

- `*_full` / `*_snap` / `*_snapshot`：**全量快照表**。每个 `dt` 是当天全量。注意是否带时间戳字段，没有就只能做静态切片，不能做事件序列分析。
- `*_1d` / `*_di` / `*_inc` / `*_delta`：**增量表**。每个 `dt` 只含当天新增/变更。必须有时间戳字段（如 `event_time`、`pay_time`）才能精确还原事件。
- `*_df` / `*_da`：日全量，按天分区；和 `_full` 类似。
- `*_rt` / `*_hourly` / `*_h`：实时或小时级，分区到小时。
- 无明显后缀：跑 `show partitions` 看分区粒度再判断。

后缀只是约定，最终以 `describe formatted` 和 `show partitions` 为准。

## L 等级处理规则

| L 等级 | 处理 |
| --- | --- |
| L1 / L2 / L3 | 正常可用，照常推荐 |
| L4 | 不推荐直接用。同时主动找替代表（同业务域、同主键、L3 及以下），告诉用户「L4 表是 X，替代候选是 Y/Z」 |
| 看不到 sensitivity 字段 | 在候选清单标注「敏感等级未知，建议跑前确认」，不要默认当成 L3 |

## 输出格式

候选清单按相关度排序，每张表一行块：

```
1. db_name.table_name_full   [推荐]
   语义匹配: 订单成交主表
   L 等级:   L3
   生命周期: 365 天
   分区:     dt（日级，最新 2026-06-25）
   类型:     全量快照（_full）
   时间戳:   pay_time, create_time
   权限:     有
   备注:     —

2. db_name.table_name_1d     [候选]
   ...
   权限:     无（describe 可读，sample 拒绝；如需用请申请）
```

如果只有 L4 表语义最贴：

```
首选语义匹配是 db.x_full，但敏感等级 L4，不直接用。
替代候选（L3 及以下、同主键 info_id）：
  - db.y_full   语义略弱（缺字段 a），L3，生命周期 180 天
  - db.z_1d     增量表，需自己累加，L2，生命周期 90 天
```

## 不要做

- 不要因为一张表权限被拒就把它从候选里删掉，至少要标注。
- 不要在没有 describe 证据时凭表名直接断敏感等级或生命周期。
- 不要扫所有库（`show databases` 不加 `--like` 是禁止行为，除非用户明确要全量目录）。
- 不要把 L4 表悄悄放进推荐位。
- 后续写 SQL 时，`dt` 范围不可超过该表的生命周期；跨多表时取最小生命周期。

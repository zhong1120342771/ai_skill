---
name: 用户分层-代码生成
description: 转转用户分层流水线第 1 步——RFMLAP 评分 SQL 生成与执行，产出用户评分宽表和层级汇总。
metadata:
  type: sub-skill
  parent: 转转用户分层
  step: 1
  inputs: ["dt (YYYY-MM-DD)"]
  outputs:
    - data_storage/user_segments_${dt}.csv
    - data_storage/user_segments_${dt}.csv.meta.json
    - data_storage/segment_distribution_${dt}.csv
---

# 用户分层-代码生成

## 基础与定位

本 skill 在 `code-generator` 通用代码生成 agent 基础上，向**取数工程师**方向窄化适配，重点是：

- 熟悉 `dm_oper_user_layer_dtl_inc_1d`（L/A 维度、regist_time）
- 熟悉 `dw_trade_order_company_all_detail_full_1d`（R/F/M/P 维度、pack_amt、order_type）
- 能处理 `regist_time`（字符串 `yyyy-MM-dd HH:mm:ss`）转换为天数差
- 能做 LEFT JOIN（无支付记录的用户仍需保留，所有维度补 0 或 9999）

## 前置阅读（每次执行前必读）

1. **[../../References/分层方案说明.md](../../References/分层方案说明.md)** — 六维评分规则、分层阈值、数据表依赖
2. **[../../References/output-schemas.md](../../References/output-schemas.md)** §一 §二 — 产物字段契约
3. **[../../Scripts/rfmlap_score_create_table.sql](../../Scripts/rfmlap_score_create_table.sql)** — Step 1 建表模板，替换 `${dt}` 后执行
4. **[../../Scripts/rfmlap_score_fetch_batch.sql](../../Scripts/rfmlap_score_fetch_batch.sql)** — Step 2 分批取数模板，替换 `${dt}` + `${batch}` 后执行

## 职责

1. 执行 Step 1（建 tmp 表）
2. 循环执行 Step 2 四次（batch=0/1/2/3），每次下载一个分片 CSV
3. 本地合并四个分片为完整 `user_segments_${dt}.csv` + `.meta.json`
4. 基于评分结果，执行层级汇总，产出 `segment_distribution_${dt}.csv`

## 执行方式

**背景**：One-Service / 星河下载接口有 100 万行截断，DAU 约 300 万，必须分批。

使用 One-Service CLI（`python ~/.claude/scripts/oneservice_cli.py`），凭证从环境变量读取：
- `$ONESERVICE_OA` / `$ONESERVICE_ACCESS_KEY`

SQL 含 `DATEDIFF`、`COALESCE`、`CASE WHEN` 等，必须走 **Hive 引擎（engine=5）**。

### Step 1：建 tmp 表

```bash
# 替换 ${dt}，提交建表 SQL（约需 5-10 分钟，写 Hive 不受行数限制）
python ~/.claude/scripts/oneservice_cli.py \
  --file ~/.claude/skills/转转用户分层agent/Scripts/rfmlap_score_create_table.sql \
  --output /dev/null
# 建表 SQL 无结果集，用 --preview 确认执行成功即可
```

### Step 2：分 4 批取数，每批约 75 万行

```python
import subprocess, os, pandas as pd

dt = "${dt}"
batches = []
for batch in range(4):
    sql = f"""
SELECT * FROM hdp_zhuanzhuan_tmp_global.tmp_rfmlap_{dt}
WHERE PMOD(HASH(token), 4) = {batch}
"""
    out = f"~/.claude/data_storage/user_segments_{dt}_batch{batch}.csv"
    subprocess.run([
        "python", "~/.claude/scripts/oneservice_cli.py",
        "--sql", sql, "--output", out, "--format", "csv"
    ])
    batches.append(out)

# 合并
dfs = [pd.read_csv(p) for p in batches]
df = pd.concat(dfs, ignore_index=True)
df.to_csv(f"~/.claude/data_storage/user_segments_{dt}.csv", index=False)
print(f"[done] data_storage/user_segments_{dt}.csv rows={len(df)}")
```

### Step 3：清理 tmp 表（可选，节省存储）

```sql
DROP TABLE IF EXISTS hdp_zhuanzhuan_tmp_global.tmp_rfmlap_${dt};
```

## 关键注意事项

- `dm_oper_user_layer_dtl_inc_1d` **有 `dt` 分区**，取 `dt='${dt}'` 且 `terminal_name='转转APP'`
- `dw_trade_order_company_all_detail_full_1d` 有 `dt` 分区，取近 180 天范围 `dt >= DATE_SUB('${dt}', 180) AND dt <= '${dt}'`
- LEFT JOIN（uid）关联：user_base 为主表，order 为附表（无支付记录的用户 R/F/M/P 均补零/9999）
- `regist_time` 格式 `yyyy-MM-dd HH:mm:ss`，取前 10 位 `SUBSTR(regist_time, 1, 10)` 再 DATEDIFF
- 无支付记录时 `r_last_pay_days` 设为 9999
- **分批逻辑**：`PMOD(HASH(token), 4)` 按 token hash 均匀分桶，4 批各约 75 万行，均在 100 万截断线以下

## 产物要求

- 编码 UTF-8；
- 每个 CSV 同时写 `.meta.json`（行数、各层用户数、空值率）；
- `user_segments_${dt}.csv` 行数应约等于转转 APP 当日 DAU（约 300 万）；
- 完成后 stdout 打：`[done] data_storage/user_segments_${dt}.csv rows=<N>`

## 失败处理

- Step 1 建表失败：报错写 `data_storage/error_seg_${dt}.log`，停止，不进 Step 2
- Step 2 某批次失败：重试当批次一次；重试仍失败则记录缺失 batch 号，停止，不合并
- 合并后行数 < 100 万：疑似分批不完整，视为失败，不交给下游
- 层分布严重异常（如全部为 L1 或 L5 占比 > 20%）：记录 warning，继续，由 Step 3 质量检查卡

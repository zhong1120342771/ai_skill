## stariver_query.py 命令速查

`$SKILL_DIR` = 本 SKILL.md 所在目录（skill 根）。

```bash
# 连通性探活
python3 $SKILL_DIR/scripts/stariver_query.py check

# 搜本地案例（LM 摘要语义检索，Step 1 硬约束）
python3 $SKILL_DIR/scripts/stariver_query.py search-cases "骑行 支付前搜索 漏斗" --top 5

# 搜本地 SQL 关键词（旧版 grep，兼容）
python3 $SKILL_DIR/scripts/stariver_query.py search-sql "info_id"

# 手动重建案例索引（cron 每天 09:07 自动跑，急需可触发）
export ANTHROPIC_AUTH_TOKEN=<your-tokenhub-key>
python3 $SKILL_DIR/scripts/build_sql_index.py

# 生命周期校验（Step 4 硬约束）
python3 $SKILL_DIR/scripts/stariver_query.py verify-lifecycle --sql-file query.sql

# 管理本地参考 SQL 搜索路径
python3 $SKILL_DIR/scripts/stariver_query.py init-paths --list
python3 $SKILL_DIR/scripts/stariver_query.py init-paths --add /path/to/dir

# 跑 SQL
python3 $SKILL_DIR/scripts/stariver_query.py run --sql-file query.sql

# 按 task-id 拉远程结果（run 本地超时后）
python3 $SKILL_DIR/scripts/stariver_query.py fetch --task-id 743254145
# 调超时避免：STARIVER_QUERY_TIMEOUT=1800（默认 900s）

# 探表
python3 $SKILL_DIR/scripts/stariver_query.py describe db.table
python3 $SKILL_DIR/scripts/stariver_query.py describe db.table --columns "uid,token,order_id,dt"
python3 $SKILL_DIR/scripts/stariver_query.py sample db.table --where "dt='2026-06-17'" --limit 20
python3 $SKILL_DIR/scripts/stariver_query.py partitions db.table

# 库/表列表（仅按需 + 有权限时）
python3 $SKILL_DIR/scripts/stariver_query.py show-databases
python3 $SKILL_DIR/scripts/stariver_query.py show-tables db_name

# 跑数产物 QA（Step 7 硬约束）
python3 $SKILL_DIR/scripts/result_qa.py \
    --result-path /Users/zz/claude-output/sql_result_xxx.tsv \
    --sql-file <SQL 文件> \
    --task-id <星河 task id>
# --no-xlsx 关掉默认自动生成的 xlsx 副本
```

**fetch 用法**：`run` 返回 `FAILED: StarRiver query timed out locally` 时看打印的 `task_id`；同事在星河 web 看到的 task_id 也能直接拉。fetch 自动查状态——SUCCESS 落盘 `sql_result_<task_id>.tsv`，RUNNING 提示等，FAILED 报错。

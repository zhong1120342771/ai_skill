-- 转转用户分层 RFMLAP 评分 — Step 2：分批取数（每批约 75 万行，低于 100 万截断线）
-- 占位符：${dt} = 统计日期 YYYY-MM-DD，${batch} = 0/1/2/3
-- 前置：rfmlap_score_create_table.sql 已建好 tmp_rfmlap_${dt}
-- 引擎：星河 Hive engine=5

SELECT *
FROM hdp_zhuanzhuan_tmp_global.tmp_rfmlap_${dt}
WHERE PMOD(HASH(token), 4) = ${batch};

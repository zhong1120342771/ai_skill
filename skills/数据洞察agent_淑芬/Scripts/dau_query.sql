-- 转转 App 全量 DAU(用户级,distinct token)
-- 用于把抽样指标(基于 1/339 哈希桶 N≈9k)反推到全量,见 agents/洞察结论生成.md「样本→全量推广」。
-- 占位符:${outFileSuffix} = dt(YYYY-MM-DD)
-- 落产物:data_storage/dau_full_${dt}.csv  字段 dt, uv

SELECT
    t3.dt,
    COUNT(DISTINCT t3.token) AS uv
FROM hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d t3
WHERE t3.dt = '${outFileSuffix}'
  AND t3.terminal_name IN ('转转APP')
GROUP BY 1;

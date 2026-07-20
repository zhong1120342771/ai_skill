-- 四页(G1001-G1004) 10 核心模块 + 逐页 home_overall 的「近 N 天日度基线」小表
-- ★ 2026-07-13 默认扩四页:actiontype IN 四页,多出 page_id 维度,GROUP BY dt,page_id,module。
--    异动判定仍以 primary_page(G1001) 为主(首页为主),场馆页基线量小仅供参考。单页模式 runner 只注入 G1001。
-- 用途：给「数据分析」agent 的异动判定提供历史窗——不是拿 D-1 单基线比，
--       而是各天单独去重算出模块 UV/PV/UV-CTR 的日序列，再对序列求
--       整窗均值/标准差（主判据）+ 同星期几分布（辅判据，去周内周期）判异动。
--
-- 关键口径（铁律，别改）：
--   1. 各天在「当天范围内」对 token 去重，绝不跨天去重——跨天去重得到的是
--      「这段时间的去重人数」，是另一个量，不是日 UV。这里 GROUP BY dt 保证每天独立。
--   2. 历史各天复用 1/339 哈希桶抽样（pmod(hash(token),339)=0），稳定 panel、
--      可复现、与当天口径一致。走星河 SparkSQL(engine=2)——SparkSQL 支持 hash()/pmod()
--      且能解析 `CASE datapool['x'] WHEN..`；engine=5 Hive 对 map下标+CASE 组合会 ParseException。
--   3. 窗口 [startDt, endDt] 含当天 dt——当天行也用同一哈希桶算，
--      这样「当天 vs 历史」在本表内部完全同口径（apples-to-apples）；
--      分析侧用 [dt-28, dt-1] 这 28 天(4 整周)当参考分布，dt 行当被检验点。
--   4. 模块映射由 runner 从 References/section-to-module.json 注入模块 CASE 表达式，
--      SQL 不自己写死 section_id，保持与主流水线切分一致。
--
-- 占位符（run_module_baseline.py 注入；下方各自只出现一次，切勿在注释里再写字面量占位符，
-- 否则多行 CASE 注入进单行注释会溢出成活 SQL）：
--   startDt        窗口起始日 = dt-28
--   endDt          窗口结束日 = dt（含当天）
--   moduleCaseWhen section_id 到模块 的 CASE 表达式（从 section-to-module.json 生成）
--   pageInList     页面白名单，如 'G1001','G1002','G1003','G1004'（从 pages 生成；单页仅 'G1001'）
--
-- 落产物：data_storage/淑芬/module_daily_baseline/module_daily_baseline_<dt>.csv
--   列：dt, page_id, module, exposure_uv, exposure_pv, click_uv, click_pv, uv_ctr

WITH ev AS (
    -- 1/339 哈希桶抽样的四页事件流（曝光 + 点击），dt 落在窗口内，带 page_id 维度
    SELECT
        dt,
        actiontype AS page_id,
        token,
        pagetype,
        ${moduleCaseWhen} AS module
    FROM hdp_zhuanzhuan_dw_global.dw_log_lego_action_1d
    WHERE dt BETWEEN '${startDt}' AND '${endDt}'
        AND actiontype IN (${pageInList}) AND region = 'g'
        AND pagetype IN ('zpmshow','Areaexposure','explosureGoods','explosureItems','zpmclick')
        AND pmod(hash(token), 339) = 0            -- 1/339 稳定哈希桶（SparkSQL hash/pmod）
),
mod_agg AS (
    -- 按 dt × page_id × 模块聚合：每天在当天内对 token 去重（GROUP BY dt 保证不跨天去重）
    SELECT
        dt,
        page_id,
        module,
        COUNT(DISTINCT CASE WHEN pagetype <> 'zpmclick' THEN token END) AS exposure_uv,
        COUNT(CASE WHEN pagetype <> 'zpmclick' THEN 1 END)              AS exposure_pv,
        COUNT(DISTINCT CASE WHEN pagetype  = 'zpmclick' THEN token END) AS click_uv,
        COUNT(CASE WHEN pagetype  = 'zpmclick' THEN 1 END)              AS click_pv
    FROM ev
    WHERE module IS NOT NULL AND module <> '其他'   -- 未映射/其他不进 11 模块基线
    GROUP BY dt, page_id, module
),
home_agg AS (
    -- 每页整体（不分模块）每天一行，module 记为 home_overall
    SELECT
        dt,
        page_id,
        'home_overall' AS module,
        COUNT(DISTINCT CASE WHEN pagetype <> 'zpmclick' THEN token END) AS exposure_uv,
        COUNT(CASE WHEN pagetype <> 'zpmclick' THEN 1 END)              AS exposure_pv,
        COUNT(DISTINCT CASE WHEN pagetype  = 'zpmclick' THEN token END) AS click_uv,
        COUNT(CASE WHEN pagetype  = 'zpmclick' THEN 1 END)              AS click_pv
    FROM ev
    GROUP BY dt, page_id
)
SELECT
    dt,
    page_id,
    module,
    exposure_uv,
    exposure_pv,
    click_uv,
    click_pv,
    CASE WHEN exposure_uv > 0 THEN click_uv / exposure_uv ELSE NULL END AS uv_ctr
FROM (
    SELECT * FROM mod_agg
    UNION ALL
    SELECT * FROM home_agg
) t
ORDER BY page_id, module, dt;

-- 核心指标异动监控 取数模板
-- 表：hdp_zhuanzhuan_tmp_global.tmp_dws_zz_core_dataagent_zmt_v2_di（已预聚合，分区 dt=yyyy-MM-dd）
-- 字段/口径见 references/字段映射与指标口径.md；维度族 tag_01 见 references/维度体系与样例数据.md
--
-- 取数通道：星河为主（xinghe_client，Hive 引擎 sql_engine=5），One-Service 兜底。
-- ⚠️ Hive strict mode：ORDER BY 必须带 LIMIT；必须有分区（dt）过滤。
-- 异动定位默认拉「分析日 + 环比基准（t-1 / 上周同日）+ 近 N 天趋势」连续区间，一次取够，落本地再切。
--
-- ⚠️ 口径核心（与旧表相反）：matched_dau_uv 是「分维度匹配」的 DAU 分母，
--    pay_pv/matched_dau_uv（dau-净支付pv转化率）是【北极星】、可跨维度比。
--    matched_dau_uv 可能为 NULL（完整性闸门失败），NULL 行不能算 DAU 类比率，绝不当 0。

-- ============================================================
-- 模板 A：按日期区间 + 指定口径族全量拉取（最常用）
-- 把 START_DT / END_DT / TAG_01 换成实际值
-- ============================================================
SELECT tag_01, wd,
       exp_pv, exp_uv, detail_pv, detail_uv,
       order_pv, order_uv, pay_pv,
       matched_dau_uv, matched_duan, matched_source, matched_type,
       dt
FROM hdp_zhuanzhuan_tmp_global.tmp_dws_zz_core_dataagent_zmt_v2_di
WHERE dt BETWEEN 'START_DT' AND 'END_DT'      -- 例：'2026-07-01' AND '2026-07-07'
  AND tag_01 = 'TAG_01'                        -- 例：'3维度交叉-端_业务/品类_用户来源'；要全部口径就删掉这行
ORDER BY dt, tag_01, wd
LIMIT 100000;

-- ============================================================
-- 模板 B：异动下钻——锁定单个维度值，拉近 N 天趋势
-- 用于「某维度某指标环比异常，进一步下钻定位」类问题
-- ============================================================
-- SELECT tag_01, wd, dt,
--        exp_uv, detail_uv, order_uv, pay_pv, matched_dau_uv,
--        round(pay_pv/matched_dau_uv,5)   AS dau_pay_rate,   -- 北极星：dau-净支付pv转化率（可跨维度比）
--        round(exp_uv/matched_dau_uv,5)   AS exp_penetration,-- 曝光渗透率
--        round(detail_uv/exp_uv,4)        AS detail_reach,   -- 商详到达率
--        round(order_uv/detail_uv,4)      AS order_rate,     -- 下单率
--        round(pay_pv/order_uv,4)         AS pay_rate        -- 支付率
-- FROM hdp_zhuanzhuan_tmp_global.tmp_dws_zz_core_dataagent_zmt_v2_di
-- WHERE dt BETWEEN 'START_DT' AND 'END_DT'
--   AND tag_01 = '3维度交叉-端_业务/品类_用户来源'
--   AND wd LIKE '%新媒体召回%'        -- 例：锁定召回维度
-- ORDER BY wd, dt
-- LIMIT 100000;

-- ============================================================
-- 模板 C：横向对比——同一指标在某维度的所有取值间比大小
-- 用于「不同来源/分层/场景/品类谁高谁低」（限定同一 tag_01 粒度内）
-- ============================================================
-- SELECT wd, dt,
--        exp_uv, detail_uv, order_uv, pay_pv, matched_dau_uv,
--        round(pay_pv/matched_dau_uv,5)  AS dau_pay_rate,    -- 北极星，跨维度可比
--        round(pay_pv/exp_uv,5)          AS bag_rate,        -- 提袋率
--        round(pay_pv/detail_uv,5)       AS detail_pay_rate  -- 商详转化率
-- FROM hdp_zhuanzhuan_tmp_global.tmp_dws_zz_core_dataagent_zmt_v2_di
-- WHERE dt = 'END_DT'
--   AND tag_01 = '单维度-拆分用户来源'                  -- 换成 拆分端/资产分层/场景/品类 即按对应维度横切
--   AND matched_dau_uv IS NOT NULL                    -- DAU 类比率必须排除 NULL 行
-- ORDER BY dau_pay_rate DESC
-- LIMIT 200;

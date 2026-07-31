-- 【仅APP端版 v5】业务重点名单(消费电子/二奢/兴趣) × 平台首次意向标签 流向分布
-- ⚠️换 dt 复用时：事件表写死的 '2026-07-27' 与 cohort CTE 的 date_sub(current_date(),1) 须同一天。
--   原始跑通场景为 2026-07-28 运行(t-1=07-27)。跑别的日期把两处对齐。
-- 口径：单日 dt='2026-07-27'，全链路限 APP 端(terminal 15安卓/16ios/20，不含小程序103)
--   平台打分 newMediaInterestScore：限 terminal in (15,16,20)
--   消费电子名单：businesslinetagname='消费电子' 且 token 属当日 APP 端活跃全集
--   二奢名单：B2C 二奢投放触达，token_base 仅 APP 端(15,16,20)
--   兴趣名单：channelMark callback sortname='C2C寄卖新媒体新归因弹窗' 且 terminal in (15,16,20)
--   只保留 matched_intent
WITH app_token AS (
    SELECT dt, token FROM (
        SELECT dt, token FROM hdp_zhuanzhuan_dm_global.dm_oper_key_user_detail_inc_1d
        WHERE dt = date_sub(current_date(), 1) AND terminal IN ('转转APP')
        UNION ALL
        SELECT dt, token FROM hdp_zhuanzhuan_dm_global.dm_trade_exposure_info_detail_inc_1d
        WHERE dt = date_sub(current_date(), 1) AND terminal IN (15, 16, 20)
        UNION ALL
        SELECT dt, token FROM hdp_zhuanzhuan_dm_global.dm_trade_visit_detail_1d
        WHERE dt = date_sub(current_date(), 1) AND terminal IN (15, 16, 20)
    ) t
    WHERE token IS NOT NULL AND token <> ''
    GROUP BY dt, token
),
b2c_lux_media AS (
    SELECT key_value AS media_id
    FROM hdp_ubu_zhuanzhuan_view_global.ads_qsj_video_b2c_tag_full_1h_view
    WHERE dt = date_sub(current_date(), 1) AND business_tag = 'b2c'
      AND multi_category_label IN (1, 24, 25, 26, 27, 28, 36, 37)
    GROUP BY key_value
),
b2c_today_new_media AS (
    SELECT t1.dt, t1.token
    FROM hdp_zhuanzhuan_dm_global.dm_market_qsj_media_token_dtl_inc_1d t1
    INNER JOIN b2c_lux_media t2 ON t1.media_id = t2.media_id
    INNER JOIN hdp_ubu_zhuanzhuan_defaultdb.t_zhuanzhuan_dau t3
        ON t1.token = t3.token AND date_format(t1.dt, 'yyyyMMdd') = t3.date
    WHERE t1.dt = date_sub(current_date(), 1) AND t1.plat_id IN (25, 26)
      AND from_unixtime(cast(t1.visit_ts AS bigint), 'yyyy-MM-dd') = cast(t1.dt AS string)
      AND t1.token IS NOT NULL AND t1.token <> ''
    GROUP BY t1.dt, t1.token
),
ershe_cohort AS (
    SELECT a.token
    FROM app_token a
    INNER JOIN b2c_today_new_media b ON a.dt = b.dt AND a.token = b.token
    GROUP BY a.token
),
dianzi_raw AS (
    SELECT DISTINCT token
    FROM hdp_zhuanzhuan_dw_global.dw_log_server_action_1d
    WHERE dt = '2026-07-27' AND action = 'queryRealTimeOneNewMediaUserTag'
      AND region = 'q' AND datapool['success'] = 'true'
      AND datapool['businesslinetagname'] = '消费电子'
      AND token IS NOT NULL AND token <> ''
),
biz AS (
    SELECT d.token, '消费电子' AS biz_tag
    FROM dianzi_raw d INNER JOIN app_token a ON d.token = a.token
    UNION ALL
    SELECT token, '二奢' AS biz_tag FROM ershe_cohort
    UNION ALL
    SELECT DISTINCT token, '兴趣' AS biz_tag
    FROM hdp_zhuanzhuan_dw_global.dw_log_server_action_1d
    WHERE dt = '2026-07-27' AND action = 'channelMark' AND region = 'c'
      AND datapool['type'] = 'callback'
      AND datapool['sortname'] = 'C2C寄卖新媒体新归因弹窗'
      AND terminal IN ('15', '16', '20')
      AND token IS NOT NULL AND token <> ''
),
plat AS (
    SELECT token, strong_guan, extreme_guan FROM (
        SELECT token,
               get_json_object(datapool['strongintent'],  '$.guan') AS strong_guan,
               get_json_object(datapool['extremeintent'], '$.guan') AS extreme_guan,
               ROW_NUMBER() OVER (PARTITION BY token ORDER BY `timestamp` ASC) AS rn
        FROM hdp_zhuanzhuan_dw_global.dw_log_server_action_1d
        WHERE dt = '2026-07-27' AND action = 'newMediaInterestScore' AND region = 'n'
          AND terminal IN ('15', '16', '20')
          AND token IS NOT NULL AND token <> ''
    ) t WHERE rn = 1
)
SELECT
    b.biz_tag AS business_user_tag,
    COUNT(*) AS business_total,
    SUM(CASE WHEN p.strong_guan IS NOT NULL OR p.extreme_guan IS NOT NULL THEN 1 ELSE 0 END) AS matched_intent,
    SUM(CASE WHEN p.strong_guan = '电子' THEN 1 ELSE 0 END) AS strong_dianzi,
    SUM(CASE WHEN p.strong_guan = '兴趣' THEN 1 ELSE 0 END) AS strong_xingqu,
    SUM(CASE WHEN p.strong_guan = '二奢' THEN 1 ELSE 0 END) AS strong_ershe,
    SUM(CASE WHEN p.strong_guan IS NOT NULL AND p.strong_guan NOT IN ('电子','兴趣','二奢') THEN 1 ELSE 0 END) AS strong_qita,
    SUM(CASE WHEN p.extreme_guan = '电子' THEN 1 ELSE 0 END) AS extreme_dianzi,
    SUM(CASE WHEN p.extreme_guan = '兴趣' THEN 1 ELSE 0 END) AS extreme_xingqu,
    SUM(CASE WHEN p.extreme_guan = '二奢' THEN 1 ELSE 0 END) AS extreme_ershe,
    SUM(CASE WHEN p.extreme_guan IS NOT NULL AND p.extreme_guan NOT IN ('电子','兴趣','二奢') THEN 1 ELSE 0 END) AS extreme_qita
FROM biz b
LEFT JOIN plat p ON b.token = p.token
GROUP BY b.biz_tag

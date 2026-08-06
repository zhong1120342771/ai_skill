-- 当日付费用户 过去7天(D-6~D) A的四信号原始频次
-- 四信号: 商详浏览PV / 搜索次数 / 下单+加购+收藏合并 / 历史成交(7天内成交订单数)
-- 付费用户 = D 当天在业务范围内有净支付的 uid; 抽样 PMOD(HASH,3)=0 与前面分层对齐
-- 占位: ${D}=活跃/统计日, ${SNAP}=订单商品全量快照(用于业务范围打标+当日付费判定)
-- 本次 D=2025-07-27, SNAP=2026-08-03; 引擎 Hive engine=5
WITH info_tag AS (
    SELECT info_id
    FROM hdp_zhuanzhuan_dw_global.dw_mysql_info_full_1d
    WHERE dt = '${SNAP}'
      AND cus_business_extend['is_cp_flag'] = '0'
      AND cus_business_extend['is_live_flag'] = '0'
      AND (cus_business_bu IN ('消费电子','长尾N','二奢')
           OR (cus_business_belong IN ('B2C') AND cate_second_id IN ('120'))
           OR (cate_id ='2120006' AND cus_business_belong IN ('B2C')))
),
paid_uid AS (      -- 当日付费用户: D当天 pay_time 有净支付、落业务范围、抽样键一致
    SELECT DISTINCT o.buyer_id AS uid
    FROM hdp_zhuanzhuan_dw_global.dw_trade_order_company_all_detail_full_1d o
    JOIN info_tag t ON o.info_id = t.info_id
    WHERE o.dt = '${SNAP}'
      AND SUBSTR(o.pay_time,1,10) = '${D}'
      AND o.is_pure_pay_success=1 AND o.order_structure_type IN (0,1)
      AND o.buyer_id IS NOT NULL AND PMOD(HASH(o.buyer_id),3)=0
),
sig_visit AS (     -- 商详浏览PV (7天)
    SELECT uid, COUNT(1) AS visit_7d
    FROM hdp_zhuanzhuan_dm_global.dm_trade_visit_detail_1d
    WHERE dt BETWEEN DATE_SUB('${D}',6) AND '${D}'
    GROUP BY uid
),
sig_search AS (    -- 搜索次数 (7天, keyword非空)
    SELECT uid, COUNT(1) AS search_7d
    FROM hdp_zhuanzhuan_dm_global.dm_trade_list_page_detail_1d
    WHERE dt BETWEEN DATE_SUB('${D}',6) AND '${D}'
      AND keyword IS NOT NULL AND keyword <> ''
    GROUP BY uid
),
sig_love AS (      -- 下单+加购+收藏 合并 (7天)
    SELECT uid, COUNT(1) AS love_7d FROM (
        SELECT buyer_id AS uid FROM hdp_zhuanzhuan_dm_global.dm_trade_com_order_detail_1d
            WHERE dt BETWEEN DATE_SUB('${D}',6) AND '${D}' AND buyer_id IS NOT NULL
        UNION ALL
        SELECT uid FROM hdp_zhuanzhuan_dm_global.dm_trade_list2cart_detail_1d
            WHERE dt BETWEEN DATE_SUB('${D}',6) AND '${D}' AND uid IS NOT NULL
        UNION ALL
        SELECT uid FROM hdp_zhuanzhuan_dw_global.dw_zz_label_b2c_favorite_product_event_detail_inc_1d
            WHERE dt BETWEEN DATE_SUB('${D}',6) AND '${D}' AND uid IS NOT NULL
    ) u GROUP BY uid
),
sig_deal AS (      -- 历史成交: 7天内业务范围内成交订单数
    SELECT o.buyer_id AS uid, COUNT(DISTINCT o.order_id) AS deal_7d
    FROM hdp_zhuanzhuan_dw_global.dw_trade_order_company_all_detail_full_1d o
    JOIN info_tag t ON o.info_id = t.info_id
    WHERE o.dt = '${SNAP}'
      AND SUBSTR(o.pay_time,1,10) BETWEEN DATE_SUB('${D}',6) AND '${D}'
      AND o.is_pure_pay_success=1 AND o.order_structure_type IN (0,1)
      AND o.buyer_id IS NOT NULL
    GROUP BY o.buyer_id
)
SELECT p.uid,
    COALESCE(v.visit_7d,0)  AS visit_7d,
    COALESCE(s.search_7d,0) AS search_7d,
    COALESCE(l.love_7d,0)   AS love_7d,
    COALESCE(d.deal_7d,0)   AS deal_7d
FROM paid_uid p
LEFT JOIN sig_visit  v ON p.uid=v.uid
LEFT JOIN sig_search s ON p.uid=s.uid
LEFT JOIN sig_love   l ON p.uid=l.uid
LEFT JOIN sig_deal   d ON p.uid=d.uid;

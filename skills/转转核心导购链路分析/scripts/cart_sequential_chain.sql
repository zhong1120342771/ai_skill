-- 【购物车来源专用】购物车=用户从「加购/购物车」列表进入的商品(埋点 actiontype=Q9753 region=q)
-- 交易dm表对购物车无 first_from 场景值，无法场景归因，故本 SQL 走时序链路补数(其余4来源见 run_full_chain.py)
-- 购物车(加购)时序链路 by 品类: 购物车曝光->商详(访问表)->收银台->支付, 各环节时间>=购物车曝光
-- 品类归属: 用购物车曝光 goodsList 展开出的 info_id join 品类维表判定业务
-- App terminal 15/16, dt 替换成目标日期; token级去重UV
WITH biz AS (
  SELECT info_id,
    CASE WHEN cus_business_bu IN ('消费电子') THEN '消费电子'
         WHEN cus_business_bu IN ('二奢') AND business_line_id IN (915051,915061) THEN '二奢'
         WHEN cus_business_bu IN ('二奢') THEN '兴趣'
         WHEN cus_business_bu IN ('长尾N') THEN '兴趣'
         ELSE '其他' END AS cate
  FROM hdp_zhuanzhuan_dw_global.dw_mysql_info_full_1d
  WHERE dt='2026-08-11'
    AND cus_business_extend['is_cp_flag']='0' AND cus_business_extend['is_live_flag']='0'
    AND (cus_business_bu IN ('消费电子','长尾N','二奢')
         OR (cus_business_belong IN ('B2C') AND cate_second_id IN ('120'))
         OR (cate_id='2120006' AND cus_business_belong IN ('B2C')))
  GROUP BY info_id, 2
),
cart AS (
  SELECT token, CAST(gid AS BIGINT) AS info_id, MIN(`timestamp`)/1000 AS cart_ts
  FROM hdp_zhuanzhuan_dw_global.dw_log_lego_action_1d
  LATERAL VIEW explode(split(datapool['goodsList'],'&')) g AS gid
  WHERE dt='2026-08-11' AND actiontype IN ('Q9753') AND region IN ('q') AND pagetype='explosureGoods'
    AND token IS NOT NULL AND token<>'' AND gid IS NOT NULL AND gid<>''
  GROUP BY token, CAST(gid AS BIGINT)
),
vv AS (SELECT token, info_id, max(`timestamp`) AS view_ts FROM hdp_zhuanzhuan_dm_global.dm_trade_visit_detail_1d WHERE dt='2026-08-11' AND terminal IN ('15','16') AND info_id IS NOT NULL GROUP BY token, info_id),
oo AS (SELECT token, info_id, max(`timestamp`) AS ord_ts  FROM hdp_zhuanzhuan_dm_global.dm_trade_order_detail_1d    WHERE dt='2026-08-11' AND terminal IN ('15','16') AND info_id IS NOT NULL GROUP BY token, info_id),
pp AS (SELECT token, info_id, max(`timestamp`) AS pay_ts  FROM hdp_zhuanzhuan_dm_global.dm_trade_pay_detail_1d      WHERE dt='2026-08-11' AND terminal IN ('15','16') AND info_id IS NOT NULL GROUP BY token, info_id),
-- 时序判定在 (token, info_id) 粒度: 购物车曝光后是否有商详/收银台/支付
chain AS (
  SELECT c.token, c.info_id,
    MAX(CASE WHEN vv.view_ts>=c.cart_ts THEN 1 ELSE 0 END) AS rv,
    MAX(CASE WHEN oo.ord_ts>=c.cart_ts THEN 1 ELSE 0 END) AS rc,
    MAX(CASE WHEN pp.pay_ts>=c.cart_ts THEN 1 ELSE 0 END) AS rp
  FROM cart c
  LEFT JOIN vv ON c.token=vv.token AND c.info_id=vv.info_id
  LEFT JOIN oo ON c.token=oo.token AND c.info_id=oo.info_id
  LEFT JOIN pp ON c.token=pp.token AND c.info_id=pp.info_id
  GROUP BY c.token, c.info_id
),
ch AS (
  SELECT chain.token, chain.rv, chain.rc, chain.rp, COALESCE(b.cate,'其他') AS cate
  FROM chain LEFT JOIN biz b ON chain.info_id=b.info_id
)
SELECT 'ALL' AS cate,
  COUNT(DISTINCT CASE WHEN rv=1 THEN token END) AS `商详UV`,
  COUNT(DISTINCT CASE WHEN rc=1 THEN token END) AS `收银台UV`,
  COUNT(DISTINCT CASE WHEN rp=1 THEN token END) AS `支付UV` FROM ch
UNION ALL
SELECT cate,
  COUNT(DISTINCT CASE WHEN rv=1 THEN token END),
  COUNT(DISTINCT CASE WHEN rc=1 THEN token END),
  COUNT(DISTINCT CASE WHEN rp=1 THEN token END) FROM ch GROUP BY cate
ORDER BY cate
LIMIT 50;

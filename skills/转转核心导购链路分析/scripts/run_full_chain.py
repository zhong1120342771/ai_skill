# -*- coding: utf-8 -*-
# 转转核心导购链路：5来源(搜索/feed/收藏/购物车/足迹) x 业务(消费电子/兴趣/二奢/其他) 完整链路
# A曝光: explosureGoods explode goodsList; B点击: zpmclick infoId非空; C商详/收银台/支付: dm表场景归因
#
# ============ 5 个导购来源含义（用户从哪个入口看到/点到商品）============
#   搜索   = 用户在搜索结果页看到/点击的商品        埋点 actiontype=E1007 region=e | 归因 first_from=search/recommend4Search
#   feed   = 首页推荐流(信息流)里刷到的商品          埋点 actiontype=G1001 region=g | 归因 first_from=homepage_rec*/homepage_filter
#   收藏   = 从「我的收藏」列表进入的商品            埋点 actiontype=J2963|T2488 region=j|t | 归因 first_from=getMyLoveInfosV3/getmyloveofflineinfoentrance
#   购物车 = 从「加购/购物车」列表进入的商品          埋点 actiontype=Q9753 region=q | 交易表无first_from,走时序链路(见cart_sequential_chain.sql)
#   足迹   = 从「浏览足迹」列表进入的商品            埋点 actiontype=V4961 region=v | 归因 first_from=getfootprint/getfootprint_invalid
#   曝光&点击共用同一套 actiontype+region；商详/收银台/支付走交易dm表 first_from(商详)/ori_firstfrom(收银台·支付)
# =====================================================================
import sys, json
sys.path.insert(0,'/Users/zhongmengting/.claude/skills/xinghe-data/scripts')
from xinghe_client import XingheExplorer
x=XingheExplorer()
# 取数日期：默认命令行第一个参数，否则 t-1；口径见 SKILL.md
DT = sys.argv[1] if len(sys.argv)>1 else None
if not DT:
    from datetime import date, timedelta
    DT=(date.today()-timedelta(days=1)).strftime('%Y-%m-%d')

BIZ = f"""biz AS (
  SELECT info_id,
    CASE WHEN cus_business_bu IN ('消费电子') THEN '消费电子'
         WHEN cus_business_bu IN ('二奢') AND business_line_id IN (915051,915061) THEN '二奢'
         WHEN cus_business_bu IN ('二奢') THEN '兴趣'
         WHEN cus_business_bu IN ('长尾N') THEN '兴趣'
         ELSE '其他' END AS cate
  FROM hdp_zhuanzhuan_dw_global.dw_mysql_info_full_1d
  WHERE dt='{DT}'
    AND cus_business_extend['is_cp_flag']='0' AND cus_business_extend['is_live_flag']='0'
    AND (cus_business_bu IN ('消费电子','长尾N','二奢')
         OR (cus_business_belong IN ('B2C') AND cate_second_id IN ('120'))
         OR (cate_id='2120006' AND cus_business_belong IN ('B2C')))
  GROUP BY info_id, 2
)"""

# A 曝光: 5来源 explode goodsList
A = f"""WITH {BIZ},
expo AS (
  SELECT src, token, CAST(gid AS BIGINT) AS info_id
  FROM (
    SELECT token, gid,
      -- 曝光来源识别: actiontype+region 定位用户在哪个导购入口看到该商品
      CASE
        WHEN actiontype='E1007' AND region='e' THEN '搜索'                       -- 搜索结果页曝光
        WHEN actiontype='G1001' AND region='g' THEN 'feed'                       -- 首页推荐流曝光
        WHEN actiontype='Q9753' AND region='q' THEN '购物车'                     -- 加购/购物车列表曝光
        WHEN actiontype IN ('J2963','T2488') AND region IN ('j','t') THEN '收藏'  -- 我的收藏列表曝光(在线J2963/离线T2488)
        WHEN actiontype='V4961' AND region='v' THEN '足迹'                       -- 浏览足迹列表曝光
      END AS src
    FROM hdp_zhuanzhuan_dw_global.dw_log_lego_action_1d
    LATERAL VIEW explode(split(datapool['goodsList'],'&')) g AS gid
    WHERE dt='{DT}' AND pagetype='explosureGoods'
      AND ( (actiontype='E1007' AND region='e') OR (actiontype='G1001' AND region='g')
         OR (actiontype='Q9753' AND region='q') OR (actiontype IN ('J2963','T2488') AND region IN ('j','t'))
         OR (actiontype='V4961' AND region='v') )
      AND token IS NOT NULL AND token<>'' AND gid IS NOT NULL AND gid<>''
  ) t WHERE src IS NOT NULL
  GROUP BY src, token, CAST(gid AS BIGINT)
)
SELECT e.src, COALESCE(b.cate,'其他') AS cate, COUNT(DISTINCT e.token) AS expo_uv
FROM expo e LEFT JOIN biz b ON e.info_id=b.info_id
GROUP BY e.src, COALESCE(b.cate,'其他') LIMIT 100"""

# B 点击: zpmclick region映射 infoId非空
B = f"""WITH {BIZ},
clk AS (
  SELECT src, token, CAST(iid AS BIGINT) AS info_id
  FROM (
    SELECT token, datapool['infoId'] AS iid,
      -- 来源: e=搜索结果页 / g=首页feed流 / q=购物车列表 / j,t=收藏列表 / v=浏览足迹
      CASE WHEN region='e' THEN '搜索' WHEN region='g' THEN 'feed' WHEN region='q' THEN '购物车'
           WHEN region IN ('j','t') THEN '收藏' WHEN region='v' THEN '足迹' END AS src
    FROM hdp_zhuanzhuan_dw_global.dw_log_lego_action_1d
    WHERE dt='{DT}' AND pagetype='zpmclick' AND region IN ('e','g','q','j','t','v')
      AND datapool['infoId'] IS NOT NULL AND datapool['infoId']<>''
      AND token IS NOT NULL AND token<>''
  ) t WHERE src IS NOT NULL AND iid RLIKE '^[0-9]+$'
  GROUP BY src, token, CAST(iid AS BIGINT)
)
SELECT c.src, COALESCE(b.cate,'其他') AS cate, COUNT(DISTINCT c.token) AS click_uv
FROM clk c LEFT JOIN biz b ON c.info_id=b.info_id
GROUP BY c.src, COALESCE(b.cate,'其他') LIMIT 100"""

# C 商详/收银台/支付: 4来源(搜索/feed/收藏/足迹)场景归因 x 品类. 商详first_from, 收银台/支付ori_firstfrom
C = f"""WITH {BIZ},
v AS (
  SELECT '1商详' AS step, token, info_id, first_from AS fromcol
  FROM hdp_zhuanzhuan_dm_global.dm_trade_visit_detail_1d
  WHERE dt='{DT}' AND terminal IN ('15','16') AND token IS NOT NULL AND token<>'' AND info_id IS NOT NULL
  UNION ALL
  SELECT '2收银台' AS step, token, info_id, ori_firstfrom AS fromcol
  FROM hdp_zhuanzhuan_dm_global.dm_trade_order_detail_1d
  WHERE dt='{DT}' AND terminal IN ('15','16') AND token IS NOT NULL AND token<>'' AND info_id IS NOT NULL
  UNION ALL
  SELECT '3支付' AS step, token, info_id, ori_firstfrom AS fromcol
  FROM hdp_zhuanzhuan_dm_global.dm_trade_pay_detail_1d
  WHERE dt='{DT}' AND terminal IN ('15','16') AND token IS NOT NULL AND token<>'' AND info_id IS NOT NULL
),
e AS (
  SELECT step, token, info_id,
    -- 交易dm表场景归因: 商详用first_from, 收银台/支付用ori_firstfrom, 映射到4个导购来源
    CASE
      WHEN fromcol IN ('search','recommend4Search') THEN '搜索'                                            -- 搜索结果页
      WHEN fromcol IN ('homepage_rec','homepage_rec_personal','homepage_filter','homepage_rec_mix') THEN 'feed'  -- 首页推荐流
      WHEN fromcol IN ('getMyLoveInfosV3','getmyloveofflineinfoentrance') THEN '收藏'                       -- 我的收藏(在线+离线)
      WHEN fromcol IN ('getfootprint','getfootprint_invalid') THEN '足迹'                                   -- 浏览足迹
      ELSE '其他来源' END AS src
  FROM v
)
SELECT e.step, e.src, COALESCE(b.cate,'其他') AS cate, COUNT(DISTINCT e.token) AS uv
FROM e LEFT JOIN biz b ON e.info_id=b.info_id
WHERE e.src<>'其他来源'
GROUP BY e.step, e.src, COALESCE(b.cate,'其他') LIMIT 200"""

jobs={}
jobs['A_expo']=x.run_sql(A, sql_engine=5)
jobs['B_click']=x.run_sql(B, sql_engine=5)
jobs['C_sd_od_pay']=x.run_sql(C, sql_engine=5)
json.dump(jobs, open('/tmp/full5_jobs.json','w'))
print(json.dumps(jobs))

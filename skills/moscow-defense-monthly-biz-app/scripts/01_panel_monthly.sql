-- 01 月度全维度面板（月报核心表）
-- 输出文件：01_panel.csv
-- 覆盖：整体 + 5 个拆分维度（tag_01），每个 (tag_01, wd, 月份) 一行
-- 时间范围：dt in ['2025-01-01', '${outFileSuffix}']（同时覆盖去年同月，供同比使用）
-- 硬规则：必须有上界 dt <= '${outFileSuffix}'（本月末日），否则会捞进下一月初分区造成穿月
-- 月口径：substring(dt,1,7) AS 月份
-- 用途：Step 2 在 Python 端按月份切片算 月环比（本月 vs 上月）+ 同比（本月 vs 去年同月）
--       同时兜底 KPI 达成率表、整体漏斗横表、4 维度拆解表，替代周报的 01/02/03/04 四段 SQL
-- 说明：本表只出「月均绝对值 + 各率」，环比/同比一律由下游 Python 计算，避免 union all 窗口 NPE

select
    tag_01
    ,wd
    ,substring(dt, 1, 7) AS `月份`
    ,count(distinct dt) as `天数`
    -- 绝对值（月日均口径，与周报 avg 一致）
    ,avg(uv_all)   as `dau_日均`
    ,avg(pay_pv)   as `单量`
    ,avg(detail_uv) as `商详uv`
    ,avg(exp_uv)   as `曝光uv`
    ,avg(order_uv) as `下单uv`
    ,avg(exp_pv)   as `曝光pv`
    -- 各率（字符串带 %，下游解析为小数）
    ,concat(round(avg(pay_pv)/avg(uv_all)*100,3),'%')     as `dau-净支付pv转化率`
    ,concat(round(avg(pay_pv)/avg(detail_uv)*100,2),'%')  as `商详转化率`
    ,concat(round(avg(detail_uv)/avg(uv_all)*100,2),'%')  as `商详渗透率`
    ,concat(round(avg(exp_uv)/avg(uv_all)*100,2),'%')     as `曝光渗透率`
    ,concat(round(avg(detail_uv)/avg(exp_uv)*100,2),'%')  as `商详到达率`
    ,concat(round(avg(order_uv)/avg(detail_uv)*100,2),'%') as `下单率`
    ,concat(round(avg(pay_pv)/avg(order_uv)*100,2),'%')   as `支付率`
    ,concat(round(avg(pay_pv)/avg(exp_uv)*100,3),'%')     as `提袋率`
    ,round(avg(exp_pv)/avg(exp_uv)*100,2) as `人均曝光pv`
from
    hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zmt_app_v2_di
where
    dt >= '2025-01-01'
    and dt <= '${outFileSuffix}'
group by 1,2,3;

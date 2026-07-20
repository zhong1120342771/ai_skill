--时长&页面访问数
SELECT
    '时长&页面访问数量' as tag
    ,pagetype
    ,dt
    ,token
    ,actiontype --页面
    ,datapool['eventduration'] as eventduration -- 页面停留时长（秒）（LengthOfStay）
    ,timestamp
from hdp_zhuanzhuan_dw_global.dw_log_lego_action_1d
where
    dt='${outFileSuffix}'
    --AND actiontype in  ('G1001') and region='g' --(注：新版本四页面 G1001、G1002、G1003、G1004)
    --1.首页范围：首页整体只包含 g1001,在此页面产生的所有区域/元素/商品卡曝光
    and pagetype in ('AppStart','AppEnd','zpmshow');

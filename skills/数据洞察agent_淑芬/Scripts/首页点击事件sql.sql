--首页点击事件
SELECT
    '首页（G1001）点击事件' as tag
    ,dt
    ,token
    ,pagetype
    ,datapool['sectionId']  as sectionId -- 区域id
    ,datapool['subSectionId']  as subSectionId -- 子区域id
    ,datapool['subSectionName'] as subSectionName --子区域名称(2026-06-17 新增,与曝光事件对称)
    ,datapool['firsttab']  as firsttab -- 顶部tab
    ,datapool['infoId'] as infoid --商品id
    ,datapool['goodsList'] as goodsList --商品id list (feed流商品曝光，&分隔)
    ,datapool['indexList'] as indexList -- 顺序列表 indexList （金刚位的曝光，'&' 分隔,0开始编码）
    ,datapool['sortId'] as sortId --区域内子元素的ID值 （点击事件通用zpmclick，纯数字，默认从 0 开始自增)
    ,datapool['sortName'] AS sortName----区域内子元素的名称（点击事件通用zpmclick，1. 同一个sectionId内，避免重复；2. 支持中文、英文，确保好理解；3. 字符串长度限制，避免超长）
    ,datapool['sortIdList'] as sortIdList --索引ID数组 （组合元素曝光事件explosureitems，纯数字使用&分隔拼接)
    ,datapool['tabNameList'] AS tabNameList --tab的中文名称（数组）（组合元素曝光explosureitems）
    ,datapool['tabId'] AS tabId
    ,datapool['tabName'] AS tabName
    ,datapool['eventduration'] as eventduration -- 页面停留时长（秒）（LengthOfStay）
    ,timestamp
from hdp_zhuanzhuan_dw_global.dw_log_lego_action_1d
where
    dt='${outFileSuffix}'
    AND actiontype in  ('G1001') and region='g' --(注：新版本四页面 G1001、G1002、G1003、G1004)
    --1.首页范围：首页整体只包含 g1001,在此页面产生的所有区域/元素/商品卡点击
    and pagetype='zpmclick' --点击事件
    and datapool['sectionId'] in ('100','101','106','102','103','105','2001','108','109','110','139','164','165','301','302','500','300');--区域id限定

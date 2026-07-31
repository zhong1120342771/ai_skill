# 未达标指标归因打法

达成率表格填完后，对**未达标**指标做归因，写进飞书文档"未达标指标归因"章节。每条结论旁配图（见全局规则：图必须作为图片实体插在对应结论旁，不许只写图名、不许堆文末）。

## 归因主线（本轮已验证的叙事骨架）

把每个未达标指标沿漏斗链拆开（`drilldown.py` 的 `funnel_decomp`），先判断卡在前端还是后端：

1. **多数未达标卡在最前端"曝光渗透"环节，后端反而在改善。** 手机提袋率、新媒手机提袋率、5品类商详渗透率的下单率/支付效率都在涨，被曝光渗透率拖平。转化没变差，问题在流量触达面收缩。
2. **5品类曝光量在收缩，只有手机在扛增长。** 消电内部细拆（手机/5品类/N品类，再拆 5品类成员）：手机曝光UV 正增长且跑赢大盘，5品类/N品类曝光收缩。用 `growth()` 看 exp_uv 增长率。
3. **馆场景：入口在恢复，卡的是馆内转化。** 馆曝光渗透率回升，但馆提袋率/商详到达率全线下跌，指向选品、排序、承接策略变差（全人群普跌，非某类用户问题）。
4. **业务侧成因：曝光增量向兴趣、二奢倾斜，消电让出份额。** 兴趣/二奢曝光UV 高速增长，消电渗透率基数已高（~85%）天花板低，增量份额被摊薄。用底表业务行对比（只横比曝光UV 增长率，加脚注）。

叙事定位为"三类直接根因（前端曝光渗透 / 5品类曝光收缩 / 馆内转化 or 新媒召回承接）+ 一层业务侧成因"。具体几类按当期数据定，别硬套。

## tasks.json（喂给 drilldown.py --tasks）结构

```json
[
  {"kind": "funnel", "label": "手机提袋率(品类=1-手机)", "tag": "拆分品类", "wd": "1-手机"},
  {"kind": "drill",  "label": "手机提袋率 按场景", "tag": "交叉-品类_场景",
   "members": ["首页金刚位_1-手机","首页feeds_1-手机","馆_1-手机"], "num": "pay_pv", "den": "exp_uv"},
  {"kind": "growth", "label": "消电内部细拆", "tag": "拆分品类",
   "members": ["1-手机","2_5类目","3-N聚合"], "col": "exp_uv"},
  {"kind": "growth", "label": "业务侧曝光对比", "tag": "单维度-拆分品类",
   "members": ["业务_消费电子","业务_兴趣","业务_二奢"], "col": "exp_uv"}
]
```
注意 members 是**完整 wd 名**（交叉维度自己拼好下划线，脚本不再拼）。

## 底表补数（手表/耳机、业务对比）

明细缺的维度走星河底表。`xinghe_client` 是**库不是 CLI**：

```python
import sys; sys.path.insert(0, '/Users/zhongmengting/.claude/skills/xinghe-data/scripts')
from xinghe_client import XingheExplorer
c = XingheExplorer()
eid = c.run_sql(sql, sql_engine=5)          # 引擎5=Hive，hdp_zhuanzhuan_tmp_global 必须用它
res = c.wait_and_get_result(eid)
rows = res.get('previews')
```
Hive 严格模式：ORDER BY 必须带 LIMIT。凭证走环境变量（XINGHE_CLIENT_USER/SECRET/OA），别硬编码。参考 `biz_expose.sql` / `watch_earphone.sql` 模板（在本轮工作目录 xd_h1_analysis）。

## 归因图与文档写入

- 归因图用 matplotlib（PingFang 字体）：条形图标注增长率，达标/跑赢大盘绿、临界橙、未达标/负增长红，画参考线（大盘增速）。
- 插图到正文锚点旁：`lark-cli docs +media-insert` 传图拿 token → `block_replace` 把 `<img>` 塞进目标块（飞书 copy 成新 token）→ `block_delete` 临时块。`--file` 只吃 cwd 相对路径，绝对路径会被判 unsafe 静默丢图（记忆 `feedback-larkcli-media-insert-relpath`）。
- 文字段落写完先过 humanizer 去 AI 味，但绝不改数字/口径/结论。

---
name: 618消电数据日报机器人推送
version: 2.0.0
description: "莫斯科保卫战消电数据日报自动推送：读取监控方案文档、拉取最新漏斗数据、生成趋势图+汇总表+文字结论，推送到飞书群。每日定时推送或手动触发，长期常态运行。触发词：消电日报、莫斯科日报、推送日报、消电数据推送、618日报。"
metadata:
  requires:
    bins: ["lark-cli", "python3"]
---

# 莫斯科保卫战消电数据日报机器人推送

## 概述

每日自动执行以下流程，推送莫斯科保卫战项目的消电漏斗数据日报到飞书群。这是**长期常态日报**，起于 618 大促、618 结束后照常每天推送，不因大促结束而停。

> 命名与部分脚本文件名保留历史"618"字样只是遗留，业务上是莫斯科保卫战消电日报。**不要因"618 已结束"而停推或提醒停推。**

**推送目标群：** `oc_5306dee97d7bfecb2c5cadbabd0b59ec`  
**推送截止日期：** 无（长期持续推送）  
**方案文档：** https://zhuanspirit.feishu.cn/wiki/I6llwUEboi9QtKkBjS8cQpXAnlc  
**绘图脚本：** `scripts/gen_618_chart.py`（本 skill 目录下，复用避免重复造轮子）

> **日期口径（关键）**：`dt` 默认 = t-1，不要写死年月。**趋势对比统一用近 30 天滚动窗口**（今年 t-30~t-1；去年按日期对齐取同 30 天），不再按自然月、不锁任何大促窗口。Step2 就绪检查按 t-1 所在当月查 max_dt 属正常。SQL 里 `<今年start/end>`、`<去年start/end>`、`<t-1>` 均按运行日实际值代入。

---

## Step 1：读取方案文档，确认最新要求

```bash
lark-cli docs +fetch --api-version v2 \
  --doc "https://zhuanspirit.feishu.cn/wiki/I6llwUEboi9QtKkBjS8cQpXAnlc" \
  --scope section --start-block-id V3WNdBOV2oRyATx8O5NcIoGUnqe \
  --doc-format markdown
```

---

## Step 2：加载 Xinghe 凭证 & 检查数据就绪

每次执行前先确认凭证已加载（避免用错账号）：

```bash
source ~/.zshrc && echo "USER=${XINGHE_CLIENT_USER} OA=${XINGHE_OA}"
# 期望: USER=xn_zhongmengting OA=zz_zhongmengting
```

**检查 t-1 数据是否就绪：**

```python
import sys
from datetime import date, timedelta
sys.path.insert(0, '/Users/zhongmengting/.claude/skills/xinghe-data/scripts')
from xinghe_client import XingheExplorer
client = XingheExplorer()
t1 = date.today() - timedelta(days=1)          # t-1
ym = t1.strftime('%Y-%m')                       # 动态当月，如 '2026-07'
sql = f"""select max(dt) as max_dt
from hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zhibiao_zmt_3duan_sep_di
where tag_01='整体' and wd='整体' and substr(dt,1,7)='{ym}'"""
eid = client.run_sql(sql, sql_engine=5)   # ← 必须用 sql_engine=5（Hive），不是 engine=
r = client.wait_and_get_result(eid)
print(r['previews'])   # 与 t1.strftime('%Y-%m-%d') 比较判断是否就绪
```

**若 `max_dt < t-1`（数据未就绪）：自动触发星河刷新，不要干等、也不要只提示用户手动跑。**

处理步骤（严格按序）：

1. 自动触发星河数据更新任务 `doc_id=766872`（消电漏斗数仓刷新）：

```python
import sys, time
sys.path.insert(0, '/Users/zhongmengting/.claude/skills/xinghe-data/scripts')
from xinghe_client import XingheExplorer
client = XingheExplorer()
# 触发 doc_id=766872 的调度刷新（补 t-1 分区）
# ← 方法名是 run_doc_by_id，不是 run_doc；返回 execute_id
eid = client.run_doc_by_id(766872)
r = client.wait_and_get_result(eid)   # 等这次刷新跑完
print('refresh done:', r.get('previews'))
```

2. 触发后轮询等待：每隔几分钟重查 Step2 的 `max_dt`，直到 `max_dt >= t-1`。合理上限约 30 分钟。
3. 就绪后继续 Step3；若超时仍未就绪，则**不强推**，P2P 私信钟梦婷说明"消电日报 t-1 数据刷新超时，暂缓推送"，不要推半成品到群。
4. 触发失败或方法不可用时，回退为提示钟梦婷手动在星河运行 `doc_id=766872`，数据就绪后重跑本任务。

---

## Step 3：拉取趋势数据

**⚠️ Hive strict mode 限制：所有 ORDER BY 必须带 `limit 200`，否则报错。**

> **趋势窗口 = 近 30 天滚动窗口**（固定，不再按自然月）：今年取 `t-30 ~ t-1`，去年取**日期对齐的同一 30 天窗口**（去年同月同日的 t-1 往前 30 天）。跨月由日期直接圈定，无需再按 `substr(dt,1,7)` 卡月份。
> 下面 SQL 里 `<今年start>`=t-30、`<今年end>`=t-1；`<去年start>`/`<去年end>`=去年同期对齐窗口（见 Step 5a 计算）。
> **⚠️ 必须分年各查一次**（今年一条 SQL、去年一条 SQL，各自 `dt between ... limit 200`），Python 端再合并。星河 `previews` 单次约 50 行截断，两年 60 行一条混查会丢掉后半段（典型症状：8 月数据缺失、轴到 08-09 但线只到 07-30）。下面这条合并写法仅示意口径，实跑请拆成两条。

### 优先：旧表（有 uv_all，数据最完整）

```sql
-- 近30天滚动窗口（示意口径；实跑请分年各查一次避免 previews 截断）
select dt, uv_all, pay_pv, detail_uv, exp_uv, order_uv,
  round(pay_pv/uv_all*100,3) as conv_rate,
  round(exp_uv/uv_all*100,2) as exp_rate,
  round(detail_uv/exp_uv*100,2) as detail_reach_rate,
  round(order_uv/detail_uv*100,2) as order_rate,
  round(pay_pv/order_uv*100,2) as pay_rate
from hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zhibiao_zmt_v2_di
where tag_01='整体' and wd='整体'
  and ((dt between '<今年start>' and '<今年end>')
    or (dt between '<去年start>' and '<去年end>'))
order by dt limit 200
```

若旧表中 t-1 数据缺失（新表有但旧表没有），则用新表补充 t-1 当天漏斗：

```sql
-- 新表漏斗（uv_all 为 NULL，需另外补 DAU）
select dt, pay_pv, detail_uv, exp_uv, order_uv,
  round(detail_uv/exp_uv*100,2) as detail_reach_rate,
  round(order_uv/detail_uv*100,2) as order_rate,
  round(pay_pv/order_uv*100,2) as pay_rate
from hdp_zhuanzhuan_tmp_global.tmp_dws_msk_zhibiao_zmt_3duan_sep_di
where tag_01='整体' and wd='整体' and dt='<t-1>'
limit 10
```

```sql
-- 补 DAU（新表 uv_all 为 NULL 时）
select dt, count(distinct token) as uv_all
from hdp_zhuanzhuan_dm_global.dm_oper_user_layer_dtl_inc_1d
where dt='<t-1>' and terminal_name in ('转转APP','转转小程序','找靓机')
group by dt
```

拿到数据后，手动计算 conv_rate = pay_pv/uv_all×100，exp_rate = exp_uv/uv_all×100。

---

## Step 4：计算同环比

| 对比类型 | 说明 |
|------|------|
| 环比 | t-1 vs t-2（同为今年） |
| 同比-日期对齐 | t-1 vs 去年同月同日 |
| 同比-星期对齐 | t-1 vs 去年同月中最近的同一星期几 |

**如何确定同比星期对齐日期（按 t-1 动态取当年当月，不写死 6 月）：**

```python
from datetime import date, timedelta
t1 = date.today() - timedelta(days=1)          # t-1
y_last = t1.year - 1                             # 去年
mth = t1.month                                   # 当月
weekday = t1.weekday()                           # 0=周一 ... 6=周日
# 在去年同月内找与 weekday 相同、且最接近同日期的那天
import calendar
ndays = calendar.monthrange(y_last, mth)[1]
candidates = [date(y_last, mth, i) for i in range(1, ndays + 1)
              if date(y_last, mth, i).weekday() == weekday]
yoy_week_date = min(candidates, key=lambda d: abs(d.day - t1.day))
```

---

## Step 5：生成趋势图

使用 skill 目录下的复用脚本，避免每次重写绘图代码。

**Step 5a：准备数据 JSON**

```python
import json, calendar
from datetime import date, timedelta

WINDOW_DAYS = 30
# 按 t-1 动态确定窗口与对齐日期（不写死月份）
t1 = date.today() - timedelta(days=1)
latest_day = t1.strftime('%m-%d')                 # t-1 的月日，如 "08-09"
prev_day = (t1 - timedelta(days=1)).strftime('%m-%d')   # t-2

# 今年近30天窗口：t-30 ~ t-1
cy_start = (t1 - timedelta(days=WINDOW_DAYS - 1)).strftime('%Y-%m-%d')
cy_end   = t1.strftime('%Y-%m-%d')

# 去年日期对齐：去年同月同日为 t-1 对照，往前 30 天
ly_t1    = date(t1.year - 1, t1.month, t1.day)
ly_start = (ly_t1 - timedelta(days=WINDOW_DAYS - 1)).strftime('%Y-%m-%d')
ly_end   = ly_t1.strftime('%Y-%m-%d')

# 同比星期对齐：去年同月内与 t-1 同星期几、最接近同日的那天
y_last, mth, weekday = t1.year - 1, t1.month, t1.weekday()
ndays = calendar.monthrange(y_last, mth)[1]
cands = [date(y_last, mth, i) for i in range(1, ndays + 1)
         if date(y_last, mth, i).weekday() == weekday]
yoy_week_day = min(cands, key=lambda d: abs(d.day - t1.day)).strftime('%m-%d')

# 上面 SQL 的窗口占位符：今年 cy_start/cy_end；去年 ly_start/ly_end
chart_data = {
    "2025": { ... },   # 去年对齐 30 天窗口，键为 "MM-DD"
    "2026": { ... },   # 今年近 30 天窗口（含 t-1），键为 "MM-DD"
    "meta": {
        "latest_day": latest_day,
        "prev_day": prev_day,
        "yoy_date_day": latest_day,    # 同比日期对齐：去年同日
        "yoy_week_day": yoy_week_day,  # 同比星期对齐
    }
}
with open('/tmp/chart_data.json', 'w') as f:
    json.dump(chart_data, f)
```

> 绘图脚本 `gen_618_chart.py` 读取顶层年份键 `"2025"`/`"2026"`（每个是 `{"MM-DD": {...}}`）与 `meta`。跨年运行时按脚本约定填对应年份键。注意去年窗口按**日期对齐**（去年同月同日往前 30 天），画到同一条 x 轴上做同比对比。

**Step 5b：调用绘图脚本**

```bash
SKILL_DIR="/Users/zhongmengting/.claude/skills/618消电数据日报机器人推送"
python3 "${SKILL_DIR}/scripts/gen_618_chart.py" \
  "$(date -v-1d +%Y-%m-%d)" \
  /tmp/chart_data.json \
  ~/.claude/618_chart_$(date -v-1d +%m%d).png
```

---

## Step 6：上传图片到飞书

⚠️ **必须从 `~/.claude/` 目录调用，且使用 `./文件名` 相对路径，绝对路径会报错。**

```bash
cd ~/.claude && lark-cli im images create \
  --data '{"image_type":"message"}' \
  --file ./618_chart_<MMDD>.png \
  --as bot
# 返回 image_key，格式: img_v3_xxxx_...g
```

---

## Step 7：组装推送内容并推送

**消息格式模板（严格按此顺序）：**

```
## 【YYYY-MM-DD 消电数据日报】

**【结论】** {DAU净支付PV转化率}，同比/环比情况，涨在哪个环节/跌在哪个环节。
曝光渗透率持续同比偏低则注明差值。
单量 {单量}，同比日/周/环比；环比异常说明（周内规律或特殊节点）。
DAU {DAU}，同比/环比，是否正常。

---

**图1：去年 vs 今年 近30天趋势对比（{t-30} ~ {t-1}）**

![消电趋势图]({image_key})

---

**表1：{t-1}（t-1）各指标汇总**

| 指标 | 绝对值 | 环比(vs {t-2}) | 同比-日期对齐(vs 25/{月/日}) | 同比-星期对齐(vs 25/{月/日} {星期几}) |
|---|---|---|---|---|
| 单量 | ... | ... | ... | ... |
| DAU | ... | ... | ... | ... |
| DAU净支付PV转化率 | ... | ... | ... | ... |
| 曝光渗透率 | ... | ... | ... | ... |
| 商详到达率 | ... | ... | ... | ... |
| 下单率 | ... | ... | ... | ... |
| 支付率 | ... | ... | ... | ... |
```

**结论撰写要点：**
- 转化率涨 → 涨在哪个环节（商详到达率/下单率/支付率）
- 转化率跌 → 跌在哪个环节，是否持续
- 曝光渗透率同比持续偏低 5pp+ → 注明差值，建议关注曝光侧供给/策略
- 单量/DAU 同比偏低需判断是否大促节点高基数（如去年同期恰逢 618/双十一大促当日，属预期高基数非异动）
- 正向数据加粗，负向异常也加粗
- 环比下滑需说明是否属于正常周内节奏（注明星期几）

**推送命令：**

```bash
lark-cli im +messages-send \
  --chat-id oc_5306dee97d7bfecb2c5cadbabd0b59ec \
  --as bot \
  --markdown "..."
```

---

## 注意事项 & 常见坑

| 问题 | 原因 | 解决 |
|------|------|------|
| `run_sql()` 报 unexpected keyword argument | 参数名是 `sql_engine`，不是 `engine` | 用 `client.run_sql(sql, sql_engine=5)` |
| ORDER BY 报 SemanticException | Hive strict mode 禁止无 LIMIT 的 ORDER BY | 所有 ORDER BY 加 `limit 200` |
| 图片上传报 "cannot open file" | lark-cli 沙盒限制，不识别绝对路径 | `cd ~/.claude && lark-cli ... --file ./文件名.png` |
| 新表 uv_all 为 NULL | 新表 3duan_sep_di 设计如此 | 旧表优先；旧表无当天数据才用新表+单独补DAU |
| 同比星期对齐 | 按 t-1 动态取去年同月，不锁 618 窗口 | 在去年同月内取与 t-1 同星期几、最接近同日的那天 |
| 误以为 618 结束要停推 | 本 bot 实为莫斯科保卫战常态日报，命名带 618 是遗留 | 长期每天推，不停、不提醒停 |
| 数据未就绪 | 数仓调度延迟 | 等数据就绪后再推，不强制 |
| 趋势图轴30天但数据只有当月 | 取数仍按当月拉，只有当月点位 | 取数改近30天窗口（今年 t-30~t-1 + 去年日期对齐同窗口），Step3/Step5a 已改 |
| 近30天两年合并查只回到一半（如缺8月） | 星河 `previews` 单次约50行截断，60行会被砍 | **分年各查一次**（今年一条、去年一条）再在 Python 合并，别一条 SQL 混查两年 |

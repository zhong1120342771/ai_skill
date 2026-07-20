---
name: 用户分层-数据分析
description: 转转用户分层流水线第 2 步——分析各层用户特征画像，计算特征人群规模，发现关键洞察。
metadata:
  type: sub-skill
  parent: 转转用户分层
  step: 2
  inputs:
    - data_storage/user_segments_${dt}.csv
    - data_storage/segment_distribution_${dt}.csv
  outputs:
    - analysis_reports/seg_analysis_${dt}.json
    - analysis_reports/seg_analysis_${dt}.summary.md
---

# 用户分层-数据分析

## 基础与定位

本 skill 在 `data-explorer` 通用数据探索 agent 基础上，针对用户分层结果做**画像挖掘**，产出层级特征对比与特征人群规模，为报告生成提供数据依据。

## 前置阅读（每次执行前必读）

1. **[../../References/分层方案说明.md](../../References/分层方案说明.md)** — 各层业务含义、9 个特征人群的圈选逻辑
2. **[../../References/output-schemas.md](../../References/output-schemas.md)** §三 — `seg_analysis_${dt}.json` 字段契约

## 职责

用 pandas 读取 Step 1 产物，计算：

1. **整体分布**：各层用户数 + 占比（从 `segment_distribution_${dt}.csv` 直读）
2. **层级画像**：L5-L1 各层的六维均值（avg R 间隔、avg F 频次、avg M 金额、avg A 活跃分、avg P 价格分）+ 注册天数中位数
3. **特征人群圈选**：按 `References/分层方案说明.md` 第四章的圈选条件，计算 9 个人群各自的用户数和层内分布
4. **关键发现**：自动生成 3-5 条文字洞察（带数字，不要泛泛而谈）：
   - 高价值层（L5+L4）用户数 + 占比
   - L1 沉睡用户数 + 占比（激活空间）
   - 各维度在层间的最大差异（如 L5 vs L1 的支付频次倍数）
   - 新用户活跃人群规模（注册≤30天 + A_score≥3）
   - 搜而不买 / 加购未付人群的挽救价值估算（人数 × 同品类历史成交率）

## 执行方式（Python pandas）

```python
import pandas as pd
import numpy as np

df = pd.read_csv('~/.claude/data_storage/user_segments_${dt}.csv')
dist = pd.read_csv('~/.claude/data_storage/segment_distribution_${dt}.csv')

# 层级画像
profile = df.groupby('segment_level').agg(
    avg_r_days   = ('r_last_pay_days', lambda x: x[x < 9999].mean()),
    avg_f_cnt    = ('f_pay_cnt_180d', 'mean'),
    avg_m_amt    = ('m_pay_amt_180d', 'mean'),
    avg_a_score  = ('a_score', 'mean'),
    avg_p_score  = ('p_score', 'mean'),
    med_regist_days = ('regist_days', 'median')
).round(2)

# 特征人群圈选（按 References/分层方案说明.md 第四章）
# 高频金主
gaojin = df[(df['segment_level'].isin(['L4','L5'])) & (df['f_score']==4) & (df['m_score']>=2)]
# 价值回流（历史成交≥3但近期沉睡）
huiliú = df[(df['r_score']==0) & (df['a_hist_order_cnt']>=3)]
# ... 按方案说明的其他圈选逻辑
```

## 产出

### `analysis_reports/seg_analysis_${dt}.json`

严格按 `References/output-schemas.md` §三的 schema，不要自创字段。

### `analysis_reports/seg_analysis_${dt}.summary.md`

一页纸摘要，格式：

```
## 用户分层分析摘要 · ${dt}

### 整体分布
| 层级 | 用户数 | 占比 | 均分 |
|---|---|---|---|
| L5 | xxx | x.xx% | xx.x |
...

### 关键发现
1. L5+L4 高价值用户 xx 万，占比 x.x%
2. L1 沉睡用户 xx 万，占比 xx%，…
3. ...

### 特征人群 TOP3
1. 搜而不买：xx 万人，是最大的潜力人群
2. ...
```

## 不要做的事

- 不要重新算评分（评分已在 Step 1 算好）
- 不要修改 References（真源在飞书文档）
- 不要在本步骤画图（画图是报告生成的事）
- 不要凭空推断业务结论（只描述数字事实和对比，机会点说"待验证"）

---
name: zhuanzhuan-retained-user-analysis
version: 2.0.0
description: "转转APP自然留存用户付费转化增长分析——全流程 SOP。覆盖分析框架搭建、数据处理、数据分析、报告可视化、全文双重数据校验、报告撰写、写入飞书、推送飞书消息 8 个阶段。当用户说「帮我做留存用户分析」「留存付费专题分析」「自然留存用户转化分析」「按上次的分析流程跑一遍」时触发。"
metadata:
  requires:
    bins: ["lark-cli", "python3"]
    python_libs: ["pandas", "numpy", "matplotlib"]
---

# 转转APP自然留存用户付费转化分析 — 全流程 SOP

> **前置条件：** 先阅读 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md) 了解认证规则。

---

## 快速上下文恢复

用户说"继续分析"或"按上次流程"时，先确认以下信息：

1. **数据文件路径**（100万抽样 CSV）——上次路径：`/Users/zhongmengting/Downloads/留存用户付费专题分析样本（100万抽样）.csv`
2. **目标飞书文档**（写入报告的文档 token）——上次：`HeQVdQqY9oyFKYxg4Mwcwh8An8g`
3. **推送对象**——默认推送给钟梦婷 P2P：`ou_5e572adca6deef8ef21c3b18dfade573`
4. **图表输出目录**——默认 `/tmp/report_charts/`（mkdir -p 确保存在）

---

## 阶段一：分析框架搭建

### 1.1 业务口径确认

在开始前，必须和用户确认以下口径，避免后续返工：

| 口径 | 本次使用的定义 |
|------|-------------|
| 分析对象 | 自然留存用户（非当日新增，App 端活跃） |
| 支付口径 | 净支付 = 支付且当日无退款 |
| 分析窗口 | 活跃后 7 日内净支付转化率 |
| 样本范围 | 随机抽样 100 万用户，全量换算系数 ×1.115 |
| 业务线范围 | 消费电子 / 二奢 / 兴趣N |

### 1.2 字段映射表（CSV 字段 → 业务含义）

```
token          用户唯一标识
dt             数据日期
register_gap   注册至今天数（用于注册阶段分层）
act_30         过去30天活跃天数
pay_gap_all    整体最近支付间隔（9999=无支付记录）
pay_gap_xfdz   消费电子最近支付间隔
pay_gap_es     二奢最近支付间隔
pay_gap_xq     兴趣N最近支付间隔
ord_t_365      过去365天整体支付次数
ord_7          7日内净支付（>0 表示有支付，支持累计次数）
ord_xfdz_7     7日内消费电子净支付
ord_es_7       7日内二奢净支付
ord_xq_7       7日内兴趣N净支付
sx_all         当日整体商详浏览次数（all=全品类）
sx_xfdz        当日消费电子商详浏览次数
sx_es          当日二奢商详浏览次数
sx_xq          当日兴趣N商详浏览次数
jg_all/xfdz/es/xq   加购次数（同上）
sc_all/xfdz/es/xq   收藏次数（同上）
xd_all/xfdz/es/xq   下单次数（注：二奢/兴趣N下单打点不准，不用于预测）
```

**⚠️ 重要注意事项：**
- `ord_7` 等支付字段是**次数**而非 0/1 标志，转化判断用 `(df['ord_7'] > 0)` 而非 `df['ord_7'].sum()`
- `pay_gap=9999` 表示无支付记录，分组时归入「365天+/无支付」
- 二奢/兴趣N 多信号分析**不含下单信号**（打点不准）

### 1.3 数据预检

```python
import pandas as pd
import numpy as np

df = pd.read_csv('/path/to/sample.csv')
print(f"总行数: {len(df):,}")
print(f"唯一用户: {df['token'].nunique():,}")
print(f"字段列表: {list(df.columns)}")
print(f"各字段 null 数:\n{df.isnull().sum()}")
print(f"\n整体转化率验证: {(df['ord_7']>0).sum()/len(df)*100:.2f}%")
# 期望约 2.3-2.9%（100万样本单日口径）
```

---

## 阶段二：数据处理

### 2.1 通用分组函数

```python
SCALE = 1.115  # 全量换算系数

def pay_gap_group(gap):
    """支付间隔分组"""
    if gap <= 30:   return '近期(0-30天)'
    elif gap <= 180: return '中期(31-180天)'
    elif gap <= 365: return '远期(181-365天)'
    else:            return '365天+/无支付'

def register_group(days):
    """注册阶段分组"""
    if days <= 30:   return '新用户(30天内)'
    elif days <= 180: return '早期(31-180天)'
    elif days <= 365: return '成长期(181-365天)'
    elif days <= 730: return '成熟用户(1-2年)'
    else:             return '老用户(2年+)'

def act_group(days):
    """活跃天数分组"""
    if days == 0:    return '0天'
    elif days <= 2:  return '1-2天'
    elif days <= 5:  return '3-5天'
    elif days <= 10: return '6-10天'
    else:            return '10天+'

# 应用分组
df['pay_gap_all_grp'] = df['pay_gap_all'].apply(pay_gap_group)
df['register_grp'] = df['register_gap'].apply(register_group)
df['act_grp'] = df['act_30'].apply(act_group)
```

### 2.2 转化率计算（正确口径）

```python
def calc_rate(sub_df, ord_col):
    """正确的转化率计算：分母是人数，判断是否 >0"""
    n = len(sub_df)
    paid = (sub_df[ord_col] > 0).sum()
    return paid / n * 100 if n > 0 else 0

# 按分组计算（示例：注册阶段 × 各业务线）
result = df.groupby('register_grp').apply(lambda g: pd.Series({
    'N': len(g),
    'pct': len(g)/len(df)*100,
    'full_est': len(g)*SCALE/10000,  # 万
    'rate_all': calc_rate(g, 'ord_7'),
    'rate_xfdz': calc_rate(g, 'ord_xfdz_7'),
    'rate_es': calc_rate(g, 'ord_es_7'),
    'rate_xq': calc_rate(g, 'ord_xq_7'),
}))
```

### 2.3 行为阈值分析（累计 ≥N 口径）

```python
def threshold_analysis(df, behavior_col, ord_col, thresholds):
    """
    行为阈值曲线数据
    thresholds: [(0, '0次基准'), (1, '≥1次'), (4, '≥4次'), ...]
    """
    rows = []
    for lo, label in thresholds:
        mask = (df[behavior_col] == 0) if lo == 0 else (df[behavior_col] >= lo)
        sub = df[mask]
        rows.append({
            'label': label,
            'N': len(sub),
            'pct': len(sub)/len(df)*100,
            'full': len(sub)*SCALE/10000 if len(sub)*SCALE >= 10000 else int(len(sub)*SCALE),
            'rate': calc_rate(sub, ord_col)
        })
    return pd.DataFrame(rows)

# 商详浏览阈值
sx_thresh = [(0,'0次'),(1,'≥1次'),(4,'≥4次'),(8,'≥8次'),(16,'≥16次'),(30,'≥30次')]
sx_all_res = threshold_analysis(df, 'sx_all', 'ord_7', sx_thresh)
```

---

## 阶段三：数据分析模块

分析模块按报告章节组织，每个模块输出一个 DataFrame，供后续可视化和报告撰写使用。

### 3.1 基础指标（一、分业务线基础指标）

```python
# 整体 + 各业务线转化率
base = {
    '整体': calc_rate(df, 'ord_7'),
    '消费电子': calc_rate(df, 'ord_xfdz_7'),
    '二奢': calc_rate(df, 'ord_es_7'),
    '兴趣N': calc_rate(df, 'ord_xq_7'),
}

# 商详渗透率
penetration = {
    '整体': (df['sx_all']>0).sum()/len(df)*100,
    '消电': (df['sx_xfdz']>0).sum()/len(df)*100,
    '二奢': (df['sx_es']>0).sum()/len(df)*100,
    '兴趣N': (df['sx_xq']>0).sum()/len(df)*100,
}

# 有行为用户的人均次数（两口径）
def per_user_stats(col):
    all_mean = df[col].mean()
    active_mean = df[df[col]>0][col].mean()
    return all_mean, active_mean
```

### 3.2 分层分析（二、分层分析）

按注册阶段、活跃天数、支付间隔、支付频次分别建表，调用 2.2 的分组函数。

### 3.3 行为阈值（三、关键行为阈值曲线）

```python
# 各行为 × 各业务线
behaviors = [
    ('sx_all','ord_7','整体商详'), ('sx_xfdz','ord_xfdz_7','消电商详'),
    ('sx_es','ord_es_7','二奢商详'), ('sx_xq','ord_xq_7','兴趣N商详'),
    ('jg_all','ord_7','整体加购'), ('sc_xfdz','ord_xfdz_7','消电收藏'),
    ('sc_es','ord_es_7','二奢收藏'), ('sc_xq','ord_xq_7','兴趣N收藏'),
]
threshold_results = {}
for bc, oc, name in behaviors:
    threshold_results[name] = threshold_analysis(df, bc, oc,
        [(0,'0次'),(1,'≥1次'),(2,'≥2次'),(4,'≥4次'),(8,'≥8次'),(16,'≥16次'),(30,'≥30次')])
```

### 3.4 多信号组合

```python
# 信号定义：收藏/加购/下单各算1重；二奢/兴趣N不含下单
df['sig_xfdz'] = (df['sc_xfdz']>0).astype(int) + (df['jg_xfdz']>0).astype(int) + (df['xd_xfdz']>0).astype(int)
df['sig_es']   = (df['sc_es']>0).astype(int) + (df['jg_es']>0).astype(int)
df['sig_xq']   = (df['sc_xq']>0).astype(int) + (df['jg_xq']>0).astype(int)
df['sig_all']  = (df['sc_all']>0).astype(int) + (df['jg_all']>0).astype(int) + (df['xd_all']>0).astype(int)
```

---

## 阶段四：报告可视化

### 4.1 统一图表风格（必须遵守）

```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 全局字体设置
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti TC', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 统一配色
COLOR_OVERALL = '#4472C4'   # 整体——蓝
COLOR_XFDZ    = '#70AD47'   # 消费电子——绿
COLOR_ES      = '#FF6B6B'   # 二奢——红
COLOR_XQ      = '#FFC000'   # 兴趣N——黄

OUTPUT_DIR = '/tmp/report_charts'
import os; os.makedirs(OUTPUT_DIR, exist_ok=True)
```

### 4.2 标准双轴折线图（适用于分层分析各模块）

```python
def draw_dual_axis_line(x_labels, overall, xfdz, es, xq,
                         title, ylabel_left, ylabel_right, filename,
                         left_fmt='{:.1f}%', right_fmt='{:.3f}%'):
    """
    整体/消电用左轴，二奢/兴趣N用右轴（量级差异大时使用双轴）
    """
    x = np.arange(len(x_labels))
    fig, ax1 = plt.subplots(figsize=(10, 5.5))
    
    l1, = ax1.plot(x, overall, marker='o', color=COLOR_OVERALL, linewidth=2.2, markersize=7, label='整体')
    l2, = ax1.plot(x, xfdz,    marker='s', color=COLOR_XFDZ,    linewidth=2.2, markersize=7, label='消费电子')
    ax1.set_ylabel(ylabel_left, fontsize=11)
    ax1.set_ylim(0, max(overall+xfdz)*1.3)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: left_fmt.format(v)))
    
    ax2 = ax1.twinx()
    l3, = ax2.plot(x, es, marker='^', color=COLOR_ES, linewidth=2.2, markersize=7, linestyle='--', label='二奢')
    l4, = ax2.plot(x, xq, marker='D', color=COLOR_XQ, linewidth=2.2, markersize=7, linestyle='--', label='兴趣N')
    ax2.set_ylabel(ylabel_right, fontsize=11)
    ax2.set_ylim(0, max(es+xq)*1.3)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: right_fmt.format(v)))
    
    # 数据标签
    for xi, (ov, xf) in enumerate(zip(overall, xfdz)):
        ax1.annotate(left_fmt.format(ov), (xi, ov), textcoords='offset points', xytext=(0,8), ha='center', fontsize=8.5, color=COLOR_OVERALL)
        ax1.annotate(left_fmt.format(xf), (xi, xf), textcoords='offset points', xytext=(0,-14), ha='center', fontsize=8.5, color=COLOR_XFDZ)
    for xi, (ev, qv) in enumerate(zip(es, xq)):
        ax2.annotate(right_fmt.format(ev), (xi, ev), textcoords='offset points', xytext=(0,8), ha='center', fontsize=8.5, color=COLOR_ES)
        ax2.annotate(right_fmt.format(qv), (xi, qv), textcoords='offset points', xytext=(0,-14), ha='center', fontsize=8.5, color=COLOR_XQ)
    
    ax1.set_xticks(x)
    ax1.set_xticklabels(x_labels, fontsize=10.5)
    ax1.set_title(title, fontsize=13, fontweight='bold', pad=12)
    ax1.grid(axis='y', linestyle='--', alpha=0.4)
    
    fig.legend(handles=[l1,l2,l3,l4], loc='lower center', ncol=4,
               bbox_to_anchor=(0.5,-0.06), fontsize=10, frameon=True)
    plt.tight_layout()
    fig.savefig(f'{OUTPUT_DIR}/{filename}', dpi=150, bbox_inches='tight')
    plt.close()
```

### 4.3 热力图（支付间隔 × 频次交叉）

```python
def draw_heatmap(data_matrix, row_labels, col_labels, title, filename):
    """3×4 or N×M 热力图，颜色代表转化率高低"""
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    im = ax.imshow(data_matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=data_matrix.max()*1.1)
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.03)
    cbar.set_label('净支付转化率 (%)', fontsize=10)
    for i in range(len(row_labels)):
        for j in range(len(col_labels)):
            val = data_matrix[i, j]
            color = 'white' if val > data_matrix.max()*0.7 else 'black'
            ax.text(j, i, f'{val:.2f}%', ha='center', va='center', fontsize=12, fontweight='bold', color=color)
    ax.set_xticks(range(len(col_labels))); ax.set_xticklabels(col_labels, fontsize=11)
    ax.set_yticks(range(len(row_labels))); ax.set_yticklabels(row_labels, fontsize=11)
    ax.set_title(title, fontsize=13, fontweight='bold', pad=12)
    plt.tight_layout()
    fig.savefig(f'{OUTPUT_DIR}/{filename}', dpi=150, bbox_inches='tight')
    plt.close()
```

### 4.4 图表上传到飞书文档

```python
# 上传图片并记录 block_id（后续 move 到正确位置）
# ⚠️ 必须 cd 到 OUTPUT_DIR，使用相对路径
import subprocess
result = subprocess.run([
    'lark-cli', 'docs', '+media-insert', '--as', 'user',
    '--doc', DOC_ID,
    '--file', f'./{filename}',
    '--caption', caption,
    '--width', '800'
], cwd=OUTPUT_DIR, capture_output=True, text=True)

import json
data = json.loads(result.stdout)
block_id = data['data']['block_id']
```

---

## 阶段五：全文双重数据校验

**⚠️ 必须做两遍，校验顺序：**

### 第一遍：明细数据 vs 计算数据

对每个关键数字，用 Python 直接从 CSV 重新计算，和报告草稿对比：

```python
# 校验清单模板
VALIDATION_CHECKS = [
    # (校验项描述, 计算方式, 报告中的值)
    ('整体转化率', lambda: (df['ord_7']>0).sum()/len(df)*100, 'X.XX%'),
    ('消电转化率', lambda: (df['ord_xfdz_7']>0).sum()/len(df)*100, 'X.XX%'),
    ('商详渗透率', lambda: (df['sx_all']>0).sum()/len(df)*100, 'XX.XX%'),
    ('注册≤30天人数', lambda: (df['register_gap']<=30).sum(), 'XXXXX'),
    # ... 每个报告数字都列一条
]

for desc, calc_fn, reported in VALIDATION_CHECKS:
    actual = calc_fn()
    match = abs(actual - float(str(reported).replace('%','').replace(',',''))) < 0.01
    print(f"{'✅' if match else '❌'} {desc}: 计算={actual:.4f} 报告={reported}")
```

### 第二遍：报告内各模块数据内部一致性

检查以下逻辑一致性：

1. **占比加和 ≈ 100%**：注册阶段各段占比之和、支付间隔各段占比之和
2. **全量估算 = 样本量 × 1.115**：每个规模数字验证换算是否正确
3. **累计口径单调性**：阈值分析中 ≥1次、≥4次、≥8次的转化率应单调递增（如非单调，数据有问题）
4. **N 值大小关系**：≥4次的 N < ≥1次的 N
5. **二奢/兴趣N 无下单信号**：多信号分析中确认无下单字段

```python
# 累计阈值单调性校验
for name, res_df in threshold_results.items():
    rates = res_df[res_df['label'] != '0次']['rate'].values
    if not all(rates[i] <= rates[i+1] for i in range(len(rates)-1)):
        print(f"⚠️ {name} 阈值转化率非单调，请检查")
    else:
        print(f"✅ {name} 单调性通过")

# 占比加和
for col, grp_col in [('全量', 'register_grp')]:
    s = df.groupby(grp_col).size() / len(df) * 100
    print(f"{grp_col} 占比之和: {s.sum():.2f}%（应≈100%）")
```

---

## 阶段六：报告撰写规范

### 6.1 飞书文档 XML 格式规范

```bash
# 创建文档骨架
lark-cli docs +create --api-version v2 --content '<title>报告标题</title>...'

# 追加各章节内容
lark-cli docs +update --api-version v2 --doc "<doc_id>" --command append --content '...'

# 替换特定 block
lark-cli docs +update --api-version v2 --doc "<doc_id>" \
  --command block_replace --block-id "<id>" --content '...'

# 移动图片到表格下方（图片不能在单元格内）
lark-cli docs +update --api-version v2 --doc "<doc_id>" \
  --command block_move_after --block-id "<锚点id>" --src-block-ids "<img_id>"

# 删除 block
lark-cli docs +update --api-version v2 --doc "<doc_id>" \
  --command block_delete --block-id "<id>"
```

### 6.2 标准文档结构

```
<title>报告标题</title>

<!-- 取样说明 callout（蓝色，📌）-->
<callout emoji="📌" background-color="light-blue" border-color="blue">
  <p><b>取样范围</b>：... | <b>样本量</b>：... | <b>全量换算</b>：×1.115</p>
</callout>

<!-- 逻辑架构图（matplotlib 生成后 media-insert） -->

<!-- 核心结论 callout（黄色，💡）-->
<callout emoji="💡" background-color="light-yellow" border-color="yellow">
  <p>结论1... 结论2... 结论N...</p>
</callout>

<h1>一、分业务线基础指标对比</h1>
<h2>1.1 净支付转化率与支付用户体量</h2>
  <!-- callout + table + img（图在表格下方，不在单元格内）-->

<h2>1.2 品类渗透率与行为特征</h2>
  <!-- 两口径表格（全量口径/有行为用户口径）-->

<h1>二、分层分析</h1>
  <!-- 5个子章节，每章：callout 关键发现 + table + img -->

<h1>三、关键行为阈值曲线</h1>
  <!-- 商详/加购/收藏/多信号，格式统一：
       行为分层 | 整体（转化率 N值）| 消费电子 | 二奢 | 兴趣N -->

<h1>四、分业务线用户画像总结</h1>
  <!-- 3列表格：消电/二奢/兴趣N -->

<h1>五、策略优先级</h1>
  <!-- 含「超额贡献人数」列（不叫「增量」），callout 说明口径 -->
```

### 6.3 表格格式规范

```xml
<!-- 表头统一 light-gray 背景 -->
<table>
  <thead><tr>
    <th background-color="light-gray"><p><b>列1</b></p></th>
    <th background-color="light-gray"><p><b>列2</b></p></th>
  </tr></thead>
  <tbody><tr>
    <td><p>数据</p></td>
    <td><p>转化率<br/><span text-color="gray">（N=xx,xxx）</span></p></td>
  </tr></tbody>
</table>
```

### 6.4 Callout 颜色语义

| 语义 | emoji | background | border |
|------|-------|-----------|--------|
| 关键发现/结论 | 💡 | light-yellow | yellow |
| 取样/口径说明 | 📌 | light-blue | blue |
| 补充说明 | ℹ️ | light-gray | gray |
| 小样本警告 | ⚠️ | light-red | red |
| 最佳实践/推荐 | ✅ | light-green | green |

### 6.5 注意事项

- **图片不能放在表格单元格内**，必须在表格下方（用 `block_move_after` 调整位置）
- 表格和图片之间不需要空行
- `<br/>` 用于在同一个 `<p>` 内换行（如：转化率 + N值）
- XML 标签内文本：`<` → `&lt;`，`>` → `&gt;`，`&` → `&amp;`

---

## 阶段七：写入飞书文档

### 7.1 图片上传完整流程

```bash
# 1. 上传图片到文档末尾（自动获得 block_id）
cd /tmp/report_charts
lark-cli docs +media-insert --as user \
  --doc "<doc_id>" \
  --file ./chart_xxx.png \
  --caption "图：XXX" \
  --width 800

# 2. 记录返回的 block_id
# 3. 将图片 move 到对应表格下方
lark-cli docs +update --api-version v2 --doc "<doc_id>" \
  --command block_move_after \
  --block-id "<table_block_id>" \
  --src-block-ids "<img_block_id>"

# 4. 如果替换旧图：先 move 新图，再 block_delete 旧图
```

### 7.2 大段内容分批写入

超过 50 行 XML 时分批追加，每批不超过 50 行：

```bash
# 第一批：文档骨架 + 第一章
lark-cli docs +create --api-version v2 --content '<title>...</title><h1>...</h1>...'

# 后续每批追加
lark-cli docs +update --api-version v2 --doc "<doc_id>" \
  --command append --content '<h1>二、...</h1>...'
```

---

## 阶段八：推送飞书消息

```bash
# 标准推送格式（推给钟梦婷 P2P）
lark-cli im +messages-send --as user \
  --user-id "ou_5e572adca6deef8ef21c3b18dfade573" \
  --msg-type text \
  --text "✅ 报告标题\n报告链接：https://zhuanspirit.feishu.cn/docx/xxx\n\n核心结论摘要：\n• 结论1\n• 结论2"
```

---

## 数据一致性常见问题 & 解法

| 问题 | 原因 | 解法 |
|------|------|------|
| 转化率和预期差一倍 | 用了 `.sum()` 而非 `(>0).sum()` | 改为 `(df[col] > 0).sum() / len(df)` |
| 某业务线N值对不上 | 用了全量 pay_gap_all 分组，而非各自 pay_gap | 每个业务线用对应的 pay_gap_xfdz/es/xq 分组 |
| 双重结论文字不一致 | 开头结论和正文各模块数字不同步 | 以正文各模块的 DataFrame 为准，最后回写结论 |
| 图例和柱子重叠 | `fig.legend` 位置不对 | 用 `bbox_to_anchor=(0.5, -0.06)` 把图例移到图底部 |
| 图表在单元格内 | media-insert 默认插末尾，没有 move | 上传后立即做 block_move_after + 如有旧图做 block_delete |

---

## 参考数据（上次实际分析结果，可作基线校验）

| 指标 | 数值 | 口径 |
|------|------|------|
| 样本整体转化率 | 约 2.86% | ord_7 > 0，100万样本 |
| 消费电子转化率 | 2.24% | ord_xfdz_7 > 0 |
| 二奢转化率 | 0.04% | ord_es_7 > 0 |
| 兴趣N转化率 | 0.11% | ord_xq_7 > 0 |
| 商详渗透率（整体）| 45.07% | sx_all > 0 |
| 商详渗透率（消电）| 41.53% | sx_xfdz > 0 |
| 商详渗透率（二奢）| 2.09% | sx_es > 0 |
| 加购渗透率（整体）| 37.94% | jg_all > 0 |
| 二奢近期支付转化率 | 7.77% | pay_gap_es ≤ 30，ord_es_7 > 0 |
| 消电 Aha Moment | 商详 ≥8次，转化率 11.08% | sx_xfdz ≥ 8 |
| 二奢 Aha Moment | 商详 ≥30次，转化率 8.75% | sx_es ≥ 30 |
| 8+次历史支付转化率 | 23.66% | ord_t_365 ≥ 8 |

---

## 知识库位置

已完成的报告：
- V2报告（2026.04）：`https://zhuanspirit.feishu.cn/docx/HeQVdQqY9oyFKYxg4Mwcwh8An8g`
- 知识库路径：梦婷的知识库 → 分析文档 → 【260525】自然留存用户支付转化增长分析报告

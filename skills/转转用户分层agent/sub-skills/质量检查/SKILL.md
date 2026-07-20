---
name: 用户分层-质量检查
description: 转转用户分层流水线第 3 步——数据质量闸口，层级分布合理性检验，passed=false 则阻断流水线。
metadata:
  type: sub-skill
  parent: 转转用户分层
  step: 3
  inputs:
    - data_storage/user_segments_${dt}.csv
    - analysis_reports/seg_analysis_${dt}.json
  outputs:
    - analysis_reports/quality_check_seg_${dt}.json
---

# 用户分层-质量检查

## 基础与定位

本 skill 承袭 `quality-assurance` 通用质量保障 agent 的能力，适配到用户分层场景：校验评分结果的完整性、层级分布的合理性、分析 JSON 的字段契约符合性。**只判定，不修复**，`passed=false` 则阻断流水线。

## 前置阅读

**[../../References/output-schemas.md](../../References/output-schemas.md)** §四 — `quality_check_seg_${dt}.json` schema 与硬/软失败规则。

## 执行方式

**直接调固化脚本，不要即兴写 Python：**

```bash
python ~/.claude/skills/转转用户分层agent/scripts/qa_check.py --dt ${dt}
```

退出码：`0=passed`、`2=hard 失败`、`3=输入文件缺失`、`4=内部异常`。

## 校验清单

### 硬失败（hard_failures，阻断流水线）

| 检查项 | 阈值 | 说明 |
|---|---|---|
| user_segments 文件存在且非空 | rows > 0 | 文件为空视为 Step 1 失败 |
| L5 占比 | < 2% | 超过说明评分参数可能异常 |
| L1 占比 | > 10%（预期 50-60%，差异>20pp 视为异常）| 极端分布触发人工确认 |
| total_score 范围 | 0 ≤ score ≤ 39 | 超出说明评分公式错误 |
| 必备字段非空率 | token/segment_level ≥ 99.9% | 分层字段缺失无意义 |

### 软失败（soft_failures，不阻断，报告中标注）

| 检查项 | 阈值 |
|---|---|
| L5 占比 < 0.1%（过少，可能评分阈值过严） | warn |
| L1 占比 > 70%（过多） | warn |
| p_score = 0 的用户占比 > 80%（可能 P 维度数据不全）| warn |

### 统计抽检

- 随机抽 5 个 token，复算其 total_score（r×2+f×3+m+l+a×2+p），与 CSV 中字段比对是否一致

## 产物

按 `output-schemas.md` §四输出 `quality_check_seg_${dt}.json`：
- `passed` = `len(hard_failures) == 0`
- 所有检查项结果都写进 `notes` 以便审计

## 失败处理

- 硬失败：退出码 2，编排器停止，等人工处理
- 软失败：继续，但 Step 4 报告必须在「数据说明」中标注⚠

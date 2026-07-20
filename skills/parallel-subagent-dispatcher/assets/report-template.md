# Unified Report Template

Use this template for the final merged output presented to the
user.

---

# {Task Title} — 并行分析报告

## 📊 概览

| 指标 | 数值 |
|------|------|
| 处理项目数 | {N} |
| 成功完成 | {N_success} |
| 失败 | {N_failed} |
| 发现问题总数 | {M_total} |
| 🔴 高优先级 | {X} |
| 🟡 中优先级 | {Y} |
| 🟢 低优先级 | {Z} |

---

## 🔴 高优先级 ({X})

| 来源 | 位置 | 问题 | 建议 |
|------|------|------|------|
| {source} | {line/section} | {issue} | {suggestion} |

*如无高优先级问题，显示：✅ 未发现高优先级问题*

---

## 🟡 中优先级 ({Y})

| 来源 | 位置 | 问题 | 建议 |
|------|------|------|------|

---

## 🟢 低优先级 ({Z})

| 来源 | 位置 | 问题 | 建议 |
|------|------|------|------|

---

## 跨项目共性问题

*仅当同一问题在 >= 2 个项目中出现时填写*

| 问题 | 影响范围 |
|------|---------|
| {issue} | {source1}, {source2}, {source3} |

---

## ❌ 失败项目

*如全部成功，跳过此节*

| 项目 | 失败原因 |
|------|---------|
| {item} | {error} |

---

## 📝 处理说明

- 并行子代理数：{agent_count}
- 合并策略：{merge_strategy}
- 去重规则：{dedup_rule}
- 生成时间：{timestamp}

# 子 agent 回传契约

每个执行型子 agent 完成后，必须回传**结构化结果**给主流程，而不是长篇叙述。
主流程只读这份回传就能判断该单元成没成、有没有越界、要不要重试。

## 标准回传 schema

```json
{
  "unit_id": "string，与分派清单一致（必填）",
  "status": "done | partial | failed",
  "files_changed": ["实际改动的文件路径列表"],
  "summary": "一两句话：这个单元做了什么",
  "self_check": {
    "ran": "自检跑了什么（如 tsc / pytest tests/x）",
    "passed": true,
    "detail": "失败时写失败信息"
  },
  "out_of_scope_touched": ["越界改到的文件，正常应为空数组"],
  "leftovers": ["没做完或留给主流程/人工确认的事项"],
  "notes": "给集成阶段的提示，如改了某接口签名、加了依赖 X"
}
```

## 字段约束

- **files_changed**：必须落在 brief 声明的文件边界内。若 `out_of_scope_touched` 非空，
  主流程要警惕并行写冲突，进集成验证前重点核对。
- **status=partial**：做了一部分，`leftovers` 说明剩什么、为什么（如缺依赖、需人工决策）。
- **status=failed**：`self_check.detail` 或 `notes` 写清失败原因，供主流程决定重试还是跳过。
- **notes** 是跨单元协同的关键：改了共享接口、加了新依赖、约定了新常量都写这里，
  集成阶段据此查交界处。

## 为什么要结构化

- 主流程上下文只进 JSON，不进子 agent 的完整改动过程和推理链，省 context。
- `files_changed` + `out_of_scope_touched` 让主流程能机械地校验「无并行写冲突」这条硬约束。
- 失败单元有统一字段，方便批量汇总而不是逐个读长文本。

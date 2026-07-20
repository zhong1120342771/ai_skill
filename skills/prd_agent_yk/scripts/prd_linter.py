#!/usr/bin/env python3
"""PRD 交付助手 v0.7 的最小结构校验器。

本校验器只检查硬性输出契约，不判断产品方案质量。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_REQUIRED_SECTIONS = [
    "## 1. 文档信息与需求摘要",
    "## 2. 需求成立：背景、目标、用户、范围",
    "## 3. 方案总览与关键决策",
    "## 4. 核心改动对象",
    "## 5. 发布、产品风险与待确认项",
    "## 6. 下游关注",
]

DEFAULT_DOCUMENT_STATUSES = [
    "需求梳理稿",
    "PRD 草案",
    "PRD 草案（含待确认项，不可研发排期）",
    "研发交付版",
]

DEFAULT_REQUIRED_CCO_FIELDS = [
    "对象信息",
    "当前逻辑",
    "目标行为",
    "触发条件与前置条件",
    "主流程",
    "业务规则",
    "异常与边界",
    "页面 / 原型",
    "数据需求 / 系统能力 / 权限 / 埋点目标",
    "验收标准",
    "测试建议",
]

DEFAULT_DOWNSTREAM_COLUMNS = ["协作方", "关注内容", "为什么需要关注", "是否可能影响产品策略", "建议处理阶段"]
DEFAULT_DOWNSTREAM_VALUES = {"是", "否", "N/A"}
DEFAULT_LIGHT_REQUIRED_TERMS = ["改动内容", "影响范围", "验收"]
DEFAULT_STRATEGY_LEVELS = {"lightweight", "standard", "complex"}
DEFAULT_STRATEGY_STATUS_VALUES = {"confirmed", "assumption", "blocker", "N/A"}
DEFAULT_INPUT_SIGNAL_FIELDS = ["name", "source", "status"]
DEFAULT_RESOURCE_MAPPING_FIELDS = [
    "strategy_result",
    "surface",
    "display_priority",
    "replace_or_mix",
    "fallback",
    "status",
]
DEFAULT_COMPLEX_UPGRADE_HINTS = [
    "multi_signal",
    "multi_object",
    "multi_resource",
    "multi_goal",
    "multi_conflict",
    "affects_core_business_goal",
    "affects_experiment_result",
    "affects_downstream_start",
]
DEFAULT_SIGNOFF_STATUSES = {"pending", "accepted", "modified", "skipped_with_blocker"}
DEFAULT_SIGNOFF_CHOICES = {"A", "B", "C", "unknown"}
DEFAULT_SIGNOFF_ITEM_FIELDS = [
    "id",
    "item",
    "status",
    "user_choice",
    "user_choice_evidence",
    "recommended_value",
    "alternatives",
    "impact_if_unconfirmed",
    "default_handling",
    "blocker_ref",
]
DEFAULT_SIGNOFF_RECORD_FIELDS = [
    "agent_prompt_type",
    "user_raw_reply",
    "interpreted_choice",
    "fuzzy_confirmation_detected",
    "followup_required",
]
DEFAULT_SIGNOFF_PROMPT_TYPES = {
    "strategy_signoff_card",
    "strategy_signoff_followup",
    "modified_strategy_summary",
    "prd_generation_after_signoff",
}
DEFAULT_SIGNOFF_ACTIONS = {
    "accept_recommendation",
    "modify_strategy",
    "skip_signoff_with_blocker",
    "unknown",
}
DOWNSTREAM_ASSUMPTION_KEYWORDS = {
    "研发": ["研发", "实现", "接口", "开发", "联调", "技术"],
    "设计": ["设计", "设计范围", "页面", "交互", "原型", "视觉", "展示"],
    "测试": ["测试", "验收", "用例"],
    "数据": ["数据", "指标", "口径", "埋点", "实验", "结论", "归因", "看板"],
    "运营/客服": ["运营", "客服", "上线", "发布", "灰度", "回滚", "配置", "资源位配置"],
}
KEY_ASSUMPTION_IMPACT_PATTERN = re.compile(
    r"研发|实现|测试|验收|数据|口径|实验|结论|上线|风险|资源位|接口|埋点|归因|灰度|回滚|"
    r"权限|资金|核心流程|状态流转|核心策略|权重|阈值|资源位映射|频控|冲突优先级|"
    r"净支付\s*PV|站外数据|可用性|观察窗口"
)
DELIVERY_BLOCKING_ASSUMPTION_PATTERN = re.compile(
    r"研发|实现|测试|验收|数据|口径|实验|结论|上线|风险|接口|埋点|归因|灰度|回滚"
)
WEAK_STRATEGY_PATTERNS = [
    r"强\s*/\s*中\s*/\s*弱",
    r"高优先级",
    r"低频曝光",
    r"资源位倾斜",
    r"根据实际情况",
    r"由算法确认",
    r"由研发确认",
    r"后续补充",
]

STATE_FLOW_KEYWORDS = [
    "订单",
    "支付",
    "退款",
    "履约",
    "工单",
    "审核",
    "审批",
    "状态流转",
    "状态机",
]

RETRIEVAL_SOURCE_STATUSES = {"checked", "not_checked", "not_found", "unavailable", "N/A"}
RETRIEVAL_NO_EVIDENCE_STATUSES = {"not_checked", "not_found", "unavailable", "N/A", ""}
RETRIEVAL_SCAN_LEVELS = {"none", "light", "deep"}
RETRIEVAL_HIGH_IMPACT_HANDLINGS = {"ask_user", "dev_fallback", "block"}
RETRIEVAL_QUERY_SCOPES = {
    "specified_root",
    "specified_subtree",
    "global_search",
    "local_file",
    "user_provided",
    "unavailable",
    "N/A",
}
RETRIEVAL_VALID_LIBRARY_QUERY_SCOPES = {"specified_root", "specified_subtree"}
HISTORICAL_PRD_VALID_SOURCE_SCOPES = {
    "default_historical_prd_library",
    "user_provided_historical_prd_library",
}
HISTORICAL_PRD_INVALID_SOURCE_SCOPES = {"local_file", "test_export"}
BEHAVIOR_DELTA_REQUIRED_FIELDS = [
    "triggered",
    "draft_after_retrieval",
    "closure_before_prd",
]
BEHAVIOR_DELTA_DRAFT_FIELDS = [
    "changed_behaviors",
    "scenarios",
    "unresolved_scenarios",
]
BEHAVIOR_DELTA_CLOSURE_FIELDS = ["checked", "unresolved_scenarios", "handling_summary"]
BEHAVIOR_DELTA_SCENARIO_FIELDS = ["given", "when", "then", "status", "handling"]
BEHAVIOR_DELTA_STATUSES = {"closed", "assumption", "blocker", "needs_signoff", "N/A"}
BEHAVIOR_DELTA_HANDLINGS = {
    "include_in_signoff",
    "write_as_assumption",
    "write_as_blocker",
    "no_action",
}
DEMAND_ESTABLISHMENT_FIELDS = [
    "status",
    "confirmation_mode",
    "summary",
    "inferred_fields",
    "user_action",
    "blocks_strategy_signoff",
]
DEMAND_ESTABLISHMENT_STATUSES = {
    "display_passed",
    "confirmation_required",
    "accepted",
    "modified",
    "assumed",
    "blocked",
    "pending",
}
DEMAND_ESTABLISHMENT_MODES = {"display", "confirm", "N/A"}
DEMAND_ESTABLISHMENT_ACTIONS = {
    "not_required",
    "accepted",
    "modified",
    "proceed_with_assumption",
    "pending",
}
DEMAND_ESTABLISHMENT_BLOCKING_STATUSES = {"confirmation_required", "blocked", "pending"}
DEMAND_ESTABLISHMENT_DELIVERY_BLOCKING_STATUSES = {
    "assumed",
    "blocked",
    "confirmation_required",
    "pending",
}

CCO_DIMENSION_ONLY_PATTERN = re.compile(
    r"规则|数据|观测|实验|验收|测试|埋点|原型|指标|记录|统计"
)
CCO_PRODUCT_OBJECT_PATTERN = re.compile(
    r"页面|模块|入口|流程|状态|能力|配置|资源位|商卡|弹窗|浮层|订单|退款|支付|审核|任务"
)

CHATTER_PATTERNS = [
    r"少爷",
    r"丁丁",
    r"❤️",
    r"下面是.*PRD",
    r"我已经",
    r"我来",
    r"可直接用于研发评审",
]


@dataclass
class Finding:
    code: str
    severity: str
    message: str
    autofixable: bool


@dataclass
class Contracts:
    required_sections: list[str]
    document_statuses: list[str]
    required_cco_fields: list[str]
    downstream_columns: list[str]
    downstream_values: set[str]
    core_downstream_roles: list[str]
    strategy_levels: set[str]
    input_signal_statuses: set[str]
    input_signal_fields: list[str]
    resource_mapping_fields: list[str]
    complex_upgrade_hints: list[str]
    signoff_statuses: set[str]
    signoff_choices: set[str]
    signoff_item_fields: list[str]
    signoff_record_fields: list[str]
    signoff_prompt_types: set[str]
    signoff_actions: set[str]


def read_yaml_list(path: Path, key: str) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    values: list[str] = []
    in_key = False
    for line in lines:
        if re.match(rf"^{re.escape(key)}\s*:", line):
            in_key = True
            continue
        if in_key:
            if line and not line.startswith(" ") and not line.startswith("-"):
                break
            match = re.match(r'\s*-\s*"?(.+?)"?\s*$', line)
            if match:
                values.append(match.group(1))
    return values


def load_contracts() -> Contracts:
    contracts_dir = ROOT / "contracts"
    required_sections = read_yaml_list(contracts_dir / "prd_contract.yaml", "required_sections")
    document_statuses = read_yaml_list(contracts_dir / "prd_contract.yaml", "document_status_enum")
    required_cco_fields = read_yaml_list(contracts_dir / "cco_contract.yaml", "required_cco_fields")
    downstream_columns = read_yaml_list(
        contracts_dir / "downstream_readiness_contract.yaml", "required_columns"
    )
    downstream_values = set(
        read_yaml_list(contracts_dir / "downstream_readiness_contract.yaml", "strategy_impact_enum")
    )
    core_downstream_roles = read_yaml_list(
        contracts_dir / "downstream_readiness_contract.yaml", "default_roles"
    )
    strategy_levels: set[str] = set()
    input_signal_statuses = set(
        read_yaml_list(contracts_dir / "strategy_contract.yaml", "input_signal_status_enum")
    )
    input_signal_fields = read_yaml_list(
        contracts_dir / "strategy_contract.yaml", "input_signal_required_fields"
    )
    resource_mapping_fields = read_yaml_list(
        contracts_dir / "strategy_contract.yaml", "resource_mapping_required_fields"
    )
    complex_upgrade_hints = read_yaml_list(
        contracts_dir / "strategy_contract.yaml", "upgrade_when_any_of"
    )
    signoff_statuses = set(
        read_yaml_list(contracts_dir / "strategy_contract.yaml", "strategy_signoff_status_enum")
    )
    signoff_choices = set(
        read_yaml_list(contracts_dir / "strategy_contract.yaml", "strategy_signoff_user_choice_enum")
    )
    signoff_item_fields = read_yaml_list(
        contracts_dir / "strategy_contract.yaml", "signoff_item_required_fields"
    )
    signoff_record_fields = read_yaml_list(
        contracts_dir / "strategy_contract.yaml", "signoff_record_required_fields"
    )
    signoff_prompt_types = set(
        read_yaml_list(contracts_dir / "strategy_contract.yaml", "signoff_agent_prompt_type_enum")
    )
    signoff_actions = set(
        read_yaml_list(contracts_dir / "strategy_contract.yaml", "signoff_interpreted_action_enum")
    )
    return Contracts(
        required_sections or DEFAULT_REQUIRED_SECTIONS,
        document_statuses or DEFAULT_DOCUMENT_STATUSES,
        required_cco_fields or DEFAULT_REQUIRED_CCO_FIELDS,
        downstream_columns or DEFAULT_DOWNSTREAM_COLUMNS,
        downstream_values or DEFAULT_DOWNSTREAM_VALUES,
        core_downstream_roles or ["研发", "设计", "测试", "数据", "运营/客服"],
        strategy_levels or DEFAULT_STRATEGY_LEVELS,
        input_signal_statuses or DEFAULT_STRATEGY_STATUS_VALUES,
        input_signal_fields or DEFAULT_INPUT_SIGNAL_FIELDS,
        resource_mapping_fields or DEFAULT_RESOURCE_MAPPING_FIELDS,
        complex_upgrade_hints or DEFAULT_COMPLEX_UPGRADE_HINTS,
        signoff_statuses or DEFAULT_SIGNOFF_STATUSES,
        signoff_choices or DEFAULT_SIGNOFF_CHOICES,
        signoff_item_fields or DEFAULT_SIGNOFF_ITEM_FIELDS,
        signoff_record_fields or DEFAULT_SIGNOFF_RECORD_FIELDS,
        signoff_prompt_types or DEFAULT_SIGNOFF_PROMPT_TYPES,
        signoff_actions or DEFAULT_SIGNOFF_ACTIONS,
    )


def section_between(text: str, start: str, end: str | None = None) -> str:
    start_idx = text.find(start)
    if start_idx == -1:
        return ""
    content_start = start_idx + len(start)
    if end is None:
        return text[content_start:]
    end_idx = text.find(end, content_start)
    if end_idx == -1:
        return text[content_start:]
    return text[content_start:end_idx]


def h2_headings(text: str) -> list[str]:
    return [line.rstrip() for line in text.splitlines() if line.startswith("## ")]


def extract_status(section_1: str, document_statuses: list[str]) -> str | None:
    for status in sorted(document_statuses, key=len, reverse=True):
        if status in section_1:
            return status
    return None


def lintable_blocker_line_items(text: str) -> list[tuple[int, str]]:
    """Return lines where blocker markers should count as real PRD content.

    Headings and fenced examples often mention the marker names themselves, such
    as "假设 / 阻塞 / N/A". Those should not downgrade the document status.
    """
    lines: list[tuple[int, str]] = []
    in_code = False
    for idx, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code or stripped.startswith("#"):
            continue
        lines.append((idx, line))
    return lines


def lintable_blocker_lines(text: str) -> list[str]:
    return [line for _, line in lintable_blocker_line_items(text)]


def has_blocker(text: str) -> bool:
    lintable = "\n".join(lintable_blocker_lines(text))
    return "[阻塞]" in lintable or re.search(r"\[阻塞 6-R[0-9]+\]", lintable) is not None


def split_cco_blocks(section_5: str) -> list[str]:
    matches = list(re.finditer(r"^### 核心改动对象", section_5, flags=re.M))
    blocks: list[str] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(section_5)
        blocks.append(section_5[start:end])
    return blocks


def cco_uses_fixed_field_content_table(block: str, required_fields: list[str]) -> bool:
    rows = markdown_table_rows(block)
    for index, row in enumerate(rows):
        if len(row) < 2:
            continue
        header = [cell.strip() for cell in row[:2]]
        if header[0] not in {"固定字段", "字段"} or header[1] != "内容":
            continue
        field_count = 0
        for data_row in rows[index + 1 :]:
            if len(data_row) < 2:
                continue
            field_name = re.sub(r"^[0-9]+[.、]\s*", "", data_row[0].strip())
            if field_name in required_fields:
                field_count += 1
        if field_count >= 5:
            return True
    return False


def markdown_table_rows(section: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def parse_blocker_refs(value: str) -> list[str]:
    return re.findall(r"6-R[0-9]+", value)


def extract_key_assumption_rows(section_6: str) -> list[tuple[str, str]]:
    rows = markdown_table_rows(section_6)
    assumption_rows: list[tuple[str, str]] = []
    for row in rows[1:]:
        row_text = " ".join(row)
        if not re.search(r"\b6-R[0-9]+\b", row_text):
            continue
        if "[假设]" not in row_text:
            continue
        if not KEY_ASSUMPTION_IMPACT_PATTERN.search(row_text):
            continue
        ref_match = re.search(r"\b6-R[0-9]+\b", row_text)
        assumption_rows.append((ref_match.group(0) if ref_match else "", row_text))
    return assumption_rows


def affected_by_key_assumption(role: str, assumption_text: str) -> bool:
    keywords = DOWNSTREAM_ASSUMPTION_KEYWORDS.get(role, [])
    return any(keyword in assumption_text for keyword in keywords)


def delivery_blocking_assumptions(
    assumption_rows: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    return [
        (assumption_ref, assumption_text)
        for assumption_ref, assumption_text in assumption_rows
        if DELIVERY_BLOCKING_ASSUMPTION_PATTERN.search(assumption_text)
    ]


def plan_has_dev_fallback(plan_text: str | None) -> bool:
    if not plan_text:
        return False
    retrieval = extract_top_level_block(plan_text, "retrieval_evidence")
    if not retrieval:
        return False
    dev_block = extract_yamlish_block(retrieval, "dev_fallback")
    fact_block = extract_yamlish_block(retrieval, "fact_classification")
    dev_status = clean_scalar(field_value(dev_block, "status"))
    dev_items = extract_yamlish_block(dev_block, "items")
    if dev_status == "registered" and ("- " in dev_items or "items: []" not in dev_block):
        return True
    requires_block = extract_yamlish_block(fact_block, "requires_dev_fallback")
    if "- " in requires_block:
        return True
    return re.search(r"requires_dev_fallback\s*:\s*\[[^\]\s].*?\]", fact_block) is not None


def retrieval_has_confirmed_current_fact(plan_text: str | None) -> bool:
    if not plan_text:
        return False
    retrieval = extract_top_level_block(plan_text, "retrieval_evidence")
    if not retrieval:
        return False
    fact_block = extract_yamlish_block(retrieval, "fact_classification")
    block = extract_yamlish_block(fact_block, "confirmed_by_business_map")
    if "- " in block:
        return True
    if re.search(r"confirmed_by_business_map\s*:\s*\[[^\]\s].*?\]", fact_block):
        return True
    dev_block = extract_yamlish_block(retrieval, "dev_fallback")
    return re.search(r"^\s*status\s*:\s*checked\s*$", dev_block, flags=re.M) is not None


def retrieval_plan_has_storage_context(plan_text: str | None) -> bool:
    if not plan_text:
        return False
    retrieval = extract_top_level_block(plan_text, "retrieval_evidence")
    if not retrieval:
        return False
    scan_required = clean_scalar(field_value(retrieval, "scan_required"))
    if scan_required == "true":
        return True
    for key in [
        "confirmed_by_business_map",
        "confirmed_by_user_input",
        "historical_reference_only",
        "requires_dev_fallback",
        "assumptions",
        "blockers",
        "findings",
    ]:
        block = extract_yamlish_block(retrieval, key)
        if "- " in block or re.search(rf"{key}\s*:\s*\[[^\]\s].*?\]", retrieval):
            return True
    return any(
        re.search(rf"^\s*status\s*:\s*{status}\s*$", retrieval, flags=re.M)
        for status in ["checked", "not_found", "unavailable", "registered"]
    )


def prd_consumes_storage_context(text: str) -> bool:
    return re.search(
        r"存量|历史\s*PRD|历史方案|业务地图|当前产品上下文|当前存量依据|"
        r"已确认产品规则|研发兜底|未命中|冲突|复用|现有|已有|一期",
        text,
    ) is not None


def line_section(text: str, line_index: int) -> str | None:
    current = None
    for idx, line in enumerate(text.splitlines()):
        if line.startswith("## "):
            current = line.rstrip()
        if idx == line_index:
            return current
    return current


def extract_required_artifact_types(plan_text: str | None) -> set[str]:
    if not plan_text:
        return set()
    block = extract_top_level_block(plan_text, "required_artifacts")
    if not block:
        return set()
    artifacts: set[str] = set()

    for line in block.splitlines():
        normalized = line.strip()
        if not normalized:
            continue
        lower = normalized.lower()
        if "n/a" in lower or "不适用" in normalized:
            continue
        if "flowchart" in lower or "流程图" in normalized:
            artifacts.add("flowchart")
        if "main_flowchart" in lower or "主流程图" in normalized:
            artifacts.add("main_flowchart")
        if "state_machine" in lower or "state machine" in lower or "状态机" in normalized:
                artifacts.add("state_machine")
    return artifacts


def lint_retrieval_plan(text: str) -> list[Finding]:
    findings: list[Finding] = []
    retrieval = extract_top_level_block(text, "retrieval_evidence")
    if not retrieval:
        findings.append(
            Finding(
                "R0",
                "Major",
                "完整 PRD 的结构计划应包含 retrieval_evidence，用于记录存量查询是否触发及证据来源。",
                True,
            )
        )
        return findings

    scan_required = clean_bool(field_value(retrieval, "scan_required"))
    scan_level = clean_scalar(field_value(retrieval, "scan_level"))
    deep_query_required = clean_bool(field_value(retrieval, "deep_query_required"))
    triggered = clean_bool(field_value(retrieval, "triggered"))
    if scan_required not in {"true", "false"} and triggered in {"true", "false"}:
        scan_required = triggered
    if triggered not in {"true", "false"} and scan_required in {"true", "false"}:
        triggered = scan_required

    if scan_required not in {"true", "false"}:
        findings.append(
            Finding(
                "R1",
                "Major",
                "retrieval_evidence.scan_required 必须为 true / false；旧结构可用 triggered 兼容，但新结构应写 scan_required。",
                True,
            )
        )
        return findings

    if scan_level and scan_level not in RETRIEVAL_SCAN_LEVELS:
        findings.append(
            Finding(
                "R2",
                "Major",
                "retrieval_evidence.scan_level 必须为 none / light / deep。",
                True,
            )
        )

    if scan_required == "false":
        if not extract_yamlish_block(retrieval, "scan_reason") and not extract_yamlish_block(retrieval, "trigger_reason"):
            findings.append(
                Finding(
                    "R3",
                    "Review note",
                    "retrieval_evidence.scan_required=false 时，建议说明为什么本需求不需要存量轻扫。",
                    True,
                )
            )
        return findings

    if scan_level in {"", "none"}:
        findings.append(
            Finding(
                "R4",
                "Major",
                "正式 PRD 需要存量轻扫时，scan_level 不应为空或 none；应写 light 或 deep。",
                True,
            )
        )

    business_status = clean_scalar(
        field_value(extract_yamlish_block(retrieval, "business_map"), "status")
    )
    business_block = extract_yamlish_block(retrieval, "business_map")
    business_source_scope = clean_scalar(field_value(business_block, "source_scope"))
    business_source_root_uri = clean_scalar(field_value(business_block, "source_root_uri"))
    business_query_scope = clean_scalar(field_value(business_block, "query_scope"))
    business_source_uri = clean_scalar(field_value(business_block, "source_uri"))
    history_block = extract_yamlish_block(retrieval, "historical_prd")
    history_status = clean_scalar(field_value(history_block, "status"))
    history_source_scope = clean_scalar(field_value(history_block, "source_scope"))
    history_source_root_uri = clean_scalar(field_value(history_block, "source_root_uri"))
    history_query_scope = clean_scalar(field_value(history_block, "query_scope"))
    history_source_uri = clean_scalar(field_value(history_block, "source_uri"))
    dev_block = extract_yamlish_block(retrieval, "dev_fallback")
    dev_status = clean_scalar(field_value(dev_block, "status"))
    judgement_block = extract_yamlish_block(retrieval, "dependency_judgement")
    dependency_impact = clean_scalar(field_value(judgement_block, "dependency_impact"))
    dependency_handling = clean_scalar(field_value(judgement_block, "handling"))

    if business_status not in RETRIEVAL_SOURCE_STATUSES:
        findings.append(
            Finding(
                "R5",
                "Major",
                "retrieval_evidence.business_map.status 必须为 checked / not_checked / not_found / unavailable / N/A。",
                True,
            )
        )
    if history_status not in RETRIEVAL_SOURCE_STATUSES:
        findings.append(
            Finding(
                "R6",
                "Major",
                "retrieval_evidence.historical_prd.status 必须为 checked / not_checked / not_found / unavailable / N/A。",
                True,
            )
        )
    if business_query_scope and business_query_scope not in RETRIEVAL_QUERY_SCOPES:
        findings.append(
            Finding(
                "R7",
                "Major",
                "business_map.query_scope 必须为 specified_root / specified_subtree / global_search / local_file / user_provided / unavailable / N/A。",
                True,
            )
        )
    if history_query_scope and history_query_scope not in RETRIEVAL_QUERY_SCOPES:
        findings.append(
            Finding(
                "R8",
                "Major",
                "historical_prd.query_scope 必须为 specified_root / specified_subtree / global_search / local_file / user_provided / unavailable / N/A。",
                True,
            )
        )
    if (
        business_status in RETRIEVAL_NO_EVIDENCE_STATUSES
        and history_status in RETRIEVAL_NO_EVIDENCE_STATUSES
    ):
        fact_block = extract_yamlish_block(retrieval, "fact_classification")
        user_confirmed_block = extract_yamlish_block(fact_block, "confirmed_by_user_input")
        has_user_confirmed_context = "- " in user_confirmed_block or re.search(
            r"confirmed_by_user_input\s*:\s*\[[^\]\s].*?\]", fact_block
        )
        if dependency_impact == "high":
            findings.append(
                Finding(
                    "R9",
                    "Major",
                    "存量轻扫未命中且 dependency_impact=high 时，不能直接推进；应请求用户确认、登记研发兜底或写入第 5 章 R-x。",
                    True,
                )
            )
        elif not has_user_confirmed_context:
            findings.append(
                Finding(
                    "R9",
                    "Review note",
                    "业务地图和历史 PRD 均未命中时，请确认当前结论是否有用户输入支撑；未命中不等于无存量，也不必自动阻塞。",
                    True,
                )
            )
    if business_status in {"not_checked", "N/A"}:
        findings.append(
            Finding(
                "R10",
                "Major",
                "scan_required=true 时，业务地图不得保持 not_checked 或 N/A；查不到写 not_found，无法访问写 unavailable。",
                True,
            )
        )
    if business_status == "checked" and (not business_source_scope or not business_source_uri):
        findings.append(
            Finding(
                "R11",
                "Major",
                "business_map.status=checked 时，必须填写 source_scope 和 source_uri，说明来自默认业务地图还是用户指定业务地图。",
                True,
            )
        )
    if business_status == "checked" and business_query_scope not in RETRIEVAL_VALID_LIBRARY_QUERY_SCOPES:
        findings.append(
            Finding(
                "R12",
                "Major",
                "business_map.status=checked 只能代表指定业务地图库已查询；query_scope 必须为 specified_root 或 specified_subtree，全局搜索不能算 checked。",
                True,
            )
        )
    if business_status in {"checked", "not_found", "unavailable"} and not business_source_root_uri:
        findings.append(
            Finding(
                "R13",
                "Major",
                "business_map.status 为 checked / not_found / unavailable 时，必须填写 source_root_uri，证明查询目标是指定业务地图库。",
                True,
            )
        )
    if business_status == "unavailable" and business_query_scope != "unavailable":
        findings.append(
            Finding(
                "R14",
                "Major",
                "business_map.status=unavailable 时，query_scope 必须写 unavailable，并说明指定业务地图库不可访问；不能用 unavailable 代替未查询。",
                True,
            )
        )
    if history_status == "checked":
        if not history_source_scope or not history_source_uri:
            findings.append(
                Finding(
                    "R15",
                    "Major",
                    "historical_prd.status=checked 时，必须填写 source_scope 和 source_uri，说明来自默认历史 PRD 库还是用户指定历史 PRD 库。",
                    True,
                )
            )
        elif history_source_scope not in HISTORICAL_PRD_VALID_SOURCE_SCOPES:
            severity = "Major" if history_source_scope in HISTORICAL_PRD_INVALID_SOURCE_SCOPES else "Review note"
            findings.append(
                Finding(
                    "R16",
                    severity,
                    "historical_prd.status=checked 只能代表默认 / 用户指定历史 PRD 库已查询；local_file 或 test_export 只能作为本地参考，不能算历史 PRD 库查询。",
                    True,
                )
            )
        if history_query_scope not in RETRIEVAL_VALID_LIBRARY_QUERY_SCOPES:
            findings.append(
                Finding(
                    "R17",
                    "Major",
                    "historical_prd.status=checked 只能代表指定历史 PRD 库已查询；query_scope 必须为 specified_root 或 specified_subtree，全局搜索不能算 checked。",
                    True,
                )
            )
        if not history_source_root_uri:
            findings.append(
                Finding(
                    "R18",
                    "Major",
                    "historical_prd.status=checked 时，必须填写 source_root_uri，证明查询目标是指定历史 PRD 库。",
                    True,
                )
            )
    if history_status in {"not_found", "unavailable"} and not history_source_root_uri:
        findings.append(
            Finding(
                "R19",
                "Major",
                "historical_prd.status 为 not_found / unavailable 时，必须填写 source_root_uri，说明是在指定历史 PRD 库内查不到或不可用。",
                True,
            )
        )
    if history_status == "unavailable" and history_query_scope != "unavailable":
        findings.append(
            Finding(
                "R20",
                "Major",
                "historical_prd.status=unavailable 时，query_scope 必须写 unavailable，并说明指定历史 PRD 库不可访问；不能用 unavailable 代替未查询。",
                True,
            )
        )
    if plan_has_dev_fallback(text) and dev_status in {"", "N/A", "not_required"}:
        findings.append(
            Finding(
                "R21",
                "Major",
                "fact_classification.requires_dev_fallback 非空时，dev_fallback.status 不得为 N/A / not_required；应登记 registered、checked 或 unavailable。",
                True,
            )
        )
    if dependency_impact == "high" and dependency_handling not in RETRIEVAL_HIGH_IMPACT_HANDLINGS:
        findings.append(
            Finding(
                "R22",
                "Major",
                "dependency_impact=high 时，handling 不应是直接增量推进；应追问、登记研发兜底或标阻塞。",
                True,
            )
        )
    if dependency_impact == "high" and scan_level == "light" and deep_query_required != "true":
        findings.append(
            Finding(
                "R23",
                "Major",
                "dependency_impact=high 时，不能只停留在 light scan 且 deep_query_required=false；应深查、请求用户确认、登记研发兜底或说明阻塞。",
                True,
            )
        )
    fact_block = extract_yamlish_block(retrieval, "fact_classification")
    if fact_block and "confirmed_by_user_input" not in fact_block:
        findings.append(
            Finding(
                "R24",
                "Review note",
                "fact_classification 建议使用 confirmed_by_user_input 记录用户确认的需求前提，避免自造字段导致后续归位不一致。",
                True,
            )
        )

    if plan_has_dev_fallback(text):
        findings.append(
            Finding(
                "R-REVIEW",
                "Review note",
                "结构计划存在研发兜底项；请确认 PRD 第 6 节没有把依赖兜底的研发 / 数据工作直接标为“是”。",
                False,
            )
        )
    return findings


def lint(
    text: str,
    contracts: Contracts | None = None,
    required_artifact_types: set[str] | None = None,
    plan_text: str | None = None,
) -> list[Finding]:
    contracts = contracts or load_contracts()
    findings: list[Finding] = []

    headings = h2_headings(text)
    if headings != contracts.required_sections:
        findings.append(
            Finding(
                "L1",
                "Blocker",
                "一级章节必须有且仅有固定 6 节，并保持顺序与标题完全一致。",
                True,
            )
        )

    section_1 = section_between(text, contracts.required_sections[0], contracts.required_sections[1])
    status = extract_status(section_1, contracts.document_statuses)
    if not status:
        findings.append(Finding("L2", "Blocker", "第 1 节缺少合法文档状态。", True))
    elif status not in contracts.document_statuses:
        findings.append(Finding("L3", "Blocker", "文档状态不属于 4 类枚举。", True))

    risk_section = section_between(text, contracts.required_sections[4], contracts.required_sections[5])
    goal_section = section_between(text, contracts.required_sections[1], contracts.required_sections[2])
    metric_terms = ["核心结果指标", "主要过程指标", "动作指标", "护栏指标"]
    missing_metric_terms = [term for term in metric_terms if term not in goal_section]
    if missing_metric_terms and "N/A" not in goal_section:
        findings.append(
            Finding(
                "L24",
                "Major",
                "第 2 章目标指标应按“核心结果指标 / 主要过程指标 / 动作指标 / 护栏指标”组织；不适用时说明 N/A 原因。",
                True,
            )
        )
    product_body = "\n".join(
        [
            section_between(text, contracts.required_sections[0], contracts.required_sections[1]),
            section_between(text, contracts.required_sections[1], contracts.required_sections[2]),
            section_between(text, contracts.required_sections[2], contracts.required_sections[3]),
            section_between(text, contracts.required_sections[3], contracts.required_sections[4]),
        ]
    )
    forbidden_state = re.search(r"\[假设\]|\[阻塞\]|\b6-R[0-9]+\b|策略拍板审计摘要|retrieval_evidence|signoff|linter|contract", product_body, re.I)
    if forbidden_state:
        findings.append(
            Finding(
                "L4",
                "Blocker",
                "PRD 第 1-4 章不得出现 [假设] / [阻塞] / 6-Rx / 策略拍板审计摘要等内部状态；影响产品策略的未确认项应集中到第 5 章。",
                True,
            )
        )

    if re.search(r"\[假设\]|\[阻塞\]|\b6-R[0-9]+\b", text):
        findings.append(
            Finding(
                "L5",
                "Major",
                "用户可见 PRD 不应使用 [假设] / [阻塞] / 6-Rx；请改为第 5 章 R-x 风险或待确认项，内部结构计划可保留兼容字段。",
                True,
            )
        )

    for bad in [r"\[阻塞-[0-9]+\]", r"\[R[0-9]+\]", r"\[阻塞项[0-9]+\]"]:
        if re.search(bad, text):
            findings.append(Finding("L6", "Blocker", "开放事项编号存在禁用格式，用户可见 PRD 使用 R-x。", True))
            break

    if re.search(r"产品待确认|产品风险|发布风险|下游反向风险|待确认", risk_section) and not re.search(r"\bR-[0-9]+\b|N/A|无", risk_section):
        findings.append(
            Finding(
                "L7",
                "Major",
                "第 5 章存在风险或待确认内容时，应使用 R-x 编号集中维护。",
                True,
            )
        )

    cco_section = section_between(text, contracts.required_sections[3], contracts.required_sections[4])
    technical_pollution = re.search(r"\bVO\b|\bModel\b|schema|数据库字段|接口字段|字段名|入参|出参|返回结构|异常码", product_body, re.I)
    if technical_pollution:
        findings.append(
            Finding(
                "L8",
                "Warning",
                "PRD 第 1-4 章出现具体技术字段或接口实现表达；产品正文应写业务数据需求，具体字段 / 接口定义放第 6 章下游关注。",
                True,
            )
        )

    if "### 核心改动对象" not in cco_section:
        findings.append(Finding("L9", "Blocker", "第 4 节必须包含核心改动对象。", True))
    else:
        cco_blocks = split_cco_blocks(cco_section)
        for index, block in enumerate(cco_blocks, start=1):
            missing = [field for field in contracts.required_cco_fields if field not in block]
            forbidden = [
                field
                for field in ["Context", "Change", "Outcome", "处理规则", "记录要求"]
                if field in block
            ]
            if cco_uses_fixed_field_content_table(block, contracts.required_cco_fields):
                findings.append(
                    Finding(
                        "L26",
                        "Review note",
                        f"核心改动对象 {index} 不应把全部固定字段压缩成“固定字段 / 内容”两列表；固定字段应作为对象内部章节锚点展开，避免 PRD 变成字段清单。",
                        False,
                    )
                )
            if missing or forbidden:
                parts = []
                if missing:
                    parts.append("缺少字段：" + "、".join(missing))
                if forbidden:
                    parts.append("存在禁用替代字段：" + "、".join(forbidden))
                findings.append(
                    Finding(
                        "L10",
                        "Blocker",
                        f"核心改动对象 {index} 未使用固定字段模板；" + "；".join(parts),
                        True,
                    )
                )

    if headings and headings[-1] != contracts.required_sections[5]:
        findings.append(Finding("L11", "Blocker", "第 6 节必须是最后一个一级章节。", True))

    downstream_section = section_between(text, contracts.required_sections[5], None)
    rows = markdown_table_rows(downstream_section)
    header = rows[0] if rows else []
    if header[:5] != contracts.downstream_columns:
        findings.append(Finding("L12", "Blocker", "下游关注必须使用固定列：协作方 / 关注内容 / 为什么需要关注 / 是否可能影响产品策略 / 建议处理阶段。", True))
    elif len(rows) > 1:
        role_index = header.index("协作方") if "协作方" in header else 0
        attention_index = header.index("关注内容")
        reason_index = header.index("为什么需要关注")
        impact_index = header.index("是否可能影响产品策略")
        phase_index = header.index("建议处理阶段")
        for row in rows[1:]:
            if len(row) <= impact_index:
                continue
            role = row[role_index].strip() if len(row) > role_index else ""
            attention = row[attention_index].strip() if len(row) > attention_index else ""
            reason = row[reason_index].strip() if len(row) > reason_index else ""
            value = row[impact_index].strip()
            phase = row[phase_index].strip() if len(row) > phase_index else ""
            if not role or not attention or not reason or not phase:
                findings.append(
                    Finding(
                        "L13",
                        "Major",
                        "下游关注表每行都应说明协作方、关注内容、关注原因和建议处理阶段。",
                        True,
                    )
                )
                break
            if value not in contracts.downstream_values:
                findings.append(
                    Finding(
                        "L14",
                        "Major",
                        "下游关注“是否可能影响产品策略”只能是：是 / 否 / N/A。",
                        True,
                    )
                )
                break
            if value == "是" and not re.search(r"\bR-[0-9]+\b", risk_section):
                findings.append(
                    Finding(
                        "L15",
                        "Major",
                        "下游关注中存在“可能影响产品策略=是”的事项时，第 5 章必须有对应 R-x 风险或待确认项。",
                        True,
                    )
                )
                break

    required_artifact_types = required_artifact_types or set()
    needs_flow_artifact = bool(
        required_artifact_types.intersection({"flowchart", "main_flowchart", "state_machine"})
    )
    if needs_flow_artifact:
        if "stateDiagram" not in text and "flowchart" not in text:
            findings.append(
                Finding(
                    "L14",
                    "Major",
                    "结构计划 required_artifacts 声明需要流程图 / 主流程图 / 状态机时，PRD 必须包含 Mermaid flowchart 或 stateDiagram。",
                    False,
                )
            )

    storage_context_sections = "\n".join(
        [
            section_between(text, contracts.required_sections[2], contracts.required_sections[3]),
            cco_section,
            risk_section,
        ]
    )
    if "已确认的存量逻辑" in storage_context_sections and not retrieval_has_confirmed_current_fact(plan_text):
        findings.append(
            Finding(
                "L24",
                "Major",
                "PRD 正文写“已确认的存量逻辑”时，结构计划必须提供业务地图、研发验证或用户明确确认当前有效的证据；仅用户输入或历史 PRD 不足以证明。",
                True,
            )
        )
    if retrieval_plan_has_storage_context(plan_text) and not prd_consumes_storage_context(
        storage_context_sections
    ):
        findings.append(
            Finding(
                "L25",
                "Review note",
                "结构计划存在 retrieval_evidence，但 PRD 第 3/4/5 节未明显消费存量依据、历史参考、未命中、冲突或研发兜底结论。",
                False,
            )
        )

    section_3 = section_between(text, contracts.required_sections[2], contracts.required_sections[3])
    if "是否已确认" in section_3:
        findings.append(
            Finding(
                "L28",
                "Major",
                "第 3 节关键决策表不要使用“是否已确认”列；请改为“处理状态”，用“已拍板 / 本期暂按，待确认见 R-x / N/A”区分策略拍板、事实确认和待确认范围。",
                True,
            )
        )
    if "方案取舍" in section_3:
        option_table_rows = [
            row
            for row in markdown_table_rows(section_3)
            if row and any("方案" in cell for cell in row)
        ]
        if len(option_table_rows) >= 4:
            findings.append(
                Finding(
                    "L27",
                    "Review note",
                    "第 3 节不默认展示完整方案取舍表；正式 PRD 应优先保留最终方案、关键决策、必要理由和范围边界。",
                    False,
                )
            )

    for pattern in CHATTER_PATTERNS:
        if re.search(pattern, text):
            findings.append(
                Finding(
                    "L15",
                    "Major",
                    "PRD 正文包含面向用户的闲聊、称赞或过程播报，应移除。",
                    True,
                )
            )
            break

    return findings


def extract_top_level_block(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}\s*:\s*$", text, flags=re.M)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^\w[\w_-]*\s*:", text[start:], flags=re.M)
    end = start + next_match.start() if next_match else len(text)
    return text[start:end]


def extract_yamlish_block(text: str, key: str) -> str:
    match = re.search(rf"^(?P<indent>\s*){re.escape(key)}\s*:\s*(?:.*)$", text, flags=re.M)
    if not match:
        return ""
    indent = len(match.group("indent"))
    search_start = match.end()
    tail = text[search_start:]
    next_match = re.search(rf"^\s{{0,{indent}}}[\w_-]+\s*:", tail, flags=re.M)
    end = search_start + next_match.start() if next_match else len(text)
    return text[match.start():end]


def split_plan_cco_blocks(text: str) -> list[str]:
    start = text.find("core_change_objects:")
    if start == -1:
        return []
    tail = text[start:]
    next_top = re.search(r"^\w[^:\n]*:", tail[len("core_change_objects:") :], flags=re.M)
    content = tail if not next_top else tail[: len("core_change_objects:") + next_top.start()]
    matches = list(re.finditer(r"^\s*-\s+id\s*:", content, flags=re.M))
    blocks: list[str] = []
    for idx, match in enumerate(matches):
        block_start = match.start()
        block_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(content)
        blocks.append(content[block_start:block_end])
    return blocks


def field_value(block: str, key: str) -> str | None:
    match = re.search(rf"^\s*(?:-\s+)?{re.escape(key)}\s*:\s*(.+?)\s*$", block, flags=re.M)
    return match.group(1).strip() if match else None


def plan_cco_name(block: str) -> str:
    return clean_scalar(field_value(block, "name"))


def clean_scalar(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().strip("'\"")


def clean_bool(value: str | None) -> str:
    return clean_scalar(value).lower()


def block_has_any(block: str, keys: list[str]) -> bool:
    return any(
        re.search(rf"^\s*(?:-\s+)?{re.escape(key)}\s*:", block, flags=re.M)
        for key in keys
    )


def split_list_item_blocks(block: str, item_key: str | None = None) -> list[str]:
    if item_key:
        pattern = rf"^\s*-\s+{re.escape(item_key)}\s*:"
    else:
        pattern = r"^\s*-\s+[\w_-]+\s*:"
    matches = list(re.finditer(pattern, block, flags=re.M))
    items: list[str] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(block)
        items.append(block[start:end])
    return items


def lint_strategy_plan(text: str, contracts: Contracts) -> list[Finding]:
    findings: list[Finding] = []
    assessment = extract_top_level_block(text, "strategy_assessment")
    plan = extract_top_level_block(text, "strategy_plan")

    if not assessment:
        findings.append(
            Finding(
                "S1",
                "Blocker",
                "完整 PRD 的结构计划必须包含 strategy_assessment；--light 轻量输出不强制。",
                True,
            )
        )
        return findings

    triggered_value = clean_scalar(field_value(assessment, "triggered")).lower()
    if triggered_value not in {"true", "false"}:
        findings.append(
            Finding("S2", "Blocker", "strategy_assessment.triggered 必须为 true / false。", True)
        )
        return findings

    level = clean_scalar(field_value(assessment, "strategy_level"))
    if triggered_value == "false":
        if not field_value(assessment, "reason"):
            findings.append(
                Finding(
                    "S3",
                    "Major",
                    "strategy_assessment.triggered=false 时应说明不触发策略增强的原因。",
                    True,
                )
            )
        if plan:
            findings.append(
                Finding(
                    "S4",
                    "Major",
                    "strategy_assessment.triggered=false 时不应生成完整 strategy_plan。",
                    True,
                )
            )
        return findings

    if level not in contracts.strategy_levels:
        findings.append(
            Finding(
                "S5",
                "Blocker",
                "strategy_assessment.strategy_level 只能是 lightweight / standard / complex。",
                True,
            )
        )

    reasons = extract_yamlish_block(assessment, "trigger_reasons") or assessment
    explicit_block = extract_yamlish_block(reasons, "explicit_type")
    decision_block = extract_yamlish_block(reasons, "decision_nature")
    downstream_block = extract_yamlish_block(reasons, "downstream_impact")
    explicit_matched = re.search(r"^\s*matched\s*:\s*true\s*$", explicit_block, flags=re.M) is not None
    decision_matched = re.search(r"^\s*matched\s*:\s*true\s*$", decision_block, flags=re.M) is not None
    downstream_matched = re.search(r"^\s*matched\s*:\s*true\s*$", downstream_block, flags=re.M) is not None
    if not explicit_matched and not decision_matched:
        findings.append(
            Finding(
                "S6",
                "Blocker",
                "策略增强不能只由 downstream_impact 触发；必须命中显性类型或决策性质。",
                True,
            )
        )
    elif downstream_matched and not (explicit_matched or decision_matched):
        findings.append(
            Finding(
                "S7",
                "Blocker",
                "downstream_impact 不能单独触发完整 strategy_plan。",
                True,
            )
        )

    if level == "lightweight":
        if "lightweight_reason" not in assessment:
            findings.append(
                Finding(
                    "S8",
                    "Blocker",
                    "strategy_level=lightweight 时必须说明 lightweight_reason。",
                    True,
                )
            )
        if plan:
            findings.append(
                Finding(
                    "S9",
                    "Major",
                    "lightweight 策略不应强制完整 strategy_plan，除非已升级为 standard / complex。",
                    True,
                )
            )
        if re.search(r"weight|threshold|resource_mapping|conflict_handling|权重|阈值|资源分配|冲突", assessment):
            findings.append(
                Finding(
                    "S10",
                    "Major",
                    "lightweight 中出现权重、阈值、资源分配或冲突信号，可能误降级。",
                    False,
                )
            )
        return findings

    if level in {"standard", "complex"} and not plan:
        findings.append(
            Finding("S11", "Blocker", "standard / complex 策略必须包含完整 strategy_plan。", True)
        )
        return findings

    confirmation_required = False

    if plan:
        for key in [
            "level",
            "strategy_type",
            "related_cco",
            "strategy_goal",
            "target_users",
            "target_objects",
            "input_signals",
            "fallback_rules",
            "example_users",
            "confirmation_required",
        ]:
            if not re.search(rf"^\s*{re.escape(key)}\s*:", plan, flags=re.M):
                findings.append(
                    Finding("S12", "Blocker", f"strategy_plan 缺少必填字段：{key}。", True)
                )
                break

        input_block = extract_yamlish_block(plan, "input_signals")
        if input_block:
            items = split_list_item_blocks(input_block, "name")
            if not items:
                findings.append(Finding("S13", "Blocker", "input_signals 必须至少包含一个信号项。", True))
            for item in items:
                missing = [field for field in contracts.input_signal_fields if not block_has_any(item, [field])]
                if missing:
                    findings.append(
                        Finding(
                            "S14",
                            "Blocker",
                            "每个 input_signal 必须包含：" + "、".join(contracts.input_signal_fields) + "。",
                            True,
                        )
                    )
                    break
                status = clean_scalar(field_value(item, "status"))
                if status not in contracts.input_signal_statuses:
                    findings.append(
                        Finding(
                            "S15",
                            "Blocker",
                            "input_signal.status 只能是 confirmed / assumption / blocker / N/A。",
                            True,
                        )
                    )
                    break

        mapping_block = extract_yamlish_block(plan, "resource_mapping")
        if mapping_block:
            table_block = extract_yamlish_block(mapping_block, "mapping_table") or mapping_block
            rows = split_list_item_blocks(table_block, "strategy_result")
            if not rows:
                findings.append(
                    Finding("S16", "Major", "resource_mapping.mapping_table 应至少包含一行映射。", True)
                )
            for row in rows:
                missing = [field for field in contracts.resource_mapping_fields if not block_has_any(row, [field])]
                if missing:
                    findings.append(
                        Finding(
                            "S17",
                            "Blocker",
                            "resource_mapping.mapping_table 每行必须包含："
                            + "、".join(contracts.resource_mapping_fields)
                            + "。",
                            True,
                        )
                    )
                    break
                display_priority = clean_scalar(field_value(row, "display_priority"))
                if display_priority in {"高优先级", "中优先级", "低优先级"}:
                    findings.append(
                        Finding(
                            "S18",
                            "Major",
                            "display_priority 不能只写高/中/低优先级，必须说明相对谁优先。",
                            False,
                        )
                    )
                    break

        if level == "complex":
            complex_signals = [
                hint for hint in contracts.complex_upgrade_hints if hint in assessment or hint in plan
            ]
            if not complex_signals:
                findings.append(
                    Finding(
                        "S19",
                        "Major",
                        "complex 策略应体现多资源 / 多信号 / 多目标 / 多冲突 / 核心业务目标 / 实验结论等升级原因。",
                        False,
                    )
                )
            if "solution_readiness_summary" not in assessment and "方案成立摘要" not in text:
                findings.append(
                    Finding(
                        "S20",
                        "Major",
                        "complex 策略应有方案成立摘要拍板记录；未拍板时进入 [阻塞]。",
                        False,
                    )
                )

        for pattern in WEAK_STRATEGY_PATTERNS:
            if re.search(pattern, plan):
                findings.append(
                    Finding(
                        "S21",
                        "Major",
                        "strategy_plan 存在概念级弱表达，应补充规则表、阈值、资源映射或确认项。",
                        False,
                    )
                )
                break

        confirmation_block = extract_yamlish_block(plan, "confirmation_required")
        confirmation_required = (
            re.search(r"^\s*required\s*:\s*true\s*$", confirmation_block, flags=re.M) is not None
            or "confirmation_required" in plan
        )

    if level == "complex" and confirmation_required:
        findings.extend(lint_strategy_signoff(text, contracts))

    findings.append(
        Finding(
            "S-REVIEW",
            "Review note",
            "请人工审查推荐权重、阈值、资源分配和策略目标是否业务合理；此项不作为机器 Blocker。",
            False,
        )
    )
    return findings


def lint_strategy_signoff(text: str, contracts: Contracts) -> list[Finding]:
    findings: list[Finding] = []
    signoff = extract_top_level_block(text, "strategy_signoff")
    if not signoff:
        findings.append(
            Finding(
                "SG1",
                "Blocker",
                "complex strategy 且 confirmation_required 非空时，必须存在 strategy_signoff。",
                True,
            )
        )
        return findings

    status = clean_scalar(field_value(signoff, "status"))
    user_choice = clean_scalar(field_value(signoff, "user_choice"))
    if status not in contracts.signoff_statuses:
        findings.append(
            Finding(
                "SG2",
                "Blocker",
                "strategy_signoff.status 必须为 pending / accepted / modified / skipped_with_blocker。",
                True,
            )
        )
    if user_choice not in contracts.signoff_choices:
        findings.append(
            Finding(
                "SG3",
                "Blocker",
                "strategy_signoff.user_choice 必须为 A / B / C / unknown。",
                True,
            )
        )

    if status in {"accepted", "modified"} and not field_value(signoff, "user_choice_evidence"):
        findings.append(
            Finding(
                "SG4",
                "Major",
                "strategy_signoff.status=accepted/modified 时，必须记录 user_choice_evidence。",
                True,
            )
        )
    if status == "accepted" and user_choice == "unknown":
        findings.append(
            Finding(
                "SG5",
                "Blocker",
                "strategy_signoff.user_choice=unknown 时，不得标记为 accepted。",
                True,
            )
        )

    items_block = extract_yamlish_block(signoff, "signoff_items")
    item_blocks = split_list_item_blocks(items_block, "id")
    if not item_blocks:
        findings.append(Finding("SG6", "Blocker", "strategy_signoff 必须包含逐项 signoff_items。", True))
        return findings

    for item in item_blocks:
        missing = [field for field in contracts.signoff_item_fields if not block_has_any(item, [field])]
        if missing:
            findings.append(
                Finding(
                    "SG7",
                    "Blocker",
                    "每个 signoff_item 必须包含：" + "、".join(contracts.signoff_item_fields) + "。",
                    True,
                )
            )
            break
        item_status = clean_scalar(field_value(item, "status"))
        item_choice = clean_scalar(field_value(item, "user_choice"))
        if item_status not in contracts.signoff_statuses:
            findings.append(
                Finding(
                    "SG8",
                    "Blocker",
                    "signoff_item.status 必须为 pending / accepted / modified / skipped_with_blocker。",
                    True,
                )
            )
            break
        if item_choice not in contracts.signoff_choices:
            findings.append(
                Finding("SG9", "Blocker", "signoff_item.user_choice 必须为 A / B / C / unknown。", True)
            )
            break
        blocker_ref = clean_scalar(field_value(item, "blocker_ref"))
        default_handling = clean_scalar(field_value(item, "default_handling"))
        if item_status == "skipped_with_blocker":
            if not re.search(r"\b6-R[0-9]+\b", blocker_ref + " " + default_handling):
                findings.append(
                    Finding(
                        "SG10",
                        "Blocker",
                        "signoff_item.status=skipped_with_blocker 时，必须引用 6-R 阻塞项。",
                        True,
                    )
                )
                break

    if status == "skipped_with_blocker" and not re.search(r"\b6-R[0-9]+\b", signoff):
        findings.append(
            Finding(
                "SG11",
                "Blocker",
                "strategy_signoff.status=skipped_with_blocker 时，必须引用 6-R 阻塞项。",
                True,
            )
        )

    has_remaining_blockers = bool(extract_top_level_block(text, "blockers")) or bool(
        re.search(r"\[阻塞\s*6-R[0-9]+\]", text)
    )
    if status == "accepted" and (
        has_remaining_blockers
        or re.search(r"data|数据|resource|资源位|compliance|合规|指标|口径", signoff)
    ):
        findings.append(
            Finding(
                "SG12",
                "Review note",
                "accepted 只代表策略拍板完成，不自动解除数据源、资源位、指标口径、合规或研发可行性阻塞。",
                False,
            )
        )

    if "signoff_audit" not in text and "signoff_record" not in text:
        findings.append(
            Finding(
                "SG13",
                "Major",
                "complex strategy 应在结构计划保留 signoff_record 或 signoff_audit；不要把策略拍板审计摘要写入 PRD 正文。",
                False,
            )
        )

    findings.extend(lint_signoff_record(text, contracts, status))

    findings.append(
        Finding(
            "SG-REVIEW",
            "Review note",
            "请人工审查 user_choice_evidence 是否真实代表用户选择，避免把模糊确认误判为拍板。",
            False,
        )
    )
    return findings


def lint_signoff_record(text: str, contracts: Contracts, signoff_status: str) -> list[Finding]:
    findings: list[Finding] = []
    record = extract_top_level_block(text, "signoff_record")
    if not record:
        findings.append(
            Finding(
                "SG14",
                "Blocker",
                "complex strategy 必须在 structure_plan 中保留 signoff_record，用于证明生成前拍板交互。",
                True,
            )
        )
        return findings

    missing = [field for field in contracts.signoff_record_fields if not block_has_any(record, [field])]
    if missing:
        findings.append(
            Finding(
                "SG15",
                "Blocker",
                "signoff_record 必须包含：" + "、".join(contracts.signoff_record_fields) + "。",
                True,
            )
        )
        return findings

    prompt_type = clean_scalar(field_value(record, "agent_prompt_type"))
    interpreted_choice = clean_scalar(field_value(record, "interpreted_choice"))
    interpreted_action = clean_scalar(field_value(record, "interpreted_action"))
    fuzzy_detected = clean_bool(field_value(record, "fuzzy_confirmation_detected"))
    followup_required = clean_bool(field_value(record, "followup_required"))
    raw_reply = clean_scalar(field_value(record, "user_raw_reply"))

    if prompt_type not in contracts.signoff_prompt_types:
        findings.append(
            Finding(
                "SG16",
                "Blocker",
                "signoff_record.agent_prompt_type 必须是 strategy_signoff_card / strategy_signoff_followup / modified_strategy_summary / prd_generation_after_signoff。",
                True,
            )
        )
    if interpreted_choice not in contracts.signoff_choices:
        findings.append(
            Finding(
                "SG17",
                "Blocker",
                "signoff_record.interpreted_choice 必须为 A / B / C / unknown。",
                True,
            )
        )
    if interpreted_action not in contracts.signoff_actions:
        findings.append(
            Finding(
                "SG21",
                "Blocker",
                "signoff_record.interpreted_action 必须为 accept_recommendation / modify_strategy / skip_signoff_with_blocker / unknown。",
                True,
            )
        )
    if fuzzy_detected not in {"true", "false"} or followup_required not in {"true", "false"}:
        findings.append(
            Finding(
                "SG18",
                "Blocker",
                "signoff_record.fuzzy_confirmation_detected 与 followup_required 必须为 true / false。",
                True,
            )
        )

    choice_action_map = {
        "A": "accept_recommendation",
        "B": "modify_strategy",
        "C": "skip_signoff_with_blocker",
        "unknown": "unknown",
    }
    if interpreted_choice in choice_action_map and interpreted_action:
        expected_action = choice_action_map[interpreted_choice]
        if interpreted_action != expected_action:
            findings.append(
                Finding(
                    "SG22",
                    "Blocker",
                    "signoff_record.interpreted_choice 与 interpreted_action 语义不一致。",
                    True,
                )
            )

    if signoff_status in {"accepted", "modified"} and interpreted_choice == "unknown":
        findings.append(
            Finding(
                "SG19",
                "Blocker",
                "signoff_record.interpreted_choice=unknown 时，不得将 strategy_signoff 标记为 accepted / modified。",
                True,
            )
        )

    fuzzy_reply = re.search(r"^(ok|OK|好|好的|继续|可以|生成吧|按这个来)$", raw_reply.strip()) is not None
    if fuzzy_reply and interpreted_choice == "unknown" and followup_required != "true":
        findings.append(
            Finding(
                "SG20",
                "Blocker",
                "用户原始回复为模糊确认且 interpreted_choice=unknown 时，followup_required 必须为 true。",
                True,
            )
        )
    if fuzzy_reply and interpreted_action != "unknown":
        findings.append(
            Finding(
                "SG23",
                "Blocker",
                "用户原始回复为模糊确认时，interpreted_action 必须为 unknown，不得推断为接受推荐、修改策略或暂不拍板。",
                True,
            )
        )
    return findings


def lint_prd_generation_guard(plan_text: str | None, document_text: str | None = None) -> list[Finding]:
    if not plan_text:
        return []
    findings: list[Finding] = lint_demand_establishment_plan(plan_text)
    document_status = None
    if document_text:
        contracts = load_contracts()
        section_1 = section_between(document_text, contracts.required_sections[0], contracts.required_sections[1])
        document_status = extract_status(section_1, contracts.document_statuses)

    demand = extract_top_level_block(plan_text, "demand_establishment")
    if document_status == "研发交付版":
        if not demand:
            findings.append(
                Finding(
                    "DE10",
                    "Major",
                    "研发交付版建议在结构计划记录 demand_establishment，证明背景、用户、目标、范围已完成需求成立检查点。",
                    True,
                )
            )
        else:
            demand_status = clean_scalar(field_value(demand, "status"))
            if demand_status in DEMAND_ESTABLISHMENT_DELIVERY_BLOCKING_STATUSES:
                findings.append(
                    Finding(
                        "DE11",
                        "Blocker",
                        "研发交付版不得建立在 assumed / blocked / confirmation_required / pending 的需求成立状态上；应先完成需求成立确认，或降级为 PRD 草案。",
                        True,
                    )
                )

    assessment = extract_top_level_block(plan_text, "strategy_assessment")
    plan = extract_top_level_block(plan_text, "strategy_plan")
    if not assessment or not plan:
        return findings

    triggered_value = clean_bool(field_value(assessment, "triggered"))
    level = clean_scalar(field_value(assessment, "strategy_level"))
    confirmation_block = extract_yamlish_block(plan, "confirmation_required")
    confirmation_required = (
        re.search(r"^\s*required\s*:\s*true\s*$", confirmation_block, flags=re.M) is not None
        or "confirmation_required" in plan
    )
    if triggered_value != "true" or level != "complex" or not confirmation_required:
        return findings

    signoff = extract_top_level_block(plan_text, "strategy_signoff")
    record = extract_top_level_block(plan_text, "signoff_record")
    status = clean_scalar(field_value(signoff, "status"))
    user_choice = clean_scalar(field_value(signoff, "user_choice"))
    followup_required = clean_bool(field_value(record, "followup_required"))

    if (
        status not in {"accepted", "modified", "skipped_with_blocker"}
        or user_choice not in {"A", "B", "C"}
        or followup_required == "true"
    ):
        findings.append(
            Finding(
                "G1",
                "Blocker",
                "Sign-off Guard：complex strategy 未完成 A/B/C 拍板时，不得生成完整 PRD；只能输出策略拍板卡或追问。",
                True,
            )
        )
    return findings


def plan_requires_behavior_delta(text: str) -> bool:
    assessment = extract_top_level_block(text, "strategy_assessment")
    retrieval = extract_top_level_block(text, "retrieval_evidence")
    if assessment:
        triggered = clean_bool(field_value(assessment, "triggered"))
        level = clean_scalar(field_value(assessment, "strategy_level"))
        if triggered == "true" and level == "complex":
            return True
    if retrieval:
        scan_required = clean_bool(field_value(retrieval, "scan_required"))
        scan_level = clean_scalar(field_value(retrieval, "scan_level"))
        if scan_required == "true" and scan_level in {"light", "deep"}:
            return True
    return False


def block_has_list_content(block: str, key: str) -> bool:
    sub_block = extract_yamlish_block(block, key)
    if "- " in sub_block:
        return True
    return re.search(rf"{re.escape(key)}\s*:\s*\[[^\]\s].*?\]", block) is not None


def lint_behavior_delta_plan(text: str) -> list[Finding]:
    findings: list[Finding] = []
    required = plan_requires_behavior_delta(text)
    delta = extract_top_level_block(text, "behavior_delta_check")
    if not required and not delta:
        return findings
    if required and not delta:
        return [
            Finding(
                "BD1",
                "Review note",
                "复杂策略或存量改造结构计划建议包含 behavior_delta_check，用于记录轻扫后 / 推荐前的行为 Delta 草稿与正文前闭合检查。",
                False,
            )
        ]

    missing = [field for field in BEHAVIOR_DELTA_REQUIRED_FIELDS if not block_has_any(delta, [field])]
    if missing:
        findings.append(
            Finding(
                "BD2",
                "Warning",
                "behavior_delta_check 建议包含：" + "、".join(BEHAVIOR_DELTA_REQUIRED_FIELDS) + "。",
                True,
            )
        )

    draft_block = extract_yamlish_block(delta, "draft_after_retrieval") or delta
    closure_block = extract_yamlish_block(delta, "closure_before_prd")
    missing_draft = [
        field for field in BEHAVIOR_DELTA_DRAFT_FIELDS if not block_has_any(draft_block, [field])
    ]
    if draft_block and missing_draft:
        findings.append(
            Finding(
                "BD10",
                "Warning",
                "behavior_delta_check.draft_after_retrieval 建议包含："
                + "、".join(BEHAVIOR_DELTA_DRAFT_FIELDS)
                + "。",
                True,
            )
        )
    if closure_block:
        missing_closure = [
            field
            for field in BEHAVIOR_DELTA_CLOSURE_FIELDS
            if not block_has_any(closure_block, [field])
        ]
        if missing_closure:
            findings.append(
                Finding(
                    "BD11",
                    "Warning",
                    "behavior_delta_check.closure_before_prd 建议包含："
                    + "、".join(BEHAVIOR_DELTA_CLOSURE_FIELDS)
                    + "。",
                    True,
                )
            )

    scenarios_block = extract_yamlish_block(draft_block, "scenarios")
    scenario_items = split_list_item_blocks(scenarios_block, "given")
    if block_has_list_content(draft_block, "scenarios") and not scenario_items:
        findings.append(
            Finding(
                "BD3",
                "Warning",
                "behavior_delta_check.draft_after_retrieval.scenarios 应以 given / when / then / status / handling 描述关键行为场景。",
                True,
            )
        )
    for scenario in scenario_items:
        missing_scenario_fields = [
            field for field in BEHAVIOR_DELTA_SCENARIO_FIELDS if not block_has_any(scenario, [field])
        ]
        if missing_scenario_fields:
            findings.append(
                Finding(
                    "BD4",
                    "Warning",
                    "每个 behavior_delta_check.scenario 建议包含："
                    + "、".join(BEHAVIOR_DELTA_SCENARIO_FIELDS)
                    + "。",
                    True,
                )
            )
            break
        status = clean_scalar(field_value(scenario, "status"))
        handling = clean_scalar(field_value(scenario, "handling"))
        if status and status not in BEHAVIOR_DELTA_STATUSES:
            findings.append(
                Finding(
                    "BD5",
                    "Warning",
                    "behavior_delta_check.scenario.status 建议使用 closed / assumption / blocker / needs_signoff / N/A。",
                    True,
                )
            )
            break
        if handling and handling not in BEHAVIOR_DELTA_HANDLINGS:
            findings.append(
                Finding(
                    "BD6",
                    "Warning",
                    "behavior_delta_check.scenario.handling 建议使用 include_in_signoff / write_as_assumption / write_as_blocker / no_action。",
                    True,
                )
            )
            break

    draft_unresolved = extract_yamlish_block(draft_block, "unresolved_scenarios")
    closure_unresolved = extract_yamlish_block(closure_block, "unresolved_scenarios")
    unresolved = closure_unresolved or draft_unresolved
    if block_has_list_content(draft_block, "unresolved_scenarios") and not closure_block:
        findings.append(
            Finding(
                "BD12",
                "Warning",
                "draft_after_retrieval 存在未闭合场景时，正文前应记录 closure_before_prd，说明这些场景已拍板、假设、阻塞或无需处理。",
                True,
            )
        )
    if block_has_list_content(closure_block or draft_block, "unresolved_scenarios"):
        if not any(handling in unresolved + "\n" + closure_block for handling in BEHAVIOR_DELTA_HANDLINGS):
            findings.append(
                Finding(
                    "BD7",
                    "Warning",
                    "unresolved_scenarios 存在时，应在 closure_before_prd 中说明处理去向：进入拍板、写为 [假设]、写为 [阻塞] 或不处理原因。",
                    True,
                )
            )
        signoff = extract_top_level_block(text, "strategy_signoff")
        has_risk_handling = any(marker in text for marker in ["assumptions:", "blockers:", "[假设]", "[阻塞]"])
        if "include_in_signoff" in unresolved and not signoff:
            findings.append(
                Finding(
                    "BD8",
                    "Warning",
                    "unresolved_scenarios 声明进入拍板时，结构计划应保留 strategy_signoff 或 signoff_record。",
                    True,
                )
            )
        if re.search(r"write_as_assumption|write_as_blocker", unresolved) and not has_risk_handling:
            findings.append(
                Finding(
                    "BD9",
                    "Warning",
                    "unresolved_scenarios 声明写为 [假设] / [阻塞] 时，结构计划应同步维护 assumptions 或 blockers。",
                    True,
                )
            )
    return findings


def lint_demand_establishment_plan(text: str) -> list[Finding]:
    findings: list[Finding] = []
    demand = extract_top_level_block(text, "demand_establishment")
    signoff = extract_top_level_block(text, "strategy_signoff")

    if not demand:
        severity = "Major" if signoff else "Review note"
        findings.append(
            Finding(
                "DE0",
                severity,
                "结构计划建议包含 demand_establishment，用于记录策略拍板前背景、用户、目标、范围是否已完成需求成立检查点。",
                True,
            )
        )
        return findings

    missing = [
        field
        for field in DEMAND_ESTABLISHMENT_FIELDS
        if not block_has_any(demand, [field])
    ]
    if missing:
        findings.append(
            Finding(
                "DE1",
                "Major",
                "demand_establishment 建议包含："
                + "、".join(DEMAND_ESTABLISHMENT_FIELDS)
                + "。",
                True,
            )
        )
        return findings

    status = clean_scalar(field_value(demand, "status"))
    mode = clean_scalar(field_value(demand, "confirmation_mode"))
    user_action = clean_scalar(field_value(demand, "user_action"))
    blocks_strategy_signoff = clean_bool(field_value(demand, "blocks_strategy_signoff"))
    summary = extract_yamlish_block(demand, "summary")

    if status not in DEMAND_ESTABLISHMENT_STATUSES:
        findings.append(
            Finding(
                "DE2",
                "Major",
                "demand_establishment.status 必须为 display_passed / confirmation_required / accepted / modified / assumed / blocked / pending。",
                True,
            )
        )
    if mode not in DEMAND_ESTABLISHMENT_MODES:
        findings.append(
            Finding(
                "DE3",
                "Major",
                "demand_establishment.confirmation_mode 必须为 display / confirm / N/A。",
                True,
            )
        )
    if user_action not in DEMAND_ESTABLISHMENT_ACTIONS:
        findings.append(
            Finding(
                "DE4",
                "Major",
                "demand_establishment.user_action 必须为 not_required / accepted / modified / proceed_with_assumption / pending。",
                True,
            )
        )
    if blocks_strategy_signoff not in {"true", "false"}:
        findings.append(
            Finding(
                "DE5",
                "Major",
                "demand_establishment.blocks_strategy_signoff 必须为 true / false。",
                True,
            )
        )
    if mode == "display" and status != "display_passed":
        findings.append(
            Finding(
                "DE12",
                "Major",
                "demand_establishment.confirmation_mode=display 时，status 必须为 display_passed；不得用后续策略拍板把需求成立倒写成 accepted / modified。",
                True,
            )
        )
    if mode == "display" and user_action != "not_required":
        findings.append(
            Finding(
                "DE13",
                "Major",
                "demand_establishment.confirmation_mode=display 时，user_action 必须为 not_required；展示型通过不代表用户已确认。",
                True,
            )
        )
    expected_action_by_status = {
        "accepted": "accepted",
        "modified": "modified",
        "assumed": "proceed_with_assumption",
    }
    expected_action = expected_action_by_status.get(status)
    if expected_action and user_action != expected_action:
        findings.append(
            Finding(
                "DE14",
                "Major",
                "demand_establishment.status 为 accepted / modified / assumed 时，user_action 必须分别对应 accepted / modified / proceed_with_assumption。",
                True,
            )
        )
    if status in expected_action_by_status and mode != "confirm":
        findings.append(
            Finding(
                "DE15",
                "Major",
                "demand_establishment.status 为 accepted / modified / assumed 时，confirmation_mode 必须为 confirm，表示来自用户对需求成立四件事的明确动作。",
                True,
            )
        )
    if mode == "display" and status == "display_passed":
        retrieval = extract_top_level_block(text, "retrieval_evidence")
        fact_classification = extract_yamlish_block(retrieval, "fact_classification")
        historical_references_present = block_has_list_content(
            fact_classification,
            "historical_reference_only",
        )
        inferred_fields_present = block_has_list_content(demand, "inferred_fields")
        scope_sensitive_summary = bool(
            summary
            and re.search(
                r"类目|具体机型|覆盖范围|适用范围|实验范围|适用页面|主搜|频道页|B2C|渠道",
                summary,
            )
        )
        if historical_references_present and not inferred_fields_present:
            findings.append(
                Finding(
                    "DE16",
                    "Major" if scope_sensitive_summary else "Review note",
                    "存在 historical_reference_only 时，若展示型需求成立摘要含类目、具体机型、覆盖范围、实验范围、适用页面等范围细节，必须写入 inferred_fields、待确认项或改为 confirmation_required。",
                    True,
                )
            )

    if summary:
        missing_summary = [
            field
            for field in ["background", "users", "goal", "scope"]
            if not block_has_any(summary, [field])
        ]
        if missing_summary:
            findings.append(
                Finding(
                    "DE6",
                    "Warning",
                    "demand_establishment.summary 建议包含 background / users / goal / scope。",
                    True,
                )
            )

    if signoff:
        if mode == "display" and status == "display_passed":
            findings.append(
                Finding(
                    "DE17",
                    "Major",
                    "完整 PRD 或复杂策略拍板前，需求成立不能只用 display_passed 无感通过；应先输出需求成立摘要，并将 demand_establishment 写为 accepted / modified / assumed。",
                    True,
                )
            )
        if status in DEMAND_ESTABLISHMENT_BLOCKING_STATUSES:
            findings.append(
                Finding(
                    "DE7",
                    "Major",
                    "strategy_signoff 存在时，demand_establishment.status 不得为 confirmation_required / blocked / pending；应先完成需求成立检查点。",
                    True,
                )
            )
        if user_action == "pending":
            findings.append(
                Finding(
                    "DE8",
                    "Major",
                    "strategy_signoff 存在时，demand_establishment.user_action 不得为 pending。",
                    True,
                )
            )
        if blocks_strategy_signoff == "true":
            findings.append(
                Finding(
                    "DE9",
                    "Major",
                    "demand_establishment.blocks_strategy_signoff=true 时，不得输出 strategy_signoff；应先完成需求成立确认。",
                    True,
                )
            )

    return findings


def lint_plan(text: str) -> list[Finding]:
    findings: list[Finding] = []
    contracts = load_contracts()
    blockers_block = extract_top_level_block(text, "blockers")
    if blockers_block:
        blocker_ids = re.findall(r"^\s*-\s+id\s*:\s*['\"]?([^'\"\s]+)", blockers_block, flags=re.M)
        for blocker_id in blocker_ids:
            if not re.fullmatch(r"6-R[0-9]+", blocker_id):
                findings.append(
                    Finding(
                        "P7",
                        "Blocker",
                        "结构计划 blockers 下所有 id 必须符合 6-Rx。",
                        True,
                    )
                )
                break

    cco_blocks = split_plan_cco_blocks(text)
    if not cco_blocks:
        findings.append(Finding("P1", "Blocker", "结构计划必须包含 core_change_objects。", True))
        return findings

    cco_names = [plan_cco_name(block) for block in cco_blocks]
    has_product_object_cco = any(CCO_PRODUCT_OBJECT_PATTERN.search(name) for name in cco_names)
    dimension_only_names = [
        name
        for name in cco_names
        if name and CCO_DIMENSION_ONLY_PATTERN.search(name)
    ]
    if len(cco_blocks) > 1 and has_product_object_cco and dimension_only_names:
        findings.append(
            Finding(
                "P8",
                "Review note",
                "结构计划疑似按页面 / 规则 / 数据 / 验收等表达维度拆分 CCO："
                + "、".join(dimension_only_names)
                + "。请确认这些对象是否具备独立产品意图、独立用户路径、独立上线 / 验收 / 复用价值或独立系统边界；否则应合并到对应完整产品改动单元内。",
                False,
            )
        )

    for index, block in enumerate(cco_blocks, start=1):
        blocks_value = field_value(block, "blocks_engineering_start")
        blocker_refs_value = field_value(block, "blocker_refs")
        if blocks_value is None:
            findings.append(
                Finding("P2", "Blocker", f"结构计划中 CCO {index} 缺少 blocks_engineering_start。", True)
            )
            continue
        normalized = blocks_value.lower()
        if normalized not in {"true", "false"}:
            findings.append(
                Finding(
                    "P3",
                    "Blocker",
                    f"结构计划中 CCO {index} 的 blocks_engineering_start 必须为 true / false。",
                    True,
                )
            )
            continue
        if blocker_refs_value is None:
            findings.append(Finding("P4", "Blocker", f"结构计划中 CCO {index} 缺少 blocker_refs。", True))
            continue
        refs = parse_blocker_refs(blocker_refs_value)
        if normalized == "true" and not refs:
            findings.append(
                Finding(
                    "P5",
                    "Blocker",
                    f"结构计划中 CCO {index} 阻塞研发启动时，必须在 blocker_refs 引用 6-R 阻塞项。",
                    True,
                )
            )
        has_blocker_signal = "[阻塞" in block or re.search(r"\b6-R[0-9]+\b", block) is not None
        if normalized == "false" and has_blocker_signal and not refs:
            findings.append(
                Finding(
                    "P6",
                    "Blocker",
                    f"结构计划中 CCO {index} 标记为不阻塞研发启动，但存在阻塞信号且未在 blocker_refs 声明。",
                    True,
                )
            )
    findings.extend(lint_strategy_plan(text, contracts))
    findings.extend(lint_retrieval_plan(text))
    findings.extend(lint_behavior_delta_plan(text))
    findings.extend(lint_demand_establishment_plan(text))
    return findings


def lint_light(text: str) -> list[Finding]:
    findings: list[Finding] = []
    if h2_headings(text) == DEFAULT_REQUIRED_SECTIONS or any(
        section in text for section in DEFAULT_REQUIRED_SECTIONS
    ):
        findings.append(
            Finding(
                "Q1",
                "Major",
                "轻量输出不应套用完整 6 节 PRD 骨架。",
                True,
            )
        )
    if "### 核心改动对象" in text or re.search(r"\bCCO\b", text):
        findings.append(Finding("Q2", "Major", "轻量输出不应生成 CCO。", True))
    has_artifact = re.search(r"```mermaid|flowchart|stateDiagram", text) is not None
    if not has_artifact:
        for line in text.splitlines():
            if not re.search(r"原型|埋点表|状态机|流程图", line):
                continue
            if re.search(r"N/A|不适用|不涉及|无需|不需要", line):
                continue
            has_artifact = True
            break
    if has_artifact:
        findings.append(
            Finding(
                "Q3",
                "Major",
                "轻量输出不应生成不必要的流程图、原型、状态机或完整埋点附属物。",
                True,
            )
        )
    for pattern in CHATTER_PATTERNS:
        if re.search(pattern, text):
            findings.append(
                Finding(
                    "Q4",
                    "Major",
                    "轻量输出包含闲聊、称赞或过程播报，应移除。",
                    True,
                )
            )
            break
    missing_terms = [term for term in DEFAULT_LIGHT_REQUIRED_TERMS if term not in text]
    if missing_terms:
        findings.append(
            Finding(
                "Q5",
                "Major",
                "轻量输出必须包含改动内容、影响范围、验收点。",
                True,
            )
        )
    if "N/A" not in text and "不适用" not in text:
        findings.append(
            Finding(
                "Q6",
                "Major",
                "轻量输出应说明不适用项，使用 N/A 或“不适用”。",
                True,
            )
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 PRD Markdown 或结构计划。", add_help=False)
    parser.add_argument("-h", "--help", action="help", help="显示帮助信息并退出")
    parser.add_argument("file", type=Path, help="需要校验的 PRD Markdown 文件")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式结果")
    parser.add_argument("--plan", action="store_true", help="校验结构计划，而不是 PRD 正文")
    parser.add_argument("--light", action="store_true", help="校验轻量需求输出")
    parser.add_argument(
        "--structure-plan",
        type=Path,
        help="结构计划文件，用于判断 PRD 是否触发附属物校验",
    )
    args = parser.parse_args()

    text = args.file.read_text(encoding="utf-8")
    if args.plan and args.light:
        parser.error("--plan 和 --light 不能同时使用")
    if args.light:
        findings = lint_light(text)
    elif args.plan:
        findings = lint_plan(text)
    else:
        plan_text = args.structure_plan.read_text(encoding="utf-8") if args.structure_plan else None
        findings = lint(
            text,
            load_contracts(),
            extract_required_artifact_types(plan_text),
            plan_text,
        )
        findings.extend(lint_prd_generation_guard(plan_text, text))
    passed = not any(item.severity in {"Blocker", "Major"} for item in findings)

    result = {
        "passed": passed,
        "errors": [asdict(item) for item in findings if item.severity == "Blocker"],
        "warnings": [asdict(item) for item in findings if item.severity != "Blocker"],
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("PASS" if passed else "FAIL")
        for item in findings:
            auto = "可自动修复" if item.autofixable else "需人工处理"
            print(f"- {item.code} [{item.severity}] ({auto}) {item.message}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

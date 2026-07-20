#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

require_file() {
  [[ -f "$ROOT/$1" ]] || fail "missing $1"
}

require_grep() {
  local pattern="$1"
  local file="$2"
  grep -q "$pattern" "$ROOT/$file" || fail "missing pattern '$pattern' in $file"
}

require_file "SKILL.md"
require_file "references/experiment-design.md"
require_file "references/lab-workflow.md"
require_file "references/aggregation-report.md"
require_file "templates/batch_plan.md"
require_file "templates/lab_run_manifest.md"
require_file "templates/lab_report.md"
require_file "agents/openai.yaml"

require_grep "^name: user-chance-lab" "SKILL.md"
require_grep "每轮.*真实跑 App" "SKILL.md"
require_grep "可直接执行的自然语言任务卡" "SKILL.md"
require_grep "目标约束槽位" "SKILL.md"
require_grep "默认有效样本数" "SKILL.md"
require_grep "失败.*自动补跑" "SKILL.md"
require_grep "lab_run_manifest.md" "SKILL.md"
require_grep "partial_valid" "SKILL.md"
require_grep "接手任务如果已经明确" "SKILL.md"

require_grep "入口倾向.*由角色" "references/experiment-design.md"
require_grep "决策弹性.*由目标槽位" "references/experiment-design.md"
require_grep "目标对象" "references/experiment-design.md"
require_grep "商品状态" "references/experiment-design.md"
require_grep "时效履约" "references/experiment-design.md"
require_grep "价格 / 风险权重" "references/experiment-design.md"

require_grep "目标有效样本数 = 5" "references/lab-workflow.md"
require_grep "最大尝试次数 = 8" "references/lab-workflow.md"
require_grep "natural_failure" "references/lab-workflow.md"
require_grep "单轮收口规则" "references/lab-workflow.md"
require_grep "静默超时规则" "references/lab-workflow.md"
require_grep "接手规则" "references/lab-workflow.md"
require_grep "已有足够证据但未写报告" "references/lab-workflow.md"
require_grep "partial_valid" "references/lab-workflow.md"
require_grep "不要再输出计划或请求确认" "references/lab-workflow.md"

require_grep "高频体验问题" "references/aggregation-report.md"
require_grep "产品机会" "references/aggregation-report.md"
require_grep "证据索引" "references/aggregation-report.md"
require_grep "样本权重说明" "references/aggregation-report.md"

bash -n "$ROOT/scripts/check_skill_contract.sh"

echo "PASS: user-chance-lab skill contract"

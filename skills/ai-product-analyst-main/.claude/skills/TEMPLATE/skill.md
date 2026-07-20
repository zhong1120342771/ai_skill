# Skill: {{BLANK_1_SKILL_NAME}}

## Purpose
{{BLANK_2_WHEN_TO_FIRE}}

## When to Use
Fires automatically when the user asks Claude to do something that matches the trigger condition above.

## Instructions
1. Detect the trigger condition
2. Execute your guardrail check
3. If the check matters, print a clear, visible warning with "{{BLANK_3_SIGNATURE_PHRASE}}" as the first line
4. Continue with the analysis, incorporating the warning into the output

## Anti-Patterns
- Do not fire when the condition doesn't apply
- Do not block the analysis — just flag and continue

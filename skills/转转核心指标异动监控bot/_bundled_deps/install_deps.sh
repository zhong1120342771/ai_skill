#!/usr/bin/env bash
# 转转核心指标异动监控bot skill —— 依赖还原脚本
# 把 _bundled_deps/ 里镜像的依赖还原到 ~/.claude 规范位置。
# 幂等：已存在的目标默认跳过；--force 覆盖。
set -euo pipefail

FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${HOME}/.claude"

restore() {
  local src="$1" dst="$2"
  if [ -e "$dst" ] && [ "$FORCE" -eq 0 ]; then
    echo "跳过（已存在）: $dst"
    return
  fi
  mkdir -p "$(dirname "$dst")"
  rm -rf "$dst"
  cp -R "$src" "$dst"
  echo "已还原: $dst"
}

echo "=== 还原依赖到 ${CLAUDE_HOME} ==="
restore "${HERE}/skills/xinghe-data" "${CLAUDE_HOME}/skills/xinghe-data"
restore "${HERE}/skills/humanizer"   "${CLAUDE_HOME}/skills/humanizer"
restore "${HERE}/scripts/oneservice_cli.py" "${CLAUDE_HOME}/scripts/oneservice_cli.py"

echo
echo "=== 完成。请继续手动配置（包外必配，见 README_迁移部署.md）==="
echo "1. 环境变量: XINGHE_CLIENT_USER / XINGHE_CLIENT_SECRET / XINGHE_OA / ONESERVICE_OA / ONESERVICE_ACCESS_KEY"
echo "2. lark-cli 授权: lark-cli auth login && lark-cli auth status"
echo "3. Python 库: pip3 install pandas numpy matplotlib requests"

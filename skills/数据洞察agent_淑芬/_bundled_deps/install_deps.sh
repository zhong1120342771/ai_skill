#!/usr/bin/env bash
# 首页数据洞察（淑芬）skill —— 外部依赖还原脚本
# 目标机解压 skill 后，在 _bundled_deps/ 目录里跑这个脚本，
# 把随包携带的 3 个依赖还原到 ~/.claude 的规范位置。
# 幂等：已存在的目标默认跳过，加 --force 覆盖。

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

echo "== 还原目标根目录: $CLAUDE_HOME =="
mkdir -p "$CLAUDE_HOME/skills" "$CLAUDE_HOME/scripts"

restore_dir() {  # $1=包内相对路径  $2=目标绝对路径
  local src="$HERE/$1" dst="$2"
  if [ -e "$dst" ] && [ "$FORCE" -eq 0 ]; then
    echo "[skip] 已存在: $dst （--force 可覆盖）"
    return
  fi
  mkdir -p "$(dirname "$dst")"
  rsync -a --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' "$src/" "$dst/"
  echo "[ok]   $1 -> $dst"
}

restore_file() { # $1=包内相对路径  $2=目标绝对路径
  local src="$HERE/$1" dst="$2"
  if [ -e "$dst" ] && [ "$FORCE" -eq 0 ]; then
    echo "[skip] 已存在: $dst （--force 可覆盖）"
    return
  fi
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  echo "[ok]   $1 -> $dst"
}

restore_dir  "skills/xinghe-data" "$CLAUDE_HOME/skills/xinghe-data"
restore_dir  "skills/humanizer"   "$CLAUDE_HOME/skills/humanizer"
restore_file "scripts/oneservice_cli.py" "$CLAUDE_HOME/scripts/oneservice_cli.py"
chmod +x "$CLAUDE_HOME/scripts/oneservice_cli.py" 2>/dev/null || true

echo ""
echo "== 依赖还原完成。剩下 3 件事目标机自己配（包里带不了）=="
echo "  1) 装 lark-cli:  brew install lark-cli   然后 lark-cli auth login"
echo "  2) 配环境变量(写进 ~/.zshrc): XINGHE_CLIENT_USER / XINGHE_CLIENT_SECRET / XINGHE_OA / ONESERVICE_OA / ONESERVICE_ACCESS_KEY"
echo "  3) pip3 install requests   (xinghe_client 唯一第三方依赖)"
echo ""
echo "自查见同目录 README_迁移部署.md"

#!/usr/bin/env bash
# 幂等还原脚本:把 _bundled_deps/ 里的外部依赖 rsync 回目标机 ~/.claude 规范位置。
# 脚本里是硬编码路径(/Users/.../. claude/scripts/...),必须还原到规范位才不用改代码。
# 用法: bash install_deps.sh [--force]
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
LA_DIR="$HOME/Library/LaunchAgents"
FORCE=""
[[ "${1:-}" == "--force" ]] && FORCE="1"

echo "== 还原 group_auto_reply 服务依赖 =="

mkdir -p "$CLAUDE_DIR/scripts" "$CLAUDE_DIR/logs" "$LA_DIR"

copy() {  # src dst
  local src="$1" dst="$2"
  if [[ -f "$dst" && -z "$FORCE" ]]; then
    if cmp -s "$src" "$dst"; then echo "  = 已一致,跳过 $dst"; return; fi
    echo "  ! 目标已存在且不同: $dst (加 --force 覆盖,或先备份)"; return
  fi
  cp "$src" "$dst" && echo "  + 写入 $dst"
}

copy "$HERE/.claude/scripts/group_auto_reply.py"             "$CLAUDE_DIR/scripts/group_auto_reply.py"
copy "$HERE/.claude/scripts/group_auto_reply_cost_report.py" "$CLAUDE_DIR/scripts/group_auto_reply_cost_report.py"
copy "$HERE/LaunchAgents/com.zmt.group-auto-reply.plist"     "$LA_DIR/com.zmt.group-auto-reply.plist"

echo ""
echo "== 语法自检 =="
python3 -m py_compile "$CLAUDE_DIR/scripts/group_auto_reply.py" && echo "  group_auto_reply.py 语法OK"

echo ""
echo "== 硬编码路径检查(目标机用户名不是 zhongmengting 时需手改) =="
if ! grep -q "$HOME" "$CLAUDE_DIR/scripts/group_auto_reply.py"; then
  echo "  注意: 脚本内 CLAUDE_BIN 等硬编码为 /Users/zhongmengting/... "
  echo "  若当前机器 HOME=$HOME 不同,请手改 group_auto_reply.py 顶部 CLAUDE_BIN 和 plist 里的绝对路径。"
fi

echo ""
echo "完成。下一步(手动):"
echo "  1) 确认已装 lark-cli 并登录 bot: lark-cli auth status"
echo "  2) 确认机器人已被拉进白名单群(ALLOWED_CHATS 里的 chat_id)"
echo "  3) 启动服务:"
echo "     launchctl unload $LA_DIR/com.zmt.group-auto-reply.plist 2>/dev/null || true"
echo "     launchctl load   $LA_DIR/com.zmt.group-auto-reply.plist"
echo "  4) 验证: pgrep -fl group_auto_reply.py"

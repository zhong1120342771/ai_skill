#!/bin/zsh
# launchd wrapper：先加载 ~/.zshrc 拿星河凭证，再跑周缓存构建。
# launchd 不走登录 shell，不会自动 source .zshrc，故这里显式 source。
source "$HOME/.zshrc" 2>/dev/null
LOG="$HOME/.claude/skills/转转核心指标异动监控bot/data_storage/weekly_cache_cron.log"
echo "===== $(date '+%Y-%m-%d %H:%M:%S') 周缓存构建开始 =====" >> "$LOG"
/usr/bin/python3 "$HOME/.claude/skills/转转核心指标异动监控bot/scripts/build_weekly_cache.py" >> "$LOG" 2>&1
echo "退出码 $? / 结束 $(date '+%H:%M:%S')" >> "$LOG"

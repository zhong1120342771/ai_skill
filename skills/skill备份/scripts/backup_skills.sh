#!/usr/bin/env bash
# skill 备份：把 ~/.claude/skills 下「用户自己的」skill 同步到 staging 仓并推送 GitHub。
# 覆盖逻辑：每次用当前 skills 目录重建 staging 快照 -> git add -A 捕获增/改/删 -> 有变动才 commit+push。
# 排除：内置 lark-* 软链 skill、*.bak.* 备份目录、data_storage/产物/缓存/密钥。
# 认证：依赖 git credential store（~/.git-credentials 里的 token）。
set -euo pipefail

SRC="$HOME/.claude/skills"
STAGE="$HOME/ai_skill_sync"
REMOTE_URL="https://github.com/zhong1120342771/ai_skill.git"
BRANCH="main"

if [ ! -d "$SRC" ]; then echo "ERR_NO_SRC: $SRC"; exit 2; fi

# 初始化 staging 仓（首次）
if [ ! -d "$STAGE/.git" ]; then
  mkdir -p "$STAGE"
  git -C "$STAGE" init -q
  git -C "$STAGE" remote add origin "$REMOTE_URL" 2>/dev/null || git -C "$STAGE" remote set-url origin "$REMOTE_URL"
fi

# .gitignore（幂等写入）
cat > "$STAGE/.gitignore" <<'IGN'
data_storage/
outputs/
visualizations/
analysis_reports/
*.csv
*.xlsx
*.xls
*.parquet
*.png
*.jpg
*.jpeg
*.pdf
*.log
__pycache__/
*.pyc
.snapshot.json
*.snapshot.json
.env
*.key
*.pem
*credential*.local*
.DS_Store
IGN

# 重建 skills 快照（先清空再拷，保证删除的 skill/文件被覆盖掉）
rm -rf "$STAGE/skills"
mkdir -p "$STAGE/skills"

RSYNC_EXCLUDES=(
  --exclude='data_storage/' --exclude='__pycache__/' --exclude='*.pyc'
  --exclude='*.csv' --exclude='*.png' --exclude='*.jpg' --exclude='*.jpeg'
  --exclude='*.xlsx' --exclude='*.xls' --exclude='*.parquet' --exclude='*.pdf'
  --exclude='*.log' --exclude='.DS_Store'
  --exclude='outputs/' --exclude='visualizations/' --exclude='analysis_reports/'
  --exclude='.snapshot.json'
)

count=0
cd "$SRC"
for d in */; do
  name="${d%/}"
  [ -L "$name" ] && continue                       # 跳过内置软链 skill
  case "$name" in *.bak.*) continue;; esac         # 跳过 .bak 备份目录
  rsync -a "${RSYNC_EXCLUDES[@]}" "$d" "$STAGE/skills/$name/"
  count=$((count+1))
done
echo "SKILLS_STAGED=$count"

# 提交与推送
cd "$STAGE"
git add -A
if git diff --cached --quiet; then
  echo "NO_CHANGES"
  exit 0
fi

# 变动摘要（供上层播报）
echo "=== CHANGES ==="
git diff --cached --stat | tail -30

TS="$(date '+%Y-%m-%d %H:%M')"
git -c user.name='zhong1120342771' -c user.email='zhong1120342771@users.noreply.github.com' \
    commit -q -m "chore: skill 备份自动同步 $TS"

if git push -u origin "$BRANCH" 2>push.err; then
  echo "PUSHED_OK $TS"
  rm -f push.err
else
  echo "PUSH_FAILED"
  sed 's/ghp_[A-Za-z0-9]*/ghp_***REDACTED***/g' push.err || true
  rm -f push.err
  exit 3
fi

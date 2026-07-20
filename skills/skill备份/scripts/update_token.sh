#!/usr/bin/env bash
# 更新本机 git 凭证库里的 GitHub token（供 skill备份 自动推送用）。
# 用法: bash update_token.sh <ghp_新token>
set -euo pipefail
TOK="${1:-}"
if [ -z "$TOK" ]; then echo "用法: bash update_token.sh <ghp_新token>"; exit 1; fi
USER="zhong1120342771"
CRED="$HOME/.git-credentials"

git config --global credential.helper store

# 移除旧的 github.com 条目，写入新条目
if [ -f "$CRED" ]; then
  grep -v 'github.com' "$CRED" > "$CRED.tmp" 2>/dev/null || true
  mv "$CRED.tmp" "$CRED"
fi
printf 'https://%s:%s@github.com\n' "$USER" "$TOK" >> "$CRED"
chmod 600 "$CRED"
echo "TOKEN_UPDATED (仅本机, chmod 600)"

# 快速校验 token 有效性与权限
scope="$(curl -sS -i -H "Authorization: token $TOK" https://api.github.com/user 2>/dev/null | grep -i '^x-oauth-scopes:' || true)"
echo "$scope"
case "$scope" in
  *repo*|*public_repo*) echo "SCOPE_OK";;
  *) echo "WARN: token 可能缺少 public_repo 权限，推送会 403";;
esac

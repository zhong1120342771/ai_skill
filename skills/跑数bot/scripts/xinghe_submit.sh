#!/bin/bash
# xinghe_submit.sh — stariver-hive-query skill 内置版
# 从 stdin 读取 SQL，提交到星河 One-Service，下载结果
# 凭证从 skill 目录下 .credentials.local 读取（不硬编码）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRED_FILE="${STARIVER_CRED_FILE:-$SCRIPT_DIR/../.credentials.local}"

BASE_URL="https://oneservice.zhuanspirit.com/sqlTask"
OUTPUT_DIR="$HOME/claude-output"

# ── 读取凭证 ────────────────────────────────────────────
OA_NAME=""
ACCESS_KEY=""
if [ -f "$CRED_FILE" ]; then
  OA_NAME=$(grep -E '^OA_NAME=' "$CRED_FILE" | head -1 | cut -d= -f2- | tr -d '[:space:]')
  ACCESS_KEY=$(grep -E '^ACCESS_KEY=' "$CRED_FILE" | head -1 | cut -d= -f2- | tr -d '[:space:]')
fi

if [ -z "$OA_NAME" ] || [ -z "$ACCESS_KEY" ]; then
  cat >&2 <<EOF
❌ 未找到 StarRiver / One-Service 凭证: $CRED_FILE

特别说明：需提前在 zeye 平台申请一个 accessKey，访问以下链接获取
（如果没访问权限，请联系业成）:
https://zeye.zhuanspirit.com/main/showPage?pageId=getOrCreateAiAccessKey

申请到 accessKey 后，在 skill 目录下创建 .credentials.local:
  路径: $SCRIPT_DIR/../.credentials.local
  内容:
    OA_NAME=你的OA账号
    ACCESS_KEY=你的accessKey

(.credentials.local 已被 .gitignore 忽略，不会随 skill 包分发)
EOF
  exit 2
fi

# ── 网络接口选择 ────────────────────────────────────────
BASE_CURL=(env -u https_proxy -u http_proxy -u HTTPS_PROXY -u HTTP_PROXY -u ALL_PROXY curl -k -s)

probe_interface() {
  local iface="$1"
  local code
  code=$("${BASE_CURL[@]}" --interface "$iface" --connect-timeout 8 -o /dev/null -w "%{http_code}" "${BASE_URL}" 2>/dev/null || true)
  case "$code" in
    200|301|302|400|401|403|404|405) return 0 ;;
    *) return 1 ;;
  esac
}

pick_interface() {
  if ! command -v ifconfig >/dev/null 2>&1; then
    return 1
  fi
  local candidates=()
  local iface
  while IFS= read -r iface; do
    [ -n "$iface" ] && candidates+=("$iface")
  done < <(
    {
      ifconfig | awk '
        /^[a-zA-Z0-9]+:/ { iface = $1; sub(/:$/, "", iface) }
        /inet 192\.168\.255\./ { print iface }
        /inet 10\./ && iface ~ /^en/ { print iface }
      '
      ifconfig | awk '/^utun[0-9]+:/{sub(/:$/,"",$1); print $1}'
    } | awk '!seen[$0]++'
  )
  if [ "${#candidates[@]}" -eq 0 ]; then
    return 1
  fi
  for iface in "${candidates[@]}"; do
    if probe_interface "$iface"; then
      echo "$iface"
      return 0
    fi
  done
  return 1
}

VPN_INTERFACE="$(pick_interface || true)"
if [ -z "$VPN_INTERFACE" ]; then
  echo "❌ 未找到可访问 oneservice 的网络接口" >&2
  echo "   已尝试: 公司 VPN(192.168.255.x)、企业网卡(en*)、utun*" >&2
  exit 1
fi
echo "🌐 使用网络接口: $VPN_INTERFACE" >&2

CURL=("${BASE_CURL[@]}" --interface "$VPN_INTERFACE" --connect-timeout 10)
CURL_LONG=("${BASE_CURL[@]}" --interface "$VPN_INTERFACE" --connect-timeout 60)

mkdir -p "$OUTPUT_DIR"

# ── 1. 读取 SQL ─────────────────────────────────────────
SQL=$(cat)
if [ -z "$SQL" ]; then
  echo "❌ 未提供 SQL" >&2
  exit 1
fi

echo "📤 提交 SQL 到星河..." >&2
echo "────────────────────────────────────────" >&2
echo "$SQL" | head -5 >&2
echo "────────────────────────────────────────" >&2

# ── 2. 提交任务 ─────────────────────────────────────────
RESP=$("${CURL[@]}" -X POST "${BASE_URL}/submit" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "sql=$SQL" \
  --data-urlencode "oaName58=$OA_NAME" \
  --data-urlencode "accessKey=$ACCESS_KEY")

TASK_ID=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['respData']['data']['execute_id'])" 2>/dev/null || echo "")
if [ -z "$TASK_ID" ]; then
  echo "❌ 提交失败: $RESP" >&2
  exit 1
fi
echo "✅ 任务已提交，ID: $TASK_ID" >&2

# ── 3. 轮询进度 ─────────────────────────────────────────
echo -n "⏳ 等待执行" >&2
while true; do
  sleep 3
  echo -n "." >&2
  PROGRESS=$("${CURL[@]}" "${BASE_URL}/queryTaskProgress/${TASK_ID}" 2>/dev/null || true)
  STATUS=$(echo "$PROGRESS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('respData',{}).get('data',[{}])[0].get('status',''))" 2>/dev/null || echo "")
  if [ "$STATUS" = "SUCCESS" ]; then
    echo " 完成!" >&2
    break
  elif [ "$STATUS" = "FAILED" ]; then
    echo "" >&2
    ERROR_MSG=$(echo "$PROGRESS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('respData',{}).get('data',[{}])[0].get('error_msg','未知错误'))" 2>/dev/null || echo "未知错误")
    echo "❌ 执行失败: $ERROR_MSG" >&2
    exit 1
  fi
done

# ── 4. 下载结果 ─────────────────────────────────────────
echo "📥 下载结果..." >&2
RESULT_FILE="$OUTPUT_DIR/sql_result_${TASK_ID}.tsv"

DOWNLOAD_INFO=$("${CURL[@]}" "${BASE_URL}/queryTaskResult/${TASK_ID}?oaName58=$OA_NAME&accessKey=$ACCESS_KEY" 2>/dev/null || true)
DOWNLOAD_URL=$(echo "$DOWNLOAD_INFO" | python3 -c "
import sys,json
d = json.load(sys.stdin)
rd = d.get('respData',{})
for key in ['filename','filename_txt','filename_csv']:
    v = rd.get('data',{}).get(key,'') or rd.get(key,'')
    if v:
        print(v)
        break
" 2>/dev/null || echo "")

if [ -n "$DOWNLOAD_URL" ]; then
  "${CURL_LONG[@]}" "$DOWNLOAD_URL" -o "$RESULT_FILE" 2>/dev/null || true
else
  "${CURL_LONG[@]}" "${BASE_URL}/downloadTaskResult/${TASK_ID}?oaName58=$OA_NAME&accessKey=$ACCESS_KEY" -o "$RESULT_FILE" 2>/dev/null || true
fi

# ── 5. 统计 & 预览 ──────────────────────────────────────
LINE_COUNT=$(wc -l < "$RESULT_FILE" | tr -d ' ')
SIZE=$(wc -c < "$RESULT_FILE" | tr -d ' ')
echo "✅ 结果已保存: $RESULT_FILE"
echo "   📊 $LINE_COUNT 行 | $SIZE bytes" >&2
echo "" >&2
echo "────────────────────────────────────────" >&2
echo "📋 预览 (前 10 行):" >&2
head -10 "$RESULT_FILE" >&2

#!/usr/bin/env bash
set -euo pipefail

PKG="${ZHUANZHUAN_PACKAGE:-com.wuba.zhuanzhuan}"
DEVICE="${1:-${ANDROID_SERIAL:-}}"

fail() {
  printf '[user-chance-env] FAIL: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '[user-chance-env] %s\n' "$*"
}

command -v adb >/dev/null 2>&1 || fail "adb is not installed or not in PATH"

if [[ -z "$DEVICE" ]]; then
  DEVICES=()
  while IFS= read -r device_id; do
    [[ -n "$device_id" ]] && DEVICES+=("$device_id")
  done < <(adb devices | awk 'NR>1 && $2=="device" {print $1}')
  if [[ "${#DEVICES[@]}" -eq 0 ]]; then
    fail "no online Android device"
  fi
  if [[ "${#DEVICES[@]}" -gt 1 ]]; then
    printf '[user-chance-env] online devices:\n' >&2
    printf '  %s\n' "${DEVICES[@]}" >&2
    fail "multiple devices online; pass a device id explicitly"
  fi
  DEVICE="${DEVICES[0]}"
fi

STATE="$(adb -s "$DEVICE" get-state 2>/dev/null || true)"
[[ "$STATE" == "device" ]] || fail "device $DEVICE is not online; state=$STATE"

MODEL="$(adb -s "$DEVICE" shell getprop ro.product.model | tr -d '\r')"
ANDROID_VERSION="$(adb -s "$DEVICE" shell getprop ro.build.version.release | tr -d '\r')"
SIZE="$(adb -s "$DEVICE" shell wm size | tr -d '\r')"
DENSITY="$(adb -s "$DEVICE" shell wm density | tr -d '\r')"

info "device_id=$DEVICE"
info "device_model=$MODEL"
info "android_version=$ANDROID_VERSION"
info "$SIZE"
info "$DENSITY"

if ! adb -s "$DEVICE" shell pm path "$PKG" >/dev/null 2>&1; then
  fail "package $PKG is not installed"
fi

VERSION_LINE="$(adb -s "$DEVICE" shell dumpsys package "$PKG" | grep -m1 'versionName=' | tr -d '\r' || true)"
VERSION_CODE_LINE="$(adb -s "$DEVICE" shell dumpsys package "$PKG" | grep -m1 'versionCode=' | tr -d '\r' || true)"
ACTIVITY="$(adb -s "$DEVICE" shell cmd package resolve-activity --brief "$PKG" | tail -n1 | tr -d '\r' || true)"

[[ -n "$ACTIVITY" && "$ACTIVITY" != "No activity found" ]] || fail "cannot resolve launch activity for $PKG"

info "package=$PKG"
info "${VERSION_LINE:-versionName=unknown}"
info "${VERSION_CODE_LINE:-versionCode=unknown}"
info "launch_activity=$ACTIVITY"

if [[ "${START_APP:-0}" == "1" ]]; then
  info "starting $ACTIVITY"
  adb -s "$DEVICE" shell am start -n "$ACTIVITY" >/dev/null
  sleep "${START_WAIT_SECONDS:-5}"
fi

FOCUS="$(adb -s "$DEVICE" shell dumpsys window | grep -E 'mCurrentFocus|mFocusedApp' | tr -d '\r' || true)"
info "focus_begin"
printf '%s\n' "$FOCUS"
info "focus_end"

if [[ "$FOCUS" == *"$PKG"* ]]; then
  info "front_app=$PKG"
else
  info "front_app=not_$PKG"
fi

info "OK"

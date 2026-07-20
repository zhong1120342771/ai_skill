#!/usr/bin/env bash
set -euo pipefail

PKG="${ZHUANZHUAN_PACKAGE:-com.wuba.zhuanzhuan}"
EMULATOR_BIN="${EMULATOR_BIN:-}"

fail() {
  printf '[user-chance-endpoints] FAIL: %s\n' "$*" >&2
  exit 1
}

command -v adb >/dev/null 2>&1 || fail "adb is not installed or not in PATH"

if [[ -z "$EMULATOR_BIN" ]]; then
  if command -v emulator >/dev/null 2>&1; then
    EMULATOR_BIN="$(command -v emulator)"
  elif [[ -x /opt/homebrew/share/android-commandlinetools/emulator/emulator ]]; then
    EMULATOR_BIN="/opt/homebrew/share/android-commandlinetools/emulator/emulator"
  elif [[ -x "$HOME/Library/Android/sdk/emulator/emulator" ]]; then
    EMULATOR_BIN="$HOME/Library/Android/sdk/emulator/emulator"
  fi
fi

DEVICES=()
while IFS= read -r device_id; do
  [[ -n "$device_id" ]] && DEVICES+=("$device_id")
done < <(adb devices | awk 'NR>1 && $2=="device" {print $1}')

printf 'endpoint_id\tendpoint_state\tdevice_type\tmodel\tandroid_version\tpackage_installed\tapp_version\tfront_app\tstart_hint\n'

RUNNING_AVD_NAMES=" "

if [[ "${#DEVICES[@]}" -gt 0 ]]; then
  for DEVICE in "${DEVICES[@]}"; do
    MODEL="$(adb -s "$DEVICE" shell getprop ro.product.model | tr -d '\r' || true)"
    ANDROID_VERSION="$(adb -s "$DEVICE" shell getprop ro.build.version.release | tr -d '\r' || true)"
    QEMU="$(adb -s "$DEVICE" shell getprop ro.kernel.qemu | tr -d '\r' || true)"
    DEVICE_TYPE="physical"
    if [[ "$DEVICE" == emulator-* || "$QEMU" == "1" ]]; then
      DEVICE_TYPE="emulator"
      AVD_RUNNING_NAME="$(adb -s "$DEVICE" emu avd name 2>/dev/null | head -n1 | tr -d '\r' || true)"
      if [[ -n "$AVD_RUNNING_NAME" ]]; then
        RUNNING_AVD_NAMES="${RUNNING_AVD_NAMES}${AVD_RUNNING_NAME} "
      fi
    fi

    PACKAGE_INSTALLED="no"
    APP_VERSION=""
    if adb -s "$DEVICE" shell pm path "$PKG" >/dev/null 2>&1; then
      PACKAGE_INSTALLED="yes"
      APP_VERSION="$(adb -s "$DEVICE" shell dumpsys package "$PKG" | sed -n 's/.*versionName=//p' | head -n1 | tr -d '\r' || true)"
    fi

    FOCUS="$(adb -s "$DEVICE" shell dumpsys window | grep -E 'mCurrentFocus|mFocusedApp' | tr -d '\r' || true)"
    FRONT_APP="unknown"
    if [[ "$FOCUS" == *"$PKG"* ]]; then
      FRONT_APP="$PKG"
    elif [[ -n "$FOCUS" ]]; then
      FRONT_APP="other"
    fi

    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$DEVICE" "online" "$DEVICE_TYPE" "${MODEL:-unknown}" "${ANDROID_VERSION:-unknown}" \
      "$PACKAGE_INSTALLED" "${APP_VERSION:-unknown}" "$FRONT_APP" ""
  done
fi

for AVD_DIR in "$HOME"/.android/avd/*.avd; do
  [[ -d "$AVD_DIR" ]] || continue
  AVD_NAME="$(basename "$AVD_DIR" .avd)"
  if [[ "$RUNNING_AVD_NAMES" == *" $AVD_NAME "* ]]; then
    continue
  fi
  START_HINT=""
  if [[ -n "$EMULATOR_BIN" ]]; then
    START_HINT="$EMULATOR_BIN -avd $AVD_NAME -no-snapshot-save -no-metrics"
  else
    START_HINT="emulator binary not found"
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "avd:$AVD_NAME" "configured" "emulator" "unknown" "unknown" \
    "unknown" "unknown" "not_running" "$START_HINT"
done

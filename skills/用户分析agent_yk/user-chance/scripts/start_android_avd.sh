#!/usr/bin/env bash
set -euo pipefail

AVD_NAME="${1:-}"
TIMEOUT_SECONDS="${START_TIMEOUT_SECONDS:-180}"
STABILITY_SECONDS="${START_STABILITY_SECONDS:-45}"
LOG_DIR="${USER_CHANCE_LOG_DIR:-/tmp}"
EMULATOR_HEADLESS="${EMULATOR_HEADLESS:-1}"
EMULATOR_EXTRA_ARGS="${EMULATOR_EXTRA_ARGS:-}"
EMULATOR_SUPERVISOR="${EMULATOR_SUPERVISOR:-auto}"

fail() {
  printf '[user-chance-avd] FAIL: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '[user-chance-avd] %s\n' "$*"
}

[[ -n "$AVD_NAME" ]] || fail "usage: start_android_avd.sh <avd_name>"
command -v adb >/dev/null 2>&1 || fail "adb is not installed or not in PATH"

EMULATOR_BIN="${EMULATOR_BIN:-}"
if [[ -z "$EMULATOR_BIN" ]]; then
  if command -v emulator >/dev/null 2>&1; then
    EMULATOR_BIN="$(command -v emulator)"
  elif [[ -x /opt/homebrew/share/android-commandlinetools/emulator/emulator ]]; then
    EMULATOR_BIN="/opt/homebrew/share/android-commandlinetools/emulator/emulator"
  elif [[ -x "$HOME/Library/Android/sdk/emulator/emulator" ]]; then
    EMULATOR_BIN="$HOME/Library/Android/sdk/emulator/emulator"
  else
    fail "emulator binary not found"
  fi
fi

if [[ ! -d "$HOME/.android/avd/$AVD_NAME.avd" ]]; then
  fail "AVD $AVD_NAME not found under $HOME/.android/avd"
fi

existing_emulator="$(adb devices | awk 'NR>1 && $1 ~ /^emulator-/ && $2=="device" {print $1; exit}')"
if [[ -n "$existing_emulator" ]]; then
  boot_completed="$(adb -s "$existing_emulator" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
  if [[ "$boot_completed" == "1" ]]; then
    info "already_running=$existing_emulator"
    printf 'device_id=%s\n' "$existing_emulator"
    exit 0
  fi
fi

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/user-chance-avd-$AVD_NAME.log"
ERR_FILE="$LOG_DIR/user-chance-avd-$AVD_NAME.err.log"
info "starting_avd=$AVD_NAME"
info "emulator_bin=$EMULATOR_BIN"
info "log_file=$LOG_FILE"

ARGS=(-avd "$AVD_NAME" -no-snapshot-save -no-metrics)
if [[ "$EMULATOR_HEADLESS" == "1" ]]; then
  ARGS+=(-no-window)
fi
if [[ "$EMULATOR_EXTRA_ARGS" != *"-idle-grpc-timeout"* ]]; then
  ARGS+=(-idle-grpc-timeout 0)
fi
if [[ -n "$EMULATOR_EXTRA_ARGS" ]]; then
  # shellcheck disable=SC2206
  EXTRA_ARGS=($EMULATOR_EXTRA_ARGS)
  ARGS+=("${EXTRA_ARGS[@]}")
fi

info "headless=$EMULATOR_HEADLESS"
info "supervisor=$EMULATOR_SUPERVISOR"
info "stability_seconds=$STABILITY_SECONDS"
info "command=$EMULATOR_BIN ${ARGS[*]}"

SUPERVISOR_USED="nohup"
if [[ "$EMULATOR_SUPERVISOR" == "auto" && "$(uname -s)" == "Darwin" && -x /bin/launchctl ]]; then
  SUPERVISOR_USED="launchctl"
elif [[ "$EMULATOR_SUPERVISOR" == "launchctl" ]]; then
  SUPERVISOR_USED="launchctl"
elif [[ "$EMULATOR_SUPERVISOR" == "nohup" ]]; then
  SUPERVISOR_USED="nohup"
fi

if [[ "$SUPERVISOR_USED" == "launchctl" ]]; then
  command -v launchctl >/dev/null 2>&1 || fail "launchctl requested but not found"
  SAFE_AVD_NAME="$(printf '%s' "$AVD_NAME" | tr -c '[:alnum:]' '-')"
  LAUNCHCTL_LABEL="com.userchance.avd.${SAFE_AVD_NAME}.$(date +%s)"
  info "launchctl_label=$LAUNCHCTL_LABEL"
  launchctl submit -l "$LAUNCHCTL_LABEL" -o "$LOG_FILE" -e "$ERR_FILE" -- "$EMULATOR_BIN" "${ARGS[@]}"
else
  nohup "$EMULATOR_BIN" "${ARGS[@]}" >"$LOG_FILE" 2>"$ERR_FILE" &
  EMULATOR_PID="$!"
  info "emulator_pid=$EMULATOR_PID"
fi
info "supervisor_used=$SUPERVISOR_USED"

deadline=$((SECONDS + TIMEOUT_SECONDS))
DEVICE_ID=""

while (( SECONDS < deadline )); do
  DEVICE_ID="$(adb devices | awk 'NR>1 && $1 ~ /^emulator-/ && $2=="device" {print $1; exit}')"
  if [[ -n "$DEVICE_ID" ]]; then
    boot_completed="$(adb -s "$DEVICE_ID" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
    if [[ "$boot_completed" == "1" ]]; then
      stable_deadline=$((SECONDS + STABILITY_SECONDS))
      while (( SECONDS < stable_deadline )); do
        if ! adb devices | awk -v device="$DEVICE_ID" 'NR>1 && $1==device && $2=="device" {found=1} END {exit !found}'; then
          fail "emulator booted but disappeared from ADB list during stability check; see $LOG_FILE"
        fi
        sleep 5
      done
      info "boot_completed=1"
      info "adb_stable=1"
      info "adb_stability_seconds=$STABILITY_SECONDS"
      info "supervisor_used=$SUPERVISOR_USED"
      if [[ "${LAUNCHCTL_LABEL:-}" != "" ]]; then
        info "launchctl_label=$LAUNCHCTL_LABEL"
      fi
      printf 'device_id=%s\n' "$DEVICE_ID"
      exit 0
    fi
  fi
  sleep 3
done

fail "AVD $AVD_NAME did not boot within ${TIMEOUT_SECONDS}s; see $LOG_FILE"

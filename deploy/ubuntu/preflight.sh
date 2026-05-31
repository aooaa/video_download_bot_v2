#!/usr/bin/env bash
set -uo pipefail

APP_DIR="${APP_DIR:-/opt/video-download-bot}"
ENV_FILE="${ENV_FILE:-/etc/video-download-bot/video-download-bot.env}"

failures=0
warnings=0

info() {
  printf '==> %s\n' "$1"
}

ok() {
  printf 'OK   %s\n' "$1"
}

warn() {
  warnings=$((warnings + 1))
  printf 'WARN %s\n' "$1"
}

fail() {
  failures=$((failures + 1))
  printf 'FAIL %s\n' "$1"
}

resolve_path() {
  local value="$1"
  if [[ -z "${value}" || "${value}" = /* ]]; then
    printf '%s\n' "${value}"
  else
    printf '%s/%s\n' "${APP_DIR}" "${value}"
  fi
}

check_command() {
  local name="$1"
  local command_path="${2:-$1}"
  local version_args="${3:---version}"

  if [[ "${command_path}" = */* ]]; then
    if [[ ! -x "${command_path}" ]]; then
      fail "${name} is not executable at ${command_path}"
      return
    fi
  elif ! command -v "${command_path}" >/dev/null 2>&1; then
    fail "${name} is not on PATH (${command_path})"
    return
  fi

  local version_output
  if version_output="$("${command_path}" ${version_args} 2>&1 | head -n 1)"; then
    ok "${name}: ${version_output}"
  else
    fail "${name} exists but '${command_path} ${version_args}' failed"
  fi
}

check_required_env() {
  local name="$1"
  local value="${!name:-}"
  if [[ -z "${value}" ]]; then
    fail "required env var ${name} is empty"
  else
    ok "required env var ${name} is set"
  fi
}

check_writable_dir() {
  local label="$1"
  local path
  path="$(resolve_path "$2")"

  if [[ -z "${path}" ]]; then
    fail "${label} path is empty"
    return
  fi
  if [[ ! -d "${path}" ]]; then
    fail "${label} directory does not exist: ${path}"
    return
  fi
  if [[ ! -w "${path}" ]]; then
    fail "${label} directory is not writable: ${path}"
    return
  fi
  ok "${label} directory is writable: ${path}"
}

check_writable_file_parent() {
  local label="$1"
  local configured="$2"
  local path
  path="$(resolve_path "${configured}")"

  if [[ -z "${path}" ]]; then
    fail "${label} path is empty"
    return
  fi
  local parent
  parent="$(dirname "${path}")"
  if [[ ! -d "${parent}" ]]; then
    fail "${label} parent directory does not exist: ${parent}"
    return
  fi
  if [[ ! -w "${parent}" ]]; then
    fail "${label} parent directory is not writable: ${parent}"
    return
  fi
  if [[ -e "${path}" && ! -w "${path}" ]]; then
    fail "${label} file exists but is not writable: ${path}"
    return
  fi
  ok "${label} path is writable: ${path}"
}

telethon_session_file() {
  local session_name="$1"
  if [[ "${session_name}" == *.session ]]; then
    printf '%s\n' "${session_name}"
  else
    printf '%s.session\n' "${session_name}"
  fi
}

check_cookie_file() {
  local env_name="$1"
  local value="${!env_name:-}"
  local path

  if [[ -z "${value}" ]]; then
    ok "${env_name} is not configured"
    return
  fi

  path="$(resolve_path "${value}")"
  if [[ ! -e "${path}" ]]; then
    warn "${env_name} points to a missing optional cookie file: ${path}"
    return
  fi
  if [[ ! -f "${path}" ]]; then
    fail "${env_name} is not a regular file: ${path}"
    return
  fi
  if [[ ! -r "${path}" ]]; then
    fail "${env_name} is not readable: ${path}"
    return
  fi
  if [[ ! -s "${path}" ]]; then
    warn "${env_name} exists but is empty: ${path}"
    return
  fi
  ok "${env_name} is readable: ${path}"
}

check_rclone_remotes() {
  local rclone_command="${RCLONE_PATH:-rclone}"
  if [[ "${rclone_command}" = */* ]]; then
    [[ -x "${rclone_command}" ]] || return
  elif ! command -v "${rclone_command}" >/dev/null 2>&1; then
    return
  fi

  local remotes
  if ! remotes="$("${rclone_command}" listremotes 2>&1)"; then
    warn "rclone could not list remotes for this user: ${remotes}"
    return
  fi
  if [[ -z "${remotes}" ]]; then
    warn "rclone has no configured remotes for this user"
    return
  fi
  ok "rclone remotes are visible to this user"
}

info "Loading deployment settings"
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
  ok "environment file loaded: ${ENV_FILE}"
else
  fail "environment file not found: ${ENV_FILE}"
fi

PYTHON_BIN="${PYTHON_BIN:-${APP_DIR}/.venv/bin/python}"

info "Checking application layout"
if [[ -d "${APP_DIR}" ]]; then
  ok "APP_DIR exists: ${APP_DIR}"
else
  fail "APP_DIR does not exist: ${APP_DIR}"
fi

if [[ -f "${APP_DIR}/main.py" ]]; then
  ok "main.py exists"
else
  fail "main.py not found under APP_DIR"
fi

info "Checking Python"
if [[ -x "${PYTHON_BIN}" ]]; then
  if "${PYTHON_BIN}" - <<'PY'
import sys

if sys.version_info < (3, 12):
    raise SystemExit(1)
print(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
PY
  then
    ok "Python version is 3.12 or newer"
  else
    fail "Python 3.12 or newer is required at ${PYTHON_BIN}"
  fi
else
  fail "Python interpreter is not executable: ${PYTHON_BIN}"
fi

info "Checking OS tools"
check_command "ffmpeg" "ffmpeg" "-version"
check_command "ffprobe" "ffprobe" "-version"
check_command "Node.js" "${YOUTUBE_NODE_PATH:-node}" "--version"
check_command "rclone" "${RCLONE_PATH:-rclone}" "version"
check_rclone_remotes

info "Checking required environment variables"
check_required_env "BOT_TOKEN"
check_required_env "TELEGRAM_API_ID"
check_required_env "TELEGRAM_API_HASH"

if [[ -n "${TELEGRAM_API_ID:-}" && ! "${TELEGRAM_API_ID}" =~ ^[0-9]+$ ]]; then
  fail "TELEGRAM_API_ID must be numeric"
fi

info "Checking writable runtime paths"
check_writable_dir "download" "${DOWNLOAD_DIR:-downloads}"
check_writable_file_parent "Telethon session" "$(telethon_session_file "${TELETHON_SESSION:-session_download_bot}")"
check_writable_file_parent "bot settings database" "${BOT_SETTINGS_DB:-bot_settings.db}"

info "Checking optional cookie files"
check_cookie_file "YOUTUBE_COOKIE_FILE"
check_cookie_file "DOUYIN_COOKIE_FILE"
check_cookie_file "TIKTOK_COOKIE_FILE"

printf '\n'
if [[ "${failures}" -gt 0 ]]; then
  printf 'Preflight failed: %d failure(s), %d warning(s).\n' "${failures}" "${warnings}"
  exit 1
fi

printf 'Preflight passed: 0 failure(s), %d warning(s).\n' "${warnings}"
exit 0

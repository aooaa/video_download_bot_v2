#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/video-download-bot}"
ENV_FILE="${ENV_FILE:-/etc/video-download-bot/video-download-bot.env}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

cd "${APP_DIR}"
exec "${APP_DIR}/.venv/bin/python" "${APP_DIR}/main.py"

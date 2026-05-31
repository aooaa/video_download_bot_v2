#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/video-download-bot}"
APP_USER="${APP_USER:-video-bot}"
SERVICE_NAME="${SERVICE_NAME:-video-download-bot}"
ENV_DIR="${ENV_DIR:-/etc/video-download-bot}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run this installer with sudo/root privileges."
  exit 1
fi

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "Installing OS packages..."
apt-get update
apt-get install -y \
  ca-certificates \
  ffmpeg \
  nodejs \
  npm \
  python3 \
  python3-venv \
  rclone \
  rsync

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi

"${PYTHON_BIN}" - <<'PY'
import sys

if sys.version_info < (3, 12):
    raise SystemExit("Python 3.12 or newer is required.")
PY

if ! id "${APP_USER}" >/dev/null 2>&1; then
  echo "Creating service user ${APP_USER}..."
  useradd --system --create-home --shell /usr/sbin/nologin "${APP_USER}"
fi

echo "Creating application directories..."
mkdir -p "${APP_DIR}" "${ENV_DIR}" "${APP_DIR}/downloads" "${APP_DIR}/logs"

echo "Copying project files to ${APP_DIR}..."
rsync -a \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '.uv-cache/' \
  --exclude '.uv-python/' \
  --exclude '.pytest_cache/' \
  --exclude '.pytest_tmp/' \
  --exclude '__pycache__/' \
  --exclude 'downloads/' \
  --exclude 'logs/' \
  --exclude '*.db' \
  --exclude '*.sqlite' \
  --exclude '*.sqlite3' \
  --exclude '*.session' \
  --exclude '*.session-journal' \
  --exclude 'config.py' \
  --exclude '*_cookies.txt' \
  "${SOURCE_DIR}/" "${APP_DIR}/"

if [[ ! -f "${ENV_DIR}/${SERVICE_NAME}.env" ]]; then
  cp "${SOURCE_DIR}/deploy/ubuntu/${SERVICE_NAME}.env.example" "${ENV_DIR}/${SERVICE_NAME}.env"
  chmod 600 "${ENV_DIR}/${SERVICE_NAME}.env"
fi

if [[ ! -f "${APP_DIR}/config.py" ]]; then
  cp "${SOURCE_DIR}/deploy/ubuntu/config.py.example" "${APP_DIR}/config.py"
fi
chmod +x "${APP_DIR}/deploy/ubuntu/run.sh" "${APP_DIR}/deploy/ubuntu/preflight.sh"

echo "Installing Python dependencies..."
"${PYTHON_BIN}" -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip
"${APP_DIR}/.venv/bin/python" -m pip install -r "${APP_DIR}/requirements.txt"

echo "Installing systemd service..."
sed \
  -e "s#User=video-bot#User=${APP_USER}#" \
  -e "s#Group=video-bot#Group=${APP_USER}#" \
  -e "s#WorkingDirectory=/opt/video-download-bot#WorkingDirectory=${APP_DIR}#" \
  -e "s#EnvironmentFile=-/etc/video-download-bot/video-download-bot.env#EnvironmentFile=-${ENV_DIR}/${SERVICE_NAME}.env#" \
  -e "s#Environment=APP_DIR=/opt/video-download-bot#Environment=APP_DIR=${APP_DIR}#" \
  -e "s#Environment=ENV_FILE=/etc/video-download-bot/video-download-bot.env#Environment=ENV_FILE=${ENV_DIR}/${SERVICE_NAME}.env#" \
  -e "s#ExecStart=/opt/video-download-bot/deploy/ubuntu/run.sh#ExecStart=${APP_DIR}/deploy/ubuntu/run.sh#" \
  "${SOURCE_DIR}/deploy/ubuntu/${SERVICE_NAME}.service" > "/etc/systemd/system/${SERVICE_NAME}.service"
chmod 644 "/etc/systemd/system/${SERVICE_NAME}.service"

chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}" "${ENV_DIR}"

systemctl daemon-reload

echo "Install complete."
echo "Next steps:"
echo "  1. Edit ${ENV_DIR}/${SERVICE_NAME}.env"
echo "  2. Configure rclone as ${APP_USER}: sudo -u ${APP_USER} rclone config"
echo "  3. Run preflight: sudo -u ${APP_USER} ${APP_DIR}/deploy/ubuntu/preflight.sh"
echo "  4. Start: systemctl enable --now ${SERVICE_NAME}"

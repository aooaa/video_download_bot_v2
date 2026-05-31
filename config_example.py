from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv()


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int | None = None) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        if default is None:
            raise RuntimeError(f"Missing required environment variable: {name}")
        return default
    return int(value)


def _list_env(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


# Telegram Bot API token.
TOKEN = _env("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Telegram client API values from https://my.telegram.org.
api_id = _int_env("TELEGRAM_API_ID", 123456)
api_hash = _env("TELEGRAM_API_HASH", "YOUR_API_HASH_HERE")

# Optional target used by Telethon for files larger than the Bot API limit.
# Keep this as a username if your existing workflow sends large files through a bot/chat username.
username = os.getenv("TELEGRAM_LARGE_FILE_TARGET") or None
TELETHON_SESSION = os.getenv("TELETHON_SESSION", "test_session_download_bot")

# Telegram proxy is automatic:
# - Windows: uses v2rayN mixed port at 127.0.0.1:10808 by default
# - Linux/macOS: connects directly by default
# Optional environment overrides:
# TELEGRAM_PROXY=auto|on|off
# TELEGRAM_PROXY_URL=socks5://127.0.0.1:10808
# TELEGRAM_PROXY_HOST=127.0.0.1
# TELEGRAM_PROXY_PORT=10808

# Download service.
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
CLEANUP_DOWNLOADS = _bool_env("CLEANUP_DOWNLOADS", True)
DOWNLOAD_BACKENDS = {
    "youtube": os.getenv("YOUTUBE_BACKEND", "ytdlp"),
    "douyin": os.getenv("DOUYIN_BACKEND", "f2"),
    "tiktok": os.getenv("TIKTOK_BACKEND", "f2"),
}

# YouTube: export browser cookies here when yt-dlp reports sign-in, bot checks, or anti-abuse errors.
YOUTUBE_COOKIE_FILE = os.getenv("YOUTUBE_COOKIE_FILE", "youtube_cookies.txt")
# YouTube's current signature challenges need a supported JavaScript runtime.
# Leave None to auto-detect node.exe from PATH, or set an absolute path.
YOUTUBE_NODE_PATH = os.getenv("YOUTUBE_NODE_PATH") or None
# Keep yt-dlp-ejs installed. This fallback lets yt-dlp fetch the EJS solver
# from npm if the local package is missing or stale.
YOUTUBE_REMOTE_COMPONENTS = _list_env("YOUTUBE_REMOTE_COMPONENTS", ["ejs:npm"])

# rclone integration for OneDrive / Google Drive.
RCLONE_PATH = os.getenv("RCLONE_PATH", "rclone")
BOT_SETTINGS_DB = os.getenv("BOT_SETTINGS_DB", "bot_settings.db")

# Douyin cookie and user-agent for F2 backend.
# Export cookies from a logged-in browser session, then save them to this file.
# F2 ships with Bark notifications enabled in its own config. Keep this False
# unless you have configured a valid Bark key and want F2 download notifications.
DOUYIN_ENABLE_BARK = _bool_env("DOUYIN_ENABLE_BARK", False)
DOUYIN_COOKIE_FILE = os.getenv("DOUYIN_COOKIE_FILE", "douyin_cookies.txt")
user_agent = os.getenv(
    "USER_AGENT",
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0"
    ),
)

HEADERS = {
    "user-agent": user_agent,
}

kwargs = {
    "mode": "one",
    "naming": "{create}_{desc}",
    "interval": "all",
    "folderize": False,
    "headers": {
        "User-Agent": user_agent,
        "Referer": "https://www.douyin.com/",
    },
    "proxies": {"http://": None, "https://": None},
}

# TikTok F2 backend. TikTok usually needs a valid browser cookie.
# Export cookies from a logged-in browser session if F2 reports auth, token,
# or region/rate-limit errors, then save them to this file.
TIKTOK_ENABLE_BARK = _bool_env("TIKTOK_ENABLE_BARK", False)
TIKTOK_COOKIE_FILE = os.getenv("TIKTOK_COOKIE_FILE", "tiktok_cookies.txt")
TIKTOK_PROXIES = {"http://": None, "https://": None}
TIKTOK_KWARGS = {
    "mode": "one",
    "naming": "{create}_{desc}",
    "interval": "all",
    "folderize": False,
    "music": False,
    "cover": False,
    "desc": False,
    "proxies": TIKTOK_PROXIES,
}

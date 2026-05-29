# Telegram Bot API token.
TOKEN = "YOUR_BOT_TOKEN_HERE"

# Telegram client API values from https://my.telegram.org.
api_id = 123456
api_hash = "YOUR_API_HASH_HERE"

# Optional target used by Telethon for files larger than the Bot API limit.
# Keep this as a username if your existing workflow sends large files through a bot/chat username.
username = "YOUR_LARGE_FILE_TARGET_USERNAME"
TELETHON_SESSION = "test_session_download_bot"

# Telegram proxy is automatic:
# - Windows: uses v2rayN mixed port at 127.0.0.1:10808 by default
# - Linux/macOS: connects directly by default
# Optional environment overrides:
# TELEGRAM_PROXY=auto|on|off
# TELEGRAM_PROXY_URL=socks5://127.0.0.1:10808
# TELEGRAM_PROXY_HOST=127.0.0.1
# TELEGRAM_PROXY_PORT=10808

# Download service.
DOWNLOAD_DIR = "downloads"
CLEANUP_DOWNLOADS = True
DOWNLOAD_BACKENDS = {
    "youtube": "ytdlp",
    "douyin": "f2",
    "tiktok": "f2",
}

# YouTube: export browser cookies here when yt-dlp reports sign-in, bot checks, or anti-abuse errors.
YOUTUBE_COOKIE_FILE = "youtube_cookies.txt"
# YouTube's current signature challenges need a supported JavaScript runtime.
# Leave None to auto-detect node.exe from PATH, or set an absolute path.
YOUTUBE_NODE_PATH = None
# Keep yt-dlp-ejs installed. This fallback lets yt-dlp fetch the EJS solver
# from npm if the local package is missing or stale.
YOUTUBE_REMOTE_COMPONENTS = ["ejs:npm"]

# rclone integration for OneDrive / Google Drive.
RCLONE_PATH = "rclone"
BOT_SETTINGS_DB = "bot_settings.db"

# Douyin cookie and user-agent for F2 backend.
# F2 ships with Bark notifications enabled in its own config. Keep this False
# unless you have configured a valid Bark key and want F2 download notifications.
DOUYIN_ENABLE_BARK = False
cookie_value = "YOUR_DOUYIN_COOKIE_HERE"
user_agent = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0"
)

HEADERS = {
    "cookie": cookie_value,
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
    "cookie": cookie_value,
    "proxies": {"http://": None, "https://": None},
}

# TikTok F2 backend. TikTok usually needs a valid browser cookie.
# Export cookies from a logged-in browser session if F2 reports auth, token,
# or region/rate-limit errors, then save them to this file.
TIKTOK_ENABLE_BARK = False
TIKTOK_COOKIE_FILE = "tiktok_cookies.txt"
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

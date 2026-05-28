# Replace with your own telegram bot token.
TOKEN = 'xxxxxxx'
api_id = 123456
api_hash = "YOUR_API_HASH_HERE"

# Telegram proxy is automatic:
# - Windows: uses v2rayN mixed port at 127.0.0.1:10808 by default
# - Linux/macOS: connects directly by default
# Optional overrides:
# TELEGRAM_PROXY=auto|on|off
# TELEGRAM_PROXY_URL=socks5://127.0.0.1:10808
# TELEGRAM_PROXY_HOST=127.0.0.1
# TELEGRAM_PROXY_PORT=10808

# Set your Douyin cookie
cookie_value = "YOUR_COOKIE_HERE"

# Set user-agent
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0"

HEADERS = {
        'cookie' : cookie_value,
        'user-agent' : user_agent,
}

kwargs = {
    "headers": {
        "User-Agent": user_agent,
        "Referer": "https://www.douyin.com/",
    },
    "cookie": cookie_value,
    "proxies": {"http://": None, "https://": None},
}

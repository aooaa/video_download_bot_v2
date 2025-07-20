# Replace with your own telegram bot token.
TOKEN = 'xxxxxxx'

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
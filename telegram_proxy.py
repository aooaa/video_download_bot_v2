import os
import platform
from urllib.parse import urlparse

from telebot import asyncio_helper


DEFAULT_PROXY_HOST = "127.0.0.1"
DEFAULT_PROXY_PORT = 10808
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off", "none", "direct", "disable", "disabled"}


def _env(name, default=None):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _proxy_enabled():
    mode = _env("TELEGRAM_PROXY", _env("TG_PROXY", "auto")).lower()
    if mode in FALSE_VALUES:
        return False
    if mode in TRUE_VALUES:
        return True
    if "://" in mode:
        return True
    return platform.system().lower() == "windows"


def _proxy_url(default_scheme="http"):
    configured = _env("TELEGRAM_PROXY_URL", _env("TG_PROXY_URL"))
    mode = _env("TELEGRAM_PROXY", _env("TG_PROXY", "auto"))
    if configured:
        return configured
    if "://" in mode:
        return mode

    host = _env("TELEGRAM_PROXY_HOST", _env("TG_PROXY_HOST", DEFAULT_PROXY_HOST))
    port = int(_env("TELEGRAM_PROXY_PORT", _env("TG_PROXY_PORT", DEFAULT_PROXY_PORT)))
    return f"{default_scheme}://{host}:{port}"


def get_telethon_proxy():
    """Return a Telethon-compatible proxy tuple, or None for direct connect."""
    if not _proxy_enabled():
        return None

    try:
        import socks
    except ImportError as exc:
        raise RuntimeError(
            "Telegram proxy is enabled, but PySocks is not installed. "
            "Run `uv add pysocks` or `uv pip install pysocks`."
        ) from exc

    parsed = urlparse(_proxy_url("socks5"))
    scheme = parsed.scheme.lower()
    if scheme in {"socks5", "socks5h"}:
        proxy_type = socks.SOCKS5
    elif scheme in {"socks4", "socks4a"}:
        proxy_type = socks.SOCKS4
    elif scheme in {"http", "https"}:
        proxy_type = socks.HTTP
    else:
        raise ValueError(f"Unsupported Telegram proxy scheme: {parsed.scheme}")

    return (
        proxy_type,
        parsed.hostname or DEFAULT_PROXY_HOST,
        parsed.port or DEFAULT_PROXY_PORT,
        True,
        parsed.username,
        parsed.password,
    )


def configure_bot_api_proxy():
    """Configure pyTelegramBotAPI async Bot API proxy and return its proxy URL."""
    if not _proxy_enabled():
        asyncio_helper.proxy = None
        return None

    proxy_url = _proxy_url("http")
    parsed = urlparse(proxy_url)
    if parsed.scheme.lower().startswith("socks"):
        host = parsed.hostname or DEFAULT_PROXY_HOST
        port = parsed.port or DEFAULT_PROXY_PORT
        proxy_url = f"http://{host}:{port}"

    asyncio_helper.proxy = proxy_url
    return proxy_url


def describe_telegram_proxy():
    if not _proxy_enabled():
        return "direct"
    return _proxy_url("http")

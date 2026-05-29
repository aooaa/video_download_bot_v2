from __future__ import annotations

import re


URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)
YOUTUBE_RE = re.compile(
    r"(https?://)?(www\.)?(youtube|youtu)\.(com|cn|com\.cn|be)/\S+",
    re.IGNORECASE,
)
DOUYIN_RE = re.compile(r"(douyin\.com|iesdouyin\.com|v\.douyin\.com)", re.IGNORECASE)
TIKTOK_RE = re.compile(r"(tiktok\.com|vt\.tiktok\.com|vm\.tiktok\.com)", re.IGNORECASE)


def extract_first_url(text: str) -> str | None:
    match = URL_RE.search(text or "")
    return match.group(0) if match else None


def detect_platform(text_or_url: str) -> str | None:
    url = extract_first_url(text_or_url) or text_or_url
    if not url:
        return None
    if YOUTUBE_RE.search(url):
        return "youtube"
    if DOUYIN_RE.search(url):
        return "douyin"
    if TIKTOK_RE.search(url):
        return "tiktok"
    return None

from __future__ import annotations

import re
import os
import platform
import tempfile
import asyncio
import contextlib
import io
from pathlib import Path
from typing import Any

from downloaders.base import DownloadContext, DownloadResult, MediaFile


TIKTOK_VIDEO_ID_RE = re.compile(r"/video/(\d+)", re.IGNORECASE)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".wav"}
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
DEFAULT_REFERER = "https://www.tiktok.com/"
DEFAULT_PROXY_HOST = "127.0.0.1"
DEFAULT_PROXY_PORT = 10808
FALSE_VALUES = {"0", "false", "no", "off", "none", "direct", "disable", "disabled"}


class TiktokF2Downloader:
    platform = "tiktok"
    backend_name = "f2"

    async def download(self, url: str, context: DownloadContext) -> DownloadResult:
        result = DownloadResult(platform=self.platform, backend=self.backend_name, url=url)
        result.add_progress("TikTok link detected.")

        try:
            kwargs = self._build_kwargs(context, url)
            if not kwargs.get("cookie"):
                result.error = (
                    "TikTok download requires cookies. Export cookies from a logged-in "
                    "TikTok browser session and save them to tiktok_cookies.txt, or configure "
                    "TIKTOK_COOKIE_FILE."
                )
                return result

            TiktokHandler, TiktokDownloader, AwemeIdFetcher, format_file_name = self._load_f2(kwargs)
            aweme_id = self._extract_aweme_id(url) or await AwemeIdFetcher.get_aweme_id(url)
            if not aweme_id:
                result.error = "Could not resolve TikTok aweme_id from the URL."
                return result

            result.add_progress(f"TikTok aweme_id resolved: {aweme_id}")
            handler = TiktokHandler(kwargs)
            handler.enable_bark = bool(getattr(context.config, "TIKTOK_ENABLE_BARK", False))
            video = await handler.fetch_one_video(aweme_id)
            if not video:
                result.error = f"Could not fetch TikTok metadata for aweme_id {aweme_id}."
                return result

            aweme_data = video._to_dict()
            result.title = aweme_data.get("desc") or f"tiktok_{aweme_id}"
            result.raw = {
                "aweme_id": aweme_id,
                "backend": self.backend_name,
                "uniqueId": aweme_data.get("uniqueId"),
            }

            before = self._snapshot(context.output_dir)
            downloader = TiktokDownloader(kwargs)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                await downloader.create_download_tasks(
                    kwargs,
                    aweme_datas=aweme_data,
                    user_path=context.output_dir,
                )
            files = self._new_files(context.output_dir, before)
            if not files:
                files = self._existing_files_for_aweme(
                    context.output_dir,
                    aweme_data,
                    kwargs,
                    format_file_name,
                )
            if not files:
                result.add_progress("F2 produced no file; trying yt-dlp fallback.")
                files = await self._download_with_ytdlp_fallback(url, context, before, kwargs)
            result.files.extend(self._to_media_files(files, result.title))

            if not result.files:
                result.error = (
                    "TikTok download completed but no media file was found. "
                    "TikTok may have blocked the CDN download; refresh tiktok_cookies.txt "
                    "or check the TikTok proxy."
                )
                return result

            result.add_progress("TikTok post downloaded.")
            return result
        except Exception as exc:
            result.error = f"TikTok download failed: {self._format_error(exc)}"
            return result

    def _load_f2(self, kwargs: dict) -> tuple[Any, Any, Any, Any]:
        import f2

        self._prepare_f2_config_file(f2, kwargs)
        from f2.apps.tiktok import utils as tiktok_utils

        self._configure_f2_client(tiktok_utils, kwargs)
        from f2.apps.tiktok.dl import TiktokDownloader
        from f2.apps.tiktok.handler import TiktokHandler
        from f2.apps.tiktok.utils import AwemeIdFetcher, format_file_name

        return TiktokHandler, TiktokDownloader, AwemeIdFetcher, format_file_name

    def _extract_aweme_id(self, url: str) -> str | None:
        match = TIKTOK_VIDEO_ID_RE.search(url)
        return match.group(1) if match else None

    def _build_kwargs(self, context: DownloadContext, url: str) -> dict:
        kwargs = dict(getattr(context.config, "TIKTOK_KWARGS", {}) or {})
        kwargs.setdefault("mode", "one")
        kwargs.setdefault("naming", "{create}_{desc}")
        kwargs.setdefault("interval", "all")
        kwargs.setdefault("folderize", False)
        kwargs.setdefault("music", False)
        kwargs.setdefault("cover", False)
        kwargs.setdefault("desc", False)
        kwargs.setdefault("url", url)
        proxies = kwargs.get("proxies", getattr(context.config, "TIKTOK_PROXIES", None))
        kwargs["proxies"] = self._normalize_proxies(proxies, context.config)

        headers = kwargs.get("headers") or {}
        if not isinstance(headers, dict):
            headers = {}
        headers.setdefault("User-Agent", getattr(context.config, "TIKTOK_USER_AGENT", DEFAULT_USER_AGENT))
        headers.setdefault("Referer", getattr(context.config, "TIKTOK_REFERER", DEFAULT_REFERER))
        kwargs["headers"] = headers
        kwargs["_f2_config_path"] = getattr(
            context.config,
            "TIKTOK_F2_CONFIG_FILE",
            str(Path(tempfile.gettempdir()) / "video_download_bot_f2_tiktok_conf.yaml"),
        )

        cookie = self._read_cookie_file(context)
        if cookie:
            kwargs["cookie"] = cookie
        else:
            legacy_cookie = getattr(context.config, "TIKTOK_COOKIE", None)
            if legacy_cookie is not None:
                kwargs["cookie"] = legacy_cookie
            else:
                kwargs.setdefault("cookie", None)

        return kwargs

    def _normalize_proxies(self, proxies: Any, config) -> dict:
        if isinstance(proxies, dict) and any(proxies.get(key) for key in ("http://", "https://")):
            return proxies

        proxy_url = getattr(config, "TIKTOK_PROXY_URL", None) or os.getenv("TIKTOK_PROXY_URL")
        if not proxy_url and self._should_use_telegram_proxy(config):
            proxy_url = (
                os.getenv("TELEGRAM_PROXY_URL")
                or os.getenv("TG_PROXY_URL")
                or self._proxy_url_from_parts()
            )

        if proxy_url:
            return {"http://": proxy_url, "https://": proxy_url}
        return {"http://": None, "https://": None}

    def _should_use_telegram_proxy(self, config) -> bool:
        configured = getattr(config, "TIKTOK_USE_TELEGRAM_PROXY", None)
        if configured is not None:
            return bool(configured)

        mode = (os.getenv("TELEGRAM_PROXY") or os.getenv("TG_PROXY") or "auto").strip().lower()
        if mode in FALSE_VALUES:
            return False
        if "://" in mode:
            return True
        return platform.system().lower() == "windows"

    def _proxy_url_from_parts(self) -> str:
        host = os.getenv("TELEGRAM_PROXY_HOST") or os.getenv("TG_PROXY_HOST") or DEFAULT_PROXY_HOST
        port = os.getenv("TELEGRAM_PROXY_PORT") or os.getenv("TG_PROXY_PORT") or str(DEFAULT_PROXY_PORT)
        return f"http://{host}:{port}"

    def _configure_f2_client(self, tiktok_utils, kwargs: dict) -> None:
        proxies = {
            key: value or ""
            for key, value in kwargs.get("proxies", {}).items()
        }
        headers = kwargs.get("headers", {})

        client_conf = dict(tiktok_utils.ClientConfManager.client())
        client_conf["proxies"] = proxies
        client_conf["headers"] = {
            **dict(client_conf.get("headers", {})),
            **headers,
        }
        tiktok_utils.ClientConfManager.tiktok_conf = client_conf

        tiktok_utils.TokenManager.proxies = proxies
        tiktok_utils.TokenManager.user_agent = headers.get("User-Agent", DEFAULT_USER_AGENT)
        tiktok_utils.TokenManager.mstoken_headers = {
            **dict(getattr(tiktok_utils.TokenManager, "mstoken_headers", {})),
            "User-Agent": tiktok_utils.TokenManager.user_agent,
        }
        tiktok_utils.TokenManager.ttwid_headers = {
            **dict(getattr(tiktok_utils.TokenManager, "ttwid_headers", {})),
            "User-Agent": tiktok_utils.TokenManager.user_agent,
        }
        tiktok_utils.TokenManager.odin_tt_headers = {
            **dict(getattr(tiktok_utils.TokenManager, "odin_tt_headers", {})),
            "Referer": headers.get("Referer", DEFAULT_REFERER),
            "User-Agent": tiktok_utils.TokenManager.user_agent,
        }

    def _prepare_f2_config_file(self, f2_module, kwargs: dict) -> None:
        import yaml
        from f2.utils.utils import get_resource_path

        source_path = Path(f2_module.F2_CONFIG_FILE_PATH)
        if not source_path.exists():
            source_path = Path(get_resource_path(str(source_path)))
        target_path = Path(kwargs["_f2_config_path"])
        data = yaml.safe_load(source_path.read_text(encoding="utf-8")) or {}

        f2_conf = data.setdefault("f2", {})
        tiktok_conf = f2_conf.setdefault("tiktok", {})
        tiktok_conf["headers"] = {
            **dict(tiktok_conf.get("headers", {})),
            **kwargs.get("headers", {}),
        }
        tiktok_conf["proxies"] = {
            key: value or ""
            for key, value in kwargs.get("proxies", {}).items()
        }

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        f2_module.F2_CONFIG_FILE_PATH = str(target_path)

    def _read_cookie_file(self, context: DownloadContext) -> str | None:
        cookie_file = getattr(context.config, "TIKTOK_COOKIE_FILE", "tiktok_cookies.txt")
        if not cookie_file:
            return None

        cookie_path = Path(cookie_file)
        if not cookie_path.exists():
            return None

        cookie = cookie_path.read_text(encoding="utf-8").strip()
        return self._normalize_cookie_text(cookie)

    def _normalize_cookie_text(self, cookie: str) -> str | None:
        if not cookie:
            return None
        if cookie.startswith("# Netscape HTTP Cookie File") or "\t" in cookie:
            pairs = []
            for line in cookie.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 7:
                    name = parts[5].strip()
                    value = parts[6].strip()
                    if name:
                        pairs.append(f"{name}={value}")
            return "; ".join(pairs) or None
        return " ".join(cookie.splitlines()).strip() or None

    def _format_error(self, exc: Exception) -> str:
        message = str(exc)
        if "Illegal header value" in message and "Netscape HTTP Cookie File" in message:
            return (
                "Invalid TikTok cookie header. The Netscape cookie file was not accepted by F2; "
                "please refresh tiktok_cookies.txt if the problem continues."
            )
        return message

    def _snapshot(self, root: Path) -> set[Path]:
        if not root.exists():
            return set()
        return {path.resolve() for path in root.rglob("*") if path.is_file()}

    def _new_files(self, root: Path, before: set[Path]) -> list[Path]:
        if not root.exists():
            return []
        after = [path.resolve() for path in root.rglob("*") if path.is_file()]
        return sorted((path for path in after if path not in before), key=lambda item: item.stat().st_mtime)

    def _existing_files_for_aweme(self, root: Path, aweme_data: dict, kwargs: dict, format_file_name) -> list[Path]:
        if not root.exists():
            return []

        base_name = format_file_name(kwargs.get("naming", "{create}_{desc}"), aweme_data)
        media_extensions = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | {".txt"}
        candidates = [
            path.resolve()
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in media_extensions
            and (path.stem.startswith(f"{base_name}_") or path.parent.name == base_name)
        ]
        return sorted(candidates, key=lambda item: item.stat().st_mtime)

    def _to_media_files(self, files: list[Path], title: str | None) -> list[MediaFile]:
        media_files: list[MediaFile] = []
        for path in files:
            suffix = path.suffix.lower()
            if suffix in IMAGE_EXTENSIONS:
                media_type = "photo"
            elif suffix in VIDEO_EXTENSIONS:
                media_type = "video"
            else:
                media_type = "document"
            media_files.append(MediaFile(path=path, media_type=media_type, caption=title))
        return media_files

    async def _download_with_ytdlp_fallback(
        self,
        url: str,
        context: DownloadContext,
        before: set[Path],
        kwargs: dict,
    ) -> list[Path]:
        try:
            fallback_files = await asyncio.to_thread(self._download_with_ytdlp_sync, url, context, kwargs)
        except Exception:
            return []
        return self._new_files(context.output_dir, before) or fallback_files

    def _download_with_ytdlp_sync(self, url: str, context: DownloadContext, kwargs: dict) -> list[Path]:
        import yt_dlp

        proxy = kwargs.get("proxies", {}).get("http://") or kwargs.get("proxies", {}).get("https://")
        cookie_file = getattr(context.config, "TIKTOK_COOKIE_FILE", "tiktok_cookies.txt")
        ydl_opts = {
            "outtmpl": str(context.output_dir / "%(title).80s_%(id)s.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "merge_output_format": "mp4",
        }
        if proxy:
            ydl_opts["proxy"] = proxy
        if cookie_file and Path(cookie_file).exists():
            ydl_opts["cookiefile"] = str(cookie_file)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            candidates = []
            for item in info.get("requested_downloads") or []:
                filepath = item.get("filepath") or item.get("_filename")
                if filepath:
                    candidates.append(Path(filepath))
            candidates.append(Path(ydl.prepare_filename(info)))

        resolved = []
        seen = set()
        for path in candidates:
            if not path.exists():
                continue
            resolved_path = path.resolve()
            if resolved_path not in seen:
                seen.add(resolved_path)
                resolved.append(resolved_path)
        return resolved

from __future__ import annotations

from pathlib import Path

from .base import DownloadContext, DownloadResult, DownloadTarget
from .backends.douyin_f2 import DouyinF2Downloader
from .backends.ytdlp_backend import YoutubeYtDlpDownloader
from .registry import DownloaderRegistry
from .router import detect_platform, extract_first_url


DEFAULT_BACKENDS = {"youtube": "ytdlp", "douyin": "f2"}


def create_default_registry() -> DownloaderRegistry:
    registry = DownloaderRegistry()
    registry.register("youtube", "ytdlp", YoutubeYtDlpDownloader)
    registry.register("douyin", "f2", DouyinF2Downloader)
    return registry


class DownloadService:
    def __init__(self, config, registry: DownloaderRegistry | None = None) -> None:
        self.config = config
        self.registry = registry or create_default_registry()
        self.backends = {
            **DEFAULT_BACKENDS,
            **getattr(config, "DOWNLOAD_BACKENDS", {}),
        }
        self.output_dir = Path(getattr(config, "DOWNLOAD_DIR", "downloads"))

    async def download(
        self,
        text_or_url: str,
        target: DownloadTarget | None = None,
    ) -> DownloadResult:
        url = extract_first_url(text_or_url) or text_or_url.strip()
        platform = detect_platform(url)
        if not platform:
            return DownloadResult(
                platform="unknown",
                backend="none",
                url=url,
                error="Unsupported URL. Currently supported: YouTube and Douyin.",
            )

        backend_name = self.backends.get(platform)
        if not backend_name:
            return DownloadResult(
                platform=platform,
                backend="none",
                url=url,
                error=f"No backend configured for platform: {platform}",
            )

        try:
            downloader = self.registry.get(platform, backend_name)
        except ValueError as exc:
            return DownloadResult(platform=platform, backend=backend_name, url=url, error=str(exc))

        self.output_dir.mkdir(parents=True, exist_ok=True)
        context = DownloadContext(
            output_dir=self.output_dir,
            config=self.config,
            target=target or DownloadTarget(),
        )
        return await downloader.download(url, context)

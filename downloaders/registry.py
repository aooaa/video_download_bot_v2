from __future__ import annotations

from collections.abc import Callable

from .base import PlatformDownloader


DownloaderFactory = Callable[[], PlatformDownloader]


class DownloaderRegistry:
    def __init__(self) -> None:
        self._factories: dict[tuple[str, str], DownloaderFactory] = {}

    def register(self, platform: str, backend_name: str, factory: DownloaderFactory) -> None:
        self._factories[(platform, backend_name)] = factory

    def get(self, platform: str, backend_name: str) -> PlatformDownloader:
        try:
            return self._factories[(platform, backend_name)]()
        except KeyError as exc:
            available = sorted(
                backend for item_platform, backend in self._factories if item_platform == platform
            )
            suffix = f" Available backends: {', '.join(available)}." if available else ""
            raise ValueError(
                f"No downloader backend configured for {platform!r}/{backend_name!r}.{suffix}"
            ) from exc

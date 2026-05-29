from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(slots=True)
class DownloadTarget:
    mode: str = "telegram"
    provider: str | None = None


@dataclass(slots=True)
class DownloadContext:
    output_dir: Path
    config: Any
    target: DownloadTarget = field(default_factory=DownloadTarget)


@dataclass(slots=True)
class MediaFile:
    path: Path
    media_type: str
    caption: str | None = None
    source: str | None = None


@dataclass(slots=True)
class DownloadResult:
    platform: str
    backend: str
    url: str
    title: str | None = None
    files: list[MediaFile] = field(default_factory=list)
    progress: list[str] = field(default_factory=list)
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.files)

    def add_progress(self, message: str) -> None:
        self.progress.append(message)


class PlatformDownloader(Protocol):
    platform: str
    backend_name: str

    async def download(self, url: str, context: DownloadContext) -> DownloadResult:
        ...

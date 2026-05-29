from .base import DownloadContext, DownloadResult, DownloadTarget, MediaFile, PlatformDownloader

__all__ = [
    "DownloadContext",
    "DownloadResult",
    "DownloadService",
    "DownloadTarget",
    "MediaFile",
    "PlatformDownloader",
]


def __getattr__(name):
    if name == "DownloadService":
        from .service import DownloadService

        return DownloadService
    raise AttributeError(name)

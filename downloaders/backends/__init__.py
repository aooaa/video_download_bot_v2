__all__ = ["DouyinF2Downloader", "YoutubeYtDlpDownloader"]


def __getattr__(name: str):
    if name == "DouyinF2Downloader":
        from .douyin_f2 import DouyinF2Downloader

        return DouyinF2Downloader
    if name == "YoutubeYtDlpDownloader":
        from .ytdlp_backend import YoutubeYtDlpDownloader

        return YoutubeYtDlpDownloader
    raise AttributeError(name)

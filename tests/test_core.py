from pathlib import Path
from types import SimpleNamespace
import asyncio

from downloaders.base import DownloadContext, MediaFile
from downloaders.backends.ytdlp_backend import YoutubeYtDlpDownloader
from downloaders.registry import DownloaderRegistry
from downloaders.router import detect_platform, extract_first_url
from services.media import MediaService
from storage.drive_accounts import DriveAccount, DriveAccountStore


class DummyDownloader:
    platform = "dummy"
    backend_name = "test"


def test_router_detects_supported_platforms():
    assert detect_platform("https://www.youtube.com/watch?v=abc") == "youtube"
    assert detect_platform("https://youtu.be/abc") == "youtube"
    assert detect_platform("https://v.douyin.com/abc/") == "douyin"
    assert detect_platform("hello") is None


def test_extract_first_url_from_message_text():
    assert extract_first_url("download this https://youtu.be/abc please") == "https://youtu.be/abc"
    assert extract_first_url("no url") is None


def test_downloader_registry_selects_backend():
    registry = DownloaderRegistry()
    registry.register("dummy", "test", DummyDownloader)
    downloader = registry.get("dummy", "test")
    assert isinstance(downloader, DummyDownloader)


def test_youtube_backend_enables_node_and_ejs_fallback(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("downloaders.backends.ytdlp_backend.shutil.which", lambda name: "C:/node/node.exe")
    downloader = YoutubeYtDlpDownloader()
    context = DownloadContext(output_dir=tmp_path, config=SimpleNamespace())

    opts = downloader._build_ydl_opts(context)

    assert opts["js_runtimes"] == {"node": {"path": "C:/node/node.exe"}}
    assert opts["remote_components"] == ["ejs:npm"]
    assert opts["format"] == (
        "bestvideo[height<=1600]+bestaudio[ext=m4a]/"
        "best[height<=1600]"
    )
    assert "format_sort" not in opts


def test_media_service_keeps_h264_and_hevc_without_transcoding(tmp_path: Path, monkeypatch):
    service = MediaService()
    media_file = MediaFile(path=tmp_path / "video.mp4", media_type="video")

    async def fake_video_codec(file_path: Path) -> str:
        return file_path.stem

    monkeypatch.setattr(service, "video_codec", fake_video_codec)

    h264_file = media_file.path.with_stem("h264")
    hevc_file = media_file.path.with_stem("hevc")

    h264_result, _ = asyncio.run(
        service.ensure_supported_video_codec(MediaFile(path=h264_file, media_type="video"))
    )
    hevc_result, _ = asyncio.run(
        service.ensure_supported_video_codec(MediaFile(path=hevc_file, media_type="video"))
    )

    assert h264_result.path == h264_file
    assert hevc_result.path == hevc_file


def test_drive_account_store_round_trip(tmp_path: Path):
    store = DriveAccountStore(tmp_path / "settings.db")
    account = DriveAccount(
        telegram_user_id=123,
        provider="onedrive",
        remote_name="Onedrive-P",
        upload_path="Downloads",
    )
    store.upsert_account(account)

    loaded = store.get_account(123, "onedrive")
    assert loaded is not None
    assert loaded.remote_name == "Onedrive-P"
    assert loaded.upload_path == "Downloads"

    assert store.set_upload_path(123, "onedrive", "Videos")
    assert store.get_account(123, "onedrive").upload_path == "Videos"

    assert store.delete_account(123, "onedrive")
    assert store.get_account(123, "onedrive") is None

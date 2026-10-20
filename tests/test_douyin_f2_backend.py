from pathlib import Path

import pytest

from downloaders.base import DownloadContext
from downloaders.backends import douyin_f2


class DummyConfig:
    DOUYIN_ENABLE_BARK = False
    kwargs = {
        "naming": "{create}_{desc}",
    }


class DummyVideo:
    def _to_dict(self):
        return {
            "aweme_id": "7644180653438035621",
            "aweme_type": 0,
            "create_time": "2026-05-26 20-45-02",
            "desc": "summer makeup",
            "sec_user_id": "sec-user",
        }


def test_douyin_f2_adds_argus_header_without_mutating_config(tmp_path: Path):
    headers = {"User-Agent": "test-browser"}
    config = type("Config", (), {"kwargs": {"headers": headers}, "DOUYIN_COOKIE_FILE": None})()
    kwargs = douyin_f2.DouyinF2Downloader()._build_kwargs(DownloadContext(tmp_path, config))
    assert kwargs["headers"]["x-tt-argus"] == "1"
    assert headers == {"User-Agent": "test-browser"}


def test_douyin_f2_preserves_explicit_argus_header(tmp_path: Path):
    config = type("Config", (), {
        "kwargs": {"headers": {"X-Tt-Argus": "configured-marker"}},
        "DOUYIN_COOKIE_FILE": None,
    })()
    kwargs = douyin_f2.DouyinF2Downloader()._build_kwargs(DownloadContext(tmp_path, config))
    assert kwargs["headers"] == {"X-Tt-Argus": "configured-marker"}


def fake_format_file_name(naming_template: str, aweme_data: dict) -> str:
    return f"{aweme_data['create_time']}_{aweme_data['desc']}"


@pytest.mark.asyncio
async def test_douyin_f2_uses_create_tasks_and_returns_existing_file(tmp_path: Path):
    aweme_data = DummyVideo()._to_dict()
    base_name = fake_format_file_name("{create}_{desc}", aweme_data)
    existing_file = tmp_path / f"{base_name}_video.mp4"
    existing_file.write_bytes(b"already downloaded")

    async def fake_get_aweme_id(url):
        return "7644180653438035621"

    class FakeHandler:
        def __init__(self, kwargs):
            self.kwargs = kwargs
            self.enable_bark = True

        async def fetch_one_video(self, aweme_id):
            return DummyVideo()

    class FakeDownloader:
        def __init__(self, kwargs):
            self.kwargs = kwargs

        async def create_download_tasks(self, kwargs, aweme_datas, user_path):
            assert isinstance(user_path, Path)

    class FakeAwemeIdFetcher:
        get_aweme_id = staticmethod(fake_get_aweme_id)

    class TestDownloader(douyin_f2.DouyinF2Downloader):
        def _load_f2(self):
            return (
                FakeHandler,
                FakeDownloader,
                FakeAwemeIdFetcher,
                fake_format_file_name,
                lambda urls: ["https://v.douyin.com/test/"],
            )

    result = await TestDownloader().download(
        "https://v.douyin.com/test/",
        DownloadContext(output_dir=tmp_path, config=DummyConfig()),
    )

    assert result.ok
    assert result.files[0].path == existing_file.resolve()
    assert result.files[0].media_type == "video"


@pytest.mark.asyncio
async def test_douyin_f2_returns_existing_audio_file(tmp_path: Path):
    aweme_data = DummyVideo()._to_dict()
    base_name = fake_format_file_name("{create}_{desc}", aweme_data)
    existing_file = tmp_path / f"{base_name}_music.mp3"
    existing_file.write_bytes(b"already downloaded audio")

    async def fake_get_aweme_id(url):
        return "7644180653438035621"

    class FakeHandler:
        def __init__(self, kwargs):
            self.kwargs = kwargs
            self.enable_bark = True

        async def fetch_one_video(self, aweme_id):
            return DummyVideo()

    class FakeDownloader:
        def __init__(self, kwargs):
            self.kwargs = kwargs

        async def create_download_tasks(self, kwargs, aweme_datas, user_path):
            assert isinstance(user_path, Path)

    class FakeAwemeIdFetcher:
        get_aweme_id = staticmethod(fake_get_aweme_id)

    class TestDownloader(douyin_f2.DouyinF2Downloader):
        def _load_f2(self):
            return (
                FakeHandler,
                FakeDownloader,
                FakeAwemeIdFetcher,
                fake_format_file_name,
                lambda urls: ["https://v.douyin.com/test/"],
            )

    result = await TestDownloader().download(
        "https://v.douyin.com/test/",
        DownloadContext(output_dir=tmp_path, config=DummyConfig()),
    )

    assert result.ok
    assert result.files[0].path == existing_file.resolve()
    assert result.files[0].media_type == "document"


@pytest.mark.asyncio
async def test_douyin_f2_returns_existing_folderized_file(tmp_path: Path):
    aweme_data = DummyVideo()._to_dict()
    base_name = fake_format_file_name("{create}_{desc}", aweme_data)
    post_dir = tmp_path / base_name
    post_dir.mkdir()
    existing_file = post_dir / f"{base_name}_video.mp4"
    existing_file.write_bytes(b"already downloaded")

    async def fake_get_aweme_id(url):
        return "7644180653438035621"

    class FakeHandler:
        def __init__(self, kwargs):
            self.kwargs = kwargs
            self.enable_bark = True

        async def fetch_one_video(self, aweme_id):
            return DummyVideo()

    class FakeDownloader:
        def __init__(self, kwargs):
            self.kwargs = kwargs

        async def create_download_tasks(self, kwargs, aweme_datas, user_path):
            assert isinstance(user_path, Path)

    class FakeAwemeIdFetcher:
        get_aweme_id = staticmethod(fake_get_aweme_id)

    class FolderizedConfig(DummyConfig):
        kwargs = {
            "naming": "{create}_{desc}",
            "folderize": True,
        }

    class TestDownloader(douyin_f2.DouyinF2Downloader):
        def _load_f2(self):
            return (
                FakeHandler,
                FakeDownloader,
                FakeAwemeIdFetcher,
                fake_format_file_name,
                lambda urls: ["https://v.douyin.com/test/"],
            )

    result = await TestDownloader().download(
        "https://v.douyin.com/test/",
        DownloadContext(output_dir=tmp_path, config=FolderizedConfig()),
    )

    assert result.ok
    assert result.files[0].path == existing_file.resolve()
    assert result.files[0].media_type == "video"


@pytest.mark.asyncio
async def test_douyin_f2_fallback_downloads_video_for_unknown_aweme_type(tmp_path: Path):
    aweme_data = DummyVideo()._to_dict()
    aweme_data["aweme_type"] = 999
    aweme_data["video_play_addr"] = "https://example.test/video.mp4"
    base_name = fake_format_file_name("{create}_{desc}", aweme_data)
    fallback_file = tmp_path / f"{base_name}_video.mp4"

    async def fake_get_aweme_id(url):
        return "7644180653438035621"

    class FakeUnknownTypeVideo:
        def _to_dict(self):
            return aweme_data

    class FakeHandler:
        def __init__(self, kwargs):
            self.kwargs = kwargs
            self.enable_bark = True

        async def fetch_one_video(self, aweme_id):
            return FakeUnknownTypeVideo()

    class FakeDownloader:
        def __init__(self, kwargs):
            self.kwargs = kwargs
            self.download_tasks = []

        async def create_download_tasks(self, kwargs, aweme_datas, user_path):
            assert isinstance(user_path, Path)

        async def initiate_download(self, file_type, file_url, base_path, file_name, file_suffix):
            assert file_url == "https://example.test/video.mp4"
            path = Path(base_path) / f"{file_name}{file_suffix}"
            path.write_bytes(b"fallback video")

        async def execute_tasks(self):
            pass

    class FakeAwemeIdFetcher:
        get_aweme_id = staticmethod(fake_get_aweme_id)

    class TestDownloader(douyin_f2.DouyinF2Downloader):
        def _load_f2(self):
            return (
                FakeHandler,
                FakeDownloader,
                FakeAwemeIdFetcher,
                fake_format_file_name,
                lambda urls: ["https://v.douyin.com/test/"],
            )

    result = await TestDownloader().download(
        "https://v.douyin.com/test/",
        DownloadContext(output_dir=tmp_path, config=DummyConfig()),
    )

    assert result.ok
    assert result.files[0].path == fallback_file.resolve()
    assert result.files[0].media_type == "video"


def test_douyin_f2_build_kwargs_reads_cookie_file_before_legacy_values(tmp_path: Path):
    cookie_file = tmp_path / "douyin_cookies.txt"
    cookie_file.write_text("file-cookie\n", encoding="utf-8")

    context = DownloadContext(
        output_dir=tmp_path,
        config=type(
            "Config",
            (),
            {
                "DOUYIN_COOKIE_FILE": str(cookie_file),
                "DOUYIN_COOKIE": "legacy-cookie",
                "kwargs": {"cookie": "kwargs-cookie"},
            },
        )(),
    )

    kwargs = douyin_f2.DouyinF2Downloader()._build_kwargs(context)

    assert kwargs["cookie"] == "file-cookie"


def test_douyin_f2_reads_netscape_cookie_file_as_cookie_header(tmp_path: Path):
    cookie_file = tmp_path / "douyin_cookies.txt"
    cookie_file.write_text(
        "\n".join(
            [
                "# Netscape HTTP Cookie File",
                ".douyin.com\tTRUE\t/\tTRUE\t0\tmsToken\tabc",
                ".douyin.com\tTRUE\t/\tTRUE\t0\tttwid\txyz",
            ]
        ),
        encoding="utf-8",
    )

    context = DownloadContext(
        output_dir=tmp_path,
        config=type("Config", (), {"DOUYIN_COOKIE_FILE": str(cookie_file), "kwargs": {}})(),
    )

    kwargs = douyin_f2.DouyinF2Downloader()._build_kwargs(context)

    assert kwargs["cookie"] == "msToken=abc; ttwid=xyz"


def test_douyin_f2_strips_utf8_bom_from_cookie_file(tmp_path: Path):
    cookie_file = tmp_path / "douyin_cookies.txt"
    cookie_file.write_text("\ufeffbd_ticket_guard_client_web_domain=2\n", encoding="utf-8")

    context = DownloadContext(
        output_dir=tmp_path,
        config=type("Config", (), {"DOUYIN_COOKIE_FILE": str(cookie_file), "kwargs": {}})(),
    )

    kwargs = douyin_f2.DouyinF2Downloader()._build_kwargs(context)

    assert kwargs["cookie"] == "bd_ticket_guard_client_web_domain=2"

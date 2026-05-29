from pathlib import Path
from types import SimpleNamespace

import pytest

from downloaders.base import DownloadContext
from downloaders.backends.tiktok_f2 import TiktokF2Downloader


TIKTOK_URL = "https://www.tiktok.com/@user/video/7123456789012345678"


def fake_format_file_name(naming_template: str, aweme_data: dict) -> str:
    return f"{aweme_data['createTime']}_{aweme_data['desc']}"


class DummyVideo:
    def _to_dict(self):
        return {
            "aweme_id": "7123456789012345678",
            "createTime": "2026-05-29 10-00-00",
            "desc": "street food",
            "uniqueId": "creator",
            "secUid": "sec-user",
            "video_playAddr": "https://example.com/video.mp4",
        }


def test_tiktok_f2_build_kwargs_reads_cookie_file_before_legacy_values(tmp_path: Path):
    cookie_file = tmp_path / "tiktok_cookies.txt"
    cookie_file.write_text("file-cookie\n", encoding="utf-8")

    kwargs = TiktokF2Downloader()._build_kwargs(
        DownloadContext(
            output_dir=tmp_path,
            config=SimpleNamespace(
                TIKTOK_COOKIE_FILE=str(cookie_file),
                TIKTOK_COOKIE="legacy-cookie",
                TIKTOK_KWARGS={"cookie": "kwargs-cookie"},
            ),
        ),
        TIKTOK_URL,
    )

    assert kwargs["cookie"] == "file-cookie"


def test_tiktok_f2_build_kwargs_normalizes_headers_for_f2(tmp_path: Path):
    cookie_file = tmp_path / "tiktok_cookies.txt"
    cookie_file.write_text("file-cookie\n", encoding="utf-8")

    kwargs = TiktokF2Downloader()._build_kwargs(
        DownloadContext(
            output_dir=tmp_path,
            config=SimpleNamespace(
                TIKTOK_COOKIE_FILE=str(cookie_file),
                TIKTOK_USE_TELEGRAM_PROXY=False,
                TIKTOK_KWARGS={"headers": None, "proxies": None},
            ),
        ),
        TIKTOK_URL,
    )

    assert isinstance(kwargs["headers"], dict)
    assert kwargs["headers"]["User-Agent"]
    assert kwargs["headers"]["Referer"] == "https://www.tiktok.com/"
    assert kwargs["proxies"] == {"http://": None, "https://": None}


def test_tiktok_f2_build_kwargs_can_use_explicit_proxy_url(tmp_path: Path):
    cookie_file = tmp_path / "tiktok_cookies.txt"
    cookie_file.write_text("file-cookie\n", encoding="utf-8")

    kwargs = TiktokF2Downloader()._build_kwargs(
        DownloadContext(
            output_dir=tmp_path,
            config=SimpleNamespace(
                TIKTOK_COOKIE_FILE=str(cookie_file),
                TIKTOK_PROXY_URL="http://127.0.0.1:10808",
                TIKTOK_USE_TELEGRAM_PROXY=False,
                TIKTOK_KWARGS={"proxies": None},
            ),
        ),
        TIKTOK_URL,
    )

    assert kwargs["proxies"] == {
        "http://": "http://127.0.0.1:10808",
        "https://": "http://127.0.0.1:10808",
    }


def test_tiktok_f2_reads_netscape_cookie_file_as_cookie_header(tmp_path: Path):
    cookie_file = tmp_path / "tiktok_cookies.txt"
    cookie_file.write_text(
        """
# Netscape HTTP Cookie File
.tiktok.com	TRUE	/	TRUE	1812963876	_ttp	abc
www.tiktok.com	FALSE	/	FALSE	1787822998	msToken	token-value
""".lstrip(),
        encoding="utf-8",
    )

    kwargs = TiktokF2Downloader()._build_kwargs(
        DownloadContext(
            output_dir=tmp_path,
            config=SimpleNamespace(
                TIKTOK_COOKIE_FILE=str(cookie_file),
                TIKTOK_USE_TELEGRAM_PROXY=False,
            ),
        ),
        TIKTOK_URL,
    )

    assert kwargs["cookie"] == "_ttp=abc; msToken=token-value"
    assert "\n" not in kwargs["cookie"]


def test_tiktok_f2_configures_f2_client_before_handler_import():
    class FakeClientConfManager:
        tiktok_conf = {"headers": {"Accept": "application/json"}, "proxies": {}}

        @classmethod
        def client(cls):
            return cls.tiktok_conf

    class FakeTokenManager:
        proxies = {}
        user_agent = ""
        mstoken_headers = {}
        ttwid_headers = {}
        odin_tt_headers = {}

    fake_utils = SimpleNamespace(
        ClientConfManager=FakeClientConfManager,
        TokenManager=FakeTokenManager,
    )

    TiktokF2Downloader()._configure_f2_client(
        fake_utils,
        {
            "headers": {"User-Agent": "test-agent", "Referer": "https://www.tiktok.com/"},
            "proxies": {"http://": "http://127.0.0.1:10808", "https://": "http://127.0.0.1:10808"},
        },
    )

    assert FakeClientConfManager.tiktok_conf["proxies"]["http://"] == "http://127.0.0.1:10808"
    assert FakeClientConfManager.tiktok_conf["headers"]["User-Agent"] == "test-agent"
    assert FakeTokenManager.proxies["http://"] == "http://127.0.0.1:10808"
    assert FakeTokenManager.mstoken_headers["User-Agent"] == "test-agent"


def test_tiktok_f2_prepares_runtime_f2_config_before_import(tmp_path: Path):
    source = tmp_path / "source_conf.yaml"
    target = tmp_path / "runtime_conf.yaml"
    source.write_text(
        """
f2:
  tiktok:
    headers:
      User-Agent: old-agent
      Referer: https://www.tiktok.com/
    proxies:
      http://:
      https://:
""".lstrip(),
        encoding="utf-8",
    )
    fake_f2 = SimpleNamespace(F2_CONFIG_FILE_PATH=str(source))

    TiktokF2Downloader()._prepare_f2_config_file(
        fake_f2,
        {
            "_f2_config_path": str(target),
            "headers": {"User-Agent": "new-agent", "Referer": "https://www.tiktok.com/"},
            "proxies": {"http://": "http://127.0.0.1:10808", "https://": "http://127.0.0.1:10808"},
        },
    )

    text = target.read_text(encoding="utf-8")
    assert fake_f2.F2_CONFIG_FILE_PATH == str(target)
    assert "new-agent" in text
    assert "http://127.0.0.1:10808" in text


@pytest.mark.asyncio
async def test_tiktok_f2_download_uses_adapter_and_returns_existing_file(tmp_path: Path):
    aweme_data = DummyVideo()._to_dict()
    base_name = fake_format_file_name("{create}_{desc}", aweme_data)
    existing_file = tmp_path / f"{base_name}_video.mp4"
    existing_file.write_bytes(b"already downloaded")

    class FakeAwemeIdFetcher:
        @staticmethod
        async def get_aweme_id(url):
            return "7123456789012345678"

    class FakeHandler:
        def __init__(self, kwargs):
            self.kwargs = kwargs
            self.enable_bark = True

        async def fetch_one_video(self, itemId):
            assert itemId == "7123456789012345678"
            return DummyVideo()

    class FakeDownloader:
        def __init__(self, kwargs):
            self.kwargs = kwargs

        async def create_download_tasks(self, kwargs, aweme_datas, user_path):
            assert isinstance(user_path, Path)
            assert aweme_datas == aweme_data

    class TestDownloader(TiktokF2Downloader):
        def _load_f2(self, kwargs):
            return FakeHandler, FakeDownloader, FakeAwemeIdFetcher, fake_format_file_name

    result = await TestDownloader().download(
        "https://vt.tiktok.com/ZSYabc/",
        DownloadContext(
            output_dir=tmp_path,
            config=SimpleNamespace(
                TIKTOK_COOKIE="dummy-cookie",
                TIKTOK_KWARGS={"cookie": "dummy-cookie", "naming": "{create}_{desc}"},
            ),
        ),
    )

    assert result.ok
    assert result.platform == "tiktok"
    assert result.backend == "f2"
    assert result.files[0].path == existing_file.resolve()
    assert result.files[0].media_type == "video"


@pytest.mark.asyncio
async def test_tiktok_f2_uses_ytdlp_fallback_when_f2_produces_no_file(tmp_path: Path):
    class FakeAwemeIdFetcher:
        @staticmethod
        async def get_aweme_id(url):
            return "7123456789012345678"

    class FakeHandler:
        def __init__(self, kwargs):
            self.enable_bark = True

        async def fetch_one_video(self, itemId):
            return DummyVideo()

    class FakeDownloader:
        def __init__(self, kwargs):
            pass

        async def create_download_tasks(self, kwargs, aweme_datas, user_path):
            return None

    class TestDownloader(TiktokF2Downloader):
        def _load_f2(self, kwargs):
            return FakeHandler, FakeDownloader, FakeAwemeIdFetcher, fake_format_file_name

        async def _download_with_ytdlp_fallback(self, url, context, before, kwargs):
            fallback_file = context.output_dir / "fallback.mp4"
            fallback_file.write_bytes(b"yt-dlp fallback")
            return [fallback_file.resolve()]

    result = await TestDownloader().download(
        TIKTOK_URL,
        DownloadContext(
            output_dir=tmp_path,
            config=SimpleNamespace(TIKTOK_COOKIE="dummy-cookie", TIKTOK_KWARGS={"cookie": "dummy-cookie"}),
        ),
    )

    assert result.ok
    assert result.files[0].path == (tmp_path / "fallback.mp4").resolve()
    assert any("yt-dlp fallback" in item for item in result.progress)


@pytest.mark.asyncio
async def test_tiktok_f2_requires_cookie_before_loading_f2(tmp_path: Path):
    class TestDownloader(TiktokF2Downloader):
        def _load_f2(self):
            raise AssertionError("F2 should not be imported without a cookie")

    result = await TestDownloader().download(
        TIKTOK_URL,
        DownloadContext(
            output_dir=tmp_path,
            config=SimpleNamespace(TIKTOK_COOKIE_FILE=str(tmp_path / "missing.txt"), TIKTOK_COOKIE=None),
        ),
    )

    assert not result.ok
    assert "tiktok_cookies.txt" in result.error or "TIKTOK_COOKIE_FILE" in result.error

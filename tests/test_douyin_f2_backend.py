from pathlib import Path

import pytest

from downloaders.base import DownloadContext
from downloaders.backends import douyin_f2


class DummyConfig:
    DOUYIN_ENABLE_BARK = False
    kwargs = {
        "cookie": "dummy-cookie",
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


@pytest.mark.asyncio
async def test_douyin_f2_uses_create_tasks_and_returns_existing_file(monkeypatch, tmp_path: Path):
    aweme_data = DummyVideo()._to_dict()
    base_name = douyin_f2.format_file_name("{create}_{desc}", aweme_data)
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

    monkeypatch.setattr(douyin_f2, "extract_valid_urls", lambda urls: ["https://v.douyin.com/test/"])
    monkeypatch.setattr(douyin_f2.AwemeIdFetcher, "get_aweme_id", fake_get_aweme_id)
    monkeypatch.setattr(douyin_f2, "DouyinHandler", FakeHandler)
    monkeypatch.setattr(douyin_f2, "DouyinDownloader", FakeDownloader)

    result = await douyin_f2.DouyinF2Downloader().download(
        "https://v.douyin.com/test/",
        DownloadContext(output_dir=tmp_path, config=DummyConfig()),
    )

    assert result.ok
    assert result.files[0].path == existing_file.resolve()
    assert result.files[0].media_type == "video"

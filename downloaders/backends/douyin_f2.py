from __future__ import annotations

from pathlib import Path
from typing import Any

from downloaders.base import DownloadContext, DownloadResult, MediaFile


VIDEO_TYPES = {0, 55, 61, 109, 201}
IMAGE_TYPE = 68
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".wav"}
TEXT_EXTENSIONS = {".txt", ".lrc"}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | TEXT_EXTENSIONS


class DouyinF2Downloader:
    platform = "douyin"
    backend_name = "f2"

    async def download(self, url: str, context: DownloadContext) -> DownloadResult:
        result = DownloadResult(platform=self.platform, backend=self.backend_name, url=url)
        result.add_progress("Douyin link detected.")

        try:
            DouyinHandler, DouyinDownloader, AwemeIdFetcher, format_file_name, extract_valid_urls = self._load_f2()
            valid_urls = extract_valid_urls([url])
            resolved_url = valid_urls[0] if valid_urls else url
            aweme_id = await AwemeIdFetcher.get_aweme_id(resolved_url)
            if not aweme_id:
                result.error = "Could not resolve Douyin aweme_id from the URL."
                return result

            result.add_progress(f"Douyin aweme_id resolved: {aweme_id}")
            kwargs = self._build_kwargs(context)
            handler = DouyinHandler(kwargs)
            handler.enable_bark = bool(getattr(context.config, "DOUYIN_ENABLE_BARK", False))
            video = await handler.fetch_one_video(aweme_id=aweme_id)
            if not video:
                result.error = f"Could not fetch Douyin metadata for aweme_id {aweme_id}."
                return result

            aweme_data = video._to_dict()
            result.title = aweme_data.get("desc") or f"douyin_{aweme_id}"
            result.raw = {
                "aweme_id": aweme_id,
                "aweme_type": aweme_data.get("aweme_type"),
                "backend": self.backend_name,
            }

            before = self._snapshot(context.output_dir)
            downloader = DouyinDownloader(kwargs)
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
                result.add_progress("F2 produced no file; trying metadata media fallback.")
                await self._download_from_aweme_media(
                    downloader,
                    kwargs,
                    aweme_data,
                    context.output_dir,
                    format_file_name,
                )
                files = self._new_files(context.output_dir, before)
                if not files:
                    files = self._existing_files_for_aweme(
                        context.output_dir,
                        aweme_data,
                        kwargs,
                        format_file_name,
                    )
            result.files.extend(self._to_media_files(files, aweme_data, result.title))

            if not result.files:
                result.error = "Douyin download completed but no media file was found."
                return result

            aweme_type = aweme_data.get("aweme_type")
            if aweme_type == IMAGE_TYPE:
                result.add_progress("Douyin image post downloaded.")
            elif aweme_type in VIDEO_TYPES:
                result.add_progress("Douyin video post downloaded.")
            else:
                result.add_progress(f"Douyin post downloaded with aweme_type={aweme_type}.")
            return result
        except Exception as exc:
            result.error = f"Douyin download failed: {exc}"
            return result

    def _load_f2(self) -> tuple[Any, Any, Any, Any, Any]:
        from f2.apps.douyin.dl import DouyinDownloader
        from f2.apps.douyin.handler import DouyinHandler
        from f2.apps.douyin.utils import AwemeIdFetcher, format_file_name
        from f2.utils.utils import extract_valid_urls

        return DouyinHandler, DouyinDownloader, AwemeIdFetcher, format_file_name, extract_valid_urls

    def _build_kwargs(self, context: DownloadContext) -> dict:
        kwargs = dict(getattr(context.config, "kwargs", {}) or {})
        kwargs.setdefault("mode", "one")
        kwargs.setdefault("naming", "{create}_{desc}")
        kwargs.setdefault("interval", "all")
        kwargs.setdefault("folderize", False)
        # F2 0.0.1.7 omits the header required by Douyin's Argus gateway.
        # The current gateway accepts this marker; preserve explicit overrides
        # in case its requirements change. Copy headers to avoid mutating config.
        headers = dict(kwargs.get("headers") or {})
        if not any(name.lower() == "x-tt-argus" for name in headers):
            headers["x-tt-argus"] = "1"
        kwargs["headers"] = headers
        cookie = self._read_cookie_file(context)
        if cookie:
            kwargs["cookie"] = cookie
        else:
            legacy_cookie = getattr(context.config, "DOUYIN_COOKIE", None)
            if legacy_cookie is not None:
                kwargs["cookie"] = legacy_cookie
            else:
                kwargs.pop("cookie", None)
        return kwargs

    def _read_cookie_file(self, context: DownloadContext) -> str | None:
        cookie_file = getattr(context.config, "DOUYIN_COOKIE_FILE", "douyin_cookies.txt")
        if not cookie_file:
            return None

        cookie_path = Path(cookie_file)
        if not cookie_path.exists():
            return None

        cookie = cookie_path.read_text(encoding="utf-8-sig").strip()
        return self._normalize_cookie_text(cookie)

    def _normalize_cookie_text(self, cookie: str) -> str | None:
        if not cookie:
            return None
        cookie = cookie.replace("\ufeff", "").strip()
        if cookie.startswith("# Netscape HTTP Cookie File") or "\t" in cookie:
            pairs: list[str] = []
            for line in cookie.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 7:
                    name = parts[-2].strip()
                    value = parts[-1].strip()
                    if name:
                        pairs.append(f"{name}={value}")
            return "; ".join(pairs) or None
        return " ".join(cookie.splitlines()).strip() or None

    def _snapshot(self, root: Path) -> set[Path]:
        if not root.exists():
            return set()
        return {path.resolve() for path in root.rglob("*") if path.is_file()}

    def _new_files(self, root: Path, before: set[Path]) -> list[Path]:
        if not root.exists():
            return []
        after = [path.resolve() for path in root.rglob("*") if path.is_file()]
        return sorted(
            (path for path in after if path not in before and path.suffix.lower() in MEDIA_EXTENSIONS),
            key=lambda item: item.stat().st_mtime,
        )

    def _existing_files_for_aweme(self, root: Path, aweme_data: dict, kwargs: dict, format_file_name) -> list[Path]:
        if not root.exists():
            return []

        base_name = format_file_name(kwargs.get("naming", "{create}_{desc}"), aweme_data)
        candidates = [
            path.resolve()
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in MEDIA_EXTENSIONS
            and (path.stem.startswith(f"{base_name}_") or path.parent.name == base_name)
        ]
        return sorted(candidates, key=lambda item: item.stat().st_mtime)

    async def _download_from_aweme_media(
        self,
        downloader,
        kwargs: dict,
        aweme_data: dict,
        output_dir: Path,
        format_file_name,
    ) -> None:
        base_name = format_file_name(kwargs.get("naming", "{create}_{desc}"), aweme_data)
        base_path = output_dir / base_name if kwargs.get("folderize") else output_dir

        video_url = aweme_data.get("video_play_addr")
        if video_url:
            await downloader.initiate_download("视频", video_url, base_path, f"{base_name}_video", ".mp4")

        for index, live_url in enumerate(aweme_data.get("images_video") or [], start=1):
            if live_url:
                await downloader.initiate_download("实况", live_url, base_path, f"{base_name}_live_{index}", ".mp4")

        for index, image_url in enumerate(aweme_data.get("images") or [], start=1):
            if image_url:
                await downloader.initiate_download("图集", image_url, base_path, f"{base_name}_image_{index}", ".webp")

        music_url = aweme_data.get("music_play_url")
        if music_url and not video_url:
            await downloader.initiate_download("原声", music_url, base_path, f"{base_name}_music", ".mp3")

        await downloader.execute_tasks()

    def _to_media_files(self, files: list[Path], aweme_data: dict, title: str | None) -> list[MediaFile]:
        media_files: list[MediaFile] = []
        for path in files:
            suffix = path.suffix.lower()
            if suffix in IMAGE_EXTENSIONS:
                media_type = "photo"
            elif suffix in VIDEO_EXTENSIONS:
                media_type = "live_video" if aweme_data.get("aweme_type") == IMAGE_TYPE else "video"
            else:
                media_type = "document"
            media_files.append(MediaFile(path=path, media_type=media_type, caption=title))
        return media_files

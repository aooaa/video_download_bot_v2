from __future__ import annotations

from pathlib import Path
from typing import Any

from downloaders.base import DownloadContext, DownloadResult, MediaFile


VIDEO_TYPES = {0, 55, 61, 109, 201}
IMAGE_TYPE = 68
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}


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
        return kwargs

    def _snapshot(self, root: Path) -> set[Path]:
        if not root.exists():
            return set()
        return {path.resolve() for path in root.rglob("*") if path.is_file()}

    def _new_files(self, root: Path, before: set[Path]) -> list[Path]:
        if not root.exists():
            return []
        after = [path.resolve() for path in root.rglob("*") if path.is_file()]
        return sorted((path for path in after if path not in before), key=lambda item: item.stat().st_mtime)

    def _existing_files_for_aweme(self, root: Path, aweme_data: dict, kwargs: dict, format_file_name) -> list[Path]:
        if not root.exists():
            return []

        base_name = format_file_name(kwargs.get("naming", "{create}_{desc}"), aweme_data)
        candidates = [
            path.resolve()
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
            and path.stem.startswith(f"{base_name}_")
        ]
        return sorted(candidates, key=lambda item: item.stat().st_mtime)

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

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import yt_dlp

from downloaders.base import DownloadContext, DownloadResult, MediaFile


class YoutubeYtDlpDownloader:
    platform = "youtube"
    backend_name = "ytdlp"
    default_format = (
        "bestvideo[height<=1600]+bestaudio[ext=m4a]/"
        "best[height<=1600]"
    )

    async def download(self, url: str, context: DownloadContext) -> DownloadResult:
        result = DownloadResult(platform=self.platform, backend=self.backend_name, url=url)
        result.add_progress("YouTube link detected.")
        loop = asyncio.get_running_loop()
        try:
            file_path, title, info = await loop.run_in_executor(
                None,
                self._download_sync,
                url,
                context,
            )
        except Exception as exc:
            return DownloadResult(
                platform=self.platform,
                backend=self.backend_name,
                url=url,
                error=f"YouTube download failed: {exc}",
            )

        result.title = title
        result.raw = {"id": info.get("id"), "extractor": info.get("extractor")}
        result.files.append(MediaFile(path=file_path, media_type="video", caption=title))
        result.add_progress("YouTube download finished.")
        return result

    def _download_sync(self, url: str, context: DownloadContext):
        ydl_opts = self._build_ydl_opts(context)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            requested = info.get("requested_downloads") or []
            if requested and requested[0].get("filepath"):
                file_path = Path(requested[0]["filepath"]).resolve()
            else:
                file_path = Path(ydl.prepare_filename(info)).resolve()
                if not file_path.exists() and file_path.with_suffix(".mp4").exists():
                    file_path = file_path.with_suffix(".mp4")

        return file_path, info.get("title") or "YouTube video", info

    def _build_ydl_opts(self, context: DownloadContext) -> dict:
        output_template = str(context.output_dir / "%(title).180B [%(id)s].%(ext)s")
        ydl_opts = {
            "format": getattr(context.config, "YOUTUBE_FORMAT", self.default_format),
            "outtmpl": output_template,
            "noplaylist": True,
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": False,
            "check_formats": "selected",
            "js_runtimes": self._js_runtimes(context),
            "remote_components": getattr(context.config, "YOUTUBE_REMOTE_COMPONENTS", ["ejs:npm"]),
        }
        cookie_path = Path(getattr(context.config, "YOUTUBE_COOKIE_FILE", "youtube_cookies.txt"))
        if cookie_path.exists():
            ydl_opts["cookiefile"] = str(cookie_path)

        return ydl_opts

    def _js_runtimes(self, context: DownloadContext) -> dict[str, dict[str, str]]:
        configured = getattr(context.config, "YOUTUBE_JS_RUNTIMES", None)
        if configured is not None:
            return configured

        node_path = getattr(context.config, "YOUTUBE_NODE_PATH", None) or shutil.which("node")
        if node_path:
            return {"node": {"path": node_path}}

        return {"deno": {}}

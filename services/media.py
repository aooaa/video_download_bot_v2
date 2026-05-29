from __future__ import annotations

import asyncio
from pathlib import Path

from downloaders.base import DownloadResult, MediaFile


class MediaService:
    bot_api_limit_mb = 50
    client_api_limit_mb = 2000
    supported_video_codecs = {"h264", "hevc"}

    async def file_size_mb(self, file_path: Path) -> float:
        return file_path.stat().st_size / (1024 * 1024)

    async def video_dimensions(self, file_path: Path) -> dict[str, int]:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=s=x:p=0",
            str(file_path),
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(stderr.decode(errors="ignore").strip() or "ffprobe failed")
        width, height = stdout.decode().strip().split("x")
        return {"width": int(width), "height": int(height)}

    async def video_codec(self, file_path: Path) -> str:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "default=nw=1:nk=1",
            str(file_path),
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(stderr.decode(errors="ignore").strip() or "ffprobe failed")
        return stdout.decode().strip()

    async def ensure_supported_video_codec(self, media_file: MediaFile) -> tuple[MediaFile, str]:
        if media_file.media_type not in {"video", "live_video"}:
            return media_file, "No transcoding needed for non-video media."

        codec = await self.video_codec(media_file.path)
        if codec in self.supported_video_codecs:
            return media_file, f"Video is already {codec}."

        output_path = media_file.path.with_name(f"{media_file.path.stem}_hevc.mp4")
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(media_file.path),
            "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v",
            "libx265",
            "-tag:v",
            "hvc1",
            "-c:a",
            "aac",
            str(output_path),
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(stderr.decode(errors="ignore").strip() or "ffmpeg transcode failed")

        converted = MediaFile(
            path=output_path.resolve(),
            media_type=media_file.media_type,
            caption=media_file.caption,
            source="hevc_transcode",
        )
        return converted, f"Transcoded {codec or 'unknown'} video to HEVC."

    async def ensure_result_supported_video_codec(self, result: DownloadResult) -> list[str]:
        messages: list[str] = []
        updated_files: list[MediaFile] = []
        cleanup_paths = result.raw.setdefault("cleanup_paths", [])
        for media_file in result.files:
            converted, message = await self.ensure_supported_video_codec(media_file)
            updated_files.append(converted)
            if media_file.media_type in {"video", "live_video"}:
                messages.append(message)
                if converted.path != media_file.path:
                    cleanup_paths.append(str(media_file.path))
        result.files = updated_files
        return messages

    async def ensure_h264(self, media_file: MediaFile) -> tuple[MediaFile, str]:
        return await self.ensure_supported_video_codec(media_file)

    async def ensure_result_h264(self, result: DownloadResult) -> list[str]:
        return await self.ensure_result_supported_video_codec(result)

    async def cleanup_result_files(self, result: DownloadResult) -> None:
        seen: set[Path] = set()
        paths = [media_file.path for media_file in result.files]
        paths.extend(Path(path) for path in result.raw.get("cleanup_paths", []))
        for item_path in paths:
            path = item_path.resolve()
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            path.unlink()

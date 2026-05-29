from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from storage.drive_accounts import DriveAccount


@dataclass(slots=True)
class DriveUploadResult:
    ok: bool
    message: str
    stdout: str = ""
    stderr: str = ""


class RcloneDriveService:
    def __init__(self, rclone_path: str = "rclone") -> None:
        self.rclone_path = rclone_path

    async def upload_file(self, file_path: Path, account: DriveAccount) -> DriveUploadResult:
        destination = f"{account.remote_name}:{account.upload_path}".rstrip(":")
        process = await asyncio.create_subprocess_exec(
            self.rclone_path,
            "copy",
            str(file_path),
            destination,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        stdout_text = stdout.decode(errors="ignore").strip()
        stderr_text = stderr.decode(errors="ignore").strip()
        if process.returncode == 0:
            return DriveUploadResult(True, f"Uploaded to {destination}", stdout_text, stderr_text)
        return DriveUploadResult(
            False,
            f"Upload failed with exit code {process.returncode}: {stderr_text or stdout_text}",
            stdout_text,
            stderr_text,
        )

    async def list_remotes(self) -> list[str]:
        process = await asyncio.create_subprocess_exec(
            self.rclone_path,
            "listremotes",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(stderr.decode(errors="ignore").strip() or "rclone listremotes failed")
        return [line.rstrip(":") for line in stdout.decode(errors="ignore").splitlines() if line.strip()]

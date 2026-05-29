from __future__ import annotations


class ProgressReporter:
    def __init__(self, bot) -> None:
        self.bot = bot

    async def reply(self, message, text: str) -> None:
        await self.bot.reply_to(message, text)

    async def download_started(self, message, platform: str | None) -> None:
        name = platform or "video"
        await self.reply(message, f"{name} link detected. Starting download...")

    async def failed(self, message, error: str) -> None:
        await self.reply(message, f"Download failed: {error}")

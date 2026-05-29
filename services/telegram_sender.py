from __future__ import annotations

from pathlib import Path

from telebot import types

from downloaders.base import DownloadResult, MediaFile
from .media import MediaService


class TelegramSender:
    def __init__(self, bot, client, media_service: MediaService, large_file_target: str | None = None) -> None:
        self.bot = bot
        self.client = client
        self.media_service = media_service
        self.large_file_target = large_file_target

    async def send_download_result(self, message, result: DownloadResult) -> None:
        photos = [item for item in result.files if item.media_type == "photo"]
        videos = [item for item in result.files if item.media_type in {"video", "live_video"}]
        documents = [item for item in result.files if item.media_type == "document"]

        if photos:
            await self._send_photos(message, photos)
        for video in videos:
            await self._send_video(message, video)
        for document in documents:
            await self._send_document(message, document)

    async def _send_photos(self, message, photos: list[MediaFile]) -> None:
        for index in range(0, len(photos), 10):
            chunk = photos[index : index + 10]
            if len(chunk) == 1:
                await self.bot.send_photo(
                    message.chat.id,
                    types.InputFile(str(chunk[0].path)),
                    caption=chunk[0].caption,
                    reply_to_message_id=message.message_id,
                    timeout=3600,
                )
                continue

            media = []
            for item_index, item in enumerate(chunk):
                caption = item.caption if item_index == 0 else None
                media.append(types.InputMediaPhoto(types.InputFile(str(item.path)), caption=caption))
            await self.bot.send_media_group(
                message.chat.id,
                media,
                reply_to_message_id=message.message_id,
                timeout=3600,
            )

    async def _send_video(self, message, media_file: MediaFile) -> None:
        size_mb = await self.media_service.file_size_mb(media_file.path)
        if size_mb < self.media_service.bot_api_limit_mb:
            dimensions = await self.media_service.video_dimensions(media_file.path)
            await self.bot.send_video(
                message.chat.id,
                types.InputFile(str(media_file.path)),
                caption=media_file.caption,
                timeout=3600,
                supports_streaming=True,
                width=dimensions.get("width"),
                height=dimensions.get("height"),
                reply_to_message_id=message.message_id,
            )
        elif size_mb < self.media_service.client_api_limit_mb:
            target = self.large_file_target or message.chat.id
            await self.client.send_file(
                target,
                str(media_file.path),
                caption=media_file.caption,
                supports_streaming=True,
                reply_to=message.message_id,
            )
        else:
            await self.bot.reply_to(message, "文件大小超过2G,无法上传!")

    async def _send_document(self, message, media_file: MediaFile) -> None:
        await self.bot.send_document(
            message.chat.id,
            types.InputFile(str(media_file.path)),
            caption=media_file.caption,
            reply_to_message_id=message.message_id,
            timeout=3600,
        )

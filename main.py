from __future__ import annotations

import asyncio
from pathlib import Path

from telebot import types
from telebot.async_telebot import AsyncTeleBot
from telethon import TelegramClient

import config
from downloaders import DownloadService, DownloadTarget
from downloaders.router import detect_platform, extract_first_url
from services import MediaService, ProgressReporter, RcloneDriveService, TelegramSender
from storage import DriveAccount, DriveAccountStore
from telegram_proxy import configure_bot_api_proxy, describe_telegram_proxy, get_telethon_proxy


configure_bot_api_proxy()
bot = AsyncTeleBot(config.TOKEN)
client = TelegramClient(
    getattr(config, "TELETHON_SESSION", "test_session_download_bot"),
    config.api_id,
    config.api_hash,
    proxy=get_telethon_proxy(),
)

download_service = DownloadService(config)
media_service = MediaService()
drive_store = DriveAccountStore(getattr(config, "BOT_SETTINGS_DB", "bot_settings.db"))
drive_service = RcloneDriveService(getattr(config, "RCLONE_PATH", "rclone"))
progress = ProgressReporter(bot)
telegram_sender = TelegramSender(
    bot,
    client,
    media_service,
    large_file_target=getattr(config, "username", None),
)

DRIVE_PROVIDERS = {
    "onedrive": "OneDrive",
    "googledrive": "Google Drive",
}


def _user_id(message) -> int:
    return int(message.from_user.id if message.from_user else message.chat.id)


def _settings_markup() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("View drives", callback_data="drive:view"),
        types.InlineKeyboardButton("List rclone remotes", callback_data="drive:remotes"),
    )
    markup.add(
        types.InlineKeyboardButton("Bind OneDrive", callback_data="drive:help:onedrive"),
        types.InlineKeyboardButton("Bind Google Drive", callback_data="drive:help:googledrive"),
    )
    markup.add(
        types.InlineKeyboardButton("Delete OneDrive", callback_data="drive:delete:onedrive"),
        types.InlineKeyboardButton("Delete Google Drive", callback_data="drive:delete:googledrive"),
    )
    return markup


def _format_accounts(accounts: list[DriveAccount]) -> str:
    if not accounts:
        return "No drive account is bound for your Telegram user yet."
    lines = ["Current drive bindings:"]
    for account in accounts:
        provider_name = DRIVE_PROVIDERS.get(account.provider, account.provider)
        state = "enabled" if account.enabled else "disabled"
        lines.append(
            f"- {provider_name}: remote={account.remote_name}, path={account.upload_path}, {state}"
        )
    return "\n".join(lines)


async def _download(message, text: str, target: DownloadTarget):
    platform = detect_platform(text)
    await progress.download_started(message, platform)
    result = await download_service.download(text, target=target)
    if not result.ok:
        await progress.failed(message, result.error or "No media was downloaded.")
        return result

    return result


async def _send_to_chat(message, text: str) -> None:
    result = await _download(message, text, DownloadTarget(mode="telegram"))
    if not result.ok:
        return

    try:
        await media_service.ensure_result_supported_video_codec(result)
        await telegram_sender.send_download_result(message, result)
    except Exception as exc:
        await bot.reply_to(message, f"An error occurred while sending media: {exc}")
    finally:
        if getattr(config, "CLEANUP_DOWNLOADS", True):
            await media_service.cleanup_result_files(result)


async def _send_to_drive(message, provider: str, text: str) -> None:
    account = drive_store.get_account(_user_id(message), provider)
    if not account:
        provider_name = DRIVE_PROVIDERS.get(provider, provider)
        await bot.reply_to(
            message,
            f"{provider_name} is not bound yet.\n"
            f"Run: /binddrive {provider} <rclone_remote_name> <upload_path>",
        )
        return

    result = await _download(message, text, DownloadTarget(mode="drive", provider=provider))
    if not result.ok:
        return

    try:
        await media_service.ensure_result_supported_video_codec(result)
        failures = []
        for media_file in result.files:
            upload_result = await drive_service.upload_file(media_file.path, account)
            if not upload_result.ok:
                failures.append(f"{media_file.path.name}: {upload_result.message}")
        if failures:
            await bot.reply_to(message, "Some uploads failed:\n" + "\n".join(failures))
    except Exception as exc:
        await bot.reply_to(message, f"Drive upload failed: {exc}")
    finally:
        if getattr(config, "CLEANUP_DOWNLOADS", True):
            await media_service.cleanup_result_files(result)


@bot.message_handler(commands=["start"])
async def send_welcome(message) -> None:
    await bot.reply_to(
        message,
        "Hi, welcome to the Video Downloader Bot.\n"
        "Send a YouTube, Douyin, or TikTok link to download it to this chat.\n"
        "Use /menu to manage OneDrive and Google Drive uploads.",
    )


@bot.message_handler(commands=["menu", "settings"])
async def send_menu(message) -> None:
    await bot.reply_to(message, "Bot settings", reply_markup=_settings_markup())


@bot.message_handler(commands=["binddrive"])
async def bind_drive(message) -> None:
    parts = message.text.split(maxsplit=3)
    if len(parts) < 3:
        await bot.reply_to(
            message,
            "Usage: /binddrive <onedrive|googledrive> <rclone_remote_name> [upload_path]\n"
            "Example: /binddrive onedrive Onedrive-P Downloads",
        )
        return

    provider = parts[1].lower()
    if provider not in DRIVE_PROVIDERS:
        await bot.reply_to(message, "Unsupported provider. Use onedrive or googledrive.")
        return

    account = DriveAccount(
        telegram_user_id=_user_id(message),
        provider=provider,
        remote_name=parts[2].rstrip(":"),
        upload_path=parts[3].strip("/") if len(parts) >= 4 else "Downloads",
        enabled=True,
    )
    drive_store.upsert_account(account)
    await bot.reply_to(
        message,
        f"{DRIVE_PROVIDERS[provider]} bound: remote={account.remote_name}, path={account.upload_path}",
    )


@bot.message_handler(commands=["setdrivepath"])
async def set_drive_path(message) -> None:
    parts = message.text.split(maxsplit=2)
    if len(parts) != 3:
        await bot.reply_to(message, "Usage: /setdrivepath <onedrive|googledrive> <upload_path>")
        return
    provider = parts[1].lower()
    if provider not in DRIVE_PROVIDERS:
        await bot.reply_to(message, "Unsupported provider. Use onedrive or googledrive.")
        return
    if drive_store.set_upload_path(_user_id(message), provider, parts[2].strip("/")):
        await bot.reply_to(message, f"{DRIVE_PROVIDERS[provider]} upload path updated.")
    else:
        await bot.reply_to(message, f"{DRIVE_PROVIDERS[provider]} is not bound yet.")


@bot.message_handler(commands=["deletedrive"])
async def delete_drive(message) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        await bot.reply_to(message, "Usage: /deletedrive <onedrive|googledrive>")
        return
    provider = parts[1].lower()
    if provider not in DRIVE_PROVIDERS:
        await bot.reply_to(message, "Unsupported provider. Use onedrive or googledrive.")
        return
    if drive_store.delete_account(_user_id(message), provider):
        await bot.reply_to(message, f"{DRIVE_PROVIDERS[provider]} binding deleted from bot settings.")
    else:
        await bot.reply_to(message, f"No {DRIVE_PROVIDERS[provider]} binding was found.")


@bot.message_handler(commands=["send2onedrive"])
async def send_to_onedrive(message) -> None:
    url = extract_first_url(message.text)
    if not url:
        await bot.reply_to(message, "Usage: /send2onedrive <video_url>")
        return
    await _send_to_drive(message, "onedrive", url)


@bot.message_handler(commands=["send2googledrive"])
async def send_to_googledrive(message) -> None:
    url = extract_first_url(message.text)
    if not url:
        await bot.reply_to(message, "Usage: /send2googledrive <video_url>")
        return
    await _send_to_drive(message, "googledrive", url)


@bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("drive:"))
async def drive_callback(call) -> None:
    data = call.data.split(":")
    action = data[1]
    chat_id = call.message.chat.id
    user_id = int(call.from_user.id)

    if action == "view":
        await bot.send_message(chat_id, _format_accounts(drive_store.list_accounts(user_id)))
    elif action == "remotes":
        try:
            remotes = await drive_service.list_remotes()
            text = "Available rclone remotes:\n" + "\n".join(f"- {item}" for item in remotes)
            await bot.send_message(chat_id, text if remotes else "No rclone remotes found.")
        except Exception as exc:
            await bot.send_message(chat_id, f"Could not list rclone remotes: {exc}")
    elif action == "help" and len(data) == 3:
        provider = data[2]
        await bot.send_message(
            chat_id,
            f"First authorize with rclone outside the bot, then bind it here:\n"
            f"/binddrive {provider} <rclone_remote_name> <upload_path>\n"
            f"Example: /binddrive {provider} {DRIVE_PROVIDERS[provider].replace(' ', '')} Downloads",
        )
    elif action == "delete" and len(data) == 3:
        provider = data[2]
        if drive_store.delete_account(user_id, provider):
            await bot.send_message(chat_id, f"{DRIVE_PROVIDERS[provider]} binding deleted from bot settings.")
        else:
            await bot.send_message(chat_id, f"No {DRIVE_PROVIDERS[provider]} binding was found.")

    await bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda message: True)
async def handle_message(message) -> None:
    if not message.text:
        return
    if not detect_platform(message.text):
        await bot.reply_to(message, "Sorry, the URL you entered is not supported.")
        return
    await _send_to_chat(message, message.text)


async def main() -> None:
    Path(getattr(config, "DOWNLOAD_DIR", "downloads")).mkdir(parents=True, exist_ok=True)
    print(f"Telegram proxy: {describe_telegram_proxy()}")
    await client.start()
    await bot.polling()


if __name__ == "__main__":
    asyncio.run(main())

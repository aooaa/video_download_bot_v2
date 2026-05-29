# Telegram Video Download Bot

This bot downloads YouTube, Douyin, and TikTok share links back to Telegram, or uploads them to OneDrive / Google Drive through rclone.

## Architecture

- `main.py` only handles Telegram commands, menus, and workflow orchestration.
- `downloaders/` exposes the unified `DownloadService` / `PlatformDownloader` interface.
- `downloaders/backends/` contains concrete library adapters. Current defaults:
  - YouTube: `ytdlp`
  - Douyin: `f2`
  - TikTok: `f2`
- `services/` handles Telegram sending, compatible video transcoding, and rclone uploads.
- `storage/` stores per-user drive remote/path settings in SQLite.

To switch a platform implementation later, add or replace a backend adapter and update configuration:

```python
DOWNLOAD_BACKENDS = {
    "youtube": "ytdlp",
    "douyin": "f2",
    "tiktok": "f2",
}
```

## Configuration

Copy `config_example.py` to `config.py`, then fill in Telegram, Douyin, and rclone settings.

For Douyin, export cookies from a logged-in browser session and save the cookie string as `douyin_cookies.txt`. You can also configure a custom path:

```python
DOUYIN_COOKIE_FILE = "douyin_cookies.txt"
```

When Douyin cookies expire, export fresh cookies and replace this file. Do not commit `douyin_cookies.txt` to Git. Keep `DOUYIN_ENABLE_BARK = False` unless you have configured a valid Bark key. F2 enables Bark notifications in its bundled config, and an empty Bark key can cause noisy `https://api.day.app/` 405 errors during metadata fetches.

For TikTok, export cookies from a logged-in browser session and save the cookie string as `tiktok_cookies.txt` if F2 reports auth, token, region, or rate-limit errors. You can also configure a custom path:

```python
TIKTOK_COOKIE_FILE = "tiktok_cookies.txt"
```

When TikTok cookies expire, export fresh cookies and replace this file. Do not commit `tiktok_cookies.txt` to Git. The TikTok F2 adapter is lazy-loaded so the bot can still start even when TikTok token generation fails until a TikTok link is requested.

YouTube downloads are stricter now. If yt-dlp reports sign-in, bot checks, or anti-abuse errors, export YouTube cookies from your browser and save them as `youtube_cookies.txt`, or configure:

```python
YOUTUBE_COOKIE_FILE = "youtube_cookies.txt"
```

YouTube signature and `n` challenges also need a JavaScript runtime and the EJS solver. Keep `yt-dlp>=2026.3.17` and `yt-dlp-ejs>=0.8.0` installed, and make sure Node.js is installed or configure:

```python
YOUTUBE_NODE_PATH = r"C:\Program Files\nodejs\node.exe"
YOUTUBE_REMOTE_COMPONENTS = ["ejs:npm"]
```

## Drive Setup

Drive OAuth is handled by rclone. The bot does not store OAuth tokens.

1. Authorize a remote with rclone, such as `Onedrive-P` or `GoogleDrive-P`.
2. Bind it in the bot:

```text
/binddrive onedrive Onedrive-P Downloads
/binddrive googledrive GoogleDrive-P Downloads
```

3. Update upload path:

```text
/setdrivepath onedrive Videos/Douyin
```

4. Delete a bot binding:

```text
/deletedrive onedrive
```

This only removes the SQLite binding. It does not remove the rclone remote.

## Bot Commands

- `/start` shows the introduction.
- `/menu` or `/settings` opens the drive settings menu.
- Send a YouTube/Douyin/TikTok link directly to download and send it back to the current chat.
- `/send2onedrive <url>` downloads and uploads to the bound OneDrive remote/path.
- `/send2googledrive <url>` downloads and uploads to the bound Google Drive remote/path.

## Telegram Size Rules

- Under 50MB: upload through the Bot API.
- 50MB to 2GB: upload through TelegramClient.
- Over 2GB: reply with `文件大小超过2G,无法上传!`

## systemd Notes

Telethon creates a `.session` file in the working directory. Set a writable `WorkingDirectory` when running under systemd.

```ini
[Unit]
Description=Telegram Video Download Bot

[Service]
Type=simple
WorkingDirectory=/home/telegram_bot
ExecStart=/home/telegram_bot/.venv/bin/python /home/telegram_bot/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

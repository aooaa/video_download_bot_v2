# Ubuntu Deploy Bundle

This bundle installs and runs the Telegram Video Download Bot on an Ubuntu
server with systemd.

It provides:

- `install.sh`: installs OS packages, creates an app user, copies the project,
  creates a Python virtual environment, and installs Python dependencies.
- `video-download-bot.service`: systemd unit for automatic startup and restart.
- `video-download-bot.env.example`: server-side environment variable template.
- `config.py.example`: production-friendly `config.py` template that reads the
  systemd environment file.
- `run.sh`: service/manual start wrapper.
- `preflight.sh`: manual readiness check to run before enabling the service.

The installer does not delete old files from the target directory. If you need
to remove stale files, review them and delete them manually.

## Target Layout

Default paths:

```text
/opt/video-download-bot
/etc/video-download-bot/video-download-bot.env
/etc/systemd/system/video-download-bot.service
/home/video-bot/.config/rclone/rclone.conf
```

You can override the app path and user while running the installer:

```bash
sudo APP_DIR=/opt/video-download-bot APP_USER=video-bot ./deploy/ubuntu/install.sh
```

## Install

Run these commands from the project root on the Ubuntu server:

```bash
chmod +x deploy/ubuntu/install.sh deploy/ubuntu/run.sh deploy/ubuntu/preflight.sh
sudo ./deploy/ubuntu/install.sh
```

Edit the environment file:

```bash
sudo nano /etc/video-download-bot/video-download-bot.env
```

At minimum, set:

```text
BOT_TOKEN=
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
```

Set `TELEGRAM_LARGE_FILE_TARGET` too if you want Telethon uploads for files
larger than the Bot API limit.

Run the preflight check as the service user before enabling systemd:

```bash
sudo -u video-bot /opt/video-download-bot/deploy/ubuntu/preflight.sh
```

The check validates:

- Python 3.12+ from `/opt/video-download-bot/.venv/bin/python`.
- `ffmpeg`, `ffprobe`, Node.js, and `rclone`.
- The rclone remotes visible to the service user, reported as a warning if no
  remotes are configured yet.
- Required Telegram environment variables.
- Writable download, Telethon session, and bot settings database paths.
- Optional YouTube, Douyin, and TikTok cookie files when their env vars point
  to existing files. Missing cookie files are warnings because they are only
  needed when a platform asks for cookies.

Then start the service:

```bash
sudo systemctl enable --now video-download-bot
sudo systemctl status video-download-bot
```

Follow logs:

```bash
journalctl -u video-download-bot -f
```

Restart after changing configuration:

```bash
sudo systemctl restart video-download-bot
```

## Cookies

YouTube may require browser cookies when yt-dlp reports sign-in, bot-check, or
anti-abuse errors. Douyin may also require fresh logged-in cookies.

Recommended server paths:

```text
/etc/video-download-bot/youtube_cookies.txt
/etc/video-download-bot/douyin_cookies.txt
/etc/video-download-bot/tiktok_cookies.txt
```

Copy cookie files to those paths, make them readable by the service user, and
keep them out of Git:

```bash
sudo cp youtube_cookies.txt /etc/video-download-bot/youtube_cookies.txt
sudo cp douyin_cookies.txt /etc/video-download-bot/douyin_cookies.txt
# Optional:
sudo cp tiktok_cookies.txt /etc/video-download-bot/tiktok_cookies.txt
sudo chown video-bot:video-bot /etc/video-download-bot/*_cookies.txt
sudo chmod 600 /etc/video-download-bot/*_cookies.txt
sudo systemctl restart video-download-bot
```

## rclone / Drive Uploads

Authorize OneDrive and Google Drive as the service user so the bot can see the
same rclone remotes at runtime:

```bash
sudo -u video-bot rclone config
sudo -u video-bot rclone listremotes
```

Then bind the remote inside Telegram:

```text
/binddrive onedrive Onedrive-P Downloads
/binddrive googledrive GoogleDrive-P Downloads
```

Update paths later with:

```text
/setdrivepath onedrive Videos/Douyin
/setdrivepath googledrive Videos/YouTube
```

## Manual Run

For debugging:

```bash
sudo -u video-bot /opt/video-download-bot/deploy/ubuntu/preflight.sh
sudo -u video-bot /opt/video-download-bot/deploy/ubuntu/run.sh
```

## Updating

From a fresh project checkout or updated project directory:

```bash
sudo ./deploy/ubuntu/install.sh
sudo systemctl restart video-download-bot
```

The installer copies files over the target directory but intentionally does not
delete files that no longer exist in the source checkout.

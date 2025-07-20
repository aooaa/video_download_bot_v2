## 使用的库

f2 - 抖音下载  
yt-dlp - Youtube下载  
pyTelegramBotAPI - telegram bot api

## 常用命令

```
#查看服务状态
systemctl status assistant_bot.service

#停止和重启服务
systemctl stop assistant_bot.service
systemctl restart assistant_bot.service

#删除开机启动
systemctl disable assistant_bot.service
```

## 配置后台启动

以`systemd`服务时，telethon需要对工作目录有可写入权限，默认情况下，`Telethon`会在当前工作目录下创建一个以会话名称为文件名的`.session`文件。

- 你的`systemd`服务配置中没有指定工作目录，因此默认情况下，它会使用根目录（`/`）作为工作目录。根目录通常对非特权用户不可写，甚至可能对`root`用户也有其他限制。

- 你可以通过在服务配置中设置WorkingDirectory来指定一个可写的目录。例如，将会话文件存储在/home/telegram_bot目录中：

  创建一个名为`assistant_bot.service`的服务文件

  ```
  [Unit]
  Description=My Python Telegram Assistant Bot Service
  
  [Service]
  Type=simple
  WorkingDirectory=/home/telegram_bot
  ExecStart=/home/telegram_bot/.venv/bin/python /home/telegram_bot/main.py
  Restart=always
  User=0
  Group=0
  
  [Install]
  ```

  

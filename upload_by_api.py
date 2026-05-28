from telethon import TelegramClient
import os
import sys
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import *
from telegram_proxy import get_telethon_proxy

# 定义Telegram API ID和Hash
#api_id = '25687778'
#api_hash = 'f05bcb203c68ce7afd2baf66f3db2f57'

# 定义客户端
client = TelegramClient('session_oracle', api_id, api_hash, proxy=get_telethon_proxy())

# 启动客户端
client.start()

# 定义源频道和目标组群

# 定义上传视频函数
async def send_video_by_client_api(user, file_path, reply_to=None):
    # 检查文件是否存在
    if not os.path.isfile(file_path):
        #print("文件不存在")
        return "An error occurred: file not exist"
    # 发送视频文件，以流媒体方式
    async with TelegramClient('session_telegram', api_id, api_hash, proxy=get_telethon_proxy()) as client:
        await client.send_file(user, file_path, supports_streaming=True, reply_to=reply_to)

r'''
with client:
    video_file = r"C:\Users\herry\Videos\序列 01 5-1.mp4"
    # 发送目标用户
    username = "multi_download_assistant_bot"
    print("开始上传，请稍等...")
    client.loop.run_until_complete(send_video_by_client_api(username, video_file))
'''
# 打印成功消息
#print("上传成功!")

from config import *
from telethon import TelegramClient
import os
import re
import subprocess
import yt_dlp
import requests
import asyncio
from telebot.async_telebot import AsyncTeleBot
from concurrent.futures import ThreadPoolExecutor
from f2.apps.douyin.handler import DouyinHandler
from utils.vp9_detect import process_video
from utils.dimensions_detect import get_video_dimensions
from utils.check_file_size import get_file_size

'''
- 版本变化

1.使用telethon python api来上传大文件

- 注意
1.tg定义客户端，每个客户端名称需保持不同，不然会导致缓存失效
'''

# Replace with your own Telegram bot token
#bot = telebot.TeleBot(TOKEN)
bot = AsyncTeleBot(TOKEN)

# tg定义客户端(每个客户端名称需保持不一样)
client = TelegramClient('test_session_download_bot', api_id, api_hash)

#youtube下载模块
executor = ThreadPoolExecutor()

def sync_youtube_dl(url):
    try:
        ydl_opts = {
            'format': 'bestvideo[ext=mp4][height<=1600]+bestaudio[ext=m4a]/best[ext=mp4][height<=1600]',
            'outtmpl': '%(title)s.%(ext)s',
            'noplaylist': True,
            'cookiefile': 'youtube_cookies.txt'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            #print('Start Download...')
            video_file = ydl.download([url]) #这段代码会让视频下载，不然视频不会下载
            info_dict = ydl.extract_info(url, download=False)
            filename = ydl.prepare_filename(info_dict)
            filepath = os.path.abspath(filename)
            # print('OK')
            # print(filepath)
            return filepath
    except Exception as e:
        return f"Error occurred: {str(e)}"

#在异步函数中调用同步函数（一般来说，同步函数不能被异步函数直接调用，直接调用会报错）
async def youtube_dl(content):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, sync_youtube_dl, content)
    return result



#抖音下载模块
async def douyin_dl(content):
    try:
        if 'douyin.com/user' in content:
            vid = re.findall(r'modal_id=(\d+)', content)
            url = 'https://www.douyin.com/video/'+ vid[0]

        else:
            # 提取网址
            pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
            url_list = re.findall(pattern,content)
            url = url_list[0]

            # 获取真实网站
            data = requests.get(url=url, headers=HEADERS, timeout=5)
            vid = re.findall(r'\d+',data.url)
            url = 'https://www.douyin.com/video/'+ vid[0]
        
        html_data = str(await get_video_data(vid[0])) # 使用await关键字

        # 获取视频id
        video_id = re.findall('//www.douyin.com/aweme/v1/play/\?video_id=(.*?)&line=0', html_data)[0]
        video_url = 'https://www.douyin.com/aweme/v1/play/?video_id=%s&line=0' %(video_id)
        #return video_url

        #下载视频(添加vid防止下载文件被覆盖)
        filepath = f'douyin_{video_id}.mp4'
        # 获取重定向网址
        # downlowd_url = requests.get(url=video_url, headers=HEADERS, timeout=5)
        response = requests.get(url=video_url, headers=HEADERS, timeout=5, allow_redirects=True)
        final_url = response.url
        # 使用GET请求获取视频内容
        with requests.get(final_url, stream=True) as r:
            r.raise_for_status()
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    # 如果有数据，写入文件
                    if chunk:
                        f.write(chunk)
        #返回下载路径
        return os.path.abspath(filepath)

    except Exception as e:
        return f"Error occurred: {str(e)}"


# 获取网页html数据

async def get_video_data(id):
    video = await DouyinHandler(kwargs).fetch_one_video(aweme_id=id)
    # print("=================_to_raw================")
    # print(video._to_raw())
    # return video._to_raw()
    # print("=================_to_dict================")
    # print(video._to_dict())
    return video._to_dict()



#消息推送模块

#预编译youtube网址匹配
youtube_url_pattern = re.compile(r'(https?://)?(www\.)?(youtube|youtu)\.(com|cn|com\.cn|be)/\S+')

#预

@bot.message_handler(commands=['start'])
async def send_welcome(message):
    await bot.reply_to(message, "Hi, welcome to the Video Downloader Bot! Please enter a video URL to download. Now Support: YouTube, Douyin.")

@bot.message_handler(commands=['send2onedrive'])
async def send_to_onedrive(message):
    # 判断链接是哪个网站
    # 是否是youtube链接
    file_url = message.text.split(maxsplit=1)[1]
    if youtube_url_pattern.match(file_url):
        await bot.reply_to(message, 'Youtube视频正在下载，请稍后...')
        download_info = await youtube_dl(file_url)
        if "Error occurred:" not in download_info:
            try:
                # 使用rclone发送视频到onedrive
                await bot.reply_to(message, '正在上传Onedrive，请稍后...')
                onedrive_config_name = 'Onedrive-P'
                upload_path = 'Downloads'
                result = await asyncio.create_subprocess_exec('rclone', 'copy', download_info, f'{onedrive_config_name}:{upload_path}', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = await result.communicate()
                if result.returncode == 0:
                    await bot.reply_to(message, "Successfully uploaded to Onedrive.")
                else:
                    await bot.reply_to(message, f"Upload failed with error: {stderr.decode().strip()}")
            except Exception as e:
                await bot.reply_to(message, f"An error occurred: {str(e)}")
            finally:
                # 不管文件上传onedrive是否成功，都需要将下载的文件移除
                os.remove(download_info)
    else:
        await bot.reply_to(message, "Sorry, the URL you entered is not supported.")

@bot.message_handler(func=lambda message: True)
async def echo_all(message):
    #Douyin发送模块
    if 'douyin' in message.text:
        await bot.reply_to(message, '抖音视频正在下载，请稍后...')
        download_info = await douyin_dl(message.text)
        #如果下载成功
        if "Error occurred:" not in download_info:
            try:
                #检测视频大小
                file_size = await get_file_size(download_info)
                if file_size < 50:
                    with open(download_info, 'rb') as send_file:
                        video_dimensions = await get_video_dimensions(download_info)
                        message_id = message.message_id
                        await bot.send_video(message.chat.id, send_file, timeout=3600, supports_streaming=True, width=video_dimensions.get("Width"), height=video_dimensions.get("Height"), reply_to_message_id=message_id)
                elif file_size < 2000:
                    await bot.reply_to(message, '文件上传中，请稍后...')
                    send_file = download_info
                    message_id = message.message_id
                    await client.send_file(username, send_file, supports_streaming=True, reply_to=message_id)
                    await bot.reply_to(message, '下载完成.')
                else:
                    await bot.reply_to(message, "文件大小超过2G,无法上传!")
            except Exception as e:
                await bot.reply_to(message, f"An error occurred: {str(e)}")
            finally:
                os.remove(download_info)
        else:
            await bot.reply_to(message, download_info)
                    
    #Youtube发送模块
    elif youtube_url_pattern.match(message.text):
        await bot.reply_to(message, 'Youtube视频正在下载，请稍后...')
        download_info = await youtube_dl(message.text)
        #如果下载成功
        if "Error occurred:" not in download_info:
            try:
                #检测视频大小,如果超过50MB，转码为720p，不到50MB，直接转码h.264格式发送
                file_size = await get_file_size(download_info)
                #检测是否需要转码
                await bot.reply_to(message, '检测转码中，请稍后...')
                trans_info = await process_video(download_info)
                trans_file_size = await get_file_size(trans_info.get("video_path"))
                if trans_file_size < 50:
                    with open(trans_info.get("video_path"), 'rb') as send_file:
                            await bot.reply_to(message, trans_info.get("ex_info"))
                            video_dimensions = await get_video_dimensions(trans_info.get("video_path"))
                            message_id = message.message_id
                            await bot.send_video(message.chat.id, send_file, timeout=3600, supports_streaming=True, width=video_dimensions.get("Width"), height=video_dimensions.get("Height"), reply_to_message_id=message_id)
                elif trans_file_size < 2000:
                    await bot.reply_to(message, '文件上传中，请稍后...')
                    send_file = trans_info.get("video_path")
                    message_id = message.message_id
                    await client.send_file(username, send_file, supports_streaming=True, reply_to=message_id)
                    await bot.reply_to(message, '下载完成.')
                else:
                    await bot.reply_to(message, "文件大小超过2G,无法上传!")
            except Exception as e:
                await bot.reply_to(message, f"An error occurred: {str(e)}")
            finally:
                os.remove(download_info)
                os.remove(trans_info.get("video_path"))
        else:
            await bot.reply_to(message, download_info)
    else:
        await bot.reply_to(message, "Sorry, the URL you entered is not supported.")

async def main():
    # Start polling for updates
    await client.start()
    await bot.polling()

if __name__ == "__main__":
    asyncio.run(main())
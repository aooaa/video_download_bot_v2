import os
import yt_dlp

def sync_youtube_dl(url, download_path='.'):
    try:
        output_template = os.path.join(download_path, '%(title)s.%(ext)s')
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_template,
            'noplaylist': True,
            'cookiefile': 'youtube_cookies.txt'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # print('Start Download...')
            # 调用 extract_info 并设置 download=True (或不设置，默认为True)
            # 这样可以在一次请求中完成信息获取和下载
            info_dict = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info_dict)
            filepath = os.path.abspath(filename)
            # print('OK')
            # print(filepath)
            return filepath
    except Exception as e:
        return f"Error occurred: {str(e)}"
    
url = "https://www.youtube.com/shorts/zlfUdXp2UIs"
download_directory = r"C:\Users\herry\Desktop"
filepath = sync_youtube_dl(url, download_path=download_directory)

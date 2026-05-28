import asyncio
import subprocess
import os

async def convert_video_to_720p(input_path: str) -> dict:
    # 创建转码后的视频路径
    output_path = f"{os.path.splitext(input_path)[0]}_720p.mp4"
    
    # ffmpeg命令
    command = [
        'ffmpeg',
        '-i', input_path,
        '-vf', r'scale=ceil(iw*min(720/ih\,1)/2)*2:720',
        '-c:a', 'copy',
        output_path
    ]
    
    # 异步执行ffmpeg命令
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        os.remove(output_path)
        #print(f"Error occurred: {stderr.decode()}")
        return f"Error occurred: {stderr.decode()}"
    
    # 获取文件大小
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    
    return {
        'file_size': round(file_size_mb, 2),  # 保留两位小数
        'file_path': output_path
    }

r'''
# 示例调用
if __name__ == "__main__":
    input_video_path = r"C:\Users\herry\douyin_v0d00fg10000cqei5b7og65rmqggttqg.mp4"
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(convert_video_to_720p(input_video_path))
    print(result)
'''

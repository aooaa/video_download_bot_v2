import asyncio
import os

async def is_vp9(detect_video):
    """ 检测视频是否为VP9编码格式 """
    command = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'stream=codec_name', '-of', 'default=nw=1:nk=1', detect_video
    ]
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return stdout.decode().strip() == 'vp9'

async def is_h264(detect_video):
    """检测视频是否为H.264编码格式"""
    command = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'stream=codec_name', '-of', 'default=nw=1:nk=1', detect_video
    ]
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return stdout.decode().strip() == 'h264'

async def convert_to_h264(input_path, output_path):
    """ 将视频转换为H.264编码格式 """
    command = [
        'ffmpeg', '-i', input_path, '-c:v', 'libx264', '-c:a', 'aac', output_path
    ]
    process = await asyncio.create_subprocess_exec(*command)
    await process.wait()

async def process_video(detect_video):
    try:
        """ 检测并转换视频编码格式 """
        if not await is_h264(detect_video):
            output_path = detect_video.rsplit('.', 1)[0] + '_h264.mp4'
            await convert_to_h264(detect_video, output_path)
            return {"video_path": os.path.abspath(output_path), "ex_info": "Successfully encoded to h.264"}
        else:
            return {"video_path": os.path.abspath(detect_video), "ex_info": "No need to transcode"}
    except Exception as e:
        return f"Error occurred: {str(e)}"
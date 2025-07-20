import subprocess
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Function to get video dimensions
def sync_get_video_dimensions(video_path):
    # Run ffmpeg command to get video information
    result = subprocess.run(
        ['ffmpeg', '-i', video_path],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        encoding='utf-8',  # 指定编码为 utf-8
        errors='ignore'    # 忽略解码错误
    )
    
    # Extract the output from stderr
    output = result.stderr
    
    # Check if output is None
    if output is None:
        raise ValueError("No output from ffmpeg command")
    
    # Use regex to find the width and height
    match = re.search(r'Stream.*Video.* (\d+)x(\d+)', output)
    if match:
        width, height = match.groups()
        return {"Width": int(width), "Height": int(height)}
    else:
        raise ValueError("Could not determine video dimensions")

# Asynchronous function to call the synchronous function
async def get_video_dimensions(content):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(executor, sync_get_video_dimensions, content)
    #print(result)
    return result
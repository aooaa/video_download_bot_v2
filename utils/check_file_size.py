import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

def sync_get_file_size(file_path):
    """
    接收一个文件路径，返回该文件的大小（以MB为单位）。
    """
    if os.path.isfile(file_path):
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)  # 将字节转换为MB
        return file_size_mb
    else:
        return "文件不存在或路径不正确"

# Asynchronous function to call the synchronous function
async def get_file_size(file_path):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(executor, sync_get_file_size, file_path)
    #print(result)
    return result

# 示例用法
#if __name__ == "__main__":
#    file_path = r"C:\Users\herry\Videos\二次火爆全网的《桃花诺》，小姐姐开口就惊了！-1.mp4"
#    asyncio.run(get_file_size(file_path))
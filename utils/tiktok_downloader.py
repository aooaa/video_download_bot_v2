import asyncio
import os

from f2.apps.tiktok.dl import TiktokDownloader
from f2.apps.tiktok.handler import TiktokHandler
from f2.apps.tiktok.utils import DeviceIdManager

# from f2.log.logger import logger

# set logger level to DEBUG
# logger.setLevel("DEBUG")


async def download_tiktok_video(video_id: str, kwargs: dict):
    """
    Downloads a TikTok video using the f2 library.

    Args:
        video_id: The ID of the TikTok video to download.
        kwargs: A dictionary containing the configuration parameters for the f2 library.

    Returns:
        The path to the downloaded video file, or None if the download failed.
    """
    try:
        video = await TiktokHandler(kwargs).fetch_one_video(video_id)
        if video:
            user_path = "downloads"  # 下载目录
            await TiktokDownloader(kwargs).create_download_tasks(
                kwargs,
                aweme_datas=video._to_dict(),
                user_path=user_path,
            )
            filepath = os.path.join(user_path, f"tiktok_{video_id}.mp4")  # 构建文件路径
            return filepath
        else:
            print(f"Failed to fetch TikTok video with ID {video_id}")
            return None
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return None

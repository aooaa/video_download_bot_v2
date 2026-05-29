import asyncio
import os
from pathlib import Path
from f2.apps.douyin.handler import DouyinHandler
from f2.apps.douyin.dl import DouyinDownloader
from f2.apps.douyin.utils import AwemeIdFetcher, SecUserIdFetcher
from f2.apps.douyin.db import AsyncUserDB, AsyncVideoDB
from f2.utils.utils import extract_valid_urls

async def download_douyin_video(url: str, kwargs: dict):
    """
    使用F2库下载抖音视频
    
    Args:
        url: 抖音视频URL
        kwargs: F2库配置参数
        
    Returns:
        下载的视频文件路径，如果失败则返回None
    """
    try:
        # 提取有效URL
        valid_urls = extract_valid_urls([url])
        if not valid_urls:
            print("无法提取有效的抖音URL")
            return None
            
        # 使用F2的AwemeIdFetcher提取视频ID
        aweme_id = await AwemeIdFetcher.get_aweme_id(valid_urls[0])
        if not aweme_id:
            print("无法从URL中提取视频ID")
            return None
            
        print(f"提取到视频ID: {aweme_id}")
        
        # 获取视频数据
        video_data = await DouyinHandler(kwargs).fetch_one_video(aweme_id=aweme_id)
        if not video_data:
            print(f"无法获取视频数据，视频ID: {aweme_id}")
            return None
            
        # 创建下载目录
        user_path = Path("downloads")
        user_path.mkdir(exist_ok=True)
        
        # 初始化数据库
        async with AsyncUserDB("douyin_users.db") as user_db, \
                   AsyncVideoDB("douyin_videos.db") as video_db:
            
            # 创建下载任务并处理下载
            downloader = DouyinDownloader(kwargs)
            
            # 创建下载任务
            await downloader.create_download_tasks(
                kwargs,
                aweme_datas=video_data._to_dict(),
                user_path=user_path,
            )
        
        # 构建预期的文件路径
        # F2下载器会按照配置的命名规则保存文件，我们需要找到实际下载的文件
        video_files = list(user_path.glob(f"*{aweme_id}*.mp4"))
        if video_files:
            return str(video_files[0])
        else:
            # 如果没找到，尝试其他可能的扩展名
            video_files = list(user_path.glob(f"*{aweme_id}*"))
            if video_files:
                return str(video_files[0])
            else:
                print(f"无法找到下载的视频文件，视频ID: {aweme_id}")
                return None
                
    except Exception as e:
        print(f"下载抖音视频时发生错误: {str(e)}")
        return None

async def get_douyin_video_info(url: str, kwargs: dict):
    """
    获取抖音视频信息
    
    Args:
        url: 抖音视频URL
        kwargs: F2库配置参数
        
    Returns:
        视频信息字典
    """
    try:
        # 提取有效URL
        valid_urls = extract_valid_urls([url])
        if not valid_urls:
            return None
            
        # 提取视频ID
        aweme_id = await AwemeIdFetcher.get_aweme_id(valid_urls[0])
        if not aweme_id:
            return None
            
        # 获取视频数据
        video_data = await DouyinHandler(kwargs).fetch_one_video(aweme_id=aweme_id)
        if video_data:
            return video_data._to_dict()
        else:
            return None
            
    except Exception as e:
        print(f"获取抖音视频信息时发生错误: {str(e)}")
        return None

async def download_douyin_user_videos(sec_user_id: str, kwargs: dict, max_count: int = 20):
    """
    下载抖音用户的所有视频
    
    Args:
        sec_user_id: 用户ID
        kwargs: F2库配置参数
        max_count: 最大下载数量
        
    Returns:
        下载的视频文件路径列表
    """
    try:
        user_path = Path("downloads")
        user_path.mkdir(exist_ok=True)
        
        downloaded_files = []
        
        async with AsyncUserDB("douyin_users.db") as user_db, \
                   AsyncVideoDB("douyin_videos.db") as video_db:
            
            downloader = DouyinDownloader(kwargs)
            
            # 获取用户发布的作品
            async for aweme_data_list in DouyinHandler(kwargs).fetch_user_post_videos(
                sec_user_id=sec_user_id,
                max_cursor=0,
                page_counts=20,
                max_counts=max_count
            ):
                for aweme_data in aweme_data_list._to_list():
                    # 创建下载任务
                    await downloader.create_download_tasks(
                        kwargs,
                        aweme_datas=aweme_data,
                        user_path=user_path,
                    )
                    
                    # 找到下载的文件
                    aweme_id = aweme_data.get('aweme_id')
                    video_files = list(user_path.glob(f"*{aweme_id}*.mp4"))
                    if video_files:
                        downloaded_files.append(str(video_files[0]))
                        
        return downloaded_files
        
    except Exception as e:
        print(f"下载抖音用户视频时发生错误: {str(e)}")
        return []

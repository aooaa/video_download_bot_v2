#!/usr/bin/env python3
"""
抖音下载器测试脚本
用于测试新的F2抖音下载模块是否正常工作
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.douyin_downloader import download_douyin_video, get_douyin_video_info
from config_example import kwargs

async def test_douyin_downloader():
    """测试抖音下载器功能"""
    print("=== 抖音下载器测试 ===")
    
    # 测试用的抖音视频URL（公开可访问的测试视频）
    test_urls = [
        "https://v.douyin.com/iRNBho6u/",  # 示例URL，需要替换为实际可用的URL
        "https://www.douyin.com/video/7298145681699622182",
    ]
    
    for url in test_urls:
        print(f"\n测试URL: {url}")
        
        # 测试获取视频信息
        print("1. 测试获取视频信息...")
        try:
            video_info = await get_douyin_video_info(url, kwargs)
            if video_info:
                print("✅ 成功获取视频信息")
                print(f"   视频ID: {video_info.get('aweme_id', '未知')}")
                print(f"   描述: {video_info.get('desc', '未知')}")
                print(f"   作者: {video_info.get('author', {}).get('nickname', '未知')}")
            else:
                print("❌ 获取视频信息失败")
                continue
        except Exception as e:
            print(f"❌ 获取视频信息时出错: {e}")
            continue
        
        # 测试下载视频
        print("2. 测试下载视频...")
        try:
            video_path = await download_douyin_video(url, kwargs)
            if video_path:
                print(f"✅ 视频下载成功: {video_path}")
                
                # 检查文件是否存在
                if os.path.exists(video_path):
                    file_size = os.path.getsize(video_path)
                    print(f"   文件大小: {file_size / 1024 / 1024:.2f} MB")
                else:
                    print("❌ 下载的文件不存在")
            else:
                print("❌ 视频下载失败")
        except Exception as e:
            print(f"❌ 下载视频时出错: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    # 检查F2是否安装
    try:
        import f2
        print("✅ F2库已安装")
    except ImportError:
        print("❌ F2库未安装，请运行: pip install f2")
        sys.exit(1)
    
    # 运行测试
    asyncio.run(test_douyin_downloader())
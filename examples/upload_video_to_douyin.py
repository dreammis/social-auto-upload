"""
抖音视频批量上传示例
提供批量上传视频到抖音的功能
"""

import asyncio
from pathlib import Path
import sys
import os
from typing import List
from playwright.async_api import BrowserContext
import json

# 添加项目根目录到 Python 路径
current_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(current_dir))

# 初始化必要的目录
os.makedirs(current_dir / "cookies" / "douyin_uploader", exist_ok=True)
os.makedirs(current_dir / ".playwright" / "user_data" / "douyin", exist_ok=True)

from utils.log import douyin_logger
from uploader.douyin_uploader.modules.video import DouYinVideo
from uploader.douyin_uploader.utils.db_helper import DBHelper
from utils.playwright_helper import PlaywrightHelper

async def batch_upload_videos(video_paths: List[str], context: BrowserContext, account_file: Path, daily_times: List[int] = [16]) -> None:
    """批量上传多个视频"""
    uploader = DouYinVideo()
    for video_path in video_paths:
        douyin_logger.info(f"开始上传视频: {video_path}")
        try:
            await uploader.batch_upload(
                context=context,
                video_dir=video_path,
                account_file=account_file,
                daily_times=daily_times
            )
        except Exception as e:
            douyin_logger.error(f"上传视频 {video_path} 失败: {str(e)}")

async def upload_single_video(video_path: str, context: BrowserContext, account_file: Path, daily_times: List[int] = [16]) -> None:
    """上传单个视频"""
    uploader = DouYinVideo()
    douyin_logger.info(f"开始上传视频: {video_path}")
    try:
        await uploader.batch_upload(
            context=context,
            video_dir=video_path,
            account_file=account_file,
            daily_times=daily_times
        )
    except Exception as e:
        douyin_logger.error(f"上传视频 {video_path} 失败: {str(e)}")

async def main():
    """主函数"""
    try:
        # 创建 PlaywrightHelper 实例
        playwright_helper = PlaywrightHelper()
        
        # 检查并安装Playwright浏览器
        if not PlaywrightHelper.install_browser():
            douyin_logger.error("安装Playwright浏览器失败")
            sys.exit(1)
        
        # 配置路径
        video_paths = [
            r"F:\向阳也有米\24版本\12月\1125-19-教人7",
            r"F:\向阳也有米\24版本\12月\1125-20-学历8"
        ]  # 示例视频路径
        
        # 从数据库获取cookie路径
        db_helper = DBHelper()
        nickname = "李子🍐"  # 这里需要替换为实际的账号昵称
        cookie_path = db_helper.get_cookie_path_by_nickname(nickname)
        if not cookie_path:
            douyin_logger.error(f"未找到账号 {nickname} 的cookie信息")
            sys.exit(1)
        
        account_file = Path(cookie_path)
        if not account_file.exists():
            douyin_logger.info(f"Cookie文件不存在，创建新文件: {account_file}")
            with open(account_file, 'w', encoding='utf-8') as f:
                json.dump({"cookies": [], "origins": []}, f)
            douyin_logger.info(f"新建Cookie文件成功: {account_file}")
        
        # 使用上下文管理器管理浏览器资源
        async with playwright_helper.get_context() as context:
            if len(video_paths) > 1:
                await batch_upload_videos(video_paths, context, account_file)
            else:
                await upload_single_video(video_paths[0], context, account_file)
    except KeyboardInterrupt:
        douyin_logger.warning("用户中断发布程序")
    except Exception as e:
        douyin_logger.error(f"程序执行出错: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
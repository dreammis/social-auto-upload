"""
抖音视频批量上传示例
提供批量上传视频到抖音的功能
"""

import asyncio
from pathlib import Path
import sys
import os

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
        video_dir = r"F:\向阳也有米\24版本\12月\1125-19-教人7"  # 使用实际的视频目录路径
        
        # 从数据库获取cookie路径
        db_helper = DBHelper()
        nickname = "李子🍐"  # 这里需要替换为实际的账号昵称
        cookie_path = db_helper.get_cookie_path_by_nickname(nickname)
        if not cookie_path:
            douyin_logger.error(f"未找到账号 {nickname} 的cookie信息")
            sys.exit(1)
            
        account_file = Path(cookie_path)
        if not account_file.exists():
            douyin_logger.error(f"Cookie文件不存在: {account_file}")
            sys.exit(1)
        
        # 创建上传器实例
        uploader = DouYinVideo()
        
        # 使用上下文管理器管理浏览器资源
        async with playwright_helper.get_context() as context:
            # 执行批量上传
            await uploader.batch_upload(
                context=context,
                video_dir=video_dir,
                account_file=account_file,
                daily_times=[16]  # 设置每天16点发布
            )
            
    except KeyboardInterrupt:
        douyin_logger.warning("用户中断上传程序")
    except Exception as e:
        douyin_logger.error(f"程序执行出错: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
# -*- coding: utf-8 -*-
"""
抖音Cookie获取示例
用于获取和验证抖音账号的Cookie
"""

import asyncio
import sys
from pathlib import Path
import os
from typing import Optional
import platform

# 获取项目根目录的绝对路径
BASE_DIR = Path(os.path.dirname(os.path.dirname(__file__)))
# 添加项目根目录到 Python 路径
sys.path.append(str(BASE_DIR))

from utils.log import douyin_logger
from utils.playwright_helper import PlaywrightHelper
from uploader.douyin_uploader import account_manager

def parse_args() -> Optional[str]:
    """
    解析命令行参数
    Returns:
        Optional[str]: 账号昵称，如果未提供则返回None
    """
    if len(sys.argv) > 1:
        return sys.argv[1]
    return None

def setup_platform():
    """
    设置平台特定的配置
    """
    if platform.system() == 'Windows':
        # Windows平台特定设置
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        # 设置PLAYWRIGHT_BROWSERS_PATH环境变量
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(BASE_DIR / '.playwright' / 'browsers')
    
    # 确保浏览器目录存在
    browser_path = BASE_DIR / '.playwright' / 'browsers'
    browser_path.mkdir(parents=True, exist_ok=True)

async def main() -> None:
    """主函数"""
    try:
        # 设置平台配置
        setup_platform()
        
        # 安装浏览器
        try:
            if not PlaywrightHelper.install_browser():
                douyin_logger.error("浏览器安装失败")
                sys.exit(1)
        except Exception as e:
            douyin_logger.error(f"浏览器安装出错: {str(e)}")
            douyin_logger.info("尝试使用系统安装的浏览器...")

        # 获取账号昵称
        nickname = parse_args() or "李子🍐"  # 如果未提供参数，使用默认昵称
        douyin_logger.info(f"准备获取账号 {nickname} 的Cookie")
        
        # 准备Cookie文件路径
        cookie_filename = f"{nickname}.json"
        cookie_dir = BASE_DIR / "cookies" / "douyin_uploader"
        cookie_dir.mkdir(parents=True, exist_ok=True)
        account_file = str(cookie_dir / cookie_filename)
        
        # 设置Cookie并获取账号信息
        douyin_logger.info(f"开始设置账号...")
        try:
            result = await account_manager.setup_account(account_file, handle=True)
        except Exception as e:
            douyin_logger.error(f"账号设置失败: {str(e)}")
            if "NotImplementedError" in str(e):
                douyin_logger.error("Windows平台运行错误，请确保：")
                douyin_logger.error("1. 使用管理员权限运行")
                douyin_logger.error("2. 安装了最新版本的Python和Playwright")
                douyin_logger.error("3. 系统已安装Microsoft Visual C++ Redistributable")
            sys.exit(1)
        
        if result['success']:
            douyin_logger.success(result['message'])
            douyin_logger.info(f"Cookie文件路径: {result['cookie_file']}")
            
            # 打印用户信息
            user_info = result['user_info']
            douyin_logger.info("账号信息:")
            douyin_logger.info(f"  昵称: {user_info['nickname']}")
            douyin_logger.info(f"  抖音号: {user_info['douyin_id']}")
            douyin_logger.info(f"  签名: {user_info['signature']}")
            douyin_logger.info(f"  关注数: {user_info['following_count']}")
            douyin_logger.info(f"  粉丝数: {user_info['fans_count']}")
            douyin_logger.info(f"  获赞数: {user_info['likes_count']}")
            douyin_logger.info(f"  更新时间: {user_info['updated_at']}")
        else:
            douyin_logger.error(f"设置失败: {result['message']}")
            sys.exit(1)

    except KeyboardInterrupt:
        douyin_logger.warning("用户中断操作")
        sys.exit(1)
    except Exception as e:
        douyin_logger.error(f"程序执行出错: {str(e)}")
        if "NotImplementedError" in str(e):
            douyin_logger.error("Windows平台运行错误，请尝试：")
            douyin_logger.error("1. 使用管理员权限运行")
            douyin_logger.error("2. 重新安装 playwright: pip install playwright --upgrade")
            douyin_logger.error("3. 安装浏览器: playwright install chromium")
        sys.exit(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        douyin_logger.error(f"程序启动失败: {str(e)}")
        if "NotImplementedError" in str(e):
            douyin_logger.error("Windows平台运行错误，请按以下步骤操作：")
            douyin_logger.error("1. 使用管理员权限运行命令提示符")
            douyin_logger.error("2. 运行: pip uninstall playwright")
            douyin_logger.error("3. 运行: pip install playwright --upgrade")
            douyin_logger.error("4. 运行: playwright install chromium")
            douyin_logger.error("5. 安装 Microsoft Visual C++ Redistributable")
        sys.exit(1)

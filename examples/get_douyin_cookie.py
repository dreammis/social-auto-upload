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
import warnings
import signal
from contextlib import asynccontextmanager

# 获取项目根目录的绝对路径
BASE_DIR = Path(os.path.dirname(os.path.dirname(__file__)))

# 将项目根目录添加到Python路径
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 导入必要的模块
from utils.log import douyin_logger
from uploader.douyin_uploader import account_manager
from uploader.douyin_uploader.utils.playwright_helper import PlaywrightHelper

# 全局变量用于存储事件循环
loop = None

def handle_shutdown(signum, frame):
    """处理关闭信号"""
    douyin_logger.info("接收到关闭信号，正在清理资源...")
    if loop and loop.is_running():
        loop.stop()
        # 确保事件循环完全停止
        loop.close()
    # 强制退出程序
    os._exit(0)

def parse_args() -> Optional[str]:
    """
    解析命令行参数
    Returns:
        Optional[str]: 抖音账号ID，如果未提供则返回None
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

@asynccontextmanager
async def managed_resources():
    """资源管理器"""
    try:
        yield
    finally:
        # 确保所有Playwright资源被清理
        try:
            await PlaywrightHelper.cleanup_resources()
        except Exception as e:
            douyin_logger.error(f"清理Playwright资源时发生错误: {str(e)}")

async def main() -> None:
    """主函数"""
    try:
        # 设置平台配置
        setup_platform()
        
        # 安装浏览器
        try:
            if not PlaywrightHelper.install_browser():
                douyin_logger.error("浏览器安装失败")
                os._exit(1)
        except Exception as e:
            douyin_logger.error(f"浏览器安装出错: {str(e)}")
            douyin_logger.info("尝试使用系统安装的浏览器...")

        # 获取账号信息
        account_id = parse_args() or "1441505684"  # 如果未提供参数，使用默认账号ID
        account_info = account_manager.db_helper.get_account_info(account_id)
        
        if not account_info:
            douyin_logger.error(f"未找到账号信息: {account_id}")
            os._exit(1)
            
        nickname = account_info['nickname']
        douyin_logger.info(f"准备获取账号 {nickname} 的Cookie")
        
        cookie_path = account_manager.db_helper.get_account_cookie_path(account_id)
        if not cookie_path:
            douyin_logger.error(f"未找到账号Cookie: {account_id}")
        
        account_file = str(cookie_path[0])
        
        async with managed_resources():
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
                os._exit(1)
            
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
                
                # 任务完成，主动退出程序
                douyin_logger.info("Cookie获取和账号设置已完成，程序退出")
                # 使用os._exit强制退出，避免等待其他任务
                os._exit(0)
            else:
                douyin_logger.error(f"设置失败: {result['message']}")
                os._exit(1)

    except KeyboardInterrupt:
        douyin_logger.warning("用户中断操作")
        os._exit(1)
    except Exception as e:
        douyin_logger.error(f"程序执行出错: {str(e)}")
        if "NotImplementedError" in str(e):
            douyin_logger.error("Windows平台运行错误，请尝试：")
            douyin_logger.error("1. 使用管理员权限运行")
            douyin_logger.error("2. 重新安装 playwright: pip install playwright --upgrade")
            douyin_logger.error("3. 安装浏览器: playwright install chromium")
        os._exit(1)

if __name__ == '__main__':
    # 忽略资源清理警告
    warnings.filterwarnings("ignore", category=ResourceWarning)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # 创建新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # 运行主函数
        loop.run_until_complete(main())
    except Exception as e:
        douyin_logger.error(f"程序启动失败: {str(e)}")
        if "NotImplementedError" in str(e):
            douyin_logger.error("Windows平台运行错误，请按以下步骤操作：")
            douyin_logger.error("1. 使用管理员权限运行命令提示符")
            douyin_logger.error("2. 运行: pip uninstall playwright")
            douyin_logger.error("3. 运行: pip install playwright --upgrade")
            douyin_logger.error("4. 运行: playwright install chromium")
            douyin_logger.error("5. 安装 Microsoft Visual C++ Redistributable")
        os._exit(1)
    finally:
        # 关闭事件循环
        try:
            pending = asyncio.all_tasks(loop)
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception as e:
            douyin_logger.error(f"清理任务时发生错误: {str(e)}")
        finally:
            loop.close()

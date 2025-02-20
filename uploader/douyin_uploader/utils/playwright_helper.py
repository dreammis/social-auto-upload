"""
Playwright辅助工具
提供Playwright相关的辅助功能
"""

import os
import sys
import subprocess
from typing import Optional
from utils.log import douyin_logger
from playwright.async_api import async_playwright

class PlaywrightHelper:
    """Playwright辅助工具类"""
    
    @staticmethod
    def install_browser() -> bool:
        """
        安装Playwright浏览器
        Returns:
            bool: 安装是否成功
        """
        try:
            # 检查是否已安装浏览器
            browser_path = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', None)
            if browser_path and os.path.exists(os.path.join(browser_path, 'chromium')):
                douyin_logger.info("浏览器已安装")
                return True
            
            douyin_logger.info("开始安装浏览器...")
            # 使用subprocess运行playwright install命令
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                douyin_logger.success("浏览器安装成功")
                return True
            else:
                douyin_logger.error(f"浏览器安装失败: {result.stderr}")
                return False
                
        except Exception as e:
            douyin_logger.error(f"安装浏览器时发生错误: {str(e)}")
            return False
    
    @staticmethod
    def get_browser_path() -> Optional[str]:
        """
        获取浏览器安装路径
        Returns:
            Optional[str]: 浏览器路径，如果未找到则返回None
        """
        try:
            browser_path = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', None)
            if browser_path and os.path.exists(os.path.join(browser_path, 'chromium')):
                return browser_path
            return None
        except Exception as e:
            douyin_logger.error(f"获取浏览器路径失败: {str(e)}")
            return None
            
    @staticmethod
    async def cleanup_resources() -> None:
        """
        清理Playwright资源
        """
        try:
            # 获取当前的playwright实例
            playwright = async_playwright()._impl_obj
            if playwright:
                # 停止所有浏览器实例
                for browser in playwright.chromium.browsers:
                    await browser.close()
                # 停止playwright服务
                await playwright.stop()
                douyin_logger.info("Playwright资源已清理")
        except Exception as e:
            douyin_logger.error(f"清理Playwright资源失败: {str(e)}") 
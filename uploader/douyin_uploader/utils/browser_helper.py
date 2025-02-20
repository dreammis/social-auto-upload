"""
浏览器资源管理助手
提供浏览器资源的创建、关闭和清理功能
"""

from typing import Optional, Tuple
from pathlib import Path
from playwright.async_api import Page, Browser, BrowserContext, async_playwright
from utils.log import douyin_logger

class BrowserHelper:
    """浏览器资源管理助手类"""
    
    @staticmethod
    async def create_browser_context(
        headless: bool = True,
        user_data_dir: Optional[str] = None
    ) -> Tuple[Browser, BrowserContext]:
        """
        创建浏览器和上下文
        Args:
            headless: 是否使用无头模式
            user_data_dir: 用户数据目录路径
        Returns:
            Tuple[Browser, BrowserContext]: 浏览器和上下文对象
        """
        try:
            playwright = await async_playwright().start()
            browser_args = [
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ]
            
            # 创建浏览器实例
            if user_data_dir:
                context = await playwright.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=headless,
                    args=browser_args
                )
                browser = context.browser
            else:
                browser = await playwright.chromium.launch(
                    headless=headless,
                    args=browser_args
                )
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                )
            
            return browser, context
            
        except Exception as e:
            douyin_logger.error(f"创建浏览器上下文失败: {str(e)}")
            raise
    
    @staticmethod
    async def close_resources(
        page: Optional[Page] = None,
        context: Optional[BrowserContext] = None,
        browser: Optional[Browser] = None
    ) -> None:
        """
        按顺序关闭Playwright资源
        Args:
            page: Playwright页面对象
            context: 浏览器上下文
            browser: 浏览器实例
        """
        if page:
            try:
                douyin_logger.info("正在关闭页面...")
                await page.close()
                douyin_logger.info("页面已关闭")
            except Exception as e:
                douyin_logger.warning(f"关闭页面时发生错误: {str(e)}")
            
        if context:
            try:
                douyin_logger.info("正在关闭浏览器上下文...")
                await context.close()
                douyin_logger.info("浏览器上下文已关闭")
            except Exception as e:
                douyin_logger.warning(f"关闭浏览器上下文时发生错误: {str(e)}")
                
        if browser:
            try:
                douyin_logger.info("正在关闭浏览器...")
                await browser.close()
                douyin_logger.info("浏览器已关闭")
            except Exception as e:
                douyin_logger.warning(f"关闭浏览器时发生错误: {str(e)}") 
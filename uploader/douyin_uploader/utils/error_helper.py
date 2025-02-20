"""
错误处理助手
提供统一的错误处理和异常情况管理功能
"""

import os
from datetime import datetime
from typing import Optional
from playwright.async_api import Page
from utils.log import douyin_logger

class ErrorHelper:
    """错误处理助手类"""
    
    def __init__(self):
        self.error_dir = "error_logs"
        os.makedirs(self.error_dir, exist_ok=True)
    
    def _get_error_filename(self, prefix: str) -> str:
        """
        生成错误文件名
        Args:
            prefix: 文件名前缀
        Returns:
            str: 完整的文件名
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.error_dir, f"{prefix}_{timestamp}")
    
    async def save_error_screenshot(
        self,
        page: Page,
        error: Exception,
        prefix: str = "error"
    ) -> Optional[str]:
        """
        保存错误现场截图
        Args:
            page: Playwright页面对象
            error: 异常对象
            prefix: 文件名前缀
        Returns:
            Optional[str]: 截图文件路径
        """
        try:
            screenshot_path = f"{self._get_error_filename(prefix)}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            douyin_logger.info(f"错误截图已保存: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            douyin_logger.error(f"保存错误截图失败: {str(e)}")
            return None
    
    async def save_error_page_source(
        self,
        page: Page,
        error: Exception,
        prefix: str = "error"
    ) -> Optional[str]:
        """
        保存错误页面源码
        Args:
            page: Playwright页面对象
            error: 异常对象
            prefix: 文件名前缀
        Returns:
            Optional[str]: 源码文件路径
        """
        try:
            source_path = f"{self._get_error_filename(prefix)}.html"
            with open(source_path, "w", encoding="utf-8") as f:
                f.write(await page.content())
            douyin_logger.info(f"页面源码已保存: {source_path}")
            return source_path
        except Exception as e:
            douyin_logger.error(f"保存页面源码失败: {str(e)}")
            return None
    
    async def save_error_context(
        self,
        page: Page,
        error: Exception,
        prefix: str = "error"
    ) -> tuple[Optional[str], Optional[str]]:
        """
        保存完整的错误现场信息
        Args:
            page: Playwright页面对象
            error: 异常对象
            prefix: 文件名前缀
        Returns:
            tuple[Optional[str], Optional[str]]: (截图路径, 源码路径)
        """
        screenshot_path = await self.save_error_screenshot(page, error, prefix)
        source_path = await self.save_error_page_source(page, error, prefix)
        return screenshot_path, source_path 
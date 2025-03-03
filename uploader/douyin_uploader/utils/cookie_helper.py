"""
Cookie管理助手
提供cookie的保存、验证和状态管理功能
"""

import os
from typing import Optional, List, Dict, Any
from playwright.async_api import BrowserContext, Page
from utils.log import douyin_logger
import json
from pathlib import Path
from loguru import logger

class CookieHelper:
    """Cookie管理助手类"""
    
    def __init__(self, cookie_dir: str = "cookies"):
        """
        初始化Cookie助手
        Args:
            cookie_dir: cookie存储目录
        """
        self.cookie_dir = Path(cookie_dir)
        self.cookie_dir.mkdir(exist_ok=True)
    
    async def save_cookie_state(
        self,
        context: BrowserContext,
        cookie_file: str
    ) -> bool:
        """
        保存浏览器上下文的cookie状态
        Args:
            context: 浏览器上下文
            cookie_file: cookie文件路径
        Returns:
            bool: 保存是否成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(cookie_file), exist_ok=True)
            
            # 保存cookie状态到文件
            douyin_logger.info(f"保存cookie状态到文件: {cookie_file}")
            await context.storage_state(path=cookie_file)
            
            # 验证文件大小
            if os.path.getsize(cookie_file) > 100 * 1024:  # 100KB
                douyin_logger.warning(f"Cookie文件大小超过限制: {cookie_file}")
                return False
                
            douyin_logger.success(f"Cookie保存成功: {cookie_file}")
            return True
            
        except Exception as e:
            douyin_logger.error(f"保存cookie状态失败: {str(e)}")
            return False
    
    @staticmethod
    def verify_cookie_file(cookie_file: str) -> bool:
        """
        验证cookie文件是否存在且有效
        Args:
            cookie_file: cookie文件路径
        Returns:
            bool: 文件是否有效
        """
        try:
            if not os.path.exists(cookie_file):
                douyin_logger.warning(f"Cookie文件不存在: {cookie_file}")
                return False
                
            if os.path.getsize(cookie_file) == 0:
                douyin_logger.warning(f"Cookie文件为空: {cookie_file}")
                return False
                
            return True
            
        except Exception as e:
            douyin_logger.error(f"验证cookie文件失败: {str(e)}")
            return False
    
    async def save_cookies(self, page: Page, cookie_file: str) -> bool:
        """
        保存cookies到文件
        Args:
            page: Playwright页面对象
            cookie_file: cookie文件名
        Returns:
            bool: 是否保存成功
        """
        try:
            cookies = await page.context.cookies()
            cookie_path = self.cookie_dir / cookie_file
            cookie_path.write_text(json.dumps(cookies, ensure_ascii=False, indent=2))
            logger.info(f"Cookies已保存到: {cookie_path}")
            return True
        except Exception as e:
            logger.error(f"保存cookies失败: {str(e)}")
            return False
            
    async def load_cookies(self, page: Page, cookie_file: str) -> bool:
        """
        从文件加载cookies
        Args:
            page: Playwright页面对象
            cookie_file: cookie文件名
        Returns:
            bool: 是否加载成功
        """
        try:
            cookie_path = self.cookie_dir / cookie_file
            if not cookie_path.exists():
                logger.warning(f"Cookie文件不存在: {cookie_path}")
                return False
                
            cookies = json.loads(cookie_path.read_text(encoding='utf-8'))
            await page.context.add_cookies(cookies)
            logger.info(f"已加载cookies: {cookie_path}")
            return True
        except Exception as e:
            logger.error(f"加载cookies失败: {str(e)}")
            return False
            
    def get_cookie_files(self) -> List[str]:
        """
        获取所有cookie文件列表
        Returns:
            List[str]: cookie文件名列表
        """
        try:
            return [f.name for f in self.cookie_dir.glob("*.json")]
        except Exception as e:
            logger.error(f"获取cookie文件列表失败: {str(e)}")
            return []
            
    def delete_cookie(self, cookie_file: str) -> bool:
        """
        删除指定的cookie文件
        Args:
            cookie_file: cookie文件名
        Returns:
            bool: 是否删除成功
        """
        try:
            cookie_path = self.cookie_dir / cookie_file
            if cookie_path.exists():
                cookie_path.unlink()
                logger.info(f"已删除cookie文件: {cookie_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除cookie文件失败: {str(e)}")
            return False 
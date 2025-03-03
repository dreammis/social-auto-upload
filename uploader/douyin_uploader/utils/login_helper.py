"""
登录状态检查助手
提供登录状态的检查和验证功能
"""

from typing import Optional, Dict, Any, Tuple
from playwright.async_api import Page, Browser, Response
from loguru import logger
from .page_check_helper import PageCheckHelper
from .cookie_helper import CookieHelper

class LoginHelper:
    """登录状态检查助手类"""
    
    # 页面URL常量
    EXPECTED_URL = "https://creator.douyin.com/creator-micro/home"
    LOGIN_URL = "https://creator.douyin.com/"
    
    def __init__(self, cookie_dir: str = "cookies"):
        """
        初始化登录助手
        Args:
            cookie_dir: cookie存储目录
        """
        self.cookie_helper = CookieHelper(cookie_dir)
        
    async def navigate_to_creator_center(self, page: Page) -> Tuple[bool, str]:
        """
        导航到创作者中心
        Args:
            page: Playwright页面对象
        Returns:
            Tuple[bool, str]: (是否成功, 最终URL)
        """
        try:
            logger.info("导航到创作者中心...")
            response = await page.goto(
                self.EXPECTED_URL,
                wait_until="networkidle",
                timeout=30000
            )
            
            if not response:
                logger.error("页面加载失败: 无响应")
                return False, ""
                
            if response.status >= 400:
                logger.error(f"页面加载失败: HTTP {response.status}")
                return False, ""
                
            # 获取最终URL（处理重定向）
            final_url = page.url
            logger.info(f"最终页面URL: {final_url}")
            
            # 检查是否重定向到登录页
            if self.LOGIN_URL in final_url:
                logger.info("页面已重定向到登录页面")
                return True, final_url
            
            # 验证页面加载
            if not await PageCheckHelper.check_page_loaded(page):
                logger.warning("页面加载验证失败")
                return False, final_url
                
            logger.info("页面导航成功")
            return True, final_url
            
        except Exception as e:
            logger.error(f"导航到创作者中心失败: {str(e)}")
            return False, ""
        
    async def check_login_status(self, page: Page, browser: Optional[Browser] = None, headless: bool = True) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        检查登录状态
        Args:
            page: Playwright页面对象
            browser: 浏览器实例(可选)
            headless: 是否无头模式
        Returns:
            Tuple[bool, Optional[Dict[str, Any]]]: (是否已登录, 用户信息)
        """
        try:
            # 验证登录状态
            is_logged_in = await PageCheckHelper.verify_login_status(page)
            if not is_logged_in:
                logger.warning("登录状态验证失败")
                return False, None
                
            # 获取用户信息
            try:
                user_info = await PageCheckHelper.get_user_info(page)
                if user_info and user_info.get('nickname'):  # 只检查昵称是否存在
                    logger.info(f"当前登录用户: {user_info['nickname']}")
                    return True, user_info
            except Exception as e:
                logger.warning(f"获取用户信息时出错: {str(e)}")
                
            # 即使获取用户信息失败,只要验证通过就返回True
            return True, None
            
        except Exception as e:
            logger.error(f"检查登录状态时出错: {str(e)}")
            return False, None
            
    async def verify_cookie_and_get_user_info(
        self, 
        page: Page,
        cookie_file: str,
        headless: bool = True
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        验证cookie并获取用户信息
        Args:
            page: Playwright页面对象
            cookie_file: cookie文件名
            headless: 是否无头模式
        Returns:
            Tuple[bool, Optional[Dict[str, Any]]]: (是否验证成功, 用户信息)
        """
        try:
            # 加载cookies
            if not await self.cookie_helper.load_cookies(page, cookie_file):
                return False, None
                
            # 导航到创作者平台
            success, final_url = await self.navigate_to_creator_center(page)
            if not success:
                return False, None
            
            # 验证登录状态
            return await self.check_login_status(page, None, headless)
            
        except Exception as e:
            logger.error(f"验证cookie时出错: {str(e)}")
            return False, None
            
    async def wait_for_login(self, page: Page, timeout: int = 300000) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        等待用户完成登录
        Args:
            page: Playwright页面对象
            timeout: 超时时间(毫秒)
        Returns:
            Tuple[bool, Optional[Dict[str, Any]]]: (是否登录成功, 用户信息)
        """
        try:
            # 等待URL变化
            await page.wait_for_url(self.EXPECTED_URL, timeout=timeout)
            logger.info("检测到登录成功")
            
            # 验证登录状态
            return await self.check_login_status(page)
            
        except Exception as e:
            logger.error(f"等待登录超时: {str(e)}")
            return False, None
            
    async def save_login_state(self, page: Page, cookie_file: str) -> bool:
        """
        保存登录状态
        Args:
            page: Playwright页面对象
            cookie_file: cookie文件名
        Returns:
            bool: 是否保存成功
        """
        try:
            # 验证当前是否已登录
            is_logged_in, _ = await self.check_login_status(page)
            if not is_logged_in:
                logger.warning("当前未登录,无法保存登录状态")
                return False
                
            # 保存cookies
            return await self.cookie_helper.save_cookies(page, cookie_file)
            
        except Exception as e:
            logger.error(f"保存登录状态失败: {str(e)}")
            return False 
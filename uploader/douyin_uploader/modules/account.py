"""
抖音账号管理模块
提供cookie验证、生成等功能
"""

from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from playwright.async_api import Page, Browser, BrowserContext

# 使用绝对导入
from utils.log import douyin_logger

# 使用相对导入访问douyin_uploader包内的模块
from ..utils.browser_helper import BrowserHelper
from ..utils.cookie_helper import CookieHelper
from ..utils.login_helper import LoginHelper
from ..utils.error_helper import ErrorHelper
from ..utils.db_helper import DBHelper
from ..utils.cookie_sync_manager import CookieSyncManager

class AccountManager:
    """抖音账号管理类"""
    
    def __init__(self):
        # 初始化各个助手类
        self.browser_helper = BrowserHelper()
        self.cookie_helper = CookieHelper()
        self.login_helper = LoginHelper()
        self.error_helper = ErrorHelper()
        self.db_helper = DBHelper(platform="douyin")
        self.cookie_sync_manager = CookieSyncManager()  # 添加同步管理器
        
        # 设置浏览器用户数据目录
        self.user_data_dir = Path(".playwright/user_data/douyin")
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_account_dirs(self, account_id: str) -> tuple[Path, Path]:
        """获取账号相关目录
        Args:
            account_id: 账号ID
        Returns:
            tuple[Path, Path]: (user_data_dir, cookie_file)
        """
        # 为每个账号创建独立的用户数据目录
        user_data_dir = self.user_data_dir / account_id
        
        # 修改为正确的cookie保存路径
        cookie_file = Path("cookies/douyin_uploader") / f"{account_id}.json"
        
        # 确保目录存在
        cookie_file.parent.mkdir(parents=True, exist_ok=True)
        user_data_dir.mkdir(parents=True, exist_ok=True)
        
        return user_data_dir, cookie_file
        
    async def _handle_sync_after_operation(
        self,
        account_id: str,
        operation_name: str
    ) -> None:
        """处理操作后的同步
        Args:
            account_id: 账号ID
            operation_name: 操作名称
        """
        try:
            user_data_dir, cookie_file = self._get_account_dirs(account_id)
            await self.cookie_sync_manager.sync_from_profile_to_file(
                user_data_dir,
                cookie_file,
                account_id
            )
        except Exception as e:
            douyin_logger.error(f"操作后同步失败 [{operation_name}]: {str(e)}")

    async def _verify_cookie_and_get_user_info(self, account_file: str, headless: bool = True) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        验证cookie并获取用户信息的通用方法
        Args:
            account_file: cookie文件路径
            headless: 是否使用无头模式，默认为True
        Returns:
            tuple[bool, Optional[Dict[str, Any]]]: (是否成功, 用户信息)
        """
        if not self.cookie_helper.verify_cookie_file(account_file):
            return False, None
            
        browser = None
        context = None
        page = None
        
        try:
            # 创建浏览器和上下文
            browser, context = await self.browser_helper.create_browser_context(
                headless=headless,
                user_data_dir=str(self.user_data_dir)  # 使用持久化的用户数据目录
            )
            
            # 创建新页面并加载cookie
            page = await context.new_page()
            
            # 注入stealth.js脚本
            with open('utils/stealth.min.js', 'r', encoding='utf-8') as f:
                stealth_js = f.read()
            await page.add_init_script(stealth_js)
            
            await context.storage_state(path=account_file)
            
            # 导航到创作者中心
            if not await self.login_helper.navigate_to_creator_center(page):
                return False, None
            
            # 检查登录状态并获取用户信息
            is_logged_in, user_info = await self.login_helper.check_login_status(page)
            return is_logged_in, user_info
                
        except Exception as e:
            douyin_logger.error(f"验证cookie时发生错误: {str(e)}")
            if page:
                await self.error_helper.save_error_context(page, e, "verify_cookie")
            return False, None
            
        finally:
            await self.browser_helper.close_resources(page, context, browser)

    async def cookie_gen(self, account_file: str) -> Dict[str, Any]:
        """
        生成抖音cookie文件
        Args:
            account_file: cookie文件路径
        Returns:
            Dict[str, Any]: 包含用户信息的结果字典
        """
        browser = None
        context = None
        page = None
        
        try:
            # 创建浏览器和上下文（使用持久化模式）
            browser, context = await self.browser_helper.create_browser_context(
                headless=False,
                user_data_dir=str(self.user_data_dir)
            )
            
            douyin_logger.info("创建新页面...")
            page = await context.new_page()
            
            # 导航到创作者中心
            if not await self.login_helper.navigate_to_creator_center(page):
                raise Exception("导航到创作者中心失败")
            
            try:
                # 检查登录状态
                is_logged_in, user_info = await self.login_helper.check_login_status(page)
                
                if not is_logged_in:
                    douyin_logger.info("等待用户扫码登录...")
                    # 等待登录成功
                    if not await self.login_helper.wait_for_login(page):
                        raise Exception("等待登录超时")
                    
                    # 重新检查登录状态
                    is_logged_in, user_info = await self.login_helper.check_login_status(page)
                    if not is_logged_in or not user_info:
                        raise Exception("登录后状态检查失败")
                
                # 保存cookie
                douyin_logger.info("开始保存cookie...")
                if not await self.cookie_helper.save_cookie_state(context, account_file):
                    raise Exception("保存cookie失败")
                
                return {
                    'success': True,
                    'message': 'Cookie已更新',
                    'user_info': user_info,
                    'cookie_file': account_file
                }
                
            except Exception as e:
                douyin_logger.error(f"等待登录超时或获取信息失败: {str(e)}")
                if page:
                    await self.error_helper.save_error_context(page, e, "cookie_gen")
                raise
            
        except Exception as e:
            douyin_logger.error(f"生成cookie时发生错误: {str(e)}")
            return {
                'success': False,
                'message': f'生成cookie失败: {str(e)}'
            }
            
        finally:
            await self.browser_helper.close_resources(page, context, browser)

    async def setup_account(self, account_file: str, handle: bool = False) -> Dict[str, Any]:
        """
        设置抖音账号，检查cookie是否有效，无效则重新生成
        Args:
            account_file: cookie文件路径
            handle: 是否自动处理无效cookie
        Returns:
            Dict[str, Any]: 设置结果
        """
        try:
            # 从cookie文件路径中提取account_id
            account_id = Path(account_file).stem
            user_data_dir, cookie_file = self._get_account_dirs(account_id)
            
            # 验证cookie并获取用户信息
            is_valid, user_info = await self._verify_cookie_and_get_user_info(
                str(cookie_file),
                headless=False
            )
            
            if not is_valid or not user_info:
                if not handle:
                    return {
                        'success': False,
                        'message': 'Cookie无效且未启用自动处理'
                    }
                douyin_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录')
                result = await self.cookie_gen(str(cookie_file))
                if result['success']:
                    user_info = result['user_info']
                    # 登录成功后同步
                    await self._handle_sync_after_operation(
                        account_id,
                        "setup_account"
                    )
                return result
            
            # 更新数据库
            if not self.db_helper.update_account(user_info, str(cookie_file)):
                return {
                    'success': False,
                    'message': '更新账号信息失败'
                }
            
            return {
                'success': True,
                'message': 'Cookie设置成功',
                'user_info': user_info,
                'cookie_file': str(cookie_file)
            }
            
        except Exception as e:
            douyin_logger.error(f"设置账号失败: {str(e)}")
            return {
                'success': False,
                'message': f'设置账号失败: {str(e)}'
            }

    async def update_account_info(self, account_file: str) -> Optional[Dict[str, Any]]:
        """
        更新或添加账号信息
        Args:
            account_file: cookie文件路径
        Returns:
            Optional[Dict[str, Any]]: 更新/添加后的账号信息，失败返回None
        """
        try:
            # 从cookie文件路径中提取account_id
            account_id = Path(account_file).stem
            user_data_dir, cookie_file = self._get_account_dirs(account_id)
            
            # 验证cookie并获取用户信息
            is_valid, user_info = await self._verify_cookie_and_get_user_info(
                str(cookie_file),
                headless=False
            )
            if not is_valid or not user_info:
                return None
            
            # 更新或添加到数据库
            if self.db_helper.update_account(user_info):
                # 信息更新成功后同步
                await self._handle_sync_after_operation(
                    account_id,
                    "update_account_info"
                )
                return user_info
            return None
                
        except Exception as e:
            douyin_logger.error(f"更新/添加账号信息失败: {str(e)}")
            return None

account_manager = AccountManager() 
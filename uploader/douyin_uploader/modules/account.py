"""
抖音账号管理模块
提供cookie验证、生成等功能
"""

from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from playwright.async_api import Page, BrowserContext
import os
import asyncio
import json

# 使用绝对导入
from utils.log import douyin_logger
from conf import BASE_DIR  # 导入项目根目录
from utils.playwright_helper import PlaywrightHelper

# 使用相对导入访问douyin_uploader包内的模块
from ..utils.cookie_helper import CookieHelper
from ..utils.login_helper import LoginHelper
from ..utils.error_helper import ErrorHelper
from ..utils.db_helper import DBHelper
from ..utils.cookie_sync_manager import CookieSyncManager

class AccountManager:
    """抖音账号管理类"""
    
    def __init__(self):
        # 初始化各个助手类
        self.playwright_helper = PlaywrightHelper()
        self.cookie_helper = CookieHelper()
        self.login_helper = LoginHelper()
        self.error_helper = ErrorHelper()
        self.db_helper = DBHelper(platform="douyin")
        self.cookie_sync_manager = CookieSyncManager()
        
        # 获取当前工作目录
        current_dir = Path.cwd()
        douyin_logger.info(f"当前工作目录: {current_dir}")
        
        # 设置浏览器用户数据目录（使用绝对路径）
        self.base_user_data_dir = current_dir / ".playwright" / "user_data" / "douyin"
        douyin_logger.info(f"浏览器用户数据目录: {self.base_user_data_dir}")
        self.base_user_data_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置cookie文件基础目录（使用绝对路径）
        self.base_cookie_dir = current_dir / "cookies" / "douyin_uploader"
        douyin_logger.info(f"Cookie文件目录: {self.base_cookie_dir}")
        self.base_cookie_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_account_dirs(self, account_id: str) -> tuple[Path, Path]:
        """获取账号相关目录
        Args:
            account_id: 账号ID
        Returns:
            tuple[Path, Path]: (user_data_dir, cookie_file)
        """
        # 为每个账号创建独立的用户数据目录
        user_data_dir = self.base_user_data_dir / account_id
        douyin_logger.info(f"账号 {account_id} 的用户数据目录: {user_data_dir}")
        
        # 使用绝对路径的cookie文件
        cookie_file = self.base_cookie_dir / f"{account_id}.json"
        douyin_logger.info(f"账号 {account_id} 的cookie文件: {cookie_file}")
        
        # 检查目录和文件状态
        if user_data_dir.exists():
            douyin_logger.info(f"用户数据目录已存在，内容: {[f.name for f in user_data_dir.glob('*')]}")
        else:
            douyin_logger.info("用户数据目录不存在")
            
        if cookie_file.exists():
            douyin_logger.info(f"Cookie文件存在，大小: {cookie_file.stat().st_size} 字节")
            try:
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    cookies_count = len(state.get('cookies', []))
                    origins_count = len(state.get('origins', []))
                    douyin_logger.info(f"Cookie文件内容: {cookies_count} cookies, {origins_count} origins")
            except Exception as e:
                douyin_logger.error(f"读取Cookie文件失败: {str(e)}")
        else:
            douyin_logger.info("Cookie文件不存在")
            douyin_logger.info(f"Cookie文件不存在，创建新文件: {cookie_file}")
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump({"cookies": [], "origins": []}, f)
            douyin_logger.info(f"新建Cookie文件成功: {cookie_file}")
        
        # 确保cookie目录存在
        cookie_file.parent.mkdir(parents=True, exist_ok=True)
        
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
            
        # 从cookie文件路径中提取account_id
        account_id = Path(account_file).stem
        user_data_dir, cookie_file = self._get_account_dirs(account_id)
        
        try:
            # 准备浏览器配置
            browser_config = {}
            
            # 优先使用cookie文件
            if Path(cookie_file).exists():
                try:
                    with open(cookie_file, 'r', encoding='utf-8') as f:
                        storage = json.load(f)
                        if storage.get('cookies') or storage.get('origins'):
                            douyin_logger.info(f"使用cookie文件: {cookie_file}")
                            browser_config['storage_state'] = storage
                except Exception as e:
                    douyin_logger.warning(f"读取cookie文件失败: {str(e)}")
            
            # 如果没有cookie文件，尝试使用user_data_dir
            if not browser_config.get('storage_state') and Path(user_data_dir).exists():
                douyin_logger.info(f"使用持久化上下文: {user_data_dir}")
                browser_config['user_data_dir'] = str(user_data_dir)
            
            async with self.playwright_helper.get_context(**browser_config) as context:
                # 创建新页面
                page = await context.new_page()
                
                # 导航到创作者中心
                if not await self.login_helper.navigate_to_creator_center(page):
                    return False, None
                
                # 检查登录状态并获取用户信息
                is_logged_in, user_info = await self.login_helper.check_login_status(page)
                
                # 如果登录成功，更新cookie
                if is_logged_in:
                    douyin_logger.info(f"已登录用户: {user_info.get('nickname', 'Unknown')}")
                    new_state = await context.storage_state()
                    if new_state.get('cookies') or new_state.get('origins'):
                        douyin_logger.info(f"更新cookie状态: {cookie_file}")
                        with open(cookie_file, 'w', encoding='utf-8') as f:
                            json.dump(new_state, f, ensure_ascii=False, indent=2)
                            
                        # 同步到user_data_dir（如果使用）
                        if browser_config.get('user_data_dir'):
                            await self._handle_sync_after_operation(account_id, "verify_cookie")
                
                return is_logged_in, user_info
                    
        except Exception as e:
            douyin_logger.error(f"验证cookie时发生错误: {str(e)}")
            if page:
                await self.error_helper.save_error_context(page, e, "verify_cookie")
            return False, None

    async def setup_account(
        self,
        account_file: str,
        handle: bool = False,
        context: Optional[BrowserContext] = None
    ) -> Dict[str, Any]:
        """
        设置抖音账号，优先使用已存在的浏览器会话
        Args:
            account_file: cookie文件路径
            handle: 是否自动处理无效cookie
            context: 可选的现有浏览器上下文
        Returns:
            Dict[str, Any]: 设置结果，包含浏览器上下文
        """
        try:
            account_id = Path(account_file).stem
            user_data_dir, cookie_file = self._get_account_dirs(account_id)
            
            # 扩展浏览器启动参数
            browser_args = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-position=0,0',
                '--ignore-certifcate-errors',
                '--ignore-certifcate-errors-spki-list',
                '--disable-background-networking',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-breakpad',
                '--disable-client-side-phishing-detection',
                '--disable-component-update',
                '--disable-default-apps',
                '--disable-dev-shm-usage',
                '--disable-domain-reliability',
                '--disable-features=AudioServiceOutOfProcess',
                '--disable-hang-monitor',
                '--disable-ipc-flooding-protection',
                '--disable-notifications',
                '--disable-offer-store-unmasked-wallet-cards',
                '--disable-popup-blocking',
                '--disable-print-preview',
                '--disable-prompt-on-repost',
                '--disable-renderer-backgrounding',
                '--disable-speech-api',
                '--disable-sync',
                '--disable-web-security',
                '--disk-cache-size=33554432',
                '--hide-scrollbars',
                '--ignore-gpu-blacklist',
                '--metrics-recording-only',
                '--mute-audio',
                '--no-default-browser-check',
                '--no-first-run',
                '--no-pings',
                '--no-zygote',
                '--password-store=basic',
                '--use-gl=swiftshader',
                '--use-mock-keychain',
                '--window-size=1920,1080',
                # 添加媒体相关参数
                '--autoplay-policy=no-user-gesture-required',
                '--disable-features=MediaEngagement',
                '--enable-automation',
                '--enable-features=NetworkService,NetworkServiceInProcess',
                '--force-color-profile=srgb',
                '--force-device-scale-factor=1',
            ]
            
            # 准备浏览器配置
            browser_config = {
                'headless': False,  # 确保非无头模式
                'args': browser_args,
                'ignore_default_args': ['--enable-automation'],  # 禁用自动化标记
                'viewport': {'width': 1920, 'height': 1080},
                'screen': {'width': 1920, 'height': 1080},
                'bypass_csp': True,  # 绕过内容安全策略
                'accept_downloads': True,
                'locale': 'zh-CN',
                'timezone_id': 'Asia/Shanghai',
                'geolocation': {'latitude': 39.9042, 'longitude': 116.4074},  # 北京坐标
                'permissions': ['geolocation'],
                'color_scheme': 'light',
                'device_scale_factor': 1,
                'is_mobile': False,
                'has_touch': False,
                'java_script_enabled': True
            }
            
            # 如果存在user_data_dir，使用持久化上下文
            if Path(user_data_dir).exists():
                douyin_logger.info(f"使用持久化上下文: {user_data_dir}")
                browser_config['user_data_dir'] = str(user_data_dir)
            
            # 如果没有提供现有的上下文，则创建新的
            should_close_context = False
            if not context:
                douyin_logger.info(f"使用配置创建浏览器上下文: {browser_config}")
                context = await self.playwright_helper.get_context(**browser_config)
                await asyncio.sleep(2)  # 等待上下文初始化完成
                should_close_context = True
            
            try:
                # 创建新页面
                page = await context.new_page()
                
                # 设置用户代理
                await page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive'
                })
                
                # 如果存在cookie文件，加载cookie
                if Path(cookie_file).exists():
                    try:
                        with open(cookie_file, 'r', encoding='utf-8') as f:
                            storage = json.load(f)
                            if storage.get('cookies'):
                                douyin_logger.info(f"加载cookie: {len(storage['cookies'])} cookies")
                                await context.add_cookies(storage['cookies'])
                    except Exception as e:
                        douyin_logger.error(f"加载cookie失败: {str(e)}")
                
                # 访问创作者中心，使用更稳定的导航策略
                douyin_logger.info("访问创作者中心检查登录状态...")
                try:
                    # 然后导航到创作者中心，使用更长的超时时间
                    response = await page.goto(
                        "https://creator.douyin.com/creator-micro/home",
                        wait_until="domcontentloaded",  # 改用domcontentloaded而不是networkidle
                        timeout=60000  # 增加超时时间到60秒
                    )
                    
                    if not response:
                        raise Exception("导航到创作者中心失败：无响应")
                    
                    if response.status >= 400:
                        raise Exception(f"导航到创作者中心失败：HTTP {response.status}")
                        
                    # 使用多个备选选择器等待页面加载
                    selectors = [
                        "div[class*='layout-content']",  # 更通用的布局选择器
                        "div[class*='header']",          # 页面头部
                        "div[class*='creator']",         # 创作者相关元素
                        "div[class*='menu']"             # 菜单元素
                    ]
                    
                    # 尝试等待任一选择器出现
                    for selector in selectors:
                        try:
                            await page.wait_for_selector(selector, timeout=5000)
                            douyin_logger.info(f"页面加载完成，匹配选择器: {selector}")
                            break
                        except Exception:
                            continue
                            
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    douyin_logger.error(f"导航失败: {str(e)}")
                    # 如果导航失败，尝试刷新页面
                    await page.reload(wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2)
                
                # 检查登录状态
                is_logged_in, user_info = await self.login_helper.check_login_status(page)
                
                if not is_logged_in:
                    if handle:
                        douyin_logger.info("未登录，等待用户扫码登录...")
                        if not await self.login_helper.wait_for_login(page):
                            raise Exception("等待登录超时")
                        
                        is_logged_in, user_info = await self.login_helper.check_login_status(page)
                        if not is_logged_in or not user_info:
                            raise Exception("登录后状态检查失败")
                        
                        # 保存新的登录状态
                        new_state = await context.storage_state()
                        if new_state.get('cookies') or new_state.get('origins'):
                            douyin_logger.info(f"保存新的登录状态到: {cookie_file}")
                            with open(cookie_file, 'w', encoding='utf-8') as f:
                                json.dump(new_state, f, ensure_ascii=False, indent=2)
                            
                            # 同步到user_data_dir（如果使用）
                            if browser_config.get('user_data_dir'):
                                await self._handle_sync_after_operation(account_id, "setup_account")
                    else:
                        raise Exception("未登录且未启用自动处理")
                else:
                    douyin_logger.info(f"已登录用户: {user_info.get('nickname', 'Unknown')}")
                    # 更新cookie状态
                    new_state = await context.storage_state()
                    if new_state.get('cookies') or new_state.get('origins'):
                        douyin_logger.info(f"更新cookie状态: {cookie_file}")
                        with open(cookie_file, 'w', encoding='utf-8') as f:
                            json.dump(new_state, f, ensure_ascii=False, indent=2)
                
                # 导航到上传页面，使用更稳定的导航策略
                douyin_logger.info("导航到上传页面...")
                try:
                    await page.goto(
                        "https://creator.douyin.com/creator-micro/content/upload",
                        wait_until="domcontentloaded",
                        timeout=30000
                    )
                    # 等待上传按钮出现
                    await page.wait_for_selector(".container-drag-AOMYqU", timeout=10000)
                    await asyncio.sleep(2)
                except Exception as e:
                    douyin_logger.error(f"导航到上传页面失败: {str(e)}")
                    # 如果导航失败，尝试刷新页面
                    await page.reload(wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2)
                
                return {
                    'success': True,
                    'message': '账号设置成功',
                    'user_info': user_info,
                    'page': page,
                    'context': context
                }
                
            except Exception as e:
                if page:
                    await page.close()
                if should_close_context and context:
                    await context.close()
                raise
                
        except Exception as e:
            douyin_logger.error(f"设置账号时发生错误: {str(e)}")
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
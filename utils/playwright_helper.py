# -*- coding: utf-8 -*-
import subprocess
from typing import Optional, Dict
from pathlib import Path
from playwright.async_api import async_playwright
import asyncio
from contextlib import asynccontextmanager

from utils.log import logger

class PlaywrightHelper:
    """Playwright 工具类"""
    
    def __init__(self):
        """初始化 PlaywrightHelper"""
        self._context = None
        self._browser = None
        self._playwright = None
    
    @staticmethod
    def install_browser(browser_type: str = "chromium") -> bool:
        """安装 Playwright 浏览器
        
        Args:
            browser_type: 浏览器类型，默认为 chromium
            
        Returns:
            bool: 是否安装成功
        """
        try:
            logger.info(f"正在安装 Playwright {browser_type} 浏览器...")
            subprocess.run(["playwright", "install", browser_type], check=True)
            logger.success(f"Playwright {browser_type} 浏览器安装成功！")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"安装失败: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"安装过程发生异常: {str(e)}")
            return False

    async def initialize(self, browser_type: str = "chromium", user_data_dir: Optional[str] = None, storage_state: Optional[Dict] = None):
        """初始化浏览器资源
        
        Args:
            browser_type: 浏览器类型，默认为 chromium
            user_data_dir: 用户数据目录路径，如果提供则使用持久化上下文
            storage_state: 浏览器状态，包含 cookies 和 localStorage
        """
        try:
            self._playwright = await async_playwright().start()
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
                '--disable-extensions',
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
            ]

            context_params = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'locale': 'zh-CN',
                'timezone_id': 'Asia/Shanghai',
                'geolocation': {'latitude': 39.9042, 'longitude': 116.4074},  # 北京坐标
                'permissions': ['geolocation'],
                'color_scheme': 'light',
                'device_scale_factor': 1,
                'is_mobile': False,
                'has_touch': False,
                'java_script_enabled': True,
                'bypass_csp': True,
                'proxy': None  # 如果需要代理可以在这里设置
            }

            if user_data_dir:
                logger.info(f"尝试使用持久化上下文目录: {user_data_dir}")
                if not Path(user_data_dir).exists():
                    logger.warning(f"持久化目录不存在: {user_data_dir}")
                else:
                    logger.info(f"持久化目录存在，检查内容...")
                    # 列出目录内容
                    files = list(Path(user_data_dir).glob('*'))
                    logger.info(f"目录内容: {[f.name for f in files]}")
                
                # 使用持久化上下文
                persistent_context_params = {
                    'user_data_dir': user_data_dir,
                    'headless': False,  # 默认关闭无头模式
                    'args': browser_args,
                    'ignore_default_args': ['--enable-automation'],  # 禁用自动化标记
                    'accept_downloads': True,  # 允许下载
                    'bypass_csp': True,  # 绕过内容安全策略
                    'viewport': context_params['viewport'],
                    'locale': context_params['locale'],
                    'timezone_id': context_params['timezone_id'],
                    'permissions': context_params['permissions'],
                    'persistent': True,  # 确保是持久化的
                }
                
                logger.info("创建持久化上下文...")
                self._context = await self._playwright.chromium.launch_persistent_context(**persistent_context_params)
                self._browser = self._context.browser
                logger.success("持久化上下文创建成功")
            else:
                # 创建普通浏览器实例
                logger.info("创建普通浏览器实例...")
                self._browser = await self._playwright.chromium.launch(
                    headless=False,  # 默认关闭无头模式
                    args=browser_args,
                    ignore_default_args=['--enable-automation']  # 禁用自动化标记
                )
                
                if storage_state:
                    logger.info("使用提供的存储状态...")
                    context_params['storage_state'] = storage_state
                    
                self._context = await self._browser.new_context(**context_params)
                logger.success("普通浏览器上下文创建成功")
            
            # 注入 stealth.js 脚本
            try:
                # utils/stealth.min.js打开失败，
                with open('utils/stealth.min.js', 'r', encoding='utf-8') as f:
                    stealth_js = f.read()
                await self._context.add_init_script(stealth_js)
                logger.success("注入 stealth.js 成功")
            except Exception as e:
                logger.error(f"注入 stealth.js 失败: {str(e)}")
                raise
            
            # 检查上下文状态
            try:
                state = await self._context.storage_state()
                cookies_count = len(state.get('cookies', []))
                origins_count = len(state.get('origins', []))
                logger.info(f"上下文状态: {cookies_count} cookies, {origins_count} origins")
            except Exception as e:
                logger.error(f"检查上下文状态失败: {str(e)}")
            
            logger.success("浏览器资源初始化成功")
        except Exception as e:
            logger.error(f"初始化浏览器资源失败: {str(e)}")
            await self.cleanup()
            raise

    async def cleanup(self):
        """清理浏览器资源"""
        try:
            if self._context:
                # 不要关闭持久化上下文，只关闭页面
                if not isinstance(self._context.browser, type(None)):
                    # 这是普通上下文，可以关闭
                    await self._context.close()
            if self._browser and not isinstance(self._context.browser, type(None)):
                # 只在非持久化上下文时关闭浏览器
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            logger.success("浏览器资源清理完成")
        except Exception as e:
            logger.error(f"清理浏览器资源失败: {str(e)}")
            raise

    @asynccontextmanager
    async def get_context(self, browser_type: str = "chromium", user_data_dir: Optional[str] = None, storage_state: Optional[Dict] = None):
        """获取浏览器上下文的上下文管理器
        
        Args:
            browser_type: 浏览器类型，默认为 chromium
            user_data_dir: 用户数据目录路径，如果提供则使用持久化上下文
            storage_state: 浏览器状态，包含 cookies 和 localStorage
            
        Yields:
            browser_context: 浏览器上下文
        """
        try:
            await self.initialize(browser_type, user_data_dir, storage_state)
            yield self._context
        finally:
            await self.cleanup() 
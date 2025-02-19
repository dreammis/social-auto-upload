# -*- coding: utf-8 -*-
from datetime import datetime
import os
import asyncio
from playwright.async_api import async_playwright

from utils.base_social_media import set_init_script
from utils.files_times import get_absolute_path
from utils.log import kuaishou_logger
from ..utils.constants import (
    BROWSER_ARGS, BROWSER_VIEWPORT, USER_AGENT,
    LOGIN_URL, COOKIE_VALID_TIME, COOKIE_CHECK_INTERVAL
)

class KSAccountManager:
    def __init__(self):
        self.cookie_pool = {}
        self.valid_time = 24 * 60 * 60  # Cookie有效期（24小时）

    async def validate_cookie(self, account_file: str) -> bool:
        """验证Cookie是否有效"""
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=account_file)
            context = await set_init_script(context)
            page = await context.new_page()
            await page.goto("https://cp.kuaishou.com/article/publish/video")
            try:
                await page.wait_for_selector("div.names div.container div.name:text('机构服务')", timeout=5000)
                kuaishou_logger.info("[+] 等待5秒 cookie 失效")
                return False
            except:
                kuaishou_logger.success("[+] cookie 有效")
                return True
            finally:
                await context.close()
                await browser.close()

    async def refresh_cookie(self, account_file: str) -> bool:
        """刷新Cookie"""
        async with async_playwright() as playwright:
            options = {
                'args': ['--lang en-GB'],
                'headless': False,
            }
            browser = await playwright.chromium.launch(**options)
            context = await browser.new_context()
            context = await set_init_script(context)
            page = await context.new_page()
            await page.goto("https://cp.kuaishou.com")
            await page.pause()
            await context.storage_state(path=account_file)
            await context.close()
            await browser.close()
            return True

    async def setup_account(self, account_file: str, handle: bool = False) -> bool:
        """设置账号"""
        account_file = get_absolute_path(account_file, "ks_uploader")
        if not os.path.exists(account_file) or not await self.validate_cookie(account_file):
            if not handle:
                return False
            kuaishou_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件')
            await self.refresh_cookie(account_file)
        return True

    async def batch_validate_cookies(self, cookie_files: list) -> dict:
        """批量验证Cookie"""
        results = {}
        for cookie_file in cookie_files:
            is_valid = await self.validate_cookie(cookie_file)
            results[cookie_file] = {
                'valid': is_valid,
                'checked_at': datetime.now().isoformat()
            }
        return results

account_manager = KSAccountManager() 
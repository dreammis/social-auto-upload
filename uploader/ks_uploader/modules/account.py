# -*- coding: utf-8 -*-
from datetime import datetime
import os
import asyncio
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Page
from pathlib import Path

from utils.base_social_media import set_init_script
from utils.files_times import get_absolute_path
from utils.log import kuaishou_logger
from ..utils.constants import (
    BROWSER_ARGS, BROWSER_VIEWPORT, USER_AGENT,
    LOGIN_URL, COOKIE_VALID_TIME, COOKIE_CHECK_INTERVAL,
    PROFILE_URL
)
from utils.social_media_db import SocialMediaDB
from utils.cookie_helper import CookieHelper

class KSAccountInfo:
    """快手账号信息类"""
    def __init__(self, data: Dict[str, Any]):
        self.avatar = data.get('avatar', '')  # 头像
        self.username = data.get('username', '')  # 用户名
        self.kwai_id = data.get('kwai_id', '')  # 快手ID
        self.followers = data.get('followers', 0)  # 粉丝数
        self.following = data.get('following', 0)  # 关注数
        self.likes = data.get('likes', 0)  # 获赞数
        self.description = data.get('description', '')  # 个人简介
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'avatar': self.avatar,
            'username': self.username,
            'kwai_id': self.kwai_id,
            'followers': self.followers,
            'following': self.following,
            'likes': self.likes,
            'description': self.description,
            'updated_at': self.updated_at
        }

    @staticmethod
    def parse_number(text: str) -> float:
        """解析数字（支持w/万等单位）"""
        try:
            if not text:
                return 0
            text = text.strip().lower()
            if 'w' in text:
                return float(text.replace('w', '')) * 10000
            if '万' in text:
                return float(text.replace('万', '')) * 10000
            return float(text.replace(',', ''))
        except:
            return 0

class KSAccountManager:
    def __init__(self):
        self.cookie_pool = {}
        self.valid_time = COOKIE_VALID_TIME
        self._account_info = None
        self._info_cache = {}  # 账号信息缓存
        self._last_update_time = {}  # 上次更新时间记录
        self._pending_updates = []  # 待更新的账号信息
        self._db = SocialMediaDB()  # SQLite是轻量级的，可以保持单个连接

    def __del__(self):
        """确保数据库连接正确关闭"""
        if hasattr(self, '_db'):
            self._db.close()

    def _add_pending_update(self, platform: str, username: str, info: Dict[str, Any]):
        """添加待更新的账号信息"""
        self._pending_updates.append({
            'platform': platform,
            'username': username,
            'info': info,
            'timestamp': datetime.now()
        })

    def _process_pending_updates(self):
        """处理待更新的账号信息"""
        if not self._pending_updates:
            return

        try:
            # 批量更新数据库
            for item in self._pending_updates:
                try:
                    self._db.add_or_update_account(
                        item['platform'],
                        item['username'],
                        item['info']
                    )
                except Exception as e:
                    kuaishou_logger.error(f"更新账号信息失败: {str(e)}")
            
            self._pending_updates.clear()
            
        except Exception as e:
            kuaishou_logger.error(f"处理更新队列时发生错误: {str(e)}")

    def _get_cached_info(self, account_file: str) -> Optional[Dict[str, Any]]:
        """从缓存获取账号信息"""
        if account_file not in self._info_cache:
            return None
            
        last_update = self._last_update_time.get(account_file)
        if not last_update or (datetime.now() - last_update).total_seconds() > COOKIE_CHECK_INTERVAL:
            return None
            
        return self._info_cache[account_file]

    def _update_cache(self, account_file: str, info: Dict[str, Any]):
        """更新缓存信息"""
        self._info_cache[account_file] = info
        self._last_update_time[account_file] = datetime.now()

    async def _extract_profile_info(self, page: Page) -> Optional[KSAccountInfo]:
        """提取个人资料信息"""
        try:
            # 等待页面加载完成
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)  # 等待React渲染完成
            
            # 直接通过evaluate获取所有需要的信息
            info = await page.evaluate("""() => {
                const info = {};
                
                // 获取用户名 - 从header-info-card中获取
                const usernameEl = document.querySelector('div.header-info-card .user-name');
                info.username = usernameEl ? usernameEl.textContent.trim() : '';
                
                // 获取快手ID
                const userIdEl = document.querySelector('div.header-info-card .user-kwai-id');
                info.kwai_id = userIdEl ? userIdEl.textContent.trim() : '';
                
                // 获取统计数据
                const statsElements = document.querySelectorAll('div.user-cnt__item');
                info.followers = 0;
                info.following = 0;
                info.likes = 0;
                
                statsElements.forEach(el => {
                    const text = el.textContent.toLowerCase();
                    const spanText = el.querySelector('span').textContent;
                    const numText = text.replace(spanText, '').trim();
                    
                    if (spanText === '粉丝') {
                        info.followers = numText.includes('w') || numText.includes('万') ? 
                            parseFloat(numText.replace('w', '').replace('万', '')) * 10000 : 
                            parseFloat(numText.replace(',', ''));
                    } else if (spanText === '关注') {
                        info.following = numText.includes('w') || numText.includes('万') ? 
                            parseFloat(numText.replace('w', '').replace('万', '')) * 10000 : 
                            parseFloat(numText.replace(',', ''));
                    } else if (spanText === '获赞') {
                        info.likes = numText.includes('w') || numText.includes('万') ? 
                            parseFloat(numText.replace('w', '').replace('万', '')) * 10000 : 
                            parseFloat(numText.replace(',', ''));
                    }
                });
                
                // 获取个人简介
                const descEl = document.querySelector('div.header-info-card .user-desc');
                info.description = descEl ? descEl.textContent.trim() : '';
                
                // 获取头像
                const avatarEl = document.querySelector('div.header-info-card .user-image');
                info.avatar = avatarEl ? avatarEl.getAttribute('src') : '';
                
                return info;
            }""")
            
            # 记录调试信息
            kuaishou_logger.debug("成功提取个人资料信息")
            kuaishou_logger.debug(f"用户名: {info.get('username', '')}")
            kuaishou_logger.debug(f"快手ID: {info.get('kwai_id', '')}")
            kuaishou_logger.debug(f"粉丝数: {info.get('followers', 0)}")
            kuaishou_logger.debug(f"关注数: {info.get('following', 0)}")
            kuaishou_logger.debug(f"获赞数: {info.get('likes', 0)}")
            kuaishou_logger.debug(f"头像URL: {info.get('avatar', '')}")
            kuaishou_logger.debug(f"个人简介: {info.get('description', '')}")
            
            # 如果至少有用户名，就返回结果
            if info.get('username'):
                return KSAccountInfo(info)
            
            kuaishou_logger.error("无法获取完整的账号信息")
            return None
            
        except Exception as e:
            kuaishou_logger.error(f"提取个人资料信息失败: {str(e)}")
            try:
                # 保存页面内容和截图以便调试
                page_content = await page.content()
                kuaishou_logger.debug(f"页面内容: {page_content[:1000]}...")
                await page.screenshot(path="error_extract_profile.png")
                kuaishou_logger.info("已保存错误页面截图: error_extract_profile.png")
            except Exception as debug_error:
                kuaishou_logger.error(f"保存调试信息失败: {str(debug_error)}")
            return None

    async def check_profile_page(self, page) -> tuple[bool, Optional[str]]:
        """检查是否成功加载个人资料页面并获取用户名
        Args:
            page: Playwright页面对象
        Returns:
            (是否成功, 用户名)
        """
        try:
            # 直接通过evaluate获取用户名
            result = await page.evaluate("""() => {
                const elements = document.querySelectorAll('div[class*="user-name"]');
                for (const el of elements) {
                    const text = el.textContent.trim();
                    if (text) {
                        return {
                            text: text,
                            found: true
                        };
                    }
                }
                return {
                    text: '',
                    found: false
                };
            }""")
            
            if result['found']:
                return True, result['text']
                
        except Exception as e:
            kuaishou_logger.debug(f"检查个人资料页面失败: {str(e)}")
            
        return False, None

    async def validate_cookie(
        self, 
        account_file: str, 
        expected_username: Optional[str] = None,
        quick_check: bool = True
    ) -> bool:
        """验证Cookie是否有效
        Args:
            account_file: Cookie文件路径
            expected_username: 期望的用户名，用于验证登录是否正确
            quick_check: 是否只进行快速验证，不更新用户信息
        Returns:
            bool: cookie是否有效
        """
        # 检查缓存
        if not quick_check:
            cached_info = self._get_cached_info(account_file)
            if cached_info:
                self._account_info = KSAccountInfo(cached_info)
                return True

        playwright = None
        browser = None
        context = None
        page = None
        
        try:
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True, args=BROWSER_ARGS)
            context = await browser.new_context(
                storage_state=account_file,
                viewport=BROWSER_VIEWPORT,
                user_agent=USER_AGENT
            )
            page = await context.new_page()
            
            # 访问个人资料页面
            await page.goto(PROFILE_URL, wait_until="networkidle")
            
            # 检查是否需要登录
            if "passport.kuaishou.com" in page.url:
                return False
            
            # 获取用户名
            username_result = await page.evaluate("""() => {
                const el = document.querySelector('div.header-info-card .user-name');
                return el ? el.textContent.trim() : '';
            }""")
            
            if not username_result:
                return False
                
            if expected_username and username_result != expected_username:
                return False
                
            # 如果不是快速检查，则更新用户信息
            if not quick_check:
                self._account_info = await self._extract_profile_info(page)
                if not self._account_info:
                    return False
                    
                # 更新缓存
                self._update_cache(account_file, self._account_info.to_dict())
                    
                # 添加到待更新列表
                self._add_pending_update(
                    "kuaishou",
                    username_result,
                    self._account_info.to_dict()
                )
                
                # 处理待更新
                self._process_pending_updates()
            
            return True
                
        except Exception as e:
            kuaishou_logger.error(f"验证cookie时发生错误: {str(e)}")
            return False
            
        finally:
            # 按顺序清理资源
            if page:
                try:
                    await page.close()
                except:
                    pass
            if context:
                try:
                    await context.close()
                except:
                    pass
            if browser:
                try:
                    await browser.close()
                except:
                    pass
            if playwright:
                try:
                    await playwright.stop()
                except:
                    pass

    async def update_account_info(self, account_file: str) -> Optional[Dict[str, Any]]:
        """更新账号信息"""
        if await self.validate_cookie(account_file, quick_check=False):
            return self._account_info.to_dict() if self._account_info else None
        return None

    async def setup_account(self, account_file: str, handle: bool = False) -> bool:
        """设置账号"""
        account_file = get_absolute_path(account_file, "ks_uploader")
        
        try:
            cookie_path = self._db.get_cookie_path("kuaishou", account_file)
            if cookie_path:
                account_file = cookie_path
        except Exception as e:
            kuaishou_logger.error(f"从数据库获取cookie失败: {str(e)}")
        
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
                'checked_at': datetime.now().isoformat(),
                'account_info': self._account_info.to_dict() if self._account_info else None
            }
        
        # 处理所有待更新的信息
        self._process_pending_updates()
        return results

    async def refresh_cookie(self, account_file: str, expected_username: Optional[str] = None) -> bool:
        """刷新Cookie
        Args:
            account_file: Cookie文件路径
            expected_username: 期望的用户名，用于验证登录是否正确
        """
        browser = None
        context = None
        page = None
        
        try:
            kuaishou_logger.info(f"开始刷新Cookie，目标文件: {account_file}")
            async with async_playwright() as playwright:
                options = {
                    'args': BROWSER_ARGS,
                    'headless': False,
                }
                kuaishou_logger.info("正在启动浏览器...")
                browser = await playwright.chromium.launch(**options)
                
                kuaishou_logger.info("正在创建浏览器上下文...")
                context = await browser.new_context(
                    viewport=BROWSER_VIEWPORT,
                    user_agent=USER_AGENT
                )
                context = await set_init_script(context)
                
                kuaishou_logger.info("正在创建新页面...")
                page = await context.new_page()
                
                # 直接访问登录页
                kuaishou_logger.info(f"正在访问登录页面: {LOGIN_URL}")
                await page.goto(LOGIN_URL, wait_until="networkidle")
                kuaishou_logger.info("等待用户登录...")
                
                # 等待登录成功并跳转到个人资料页面
                max_wait_time = 300  # 5分钟超时
                check_interval = 3  # 每3秒检查一次
                
                for _ in range(max_wait_time // check_interval):
                    await asyncio.sleep(check_interval)
                    current_url = page.url
                    
                    # 如果还在登录页面，继续等待
                    if "passport.kuaishou.com" in current_url:
                        kuaishou_logger.info("等待用户完成登录...")
                        continue
                        
                    # 如果已经跳转到个人资料页面
                    if PROFILE_URL in current_url:
                        kuaishou_logger.info("检测到已跳转到个人资料页面")
                        
                        # 等待页面加载完成
                        await page.wait_for_load_state("networkidle")
                        
                        # 检查是否成功加载个人资料页面
                        success, username = await self.check_profile_page(page)
                        if not success:
                            kuaishou_logger.info("等待页面加载...")
                            continue
                            
                        if expected_username and username != expected_username:
                            kuaishou_logger.error(f"用户名不匹配，期望: {expected_username}, 实际: {username}")
                            return False
                        
                        kuaishou_logger.success(f"登录成功！当前用户: {username}")
                        await context.storage_state(path=account_file)
                        kuaishou_logger.success(f"登录状态已保存到: {account_file}")
                        
                        # 提取账号信息
                        self._account_info = await self._extract_profile_info(page)
                        return True
                    else:
                        # 如果在其他页面，尝试跳转到个人资料页面
                        kuaishou_logger.info("尝试跳转到个人资料页面...")
                        await page.goto(PROFILE_URL, wait_until="networkidle")
                
                kuaishou_logger.error("登录等待超时")
                return False
                    
        except Exception as e:
            kuaishou_logger.error(f"刷新Cookie失败: {str(e)}")
            return False
            
        finally:
            try:
                kuaishou_logger.info("正在清理资源...")
                if page:
                    await page.close()
                if context:
                    await context.close()
                if browser:
                    await browser.close()
                kuaishou_logger.info("资源清理完成")
            except Exception as e:
                kuaishou_logger.error(f"清理资源时发生错误: {str(e)}")

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """获取当前账号信息"""
        return self._account_info.to_dict() if self._account_info else None

    async def setup_cookie(self, account_file: str, expected_username: Optional[str] = None, force_refresh: bool = False) -> Dict[str, Any]:
        """设置和验证Cookie
        
        完整的Cookie设置流程，包括：
        1. 验证现有Cookie
        2. 必要时刷新Cookie
        3. 更新账号信息
        4. 保存到数据库
        
        Args:
            account_file: Cookie文件路径
            expected_username: 期望的用户名
            force_refresh: 是否强制刷新
            
        Returns:
            Dict[str, Any]: 设置结果
        """
        try:
            result = {
                'success': False,
                'message': '',
                'cookie_file': str(account_file),
                'timestamp': datetime.now().isoformat()
            }
            
            # 确保目录存在
            Path(account_file).parent.mkdir(parents=True, exist_ok=True)
            
            # 检查现有Cookie
            if not force_refresh and os.path.exists(account_file):
                # 验证文件
                if not CookieHelper.validate_cookie_file(account_file):
                    kuaishou_logger.warning("现有Cookie文件无效")
                else:
                    # 验证Cookie
                    is_valid = await self.validate_cookie(account_file, expected_username, quick_check=False)
                    if is_valid:
                        result.update({
                            'success': True,
                            'message': 'Cookie有效',
                            'username': self._account_info.username if self._account_info else None,
                            'expires_at': datetime.now().timestamp() + COOKIE_VALID_TIME
                        })
                        return result
            
            # 需要刷新Cookie
            kuaishou_logger.info('开始获取新的Cookie...')
            
            # 备份现有Cookie
            if os.path.exists(account_file):
                CookieHelper.backup_cookie_file(account_file)
            
            # 刷新Cookie
            if await self.refresh_cookie(account_file, expected_username):
                # 验证新Cookie
                is_valid = await self.validate_cookie(account_file, expected_username, quick_check=False)
                if is_valid:
                    result.update({
                        'success': True,
                        'message': 'Cookie已更新并验证成功',
                        'username': self._account_info.username if self._account_info else None,
                        'expires_at': datetime.now().timestamp() + COOKIE_VALID_TIME
                    })
                else:
                    result.update({
                        'message': 'Cookie更新成功但验证失败'
                    })
            else:
                result.update({
                    'message': 'Cookie获取失败'
                })
            
            return result
            
        except Exception as e:
            kuaishou_logger.error(f"Cookie设置过程发生异常: {str(e)}")
            return {
                'success': False,
                'message': str(e),
                'cookie_file': str(account_file),
                'timestamp': datetime.now().isoformat()
            }

account_manager = KSAccountManager() 
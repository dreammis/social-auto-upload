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

    async def _extract_profile_info(self, page: Page) -> Optional[KSAccountInfo]:
        """提取个人资料信息"""
        try:
            # 等待页面完全加载
            await page.wait_for_load_state("networkidle")
            
            # 等待个人资料区域加载完成
            profile_selector = "[class*='profile-info']"
            await page.wait_for_selector(profile_selector, timeout=10000)
            
            # 提取信息
            info = {}
            
            # 获取头像
            avatar_selector = "[class*='avatar'] img"
            avatar_element = await page.locator(avatar_selector).first
            if avatar_element:
                info['avatar'] = await avatar_element.get_attribute('src') or ''
            else:
                info['avatar'] = ''
            
            # 获取用户名
            username_selector = "[class*='nickname']"
            username_element = await page.locator(username_selector).first
            if username_element:
                info['username'] = (await username_element.text_content() or '').strip()
            else:
                info['username'] = ''
            
            # 获取快手ID
            kwai_id_selector = "[class*='user-id']"
            kwai_id_element = await page.locator(kwai_id_selector).first
            if kwai_id_element:
                info['kwai_id'] = (await kwai_id_element.text_content() or '').strip()
            else:
                info['kwai_id'] = ''
            
            # 获取统计数据
            try:
                # 获取所有统计项
                stats_selector = "[class*='data-item']"
                stat_items = await page.locator(stats_selector).all()
                
                # 遍历统计项查找对应数据
                for item in stat_items:
                    text = await item.text_content()
                    if not text:
                        continue
                        
                    text = text.lower()
                    if '粉丝' in text:
                        info['followers'] = KSAccountInfo.parse_number(text.split('粉丝')[0])
                    elif '关注' in text:
                        info['following'] = KSAccountInfo.parse_number(text.split('关注')[0])
                    elif '获赞' in text:
                        info['likes'] = KSAccountInfo.parse_number(text.split('获赞')[0])
                
                # 设置默认值
                info.setdefault('followers', 0)
                info.setdefault('following', 0)
                info.setdefault('likes', 0)
                
            except Exception as e:
                kuaishou_logger.warning(f"获取统计数据失败: {str(e)}")
                info['followers'] = 0
                info['following'] = 0
                info['likes'] = 0
            
            # 获取个人简介
            desc_selector = "[class*='description']"
            desc_element = await page.locator(desc_selector).first
            if desc_element:
                info['description'] = (await desc_element.text_content() or '').strip()
            else:
                info['description'] = ''
            
            # 记录调试信息
            kuaishou_logger.debug("成功提取个人资料信息")
            kuaishou_logger.debug(f"用户名: {info['username']}")
            kuaishou_logger.debug(f"快手ID: {info['kwai_id']}")
            kuaishou_logger.debug(f"粉丝数: {info['followers']}")
            kuaishou_logger.debug(f"关注数: {info['following']}")
            kuaishou_logger.debug(f"获赞数: {info['likes']}")
            
            return KSAccountInfo(info)
            
        except Exception as e:
            kuaishou_logger.error(f"提取个人资料信息失败: {str(e)}")
            try:
                # 保存页面内容和截图以便调试
                page_content = await page.content()
                kuaishou_logger.debug(f"页面内容: {page_content[:1000]}...")
                await page.screenshot(path="error_extract_profile.png")
                kuaishou_logger.info("已保存错误页面截图: error_extract_profile.png")
                
                # 输出所有可见元素的选择器
                elements = await page.evaluate("""() => {
                    const elements = document.querySelectorAll('*');
                    return Array.from(elements).map(el => ({
                        tag: el.tagName.toLowerCase(),
                        class: el.className,
                        id: el.id
                    }));
                }""")
                kuaishou_logger.debug(f"页面元素结构: {str(elements)[:1000]}...")
            except Exception as debug_error:
                kuaishou_logger.error(f"保存调试信息失败: {str(debug_error)}")
            return None

    async def validate_cookie(self, account_file: str) -> bool:
        """验证Cookie是否有效"""
        browser = None
        context = None
        page = None
        
        try:
            kuaishou_logger.info(f"开始验证Cookie: {account_file}")
            async with async_playwright() as playwright:
                kuaishou_logger.info("正在启动浏览器...")
                browser = await playwright.chromium.launch(headless=True)
                
                kuaishou_logger.info("正在创建浏览器上下文...")
                context = await browser.new_context(storage_state=account_file)
                context = await set_init_script(context)
                
                kuaishou_logger.info("正在创建新页面...")
                page = await context.new_page()
                
                # 先访问主页面
                kuaishou_logger.info("正在访问主页面...")
                await page.goto("https://cp.kuaishou.com", wait_until="networkidle")
                
                # 检查是否需要登录
                if "passport.kuaishou.com" in page.url:
                    kuaishou_logger.error("Cookie已失效，需要重新登录")
                    return False
                
                # 等待页面加载完成
                await page.wait_for_load_state("networkidle")
                
                # 检查登录状态
                try:
                    # 检查是否存在登录状态标识
                    login_status = await page.evaluate("""() => {
                        return window.localStorage.getItem('kpn:st:token') !== null;
                    }""")
                    
                    if not login_status:
                        kuaishou_logger.error("未检测到登录状态")
                        return False
                        
                    kuaishou_logger.success("检测到有效的登录状态")
                    
                    # 访问个人资料页
                    kuaishou_logger.info(f"正在访问个人资料页: {PROFILE_URL}")
                    await page.goto(PROFILE_URL, wait_until="networkidle")
                    
                    # 等待页面加载
                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_load_state("networkidle")
                    
                    # 检查页面标题
                    title = await page.title()
                    if "快手" not in title:
                        kuaishou_logger.error(f"页面标题异常: {title}")
                        return False
                    
                    # 等待个人资料加载
                    kuaishou_logger.info("等待个人资料加载...")
                    await page.wait_for_selector("[class*='profile-info']", timeout=10000)
                    
                    # 提取个人资料信息
                    kuaishou_logger.info("正在提取个人资料信息...")
                    self._account_info = await self._extract_profile_info(page)
                    if self._account_info:
                        kuaishou_logger.success("[+] cookie 有效")
                        kuaishou_logger.info(f"账号信息: {self._account_info.username} (ID: {self._account_info.kwai_id})")
                        return True
                    
                    kuaishou_logger.error("未能获取账号信息")
                    return False
                    
                except Exception as e:
                    kuaishou_logger.error(f"验证Cookie时发生错误: {str(e)}")
                    if page:
                        try:
                            current_url = page.url
                            kuaishou_logger.error(f"错误发生时的页面URL: {current_url}")
                            page_content = await page.content()
                            kuaishou_logger.debug(f"页面内容: {page_content[:1000]}...")
                            await page.screenshot(path="error_validate.png")
                            kuaishou_logger.info("已保存错误页面截图: error_validate.png")
                        except Exception as screenshot_error:
                            kuaishou_logger.error(f"保存错误信息失败: {str(screenshot_error)}")
                    return False
                    
        except Exception as e:
            kuaishou_logger.error(f"验证Cookie过程发生错误: {str(e)}")
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

    async def refresh_cookie(self, account_file: str) -> bool:
        """刷新Cookie"""
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
                
                # 等待登录成功
                try:
                    # 等待重定向到主页面或出现登录成功的标志
                    kuaishou_logger.info("等待登录成功...")
                    await page.wait_for_url("**/cp.kuaishou.com/**", timeout=300000)  # 5分钟超时
                    
                    # 等待页面加载完成
                    await page.wait_for_load_state("networkidle")
                    kuaishou_logger.success("检测到登录成功")
                    
                    # 保存当前Cookie
                    await context.storage_state(path=account_file)
                    kuaishou_logger.info("已保存初始Cookie")
                    
                    # 等待一下确保登录状态完全生效
                    await asyncio.sleep(3)
                    
                    # 验证Cookie是否有效
                    if await self.validate_cookie(account_file):
                        kuaishou_logger.success("Cookie验证成功")
                        return True
                    else:
                        kuaishou_logger.error("Cookie验证失败")
                        return False
                        
                except Exception as e:
                    kuaishou_logger.error(f"等待登录超时或发生错误: {str(e)}")
                    if page:
                        try:
                            current_url = page.url
                            kuaishou_logger.error(f"错误发生时的页面URL: {current_url}")
                            await page.screenshot(path="error_login.png")
                            kuaishou_logger.info("已保存错误页面截图: error_login.png")
                            
                            # 保存页面内容以便调试
                            page_content = await page.content()
                            kuaishou_logger.debug(f"页面内容: {page_content[:1000]}...")
                        except:
                            pass
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

    async def setup_account(self, account_file: str, handle: bool = False) -> bool:
        """设置账号"""
        account_file = get_absolute_path(account_file, "ks_uploader")
        
        # 检查数据库中是否存在cookie
        try:
            db = SocialMediaDB()
            cookie_path = db.get_cookie_path("kuaishou", account_file)
            db.close()
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
        return results

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """获取当前账号信息"""
        return self._account_info.to_dict() if self._account_info else None

account_manager = KSAccountManager() 
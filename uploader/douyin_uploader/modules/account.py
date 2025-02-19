"""
抖音账号管理模块
提供cookie验证、生成等功能
"""

import os
import json
import gzip
import base64
from typing import Dict, Any, Optional
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from utils.base_social_media import set_init_script
from utils.log import douyin_logger
from utils.social_media_db import SocialMediaDB
from ..utils.user_info import UserInfoHelper

class AccountManager:
    """抖音账号管理类"""
    
    def __init__(self):
        self.db = SocialMediaDB()
        self.platform = "douyin"
        self.max_cookie_size = 100 * 1024  # 100KB
        # 设置浏览器用户数据目录
        self.user_data_dir = Path(".playwright/user_data/douyin")
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
    
    def _compress_cookie(self, cookie_file: str) -> bool:
        """
        压缩cookie文件
        Args:
            cookie_file: cookie文件路径
        Returns:
            bool: 压缩是否成功
        """
        try:
            # 读取原始cookie文件
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookie_data = json.load(f)
            
            # 将数据转换为JSON字符串并编码为bytes
            json_str = json.dumps(cookie_data, ensure_ascii=False)
            json_bytes = json_str.encode('utf-8')
            
            # 压缩数据
            compressed_data = gzip.compress(json_bytes)
            
            # 将压缩后的数据编码为base64
            encoded_data = base64.b64encode(compressed_data)
            
            # 保存压缩后的数据
            with open(cookie_file, 'wb') as f:
                f.write(encoded_data)
            
            douyin_logger.info(f"Cookie文件已压缩")
            return True
                
        except Exception as e:
            douyin_logger.error(f"压缩cookie文件失败: {str(e)}")
            return False
    
    def _decompress_cookie(self, cookie_file: str) -> Optional[Dict]:
        """
        解压cookie文件
        Args:
            cookie_file: cookie文件路径
        Returns:
            Optional[Dict]: 解压后的cookie数据，失败返回None
        """
        try:
            # 读取压缩的数据
            with open(cookie_file, 'rb') as f:
                encoded_data = f.read()
            
            try:
                # 尝试解析为JSON（未压缩的情况）
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                # 如果失败，尝试解压
                try:
                    # 解码base64
                    compressed_data = base64.b64decode(encoded_data)
                    # 解压数据
                    json_bytes = gzip.decompress(compressed_data)
                    # 解码为字符串
                    json_str = json_bytes.decode('utf-8')
                    # 解析JSON
                    return json.loads(json_str)
                except:
                    douyin_logger.error("无法解析cookie文件")
                    return None
                
        except Exception as e:
            douyin_logger.error(f"解压cookie文件失败: {str(e)}")
            return None
    
    def _check_cookie_size(self, cookie_file: str) -> bool:
        """
        检查cookie文件大小
        Args:
            cookie_file: cookie文件路径
        Returns:
            bool: 文件大小是否合适
        """
        if not os.path.exists(cookie_file):
            return False
            
        file_size = os.path.getsize(cookie_file)
        if file_size > self.max_cookie_size:
            douyin_logger.warning(f"Cookie文件过大: {file_size} bytes，尝试压缩")
            if self._compress_cookie(cookie_file):
                # 再次检查大小
                new_size = os.path.getsize(cookie_file)
                if new_size > self.max_cookie_size:
                    douyin_logger.error(f"压缩后仍然过大: {new_size} bytes")
                    return False
                    
                douyin_logger.info(f"压缩后大小: {new_size} bytes")
                return True
            return False
            
        return True
    
    async def _check_login_status(self, page: Page) -> bool:
        """
        检查是否已登录
        Args:
            page: Playwright页面对象
        Returns:
            bool: 是否已登录
        """
        try:
            # 等待页面加载
            await page.wait_for_load_state("networkidle")
            
            # 检查是否存在登录按钮
            login_button = await page.get_by_text('手机号登录').count()
            if login_button > 0:
                douyin_logger.warning("未检测到登录状态")
                return False
            
            # 检查是否能访问创作者中心
            await page.goto("https://creator.douyin.com/creator-micro/content/upload")
            try:
                await page.wait_for_url(
                    "https://creator.douyin.com/creator-micro/content/upload",
                    timeout=5000
                )
                douyin_logger.info("登录状态有效")
                return True
            except Exception as e:
                douyin_logger.warning(f"访问创作者中心失败: {str(e)}")
                return False
                
        except Exception as e:
            douyin_logger.error(f"检查登录状态时发生错误: {str(e)}")
            return False
    
    async def _close_resources(self, page: Optional[Page] = None, context: Optional[BrowserContext] = None, browser: Optional[Browser] = None) -> None:
        """
        按顺序关闭Playwright资源
        Args:
            page: Playwright页面对象
            context: 浏览器上下文
            browser: 浏览器实例
        """
        try:
            if page:
                await page.close()
        except Exception as e:
            douyin_logger.warning(f"关闭页面时发生错误: {str(e)}")
            
        try:
            if context:
                await context.close()
        except Exception as e:
            douyin_logger.warning(f"关闭context时发生错误: {str(e)}")
            
        try:
            if browser:
                await browser.close()
        except Exception as e:
            douyin_logger.warning(f"关闭browser时发生错误: {str(e)}")
    
    async def cookie_auth(self, account_file: str) -> bool:
        """
        验证cookie是否有效
        Args:
            account_file: cookie文件路径
        Returns:
            bool: cookie是否有效
        """
        if not os.path.exists(account_file):
            douyin_logger.warning(f"Cookie文件不存在: {account_file}")
            return False
            
        # 解压cookie文件
        cookie_data = self._decompress_cookie(account_file)
        if not cookie_data:
            douyin_logger.warning(f"Cookie文件无效")
            return False
            
        # 创建临时cookie文件
        temp_cookie_file = account_file + '.temp'
        try:
            with open(temp_cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookie_data, f)
            
            browser = None
            context = None
            page = None
            try:
                async with async_playwright() as playwright:
                    browser = await playwright.chromium.launch(headless=True)
                    context = await browser.new_context(storage_state=temp_cookie_file)
                    context = await set_init_script(context)
                    page = await context.new_page()
                    
                    return await self._check_login_status(page)
                    
            except Exception as e:
                douyin_logger.error(f"验证cookie时发生错误: {str(e)}")
                return False
                
            finally:
                await self._close_resources(page, context, browser)
                
        finally:
            # 清理临时文件
            if os.path.exists(temp_cookie_file):
                os.remove(temp_cookie_file)

    async def cookie_gen(self, account_file: str) -> None:
        """
        生成抖音cookie文件
        Args:
            account_file: cookie文件路径
        """
        context = None
        page = None
        try:
            douyin_logger.info("开始创建浏览器上下文...")
            async with async_playwright() as playwright:
                # 直接使用playwright.chromium创建持久化上下文
                douyin_logger.info(f"使用用户数据目录: {str(self.user_data_dir)}")
                context = await playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.user_data_dir),
                    headless=False
                )
                douyin_logger.info("浏览器上下文创建成功")
                
                douyin_logger.info("设置初始化脚本...")
                context = await set_init_script(context)
                
                douyin_logger.info("创建新页面...")
                page = await context.new_page()
                
                # 访问登录页面
                douyin_logger.info("正在访问抖音创作者页面...")
                await page.goto("https://creator.douyin.com/")
                douyin_logger.info("页面加载完成，等待登录...")
                
                try:
                    douyin_logger.info("等待页面跳转到首页...")
                    await page.wait_for_url("https://creator.douyin.com/creator-micro/home", timeout=300000)  # 5分钟超时
                    douyin_logger.info("检测到登录成功，等待页面加载...")
                    
                    douyin_logger.info("等待页面网络状态稳定...")
                    await page.wait_for_load_state("networkidle")
                    douyin_logger.info("等待额外2秒确保页面完全加载...")
                    await page.wait_for_timeout(2000)
                    
                    douyin_logger.info("开始获取用户信息...")
                    user_info = await UserInfoHelper.get_user_info(page)
                    if not user_info:
                        douyin_logger.info("从创作者页面获取信息失败，尝试从个人主页获取...")
                        douyin_logger.info("正在跳转到个人主页...")
                        await page.goto("https://www.douyin.com/user/self")
                        douyin_logger.info("等待个人主页加载...")
                        await page.wait_for_timeout(2000)
                        douyin_logger.info("尝试从个人主页获取用户信息...")
                        user_info = await UserInfoHelper.get_user_info(page)
                    
                    if not user_info:
                        douyin_logger.error("无法获取用户信息，保存页面截图和源码用于调试...")
                        await page.screenshot(path="debug_login_failed.png", full_page=True)
                        with open("debug_page_source.html", "w", encoding="utf-8") as f:
                            f.write(await page.content())
                        raise Exception("获取用户信息失败")
                    
                    douyin_logger.info(f"成功获取用户信息: {user_info['nickname']}")
                    
                    # 保存cookie
                    douyin_logger.info("开始保存cookie...")
                    temp_cookie_file = account_file + '.temp'
                    try:
                        # 保存cookie到临时文件
                        douyin_logger.info("保存cookie状态到临时文件...")
                        await context.storage_state(path=temp_cookie_file)
                        
                        # 读取临时文件并压缩保存
                        douyin_logger.info("读取临时cookie文件...")
                        with open(temp_cookie_file, 'r', encoding='utf-8') as f:
                            cookie_data = json.load(f)
                            
                        douyin_logger.info("压缩cookie数据...")
                        # 将数据转换为JSON字符串并编码为bytes
                        json_str = json.dumps(cookie_data, ensure_ascii=False)
                        json_bytes = json_str.encode('utf-8')
                        
                        # 压缩数据
                        compressed_data = gzip.compress(json_bytes)
                        
                        # 将压缩后的数据编码为base64
                        encoded_data = base64.b64encode(compressed_data)
                        
                        douyin_logger.info(f"保存压缩后的cookie到: {account_file}")
                        # 保存压缩后的数据
                        with open(account_file, 'wb') as f:
                            f.write(encoded_data)
                        
                        douyin_logger.success(f"Cookie保存成功: {account_file}")
                        
                    finally:
                        # 清理临时文件
                        if os.path.exists(temp_cookie_file):
                            douyin_logger.info("清理临时cookie文件...")
                            os.remove(temp_cookie_file)
                            
                except Exception as e:
                    douyin_logger.error(f"等待登录超时或获取信息失败: {str(e)}")
                    douyin_logger.info("保存错误现场信息...")
                    try:
                        await page.screenshot(path="error_login.png", full_page=True)
                        with open("error_page.html", "w", encoding="utf-8") as f:
                            f.write(await page.content())
                    except Exception as screenshot_error:
                        douyin_logger.error(f"保存错误现场失败: {str(screenshot_error)}")
                    raise
                
        except Exception as e:
            douyin_logger.error(f"生成cookie时发生错误: {str(e)}")
            # 如果保存失败，确保删除可能存在的cookie文件
            if os.path.exists(account_file):
                douyin_logger.info(f"删除失败的cookie文件: {account_file}")
                os.remove(account_file)
            raise
            
        finally:
            douyin_logger.info("开始清理资源...")
            await self._close_resources(page, context)
            douyin_logger.info("资源清理完成")

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
            # 检查cookie是否存在且有效
            if not os.path.exists(account_file) or not await self.cookie_auth(account_file):
                if not handle:
                    return {
                        'success': False,
                        'message': 'Cookie无效且未启用自动处理'
                    }
                douyin_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录')
                await self.cookie_gen(account_file)
            
            # 验证cookie并获取用户信息
            browser = None
            context = None
            page = None
            user_info = None
            
            try:
                # 解压cookie文件
                cookie_data = self._decompress_cookie(account_file)
                if not cookie_data:
                    return {
                        'success': False,
                        'message': 'Cookie文件无效'
                    }
                
                # 创建临时cookie文件
                temp_cookie_file = account_file + '.temp'
                with open(temp_cookie_file, 'w', encoding='utf-8') as f:
                    json.dump(cookie_data, f)
                
                try:
                    async with async_playwright() as playwright:
                        browser = await playwright.chromium.launch(headless=True)
                        context = await browser.new_context(storage_state=temp_cookie_file)
                        context = await set_init_script(context)
                        page = await context.new_page()
                        
                        # 获取用户信息
                        await page.goto("https://creator.douyin.com/creator-micro/home")
                        await page.wait_for_timeout(2000)  # 等待页面加载
                        
                        # 如果找不到用户信息，尝试访问个人主页
                        user_info = await UserInfoHelper.get_user_info(page)
                        if not user_info:
                            douyin_logger.info("尝试从个人主页获取信息...")
                            await page.goto("https://www.douyin.com/user/self")
                            await page.wait_for_timeout(2000)  # 等待页面加载
                            user_info = await UserInfoHelper.get_user_info(page)
                        
                        if not user_info:
                            return {
                                'success': False,
                                'message': '获取用户信息失败'
                            }
                finally:
                    # 清理临时文件
                    if os.path.exists(temp_cookie_file):
                        os.remove(temp_cookie_file)
                    
            finally:
                await self._close_resources(page, context, browser)
            
            if user_info:
                # 更新数据库
                try:
                    # 首先检查账号是否已存在
                    accounts = self.db.get_all_accounts(self.platform)
                    existing_account = next(
                        (acc for acc in accounts 
                         if acc['account_id'] == user_info['douyin_id'] or 
                         acc['nickname'] == user_info['nickname']),
                        None
                    )
                    
                    if existing_account:
                        # 更新现有账号
                        douyin_logger.info(f"更新现有账号: {user_info['nickname']}")
                        self.db.add_cookie(self.platform, existing_account['account_id'], account_file)
                        # 使用update_account_info方法更新账号信息
                        updated_info = await self.update_account_info(account_file)
                        if not updated_info:
                            return {
                                'success': False,
                                'message': '更新账号信息失败'
                            }
                    else:
                        # 添加新账号
                        douyin_logger.info(f"添加新账号: {user_info['nickname']}")
                        if not self.db.add_account(
                            self.platform,
                            user_info['douyin_id'],
                            user_info['nickname'],
                            follower_count=user_info['fans_count'],
                            extra=user_info  # 直接存储user_info，不进行JSON格式化
                        ):
                            return {
                                'success': False,
                                'message': '添加账号失败'
                            }
                        self.db.add_cookie(self.platform, user_info['douyin_id'], account_file)
                    
                    return {
                        'success': True,
                        'message': 'Cookie设置成功',
                        'user_info': user_info,
                        'cookie_file': account_file
                    }
                    
                except Exception as e:
                    douyin_logger.error(f"数据库操作失败: {str(e)}")
                    return {
                        'success': False,
                        'message': f'数据库操作失败: {str(e)}'
                    }
            
        except Exception as e:
            douyin_logger.error(f"设置账号失败: {str(e)}")
            return {
                'success': False,
                'message': f'设置账号失败: {str(e)}'
            }
            
        finally:
            self.db.close()

    async def update_account_info(self, account_file: str) -> Optional[Dict[str, Any]]:
        """
        更新账号信息
        Args:
            account_file: cookie文件路径
        Returns:
            Optional[Dict[str, Any]]: 更新后的账号信息，失败返回None
        """
        browser = None
        context = None
        page = None
        try:
            # 验证cookie并获取用户信息
            if not os.path.exists(account_file):
                douyin_logger.warning(f"Cookie文件不存在: {account_file}")
                return None
                
            # 解压cookie文件
            cookie_data = self._decompress_cookie(account_file)
            if not cookie_data:
                douyin_logger.warning(f"Cookie文件无效")
                return None
            
            # 创建临时cookie文件
            temp_cookie_file = account_file + '.temp'
            with open(temp_cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookie_data, f)
            
            try:
                async with async_playwright() as playwright:
                    browser = await playwright.chromium.launch(headless=True)
                    context = await browser.new_context(storage_state=temp_cookie_file)
                    context = await set_init_script(context)
                    page = await context.new_page()
                    
                    # 获取用户信息
                    await page.goto("https://creator.douyin.com/creator-micro/home")
                    await page.wait_for_timeout(2000)  # 等待页面加载
                    
                    # 如果找不到用户信息，尝试访问个人主页
                    user_info = await UserInfoHelper.get_user_info(page)
                    if not user_info:
                        douyin_logger.info("尝试从个人主页获取信息...")
                        await page.goto("https://www.douyin.com/user/self")
                        await page.wait_for_timeout(2000)  # 等待页面加载
                        user_info = await UserInfoHelper.get_user_info(page)
                    
                    if user_info:
                        # 更新数据库
                        accounts = self.db.get_all_accounts(self.platform)
                        existing_account = next(
                            (acc for acc in accounts 
                             if acc['account_id'] == user_info['douyin_id'] or 
                             acc['nickname'] == user_info['nickname']),
                            None
                        )
                        
                        if existing_account:
                            # 更新现有账号
                            douyin_logger.info(f"更新账号信息: {user_info['nickname']}")
                            self.db.update_account_info(
                                self.platform,
                                existing_account['account_id'],
                                {
                                    'nickname': user_info['nickname'],
                                    'video_count': 0,
                                    'follower_count': user_info['fans_count'],
                                    'extra': user_info  # 直接存储user_info
                                }
                            )
                            return user_info
                            
                        douyin_logger.warning(f"未找到对应账号: {user_info['nickname']}")
                        return None
                    
                    douyin_logger.error("获取用户信息失败")
                    return None
                    
            finally:
                # 清理临时文件
                if os.path.exists(temp_cookie_file):
                    os.remove(temp_cookie_file)
                    
        except Exception as e:
            douyin_logger.error(f"更新账号信息失败: {str(e)}")
            return None
            
        finally:
            await self._close_resources(page, context, browser)
            self.db.close()

account_manager = AccountManager() 
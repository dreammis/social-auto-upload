# -*- coding: utf-8 -*-
from pathlib import Path
import asyncio
from playwright.async_api import async_playwright
import sys
import json
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
ROOT_DIR = Path(__file__).parent.parent.parent.parent
sys.path.append(str(ROOT_DIR))

from utils.base_social_media import set_init_script
from utils.log import tencent_logger
from utils.social_media_db import SocialMediaDB
from typing import Optional

async def get_account_info(page) -> dict:
    """
    获取账号信息的通用方法，使用多重备选策略
    
    Args:
        page: playwright页面对象
    
    Returns:
        dict: 包含账号信息的字典
    """
    try:
        # 多重备选选择器，按优先级排序
        nickname_selectors = [
            'h2.finder-nickname',  # 基础类选择器
            '.finder-nickname',    # 简单类选择器
            'div:has-text("视频号ID") >> xpath=../h2',  # 使用相邻元素定位
            'h2:has-text("视频号")',  # 使用文本内容定位
        ]
        
        # 尝试所有选择器直到找到元素
        nickname = None
        for selector in nickname_selectors:
            element = page.locator(selector).first
            if await element.count():
                nickname = await element.inner_text()
                break
        
        if not nickname:
            raise Exception("无法获取账号昵称")
        
        # 获取其他账号信息
        info = {
            'nickname': nickname,
            'id': await page.locator('#finder-uid-copy').get_attribute('data-clipboard-text') or '',
            'video_count': await page.locator('.finder-content-info .finder-info-num').first.inner_text() or '0',
            'follower_count': await page.locator('.second-info .finder-info-num').inner_text() or '0',
            'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        # 更新数据库
        try:
            db = SocialMediaDB()
            account = db.get_account("tencent", info['id'])
            
            if account:
                # 如果账号已存在，更新信息
                db.update_account("tencent", info['id'], {
                    'nickname': info['nickname'],
                    'video_count': int(info['video_count']),
                    'follower_count': int(info['follower_count'])
                })
            else:
                # 如果账号不存在，添加新账号
                db.add_account(
                    "tencent",
                    info['id'],
                    info['nickname'],
                    int(info['video_count']),
                    int(info['follower_count'])
                )
            db.close()
        except Exception as e:
            tencent_logger.error(f"更新账号数据库失败: {str(e)}")
        
        return info
        
    except Exception as e:
        tencent_logger.error(f"获取账号信息失败: {str(e)}")
        return None


async def cookie_auth(account_file):
    """
    使用 account_file 中的 cookie 进行微信渠道平台的登录验证。
    如果cookie失效，会自动尝试重新登录获取新cookie。

    Args:
        account_file (str): 包含 cookie 信息的文件路径。

    Returns:
        bool: 如果 cookie 有效或成功获取新cookie，返回 True；否则返回 False。
    """
    from .cookie import get_tencent_cookie  # 避免循环导入
    
    account_name = Path(account_file).stem
    tencent_logger.info(f"[+][{account_name}] 开始验证cookie...")

    # 启动一个无头的 Chromium 浏览器实例。
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        # 创建一个新的浏览器上下文，并加载账户文件中的存储状态（cookie）。
        context = await browser.new_context(storage_state=str(account_file))
        context = await set_init_script(context)
        # 创建一个新的页面。
        page = await context.new_page()
        # 访问指定的 URL。
        await page.goto("https://channels.weixin.qq.com/platform/post/create")
        tencent_logger.info(f"访问指定的 URL。{account_file}- cookie 验证")
        try:
            # 等待页面上出现特定的元素，以验证 cookie 是否有效。
            await page.wait_for_selector('div.title-name:has-text("微信小店")', timeout=5000)  # 等待5秒
            # 如果元素出现，说明 cookie 失效。
            tencent_logger.error(f"[+][{account_name}] cookie 失效，准备重新登录")
            
            # 直接尝试重新登录获取新cookie
            if new_cookie_file := await get_tencent_cookie(str(account_file)):
                # 验证新获取的cookie是否有效
                return await cookie_auth(str(new_cookie_file))
            return False
            
        except:
            # 如果元素未出现，说明 cookie 有效。
            tencent_logger.success(f"[+][{account_name}] cookie 有效")
            
            # 更新数据库中的cookie状态
            try:
                db = SocialMediaDB()
                # 获取账号信息
                account_info = await get_account_info(page)
                if account_info:
                    db.update_cookie_status("tencent", account_info['id'], str(account_file), True)
                db.close()
            except Exception as e:
                tencent_logger.error(f"更新cookie状态失败: {str(e)}")
            
            return True


async def batch_cookie_auth(cookie_files: list) -> dict:
    """
    并发验证多个账号的cookie有效性

    Args:
        cookie_files: cookie文件路径列表

    Returns:
        dict: {cookie_file: (is_valid, account_name)}
        例如：{
            'path/to/cookie1.json': (True, '账号1'),
            'path/to/cookie2.json': (False, '账号2')
        }
    """
    async def verify_single_cookie(cookie_file):
        account_name = Path(cookie_file).stem
        is_valid = await cookie_auth(str(cookie_file))  # 确保传入字符串路径
        return str(cookie_file), (is_valid, account_name)  # 确保返回字符串路径

    # 创建所有cookie验证任务
    tasks = [verify_single_cookie(file) for file in cookie_files]

    # 并发执行所有验证任务
    results = await asyncio.gather(*tasks)

    # 转换为字典格式返回
    return dict(results)


async def get_tencent_cookie(save_dir: str) -> Optional[str]:
    """
    获取腾讯视频号的cookie
    通过扫码登录获取新账号的cookie并保存账号信息
    
    Args:
        save_dir: cookie保存目录
        
    Returns:
        Optional[str]: 成功返回cookie文件路径，失败返回None
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            context = await set_init_script(context)
            page = await context.new_page()
            
            # 访问登录页面
            await page.goto("https://channels.weixin.qq.com/platform/login")
            tencent_logger.info("请使用微信扫码登录...")
            
            # 等待登录成功并跳转到首页
            await page.wait_for_url("https://channels.weixin.qq.com/platform", timeout=300000)  # 5分钟超时
            await page.wait_for_load_state("networkidle")
            
            # 使用get_account_info获取账号信息
            account_info = await get_account_info(page)
            if not account_info:
                raise Exception("无法获取账号信息")
            
            # 使用昵称作为文件名
            nickname = account_info['nickname']
            save_path = str(Path(save_dir) / f"{nickname}.json")
            
            # 保存cookie
            await context.storage_state(path=save_path)
            tencent_logger.success(f"Cookie已保存到: {save_path}")
            
            # 确保账号信息正确添加到数据库
            db = SocialMediaDB()
            try:
                # 检查账号是否存在
                account = db.get_account("tencent", account_info['id'])
                
                if account:
                    # 更新现有账号信息
                    db.update_account("tencent", account_info['id'], {
                        'nickname': nickname,
                        'video_count': int(account_info['video_count']),
                        'follower_count': int(account_info['follower_count'])
                    })
                else:
                    # 添加新账号
                    db.add_account(
                        platform="tencent",
                        platform_id=account_info['id'],
                        nickname=nickname,
                        video_count=int(account_info['video_count']),
                        follower_count=int(account_info['follower_count'])
                    )
                
                # 添加或更新cookie
                db.add_cookie("tencent", account_info['id'], save_path)
                
                # 更新cookie状态
                db.update_cookie_status("tencent", account_info['id'], save_path, True)
                
            finally:
                db.close()
            
            return save_path
            
    except Exception as e:
        tencent_logger.error(f"获取Cookie失败: {str(e)}")
        return None 
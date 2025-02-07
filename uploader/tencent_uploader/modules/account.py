# -*- coding: utf-8 -*-
from pathlib import Path
import asyncio
from playwright.async_api import async_playwright
from utils.base_social_media import set_init_script
from utils.log import tencent_logger
from utils.social_media_db import SocialMediaDB

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
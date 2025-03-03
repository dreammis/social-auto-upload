# -*- coding: utf-8 -*-
from pathlib import Path
from playwright.async_api import async_playwright
from utils.log import tencent_logger
from utils.social_media_db import SocialMediaDB
from utils.base_social_media import set_init_script
from .account import get_account_info

async def get_tencent_cookie(account_file):
    """
    异步获取腾讯的cookie，通过启动浏览器并手动登录实现。
    """
    try:
        async with async_playwright() as playwright:
            options = {
                'args': ['--lang en-GB'],
                'headless': False,
            }
            browser = await playwright.chromium.launch(**options)
            context = await browser.new_context()
            context = await set_init_script(context)
            page = await context.new_page()
            
            # 访问登录页面
            await page.goto("https://channels.weixin.qq.com")
            
            # 等待登录成功
            tencent_logger.info("[+]等待扫码登录...")
            try:
                # 等待登录成功后的重定向
                await page.wait_for_url("https://channels.weixin.qq.com/platform", timeout=120000)  # 2分钟超时
            except Exception as e:
                tencent_logger.error("[+]登录超时，请在2分钟内完成扫码")
                return None
            
            # 确保页面完全加载
            await page.wait_for_load_state('networkidle')
            
            # 获取账号信息
            account_info = await get_account_info(page)
            if account_info:
                # 创建以账号昵称命名的cookie文件
                cookie_dir = Path(account_file).parent
                cookie_file = cookie_dir / f"{account_info['nickname']}.json"
                
                # 保存cookie
                await context.storage_state(path=str(cookie_file))
                tencent_logger.success(f'[+]成功获取账号 {account_info["nickname"]} 的cookie')
                tencent_logger.info(f'   [-]视频数: {account_info["video_count"]}')
                tencent_logger.info(f'   [-]粉丝数: {account_info["follower_count"]}')
                tencent_logger.info(f'   [-]视频号ID: {account_info["id"]}')
                
                # 添加cookie到数据库
                try:
                    db = SocialMediaDB()
                    db.add_cookie("tencent", account_info['id'], str(cookie_file))
                    db.close()
                except Exception as e:
                    tencent_logger.error(f"添加cookie到数据库失败: {str(e)}")
                
                return str(cookie_file)
            else:
                tencent_logger.error("[+]未能获取账号信息")
                return None
                
    except Exception as e:
        tencent_logger.error(f"获取cookie失败: {str(e)}")
        return None
    finally:
        try:
            await browser.close()
        except:
            pass 
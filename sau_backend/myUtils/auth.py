import asyncio
import configparser
import os

from playwright.async_api import async_playwright
from conf import BASE_DIR
from utils.base_social_media import set_init_script
from utils.log import create_logger
from pathlib import Path
from newFileUpload.platform_configs import PLATFORM_CONFIGS

async def check_cookie(type, file_path):
    """
    根据平台类型验证Cookie有效性
    Args:
        type: 平台类型 (1:小红书, 2:腾讯视频号, 3:抖音, 4:快手, 5:TikTok, 6:Instagram, 7:Facebook, 8:Bilibili, 9:Baijiahao)
        file_path: Cookie文件路径
    Returns:
        bool: Cookie是否有效
    """
    # 使用通用检测方法
    return await check_cookie_generic(type, file_path)

async def check_cookie_generic(type, file_path):
    """
    通用的Cookie有效性验证方法
    Args:
        type: 平台类型 (1:小红书, 2:腾讯视频号, 3:抖音, 4:快手, 5:TikTok, 6:Instagram, 7:Facebook, 8:Bilibili, 9:Baijiahao)
        file_path: Cookie文件路径
    Returns:
        bool: Cookie是否有效
    """
    # 根据类型获取平台配置
    platform_config = None
    for config in PLATFORM_CONFIGS.values():
        if config.get("type") == type:
            platform_config = config
            break

    if not platform_config:
        return False

    platform_name = platform_config.get("platform_name", "unknown")
    personal_url = platform_config.get("personal_url", "")
    logger = create_logger (platform_name, f'logs/{platform_name}.log')
    #logger.info(f"开始检测平台 {platform_name} 的账号有效性")
    if not personal_url:
        logger.error(f"平台 {platform_name} 未配置 personal_url")
        return False

    # 使用Playwright检测账号有效性
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=Path(BASE_DIR / "cookiesFile" / file_path))
            context = await set_init_script(context)

            # 创建一个新的页面
            page = await context.new_page()

            # 访问个人中心页面
            await page.goto(personal_url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(2)

            # 检查是否跳转到登录页面
            current_url = page.url
            #logger.info(f"[+]Current URL: {current_url}")

            # 1.检查url是否包含登录相关的关键词
            login_keywords = ["login", "signin", "auth", "登录", "登录页", "登录页面", "foryou"]
            is_login_page = any(keyword in current_url.lower() for keyword in login_keywords)

            if is_login_page:
                logger.error(f"[{platform_name}] 账号未登录，URL跳转到了登录页面")
                await context.close()
                await browser.close()
                return False

            # 根据不同平台的特征元素进行检查
            # 2.检查页面内容是否包含登录相关的文本（douyin特征，就算没登录也可以到个人中心url）
            if platform_name in ["douyin"]:
                try:
                    content = await page.content()
                    # 检查是否包含登录按钮或登录提示
                    login_texts = ["登录", "Sign in", "Log in", "登录/注册", "扫码登录"]
                    for text in login_texts:
                        if text in content:
                            logger.error(f"[{platform_name}] 页面包含登录文本: {text}")
                            await context.close()
                            await browser.close()
                            return False
                except Exception as e:
                    logger.warning(f"[{platform_name}] 读取页面内容失败: {str(e)}")

            # 检查是否成功加载个人中心页面的特征元素

            # 暂时使用通用的检查方法
            logger.success(f"[{platform_name}] 账号有效")
            await context.close()
            await browser.close()
            return True
    except Exception as e:
        logger.error(f"[{platform_name}] 检测账号有效性时出错: {str(e)}")
        return False
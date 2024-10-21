# -*- coding: utf-8 -*-
from datetime import datetime

from playwright.async_api import Playwright, async_playwright, Page
import os
import asyncio

from conf import LOCAL_CHROME_PATH
from uploader.douyin_uploader.main import douyin_cookie_gen, cookie_auth
from utils.base_social_media import set_init_script
from utils.log import douyin_logger
from utils.send_wechat import *
from utils.redis_tools import *


async def douyin_setup(account_file, handle=False):
    """
    功能：检查cookie文件是否存在或有效，并在必要时生成新的cookie。
    执行步骤：
    1. 检查account_file是否存在，或者调用cookie_auth验证cookie是否有效。
    2. 如果cookie无效且handle为True，则调用douyin_cookie_gen生成新的cookie。
    3. 如果cookie有效或成功生成新的cookie，返回True。
    """
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            # Todo alert message
            return False
        douyin_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会动生成cookie文件')
        await douyin_cookie_gen(account_file)
    return True


class DouYinImage(object):
    def __init__(self, title, file_path_list, tags, publish_date: datetime, account_file, thumbnail_path=None, location="成都市"):
        self.title = title  # 视频标题
        self.file_path_list = file_path_list
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.date_format = '%Y年%m月%d日 %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
        self.thumbnail_path = thumbnail_path
        self.location = location

    async def set_schedule_time_douyin(self, page, publish_date):
        # 选择包含特定文本内容的 label 元素
        label_element = page.locator("[class^='radio']:has-text('定时发布')")
        # 在选中的 label 元素下点击 checkbox
        await label_element.click()
        await asyncio.sleep(1)
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M")

        await asyncio.sleep(1)
        await page.locator('.semi-input[placeholder="日期和时间"]').click()
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date_hour))
        await page.keyboard.press("Enter")

        await asyncio.sleep(1)

    async def handle_upload_error(self, page):
        douyin_logger.info('视频出错了，重新上传中')
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.file_path_list)

    async def upload(self, playwright: Playwright) -> None:
        # 使用 Chromium 浏览器启动一个浏览器实例
        if self.local_executable_path:
            browser = await playwright.chromium.launch(headless=False, executable_path=self.local_executable_path)
        else:
            browser = await playwright.chromium.launch(headless=False)
        # 创建一个浏览器上下文，使用指定的 cookie 文件
        context = await browser.new_context(storage_state=f"{self.account_file}")
        context = await set_init_script(context)

        # 创建一个新的页面
        page = await context.new_page()
        await page.goto("https://creator.douyin.com/content/upload?default-tab=3")
        douyin_logger.info(f'  [-] 进入页面...')
        
        # 上传图片
        await page.locator("input[type='file'][accept^='image/']").set_input_files(self.file_path_list)
        douyin_logger.info(f'  [-] 上传图片...')

        # 等待上传完成
        # await page.wait_for_selector('.upload-success-icon', state='visible')

        # 填充标题和话题
        await asyncio.sleep(1)
        douyin_logger.info(f'  [-] 正在填充标题和话题...')
        title_container = page.get_by_placeholder("添加作品标题")
        await title_container.fill(self.title[:30])

        description = " ".join([f"#{tag}" for tag in self.tags])
        await page.locator(".zone-container").fill(f"{self.title} {description}")

        # 设置音乐（可选）
        await page.get_by_text("点击添加合适作品风格音乐选择音乐").click()
        await page.locator("span").filter(has_text="选择音乐").click()
        await page.locator(".card-container-right-BGf7nd > .semi-button").first.click()
        douyin_logger.info(f'  [-] 设置音乐...')

        # 设置位置信息
        await self.set_location(page, self.location)
        douyin_logger.info(f'  [-] 设置位置: {self.location}...')

        # 设置发布时间（如果需要）
        if self.publish_date != 0:
            await self.set_schedule_time_douyin(page, self.publish_date)

        # 点击发布按钮
        publish_button = page.get_by_role('button', name="发布", exact=True)
        await publish_button.click()

        # 等待发布完成
        await page.wait_for_url("https://creator.douyin.com/content/manage**", timeout=60000)
        douyin_logger.success("  [-]图文发布成功")

        await context.storage_state(path=self.account_file)  # 保存cookie
        douyin_logger.success('  [-]cookie更新完毕！')
        # await asyncio.sleep(2)  # 这里延迟是为了方便眼睛直观的观看
        # 关闭浏览上下文和浏览器实例
        await context.close()
        await browser.close()
    
    async def set_thumbnail(self, page: Page, thumbnail_path: str):
        if thumbnail_path:
            await page.click('text="选择封面"')
            await page.wait_for_selector("div.semi-modal-content:visible")
            await page.click('text="上传封面"')
            # 定位到上传区域并点击
            await page.locator("div[class^='semi-upload upload'] >> input.semi-upload-hidden-input").set_input_files(thumbnail_path)
            await page.wait_for_timeout(2000)  # 等2秒
            await page.locator("div[class^='uploadCrop'] button:has-text('完成')").click()

    async def set_location(self, page: Page, location: str):
        await page.locator('div.semi-select span:has-text("输入相关位置")').click()
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(2000)
        await page.keyboard.type(location)
        await page.wait_for_selector('div[role="listbox"] [role="option"]', timeout=5000)
        await page.locator('div[role="listbox"] [role="option"]').first.click()

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

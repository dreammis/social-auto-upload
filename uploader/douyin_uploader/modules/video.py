"""
抖音视频上传模块
提供视频上传、封面设置等功能
"""

import asyncio
from datetime import datetime
from typing import List, Optional

from playwright.async_api import Playwright, Page
from utils.log import douyin_logger
from conf import LOCAL_CHROME_PATH
from utils.base_social_media import set_init_script

class DouYinVideo:
    """抖音视频上传类"""
    
    def __init__(self, 
                 title: str,
                 file_path: str,
                 tags: List[str],
                 publish_date: datetime,
                 account_file: str,
                 thumbnail_path: Optional[str] = None):
        """
        初始化抖音视频上传器
        Args:
            title: 视频标题
            file_path: 视频文件路径
            tags: 视频标签列表
            publish_date: 发布时间
            account_file: cookie文件路径
            thumbnail_path: 封面图片路径
        """
        self.title = title
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.thumbnail_path = thumbnail_path
        self.local_executable_path = LOCAL_CHROME_PATH

    async def set_schedule_time(self, page: Page, publish_date: datetime) -> None:
        """
        设置定时发布时间
        Args:
            page: Playwright页面对象
            publish_date: 发布时间
        """
        label_element = page.locator("[class^='radio']:has-text('定时发布')")
        await label_element.click()
        await asyncio.sleep(1)
        
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M")
        await page.locator('.semi-input[placeholder="日期和时间"]').click()
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date_hour))
        await page.keyboard.press("Enter")
        await asyncio.sleep(1)

    async def handle_upload_error(self, page: Page) -> None:
        """
        处理上传错误
        Args:
            page: Playwright页面对象
        """
        douyin_logger.info('视频出错了，重新上传中')
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.file_path)

    async def set_thumbnail(self, page: Page, thumbnail_path: str) -> None:
        """
        设置视频封面
        Args:
            page: Playwright页面对象
            thumbnail_path: 封面图片路径
        """
        if thumbnail_path:
            await page.click('text="选择封面"')
            await page.wait_for_selector("div.semi-modal-content:visible")
            await page.click('text="设置竖封面"')
            await page.wait_for_timeout(2000)
            await page.locator("div[class^='semi-upload upload'] >> input.semi-upload-hidden-input").set_input_files(thumbnail_path)
            await page.wait_for_timeout(2000)
            await page.locator("div[class^='extractFooter'] button:visible:has-text('完成')").click()

    async def set_location(self, page: Page, location: str = "杭州市") -> None:
        """
        设置视频位置信息
        Args:
            page: Playwright页面对象
            location: 位置信息
        """
        await page.locator('div.semi-select span:has-text("输入地理位置")').click()
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(2000)
        await page.keyboard.type(location)
        await page.wait_for_selector('div[role="listbox"] [role="option"]', timeout=5000)
        await page.locator('div[role="listbox"] [role="option"]').first.click()

    async def upload(self, playwright: Playwright) -> None:
        """
        执行视频上传流程
        Args:
            playwright: Playwright实例
        """
        browser = await playwright.chromium.launch(
            headless=False,
            executable_path=self.local_executable_path if self.local_executable_path else None
        )
        context = await browser.new_context(storage_state=self.account_file)
        context = await set_init_script(context)
        page = await context.new_page()
        
        try:
            # 1. 打开上传页面
            await page.goto("https://creator.douyin.com/creator-micro/content/upload")
            douyin_logger.info(f'[+]正在上传-------{self.title}.mp4')
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload")
            
            # 2. 上传视频文件
            await page.locator("div[class^='container'] input").set_input_files(self.file_path)
            
            # 3. 等待进入发布页面
            while True:
                try:
                    await page.wait_for_url(
                        "https://creator.douyin.com/creator-micro/content/post/video?enter_from=publish_page"
                    )
                    break
                except:
                    douyin_logger.info(f'  [-] 正在等待进入视频发布页面...')
                    await asyncio.sleep(0.1)
            
            # 4. 填写视频信息
            await asyncio.sleep(1)
            douyin_logger.info(f'  [-] 正在填充标题和话题...')
            
            # 设置标题
            title_container = page.get_by_text('作品标题').locator("..").locator("xpath=following-sibling::div[1]").locator("input")
            if await title_container.count():
                await title_container.fill(self.title[:30])
            else:
                titlecontainer = page.locator(".notranslate")
                await titlecontainer.click()
                await page.keyboard.press("Control+KeyA")
                await page.keyboard.press("Delete")
                await page.keyboard.type(self.title)
                await page.keyboard.press("Enter")
            
            # 设置标签
            css_selector = ".zone-container"
            for tag in self.tags:
                await page.type(css_selector, "#" + tag)
                await page.press(css_selector, "Space")
            douyin_logger.info(f'总共添加{len(self.tags)}个话题')
            
            # 5. 等待视频上传完成
            while True:
                try:
                    number = await page.locator('[class^="long-card"] div:has-text("重新上传")').count()
                    if number > 0:
                        douyin_logger.success("  [-]视频上传完毕")
                        break
                    else:
                        douyin_logger.info("  [-] 正在上传视频中...")
                        await asyncio.sleep(2)

                        if await page.locator('div.progress-div > div:has-text("上传失败")').count():
                            douyin_logger.error("  [-] 发现上传出错了... 准备重试")
                            await self.handle_upload_error(page)
                except:
                    douyin_logger.info("  [-] 正在上传视频中...")
                    await asyncio.sleep(2)
            
            # 6. 设置封面
            await self.set_thumbnail(page, self.thumbnail_path)
            
            # 7. 设置位置信息
            await self.set_location(page, "杭州市")
            
            # 8. 设置第三方平台
            third_part_element = '[class^="info"] > [class^="first-part"] div div.semi-switch'
            if await page.locator(third_part_element).count():
                if 'semi-switch-checked' not in await page.eval_on_selector(third_part_element, 'div => div.className'):
                    await page.locator(third_part_element).locator('input.semi-switch-native-control').click()
            
            # 9. 设置发布时间
            if self.publish_date != 0:
                await self.set_schedule_time(page, self.publish_date)
            
            # 10. 发布视频
            while True:
                try:
                    publish_button = page.get_by_role('button', name="发布", exact=True)
                    if await publish_button.count():
                        await publish_button.click()
                    await page.wait_for_url("https://creator.douyin.com/creator-micro/content/manage**", timeout=3000)
                    douyin_logger.success("  [-]视频发布成功")
                    break
                except:
                    douyin_logger.info("  [-] 视频正在发布中...")
                    await page.screenshot(full_page=True)
                    await asyncio.sleep(0.5)
            
            # 11. 更新cookie
            await context.storage_state(path=self.account_file)
            douyin_logger.success('  [-]cookie更新完毕！')
            await asyncio.sleep(2)
            
        finally:
            await context.close()
            await browser.close()

    async def main(self) -> None:
        """
        主函数，执行完整的视频上传流程
        """
        async with async_playwright() as playwright:
            await self.upload(playwright) 
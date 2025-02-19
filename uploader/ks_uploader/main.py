# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Dict, Any, Optional

from playwright.async_api import Playwright, async_playwright
import os
import asyncio

from conf import LOCAL_CHROME_PATH
from utils.base_social_media import set_init_script
from utils.files_times import get_absolute_path
from utils.log import kuaishou_logger
from .modules.account import account_manager
from .modules.video import KSVideoUploader, KSBatchUploader
from .modules.validator import validator


async def cookie_auth(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://cp.kuaishou.com/article/publish/video")
        try:
            await page.wait_for_selector("div.names div.container div.name:text('机构服务')", timeout=5000)  # 等待5秒

            kuaishou_logger.info("[+] 等待5秒 cookie 失效")
            return False
        except:
            kuaishou_logger.success("[+] cookie 有效")
            return True


async def ks_setup(account_file, handle=False):
    account_file = get_absolute_path(account_file, "ks_uploader")
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            return False
        kuaishou_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件')
        await get_ks_cookie(account_file)
    return True


async def get_ks_cookie(account_file):
    async with async_playwright() as playwright:
        options = {
            'args': [
                '--lang en-GB'
            ],
            'headless': False,  # Set headless option here
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://cp.kuaishou.com")
        await page.pause()
        # 点击调试器的继续，保存cookie
        await context.storage_state(path=account_file)


class KSVideo(object):
    def __init__(self, title, file_path, tags, publish_date: datetime, account_file):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.date_format = '%Y-%m-%d %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH

    async def handle_upload_error(self, page):
        kuaishou_logger.error("视频出错了，重新上传中")
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.file_path)

    async def upload(self, playwright: Playwright) -> None:
        # 使用 Chromium 浏览器启动一个浏览器实例
        print(self.local_executable_path)
        if self.local_executable_path:
            browser = await playwright.chromium.launch(
                headless=False,
                executable_path=self.local_executable_path,
            )
        else:
            browser = await playwright.chromium.launch(
                headless=False
            )  # 创建一个浏览器上下文，使用指定的 cookie 文件
        context = await browser.new_context(storage_state=f"{self.account_file}")
        context = await set_init_script(context)
        context.on("close", lambda: context.storage_state(path=self.account_file))

        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://cp.kuaishou.com/article/publish/video")
        kuaishou_logger.info('正在上传-------{}.mp4'.format(self.title))
        # 等待页面跳转到指定的 URL，没进入，则自动等待到超时
        kuaishou_logger.info('正在打开主页...')
        await page.wait_for_url("https://cp.kuaishou.com/article/publish/video")
        # 点击 "上传视频" 按钮
        upload_button = page.locator("button[class^='_upload-btn']")
        await upload_button.wait_for(state='visible')  # 确保按钮可见

        async with page.expect_file_chooser() as fc_info:
            await upload_button.click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(self.file_path)

        await asyncio.sleep(2)

        # if not await page.get_by_text("封面编辑").count():
        #     raise Exception("似乎没有跳转到到编辑页面")

        await asyncio.sleep(1)

        # 等待按钮可交互
        new_feature_button = page.locator('button[type="button"] span:text("我知道了")')
        if await new_feature_button.count() > 0:
            await new_feature_button.click()

        kuaishou_logger.info("正在填充标题和话题...")
        await page.get_by_text("描述").locator("xpath=following-sibling::div").click()
        kuaishou_logger.info("clear existing title")
        await page.keyboard.press("Backspace")
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.press("Delete")
        kuaishou_logger.info("filling new  title")
        await page.keyboard.type(self.title)
        await page.keyboard.press("Enter")

        # 快手只能添加3个话题
        for index, tag in enumerate(self.tags[:3], start=1):
            kuaishou_logger.info("正在添加第%s个话题" % index)
            await page.keyboard.type(f"#{tag} ")
            await asyncio.sleep(2)

        max_retries = 60  # 设置最大重试次数,最大等待时间为 2 分钟
        retry_count = 0

        while retry_count < max_retries:
            try:
                # 获取包含 '上传中' 文本的元素数量
                number = await page.locator("text=上传中").count()

                if number == 0:
                    kuaishou_logger.success("视频上传完毕")
                    break
                else:
                    if retry_count % 5 == 0:
                        kuaishou_logger.info("正在上传视频中...")
                    await asyncio.sleep(2)
            except Exception as e:
                kuaishou_logger.error(f"检查上传状态时发生错误: {e}")
                await asyncio.sleep(2)  # 等待 2 秒后重试
            retry_count += 1

        if retry_count == max_retries:
            kuaishou_logger.warning("超过最大重试次数，视频上传可能未完成。")

        # 定时任务
        if self.publish_date != 0:
            await self.set_schedule_time(page, self.publish_date)

        # 判断视频是否发布成功
        while True:
            try:
                publish_button = page.get_by_text("发布", exact=True)
                if await publish_button.count() > 0:
                    await publish_button.click()

                await asyncio.sleep(1)
                confirm_button = page.get_by_text("确认发布")
                if await confirm_button.count() > 0:
                    await confirm_button.click()

                # 等待页面跳转，确认发布成功
                await page.wait_for_url(
                    "https://cp.kuaishou.com/article/manage/video?status=2&from=publish",
                    timeout=5000,
                )
                kuaishou_logger.success("视频发布成功")
                break
            except Exception as e:
                kuaishou_logger.info(f"视频正在发布中... 错误: {e}")
                await page.screenshot(full_page=True)
                await asyncio.sleep(1)

        await context.storage_state(path=self.account_file)  # 保存cookie
        kuaishou_logger.info('cookie更新完毕！')
        await asyncio.sleep(2)  # 这里延迟是为了方便眼睛直观的观看
        # 关闭浏览器上下文和浏览器实例
        await context.close()
        await browser.close()

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def set_schedule_time(self, page, publish_date):
        kuaishou_logger.info("click schedule")
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M:%S")
        await page.locator("label:text('发布时间')").locator('xpath=following-sibling::div').locator(
            '.ant-radio-input').nth(1).click()
        await asyncio.sleep(1)

        await page.locator('div.ant-picker-input input[placeholder="选择日期时间"]').click()
        await asyncio.sleep(1)

        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date_hour))
        await page.keyboard.press("Enter")
        await asyncio.sleep(1)


async def upload_video(
    title: str,
    file_path: str,
    tags: List[str],
    account_file: str,
    publish_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    上传单个视频
    Args:
        title: 视频标题
        file_path: 视频文件路径
        tags: 视频标签列表
        account_file: cookie文件路径
        publish_date: 定时发布时间
    Returns:
        Dict[str, Any]: 上传结果
    """
    try:
        # 验证参数
        validation_result = validator.validate_video_params(
            title=title,
            tags=tags,
            file_path=file_path,
            publish_date=publish_date
        )
        
        if not validation_result['valid']:
            return {
                'success': False,
                'errors': validation_result['errors']
            }

        # 验证账号
        if not await account_manager.setup_account(account_file, handle=True):
            return {
                'success': False,
                'errors': ['账号设置失败']
            }

        # 创建上传器并开始上传
        uploader = KSVideoUploader(
            title=title,
            file_path=file_path,
            tags=tags,
            publish_date=publish_date,
            account_file=account_file
        )

        success = await uploader.start()
        
        return {
            'success': success,
            'errors': [] if success else ['上传失败']
        }

    except Exception as e:
        kuaishou_logger.error(f"上传视频时发生错误: {str(e)}")
        return {
            'success': False,
            'errors': [str(e)]
        }

async def batch_upload_videos(
    videos: List[Dict[str, Any]],
    account_file: str,
    max_concurrent: int = 3
) -> Dict[str, Any]:
    """
    批量上传视频
    Args:
        videos: 视频信息列表，每个元素包含 title, file_path, tags, publish_date
        account_file: cookie文件路径
        max_concurrent: 最大并发数
    Returns:
        Dict[str, Any]: 批量上传结果
    """
    try:
        # 验证账号
        if not await account_manager.setup_account(account_file, handle=True):
            return {
                'success': False,
                'errors': ['账号设置失败'],
                'results': {}
            }

        # 创建上传器列表
        uploaders = []
        for video in videos:
            # 验证参数
            validation_result = validator.validate_video_params(
                title=video['title'],
                tags=video['tags'],
                file_path=video['file_path'],
                publish_date=video.get('publish_date')
            )
            
            if not validation_result['valid']:
                continue

            uploader = KSVideoUploader(
                title=video['title'],
                file_path=video['file_path'],
                tags=video['tags'],
                publish_date=video.get('publish_date'),
                account_file=account_file
            )
            uploaders.append(uploader)

        # 创建批量上传器
        batch_uploader = KSBatchUploader(max_concurrent=max_concurrent)
        results = await batch_uploader.batch_upload(uploaders)

        return {
            'success': True,
            'errors': [],
            'results': results
        }

    except Exception as e:
        kuaishou_logger.error(f"批量上传视频时发生错误: {str(e)}")
        return {
            'success': False,
            'errors': [str(e)],
            'results': {}
        }

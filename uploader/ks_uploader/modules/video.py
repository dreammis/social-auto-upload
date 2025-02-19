# -*- coding: utf-8 -*-
from datetime import datetime
import asyncio
import os
from typing import List, Dict, Optional, Any
from playwright.async_api import Playwright, async_playwright, Page, Browser, BrowserContext, TimeoutError

from conf import LOCAL_CHROME_PATH
from utils.base_social_media import set_init_script
from utils.log import kuaishou_logger
from ..utils.constants import (
    UPLOAD_TIMEOUT, MAX_RETRIES, 
    BASE_URL, UPLOAD_URL, MANAGE_URL
)

class UploadError(Exception):
    """上传错误基类"""
    pass

class VideoUploadError(UploadError):
    """视频上传错误"""
    pass

class VideoPublishError(UploadError):
    """视频发布错误"""
    pass

class KSVideoUploader:
    def __init__(self, title: str, file_path: str, tags: List[str], 
                 publish_date: Optional[datetime], account_file: str):
        self.title = title
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.date_format = '%Y-%m-%d %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
        self.max_retries = MAX_RETRIES
        self.upload_timeout = UPLOAD_TIMEOUT
        self._upload_start_time = None
        self._last_progress = 0
        self._retry_delays = [2, 5, 10]  # 重试延迟时间（秒）

    async def _retry_with_backoff(self, func: callable, *args, **kwargs) -> Any:
        """实现指数退避的重试机制"""
        last_error = None
        for i, delay in enumerate(self._retry_delays):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if i == len(self._retry_delays) - 1:  # 最后一次重试
                    raise last_error
                kuaishou_logger.warning(f"操作失败，{delay}秒后重试: {str(e)}")
                await asyncio.sleep(delay)
        raise last_error

    async def _check_network_status(self, page: Page) -> bool:
        """检查网络状态"""
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
            return True
        except TimeoutError:
            return False

    async def _monitor_upload_progress(self, page: Page) -> None:
        """监控上传进度"""
        try:
            progress_selector = "div.progress-text"
            progress = await page.locator(progress_selector).text_content()
            if progress and "%" in progress:
                current_progress = int(progress.strip("%"))
                if current_progress > self._last_progress:
                    self._last_progress = current_progress
                    kuaishou_logger.info(f"上传进度: {current_progress}%")
        except Exception as e:
            kuaishou_logger.warning(f"获取上传进度失败: {str(e)}")

    async def handle_upload_error(self, page: Page) -> None:
        """处理上传错误"""
        try:
            # 检查是否有错误提示
            error_text = await page.locator("div.error-message").text_content()
            if error_text:
                raise VideoUploadError(f"上传出错: {error_text}")

            # 尝试重新上传
            kuaishou_logger.error("视频出错了，重新上传中")
            await self._retry_with_backoff(
                page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files,
                self.file_path
            )
        except Exception as e:
            raise VideoUploadError(f"处理上传错误失败: {str(e)}")

    async def fill_video_info(self, page: Page) -> None:
        """填充视频信息"""
        try:
            kuaishou_logger.info("正在填充标题和话题...")
            
            # 清除现有标题
            title_input = page.get_by_text("描述").locator("xpath=following-sibling::div")
            await title_input.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Delete")
            
            # 输入新标题
            await title_input.fill(self.title)
            await page.keyboard.press("Enter")

            # 添加话题
            for index, tag in enumerate(self.tags[:3], start=1):
                kuaishou_logger.info(f"正在添加第{index}个话题")
                await page.keyboard.type(f"#{tag} ")
                await asyncio.sleep(1)  # 降低输入速度，提高稳定性
                
                # 检查话题是否成功添加
                tag_element = page.locator(f"text=#{tag}")
                if not await tag_element.count():
                    kuaishou_logger.warning(f"话题 #{tag} 可能未成功添加")

        except Exception as e:
            raise VideoUploadError(f"填充视频信息失败: {str(e)}")

    async def wait_for_upload(self, page: Page) -> bool:
        """等待上传完成"""
        retry_count = 0
        upload_start_time = datetime.now()
        
        while retry_count < self.upload_timeout // 2:
            try:
                # 检查网络状态
                if not await self._check_network_status(page):
                    kuaishou_logger.warning("网络连接不稳定")
                
                # 监控上传进度
                await self._monitor_upload_progress(page)
                
                # 检查上传状态
                number = await page.locator("text=上传中").count()
                if number == 0:
                    # 验证上传是否真的完成
                    success_text = await page.locator("text=上传成功").count()
                    if success_text > 0:
                        kuaishou_logger.success("视频上传完毕")
                        return True
                    
                # 检查是否有错误提示
                error_element = page.locator("div.error-message")
                if await error_element.count():
                    error_text = await error_element.text_content()
                    raise VideoUploadError(f"上传失败: {error_text}")
                
                # 检查上传超时
                elapsed_time = (datetime.now() - upload_start_time).total_seconds()
                if elapsed_time > self.upload_timeout:
                    raise TimeoutError("上传超时")
                
                if retry_count % 5 == 0:
                    kuaishou_logger.info("正在上传视频中...")
                await asyncio.sleep(2)
                
            except TimeoutError as e:
                raise VideoUploadError(f"上传超时: {str(e)}")
            except Exception as e:
                kuaishou_logger.error(f"检查上传状态时发生错误: {str(e)}")
                await asyncio.sleep(2)
            retry_count += 1
            
        return False

    async def set_schedule_time(self, page: Page) -> None:
        """设置定时发布"""
        if not self.publish_date:
            return
            
        try:
            kuaishou_logger.info("设置定时发布...")
            publish_date_hour = self.publish_date.strftime("%Y-%m-%d %H:%M:%S")
            
            # 选择定时发布选项
            schedule_radio = page.locator("label:text('发布时间')").locator('xpath=following-sibling::div').locator('.ant-radio-input').nth(1)
            await schedule_radio.click()
            await asyncio.sleep(1)

            # 设置发布时间
            date_input = page.locator('div.ant-picker-input input[placeholder="选择日期时间"]')
            await date_input.click()
            await asyncio.sleep(1)
            await page.keyboard.press("Control+A")
            await page.keyboard.type(str(publish_date_hour))
            await page.keyboard.press("Enter")
            
            # 验证时间是否设置成功
            await asyncio.sleep(1)
            date_text = await date_input.input_value()
            if not date_text or publish_date_hour not in date_text:
                raise VideoPublishError("定时发布时间设置失败")
                
        except Exception as e:
            raise VideoPublishError(f"设置定时发布失败: {str(e)}")

    async def publish_video(self, page: Page) -> bool:
        """发布视频"""
        max_publish_attempts = 3
        publish_attempt = 0
        
        while publish_attempt < max_publish_attempts:
            try:
                # 点击发布按钮
                publish_button = page.get_by_text("发布", exact=True)
                if await publish_button.count() > 0:
                    await publish_button.click()
                    await asyncio.sleep(1)

                # 确认发布
                confirm_button = page.get_by_text("确认发布")
                if await confirm_button.count() > 0:
                    await confirm_button.click()

                # 等待发布完成
                try:
                    await page.wait_for_url(
                        f"{MANAGE_URL}?status=2&from=publish",
                        timeout=5000,
                    )
                    kuaishou_logger.success("视频发布成功")
                    return True
                except TimeoutError:
                    # 检查是否有错误提示
                    error_element = page.locator("div.error-message")
                    if await error_element.count():
                        error_text = await error_element.text_content()
                        raise VideoPublishError(f"发布失败: {error_text}")
                    
            except Exception as e:
                publish_attempt += 1
                if publish_attempt == max_publish_attempts:
                    raise VideoPublishError(f"发布视频失败: {str(e)}")
                kuaishou_logger.warning(f"发布尝试 {publish_attempt} 失败: {str(e)}")
                await asyncio.sleep(2)
                await page.screenshot(path=f"publish_error_{publish_attempt}.png")
                
        return False

    async def upload(self, playwright: Playwright) -> bool:
        """上传视频主流程"""
        browser = None
        context = None
        try:
            # 初始化浏览器
            browser_options = {
                'headless': False,
                'args': [
                    '--disable-gpu',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-setuid-sandbox'
                ]
            }
            if self.local_executable_path:
                browser_options['executable_path'] = self.local_executable_path
                
            browser = await playwright.chromium.launch(**browser_options)

            # 创建上下文
            context = await browser.new_context(
                storage_state=self.account_file,
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
            )
            context = await set_init_script(context)
            context.set_default_timeout(30000)  # 设置默认超时时间
            context.on("close", lambda: context.storage_state(path=self.account_file))

            # 创建页面
            page = await context.new_page()
            await page.goto(UPLOAD_URL)
            kuaishou_logger.info(f'正在上传视频: {self.title}')

            # 等待页面加载
            await page.wait_for_load_state("networkidle")
            upload_button = page.locator("button[class^='_upload-btn']")
            await upload_button.wait_for(state='visible')

            # 上传文件
            async with page.expect_file_chooser() as fc_info:
                await upload_button.click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(self.file_path)

            # 处理新功能提示
            new_feature_button = page.locator('button[type="button"] span:text("我知道了")')
            if await new_feature_button.count() > 0:
                await new_feature_button.click()

            # 填充视频信息
            await self.fill_video_info(page)

            # 等待上传完成
            if not await self.wait_for_upload(page):
                raise VideoUploadError("视频上传超时或失败")

            # 设置定时发布
            if self.publish_date:
                await self.set_schedule_time(page)

            # 发布视频
            if not await self.publish_video(page):
                raise VideoPublishError("视频发布失败")

            # 保存Cookie
            await context.storage_state(path=self.account_file)
            kuaishou_logger.info('cookie更新完毕！')
            return True

        except Exception as e:
            kuaishou_logger.error(f"上传过程发生错误: {str(e)}")
            if page:
                await page.screenshot(path=f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            return False

        finally:
            if context:
                await context.close()
            if browser:
                await browser.close()

    async def start(self) -> bool:
        """开始上传流程"""
        try:
            async with async_playwright() as playwright:
                return await self._retry_with_backoff(self.upload, playwright)
        except Exception as e:
            kuaishou_logger.error(f"启动上传失败: {str(e)}")
            return False

class KSBatchUploader:
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._upload_results = {}
        self._failed_uploads = []

    async def upload_with_semaphore(self, uploader: KSVideoUploader) -> bool:
        """使用信号量控制并发上传"""
        async with self.semaphore:
            try:
                result = await uploader.start()
                self._upload_results[uploader.title] = {
                    'success': result,
                    'timestamp': datetime.now().isoformat(),
                    'file_path': uploader.file_path
                }
                if not result:
                    self._failed_uploads.append(uploader)
                return result
            except Exception as e:
                kuaishou_logger.error(f"上传视频 {uploader.title} 失败: {str(e)}")
                self._upload_results[uploader.title] = {
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat(),
                    'file_path': uploader.file_path
                }
                self._failed_uploads.append(uploader)
                return False

    async def retry_failed_uploads(self) -> None:
        """重试失败的上传"""
        if not self._failed_uploads:
            return

        kuaishou_logger.info(f"开始重试 {len(self._failed_uploads)} 个失败的上传")
        retry_tasks = [self.upload_with_semaphore(uploader) for uploader in self._failed_uploads]
        await asyncio.gather(*retry_tasks)
        self._failed_uploads.clear()

    async def batch_upload(self, uploaders: List[KSVideoUploader]) -> Dict[str, Any]:
        """批量上传视频"""
        try:
            # 创建上传任务
            upload_tasks = [self.upload_with_semaphore(uploader) for uploader in uploaders]
            
            # 执行上传任务
            results = await asyncio.gather(*upload_tasks, return_exceptions=True)
            
            # 重试失败的上传
            await self.retry_failed_uploads()
            
            # 生成报告
            return {
                'results': self._upload_results,
                'total': len(uploaders),
                'success': sum(1 for r in results if r is True),
                'failed': sum(1 for r in results if r is False),
                'errors': sum(1 for r in results if isinstance(r, Exception))
            }
            
        except Exception as e:
            kuaishou_logger.error(f"批量上传过程发生错误: {str(e)}")
            return {
                'results': self._upload_results,
                'error': str(e)
            } 
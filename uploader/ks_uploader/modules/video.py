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
                 publish_date: Optional[datetime], account_file: str, mentions: List[str] = None,
                 cover_file: Optional[str] = None):
        self.title = title
        self.file_path = file_path
        self.tags = tags
        self.mentions = mentions or []
        self.publish_date = publish_date
        self.account_file = account_file
        self.cover_file = cover_file
        self.date_format = '%Y-%m-%d %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
        self.max_retries = MAX_RETRIES
        self.upload_timeout = UPLOAD_TIMEOUT
        self._upload_start_time = None
        self._last_progress = 0
        self._retry_delays = [2, 5, 10]

    async def _retry_with_backoff(self, func: callable, *args, **kwargs) -> Any:
        """实现指数退避的重试机制"""
        last_error = None
        kuaishou_logger.debug(f"开始重试操作: func={func.__name__}, args={args}, kwargs={kwargs}")
        for i, delay in enumerate(self._retry_delays):
            try:
                result = await func(*args, **kwargs)
                kuaishou_logger.debug(f"重试操作成功: result={result}")
                return result
            except Exception as e:
                last_error = e
                if i == len(self._retry_delays) - 1:  # 最后一次重试
                    kuaishou_logger.error(f"重试次数已用完，最后错误: {str(last_error)}")
                    raise last_error
                kuaishou_logger.warning(f"第{i+1}次重试失败，{delay}秒后重试: {str(e)}")
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
            # 检查进度条元素
            progress_div = page.locator("div.progress-div")
            if await progress_div.count() > 0:
                # 尝试获取进度文本
                progress_text = await progress_div.text_content()
                if progress_text and "%" in progress_text:
                    current_progress = int(''.join(filter(str.isdigit, progress_text)))
                    if current_progress > self._last_progress:
                        self._last_progress = current_progress
                        kuaishou_logger.info(f"上传进度: {current_progress}%")
        except Exception as e:
            # 如果获取进度失败，不要报错，因为可能已经上传完成
            kuaishou_logger.debug(f"获取上传进度: {str(e)}")

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
            
            # 等待页面完全加载
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)  # 等待页面渲染完成
            
            # 等待描述输入区域加载
            description_editor = await page.wait_for_selector("#work-description-edit", timeout=15000)
            if not description_editor:
                raise VideoUploadError("无法找到描述输入区域")
            
            # 确保编辑区域可见和可交互
            await description_editor.wait_for_element_state("visible")
            await description_editor.wait_for_element_state("enabled")
            
            # 点击编辑区域激活
            await description_editor.click()
            await asyncio.sleep(1)
            
            # 清除并输入标题
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Delete")
            await asyncio.sleep(0.5)
            
            # 输入标题和描述
            await page.keyboard.type(self.title)
            await page.keyboard.press("Enter")
            await asyncio.sleep(1)

            # 添加话题（最多3个）
            for index, tag in enumerate(self.tags[:4], start=1):
                kuaishou_logger.info(f"正在添加第{index}个话题")
                await page.keyboard.type(f"#{tag}")
                await asyncio.sleep(0.25)  # 等待话题建议出现
                await page.keyboard.press("Space")
                # # 检查是否有话题建议出现
                # tag_suggestions = page.locator("._tag_oei9t_283")
                # if await tag_suggestions.count() > 0:
                #     # 点击第一个建议的话题
                #     await tag_suggestions.first.click()
                # else:
                #     # 如果没有建议，就直接用空格分隔
                #     await page.keyboard.press("Space")
                
                await asyncio.sleep(1)  # 确保话题添加完成
                
                # 验证话题是否添加成功
                content = await description_editor.text_content()
                if f"#{tag}" not in content:
                    kuaishou_logger.warning(f"话题 #{tag} 可能未成功添加")
                    
            await page.keyboard.press("Enter")
            await asyncio.sleep(1)
            
            # 输入提及用户
            for mention in self.mentions:
                await page.keyboard.type(f"@{mention}")
                await asyncio.sleep(0.2)     
                await page.keyboard.press("Space")       
                # _at-user-container_oei9t_173

            # 检查字数限制
            text_count = page.locator("._text-tip_oei9t_250")
            if await text_count.count() > 0:
                count_text = await text_count.text_content()
                kuaishou_logger.info(f"当前字数: {count_text}")

            kuaishou_logger.info("视频信息填充完成")

        except Exception as e:
            kuaishou_logger.error(f"填充视频信息失败: {str(e)}", exc_info=True)
            # 保存页面截图以便调试
            try:
                screenshot_path = f"error_fill_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                kuaishou_logger.info(f"错误截图已保存: {screenshot_path}")
            except:
                pass
            raise VideoUploadError(f"填充视频信息失败: {str(e)}")

    async def wait_for_upload(self, page: Page) -> bool:
        """等待上传完成"""
        retry_count = 0
        upload_start_time = datetime.now()
        last_log_time = datetime.now()
        
        while retry_count < self.upload_timeout // 2:
            try:
                current_time = datetime.now()
                # 每5秒记录一次基本状态
                if (current_time - last_log_time).total_seconds() >= 5:
                    kuaishou_logger.info("正在检查上传状态...")
                    last_log_time = current_time
                
                # 检查网络状态
                if not await self._check_network_status(page):
                    kuaishou_logger.warning("网络连接不稳定")
                
                # 记录当前页面URL
                current_url = page.url
                kuaishou_logger.debug(f"当前页面URL: {current_url}")
                
                # 检查上传状态
                # 1. 检查预览区域是否存在
                preview_section = page.locator("section._wrapper_1ahzu_1")
                preview_count = await preview_section.count()
                kuaishou_logger.debug(f"预览区域数量: {preview_count}")
                
                if preview_count > 0:
                    # 2. 检查是否在上传中
                    progress_text = page.locator(".ant-progress-text")
                    progress_count = await progress_text.count()
                    
                    if progress_count > 0:
                        # 获取进度
                        progress = await progress_text.text_content()
                        
                        if progress and "%" in progress:
                            current_progress = int(''.join(filter(str.isdigit, progress)))
                            # 只有当进度发生变化时才记录
                            if current_progress != self._last_progress:
                                self._last_progress = current_progress
                                kuaishou_logger.info(f"上传进度: {current_progress}%")
                                # 记录已经过时间
                                elapsed_time = (datetime.now() - upload_start_time).total_seconds()
                                kuaishou_logger.info(f"已用时: {elapsed_time:.1f}秒")
                            if current_progress >= 100:
                                kuaishou_logger.success("上传进度达到100%！")
                                return True
                    else:
                        kuaishou_logger.debug("未找到进度条")
                    
                    # 3. 检查是否已完成（预览视频区域出现）
                    preview_video = page.locator("div._preview-video_1ahzu_181")
                    video_count = await preview_video.count()
                    
                    if video_count > 0:
                        # 检查视频元素是否真的可见
                        is_visible = await preview_video.is_visible()
                        if is_visible:
                            kuaishou_logger.success("检测到预览视频区域，上传已完成！")
                            return True
                    
                    # 4. 检查上传状态文本
                    upload_status = page.locator("span._phone-label_1ahzu_34")
                    if await upload_status.count() > 0:
                        status_text = await upload_status.text_content()
                        kuaishou_logger.info(f"当前上传状态: {status_text}")
                
                # 5. 检查是否有错误提示
                error_element = page.locator("div.error-message")
                if await error_element.count():
                    error_text = await error_element.text_content()
                    kuaishou_logger.error(f"检测到错误消息: {error_text}")
                    raise VideoUploadError(f"上传失败: {error_text}")
                
                # 6. 检查上传超时
                elapsed_time = (datetime.now() - upload_start_time).total_seconds()
                if elapsed_time > self.upload_timeout:
                    kuaishou_logger.error(f"上传超时，已经过 {elapsed_time:.1f} 秒")
                    raise TimeoutError("上传超时")
                
                await asyncio.sleep(2)
                retry_count += 1
                
            except TimeoutError as e:
                kuaishou_logger.error(f"上传超时: {str(e)}")
                # 保存页面截图
                await page.screenshot(path=f"upload_timeout_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                raise VideoUploadError(f"上传超时: {str(e)}")
            except Exception as e:
                kuaishou_logger.error(f"检查上传状态时发生错误: {str(e)}")
                # 保存页面截图
                await page.screenshot(path=f"upload_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                await asyncio.sleep(2)
            
        kuaishou_logger.error("达到最大重试次数，上传可能失败")
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

    async def edit_cover(self, page: Page) -> None:
        """编辑视频封面
        
        Args:
            page: Playwright页面对象
        """
        if not self.cover_file:
            kuaishou_logger.info("未提供封面文件，跳过封面设置")
            return

        try:
            kuaishou_logger.info("开始设置视频封面...")
            
            # 等待封面编辑区域加载
            cover_editor = page.locator("div._high-cover-editor_y5cqm_1")
            await cover_editor.wait_for(state="visible", timeout=10000)
            
            # 找到默认封面区域并点击
            default_cover = cover_editor.locator("div._default-cover_y5cqm_68")
            await default_cover.wait_for(state="visible", timeout=5000)
            
            # 鼠标移动到封面区域以显示替换按钮
            await default_cover.hover()
            await asyncio.sleep(1)  # 等待替换按钮出现
            
            # 点击替换按钮打开弹窗
            replace_button = default_cover.locator("span._cover-editor-text_y5cqm_58").filter(has_text="替换")
            await replace_button.click()
            await asyncio.sleep(1)
            
            # 等待弹窗加载
            modal = page.locator("div.ant-modal")
            await modal.wait_for(state="visible", timeout=5000)
            
            # 找到上传封面的input元素
            file_input = modal.locator('input[type="file"][accept*="image"]')
            
            # 上传封面文件
            await file_input.set_input_files(self.cover_file)
            kuaishou_logger.info(f"已选择封面文件: {self.cover_file}")
            
            # 等待封面加载完成
            await asyncio.sleep(2)
            
            # 点击完成按钮
            finish_button = modal.get_by_role("button", name="完成")
            await finish_button.click()
            
            # 等待弹窗关闭
            await modal.wait_for(state="hidden", timeout=5000)
            
            # 等待封面更新
            await page.wait_for_load_state("networkidle")
            kuaishou_logger.success("封面设置完成")
            
        except Exception as e:
            kuaishou_logger.error(f"设置视频封面失败: {str(e)}")
            # 保存错误截图
            await page.screenshot(path=f"error_cover_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            raise VideoUploadError(f"设置视频封面失败: {str(e)}")

    async def start(self) -> bool:
        """开始上传流程"""
        try:
            kuaishou_logger.debug("开始上传流程")
            async with async_playwright() as playwright:
                return await self.upload(playwright)
        except Exception as e:
            kuaishou_logger.error(f"启动上传失败: {str(e)}", exc_info=True)
            return False

    async def upload(self, playwright: Playwright) -> bool:
        """上传视频主流程"""
        browser = None
        context = None
        page = None
        try:
            # 初始化浏览器
            browser_options = {
                'headless': False,  # 禁用无头模式
                'args': [
                    '--disable-gpu',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-setuid-sandbox',
                    '--start-maximized'  # 最大化窗口
                ]
            }
            if self.local_executable_path:
                browser_options['executable_path'] = self.local_executable_path
                
            kuaishou_logger.info("正在启动浏览器...")
            browser = await playwright.chromium.launch(**browser_options)

            # 创建上下文
            context = await browser.new_context(
                storage_state=self.account_file,
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            )
            context = await set_init_script(context)
            context.set_default_timeout(30000)  # 设置默认超时时间为30秒
            
            # 创建页面
            page = await context.new_page()
            
            # 访问上传页面并等待加载
            kuaishou_logger.info("正在打开上传页面...")
            await self._retry_with_backoff(page.goto, UPLOAD_URL)
            await self._retry_with_backoff(page.wait_for_load_state, "networkidle")
            
            # 处理引导框
            try:
                # 等待引导框出现
                guide_close_button = page.locator('div[class*="_close_"]')
                if await guide_close_button.count() > 0:
                    kuaishou_logger.info("检测到引导框，正在关闭...")
                    await guide_close_button.click()
                    await asyncio.sleep(1)
            except Exception as e:
                kuaishou_logger.warning(f"处理引导框时出现异常: {str(e)}")
            
            # 验证是否在上传页面
            if not await self._verify_upload_page(page):
                raise VideoUploadError("未能正确加载上传页面")
            
            kuaishou_logger.info(f'正在上传视频: {self.title}')
            
            # 等待上传按钮出现
            upload_button = page.locator("button[class^='_upload-btn']")
            await self._retry_with_backoff(upload_button.wait_for, state='visible', timeout=10000)
            
            # 上传文件
            try:
                async with page.expect_file_chooser() as fc_info:
                    await upload_button.click()
                file_chooser = await fc_info.value
                await file_chooser.set_files(self.file_path)
                kuaishou_logger.info("文件已选择，等待上传...")
            except Exception as e:
                raise VideoUploadError(f"文件选择失败: {str(e)}")

            # 等待文件上传开始
            await asyncio.sleep(2)

            # 处理新功能提示
            new_feature_button = page.locator('button[type="button"] span:text("我知道了")')
            if await new_feature_button.count() > 0:
                await new_feature_button.click()
                await asyncio.sleep(1)

            # 等待跳转到编辑页面
            try:
                await self._retry_with_backoff(
                    page.wait_for_url,
                    "**/publish/video**",
                    timeout=10000,
                    wait_until="networkidle"
                )
                kuaishou_logger.info("已跳转到视频编辑页面")
            except Exception as e:
                kuaishou_logger.error("等待跳转到编辑页面失败")
                await page.screenshot(path=f"error_redirect_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                raise VideoUploadError(f"未能跳转到视频编辑页面: {str(e)}")

            # 填充视频信息
            await self._retry_with_backoff(self.fill_video_info, page)

            # 等待上传完成
            if not await self._retry_with_backoff(self.wait_for_upload, page):
                raise VideoUploadError("视频上传超时或失败")

            # 设置视频封面（移到这里，在视频上传完成后）
            await self._retry_with_backoff(self.edit_cover, page)

            # 设置定时发布
            if self.publish_date:
                await self._retry_with_backoff(self.set_schedule_time, page)

            # 发布视频
            if not await self._retry_with_backoff(self.publish_video, page):
                raise VideoPublishError("视频发布失败")

            # 保存Cookie
            await context.storage_state(path=self.account_file)
            kuaishou_logger.info('cookie更新完毕！')
            return True

        except Exception as e:
            kuaishou_logger.error(f"上传过程发生错误: {str(e)}", exc_info=True)
            if page:
                await page.screenshot(path=f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            return False

        finally:
            if context:
                try:
                    await context.storage_state(path=self.account_file)
                except:
                    pass
                await context.close()
            if browser:
                await browser.close()

    async def _verify_upload_page(self, page: Page) -> bool:
        """验证是否在上传页面"""
        try:
            # 等待页面加载完成
            await page.wait_for_load_state("networkidle")
            
            # 检查URL
            current_url = page.url
            if "publish/video" not in current_url:
                kuaishou_logger.error(f"当前页面URL不正确: {current_url}")
                return False
            
            # 检查上传按钮是否存在
            upload_button = page.locator("button[class^='_upload-btn']")
            if not await upload_button.count():
                kuaishou_logger.error("未找到上传按钮")
                return False
                
            return True
        except Exception as e:
            kuaishou_logger.error(f"验证上传页面失败: {str(e)}")
            return False

class KSBatchUploader:
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._upload_results = {}
        self._failed_uploads = []
        kuaishou_logger.info(f"初始化批量上传器，最大并发数: {max_concurrent}")

    async def upload_with_semaphore(self, uploader: KSVideoUploader) -> bool:
        """使用信号量控制并发上传"""
        async with self.semaphore:
            try:
                kuaishou_logger.info(f"开始上传视频: {uploader.title}")
                result = await uploader.start()
                kuaishou_logger.debug(f"视频上传结果: title={uploader.title}, result={result}")
                self._upload_results[uploader.title] = {
                    'success': result,
                    'timestamp': datetime.now().isoformat(),
                    'file_path': uploader.file_path
                }
                if not result:
                    self._failed_uploads.append(uploader)
                return result
            except Exception as e:
                kuaishou_logger.error(f"上传视频失败: title={uploader.title}, error={str(e)}", exc_info=True)
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
            kuaishou_logger.info(f"开始批量上传，视频数量: {len(uploaders)}")
            # 创建上传任务
            upload_tasks = [self.upload_with_semaphore(uploader) for uploader in uploaders]
            
            # 执行上传任务
            kuaishou_logger.debug("执行上传任务")
            results = await asyncio.gather(*upload_tasks, return_exceptions=True)
            kuaishou_logger.debug(f"上传任务执行结果: {results}")
            
            # 重试失败的上传
            if self._failed_uploads:
                kuaishou_logger.info(f"有失败的上传任务，数量: {len(self._failed_uploads)}")
                await self.retry_failed_uploads()
            
            # 生成报告
            success_count = sum(1 for r in results if r is True)
            failed_count = sum(1 for r in results if r is False)
            error_count = sum(1 for r in results if isinstance(r, Exception))
            
            kuaishou_logger.info(f"批量上传完成统计 - 总数: {len(uploaders)}, 成功: {success_count}, 失败: {failed_count}, 错误: {error_count}")
            
            return {
                'results': self._upload_results,
                'total': len(uploaders),
                'success': success_count,
                'failed': failed_count,
                'errors': error_count
            }
            
        except Exception as e:
            kuaishou_logger.error(f"批量上传过程发生错误: {str(e)}", exc_info=True)
            return {
                'results': self._upload_results,
                'error': str(e)
            } 
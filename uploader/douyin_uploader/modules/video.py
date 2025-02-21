"""
抖音视频上传模块
提供视频上传、封面设置等功能
"""

import asyncio
import functools
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Callable
import os
import json

from playwright.async_api import Playwright, Page, Browser, BrowserContext
from utils.log import douyin_logger
from conf import LOCAL_CHROME_PATH, BASE_DIR
from utils.base_social_media import set_init_script
from utils.files_times import generate_schedule_time_next_day
from ..utils.playwright_helper import PlaywrightHelper
from .account import AccountManager
from ..utils.validator import VideoValidator

def handle_douyin_errors(func: Callable):
    """错误处理装饰器"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except VideoValidationError as e:
            douyin_logger.error(f"视频验证失败: {str(e)}")
            raise
        except UploadError as e:
            douyin_logger.error(f"上传失败: {str(e)}")
            raise
        except PublishError as e:
            douyin_logger.error(f"发布失败: {str(e)}")
            raise
        except BrowserOperationError as e:
            douyin_logger.error(f"浏览器操作失败: {str(e)}")
            raise
        except Exception as e:
            douyin_logger.error(f"未预期的错误: {str(e)}")
            raise DouYinVideoError(f"操作失败: {str(e)}")
    return wrapper

# 自定义异常类
class DouYinVideoError(Exception):
    """抖音视频上传基础异常类"""
    pass

class VideoValidationError(DouYinVideoError):
    """视频验证失败异常"""
    pass

class UploadError(DouYinVideoError):
    """上传失败异常"""
    pass

class PublishError(DouYinVideoError):
    """发布失败异常"""
    pass

class BrowserOperationError(DouYinVideoError):
    """浏览器操作异常"""
    pass

# 页面选择器常量
SELECTORS = {
    'UPLOAD_BUTTONS': [
        '#douyin-creator-master-side-upload-wrap button',
        'button:has-text("发布视频")',
        '[class*="header-button-wrap"] button',
        '#douyin-creator-master-side-upload'
    ],
    'TITLE_INPUT': '.notranslate',
    'TAGS_INPUT': '.zone-container',
    'PUBLISH_BUTTON': 'button.button-dhlUZE.primary-cECiOJ.fixed-J9O8Yw',
    'LOCATION_INPUT': 'div.semi-select span:has-text("输入地理位置")',
    'THIRD_PART_SWITCH': '[class^="info"] > [class^="first-part"] div div.semi-switch',
    'SCHEDULE_RADIO': "[class^='radio']:has-text('定时发布')",
    'SCHEDULE_INPUT': '.semi-input[placeholder="日期和时间"]'
}

class DouYinVideo:
    """抖音视频上传类"""
    
    # 支持的文件格式
    SUPPORTED_VIDEO_EXTENSIONS = [".mp4", ".mov", ".avi"]
    SUPPORTED_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp']
    
    def __init__(self):
        """初始化抖音视频上传器"""
        self.account_manager = AccountManager()
        
    @staticmethod
    def _validate_file_accessibility(file_path: Path) -> None:
        """验证文件可访问性"""
        if not file_path.exists():
            raise VideoValidationError(f"文件不存在: {file_path}")
        if not os.access(file_path, os.R_OK):
            raise VideoValidationError(f"文件无法读取: {file_path}")
        if file_path.stat().st_size == 0:
            raise VideoValidationError(f"文件大小为0: {file_path}")

    @classmethod
    def _validate_file_format(cls, file_path: Path, supported_extensions: List[str]) -> None:
        """验证文件格式"""
        if file_path.suffix.lower() not in supported_extensions:
            raise VideoValidationError(
                f"不支持的文件格式 {file_path.suffix}，支持的格式: {supported_extensions}"
            )

    @classmethod
    def _validate_video_file(cls, file_path: Path) -> None:
        """验证视频文件"""
        cls._validate_file_accessibility(file_path)
        cls._validate_file_format(file_path, cls.SUPPORTED_VIDEO_EXTENSIONS)
        if not VideoValidator.validate_video_file(str(file_path)):
            raise VideoValidationError(f"视频文件验证失败: {file_path}")

    @classmethod
    def _validate_thumbnail_file(cls, file_path: Path) -> None:
        """验证封面图片文件"""
        cls._validate_file_accessibility(file_path)
        cls._validate_file_format(file_path, cls.SUPPORTED_IMAGE_EXTENSIONS)
        if not VideoValidator.validate_thumbnail(str(file_path)):
            raise VideoValidationError(f"封面图片验证失败: {file_path}")

    @classmethod
    def _validate_mentions(cls, mentions: List[str]) -> None:
        """验证@提及"""
        if not mentions or not VideoValidator.validate_mentions(mentions):
            raise VideoValidationError(f"提及无效: {mentions}")
    
    @staticmethod
    def _validate_title(title: str) -> None:
        """验证标题"""
        if not title or not VideoValidator.validate_title(title):
            raise VideoValidationError(f"标题无效: {title}")

    @staticmethod
    def _validate_tags(tags: List[str]) -> None:
        """验证标签"""
        if not tags or not VideoValidator.validate_tags(tags):
            raise VideoValidationError(f"标签无效: {tags}")

    @staticmethod
    def _validate_publish_date(publish_date: datetime) -> None:
        """验证发布时间"""
        if not VideoValidator.validate_publish_date(publish_date):
            raise VideoValidationError(f"发布时间无效: {publish_date}")

    @classmethod
    def find_thumbnail(cls, video_path: Path) -> Optional[Path]:
        """查找视频对应的封面图片"""
        try:
            for ext in cls.SUPPORTED_IMAGE_EXTENSIONS:
                thumbnail = video_path.with_suffix(ext)
                if thumbnail.exists():
                    cls._validate_thumbnail_file(thumbnail)
                    douyin_logger.info(f"找到封面图片: {thumbnail.name}")
                    return thumbnail
            douyin_logger.warning(f"未找到视频 {video_path.name} 的封面图片")
            return None
        except VideoValidationError:
            return None
        except Exception as e:
            douyin_logger.error(f"查找封面图片失败: {str(e)}")
            return None

    @classmethod
    def find_video_files(cls, base_dir: Path) -> List[Path]:
        """在指定目录下查找视频文件"""
        try:
            video_files = set()
            for ext in cls.SUPPORTED_VIDEO_EXTENSIONS:
                found_files = list(base_dir.glob(f"*{ext}")) + list(base_dir.glob(f"*{ext.upper()}"))
                for file in found_files:
                    try:
                        cls._validate_video_file(file)
                        video_files.add(file)
                    except VideoValidationError as e:
                        douyin_logger.warning(f"跳过无效视频 {file}: {str(e)}")
            sorted_files = sorted(list(video_files), key=lambda x: x.stat().st_mtime)
            if not sorted_files:
                douyin_logger.warning(f"在目录 {base_dir} 中未找到有效的视频文件")
            return sorted_files
        except Exception as e:
            douyin_logger.error(f"查找视频文件失败: {str(e)}")
            return []

    @staticmethod
    def load_video_info(video_path: Path) -> Optional[Dict[str, Any]]:
        """加载视频的配置信息"""
        try:
            info_file = video_path.parent / "info.json"
            if not info_file.exists():
                douyin_logger.warning(f"未找到配置文件: {info_file}")
                return None
            
            with open(info_file, 'r', encoding='utf-8') as f:
                try:
                    info_list = json.load(f)
                except json.JSONDecodeError as e:
                    douyin_logger.error(f"配置文件格式错误: {str(e)}")
                    return None
                    
            for info in info_list:
                if isinstance(info, dict) and "douyin" in info:
                    douyin_logger.info(f"成功加载视频配置: {video_path.name}")
                    return info["douyin"]
            
            douyin_logger.warning("配置文件中未找到抖音平台信息")
            return None
        except Exception as e:
            douyin_logger.error(f"读取配置文件失败: {str(e)}")
            return None

    @handle_douyin_errors
    async def batch_upload(
        self,
        context: BrowserContext,
        video_dir: str,
        account_file: Path,
        daily_times: List[int] = [16]
    ) -> None:
        """批量上传视频"""
        try:
            # 验证目录
            video_dir_path = Path(video_dir)
            if not video_dir_path.exists() or not video_dir_path.is_dir():
                raise VideoValidationError(f"视频目录不存在: {video_dir_path}")
            
            # 获取视频文件
            files = self.find_video_files(video_dir_path)
            if not files:
                douyin_logger.warning("未找到有效的视频文件")
                return
            
            # 生成默认发布时间
            file_num = len(files)
            default_publish_times = generate_schedule_time_next_day(
                file_num,
                1,
                daily_times=daily_times
            )
            
            # 上传视频
            for index, file in enumerate(files):
                douyin_logger.info(f"正在处理第 {index + 1}/{file_num} 个视频: {file.name}")
                
                try:
                    # 加载视频配置
                    video_info = self.load_video_info(file)
                    
                    # 验证视频参数
                    is_valid, title, tags, mentions, thumbnail_path, publish_date = await self.validate_video(
                        file,
                        video_info
                    )
                    
                    if not is_valid:
                        douyin_logger.error(f"跳过无效视频: {file.name}")
                        continue
                    
                    # 使用配置文件中的发布时间或默认时间
                    if not publish_date:
                        publish_date = default_publish_times[index]
                        douyin_logger.info(f"使用默认发布时间: {publish_date}")
                    
                    # 上传单个视频
                    await self.upload_single_video(
                        context=context,
                        title=title,
                        file_path=str(file),
                        tags=tags,
                        mentions=mentions,
                        publish_date=publish_date,
                        account_file=str(account_file),
                        thumbnail_path=str(thumbnail_path) if thumbnail_path else None
                    )
                    
                    # 上传间隔
                    if index < file_num - 1:
                        await asyncio.sleep(2)
                        
                except Exception as e:
                    douyin_logger.error(f"处理视频 {file.name} 失败: {str(e)}")
                    continue
                    
        except Exception as e:
            douyin_logger.error(f"批量上传失败: {str(e)}")
            raise

    @handle_douyin_errors
    async def upload_single_video(
        self,
        context: BrowserContext,
        title: str,
        file_path: str,
        tags: List[str],
        mentions: List[str],
        publish_date: datetime,
        account_file: str,
        thumbnail_path: Optional[str] = None
    ) -> None:
        """上传单个视频"""
        MAX_RETRIES = 3
        retry_count = 0
        
        while retry_count < MAX_RETRIES:
            try:
                # 设置账号并获取浏览器上下文
                result = await self.account_manager.setup_account(
                    account_file,
                    handle=True,
                    context=context
                )
                if not result['success']:
                    raise UploadError(f"账号设置失败: {result['message']}")
                
                try:
                    # 使用已经在创作者中心的页面
                    page = result['page']
                    await self._perform_upload(
                        page=page,
                        title=title,
                        file_path=file_path,
                        tags=tags,
                        mentions=mentions,
                        publish_date=publish_date,
                        thumbnail_path=thumbnail_path
                    )
                    break
                    
                finally:
                    # 只关闭当前页面，保持浏览器和上下文打开
                    if 'page' in locals():
                        await page.close()
                        
            except Exception as e:
                retry_count += 1
                if retry_count < MAX_RETRIES:
                    douyin_logger.error(f"上传失败 (尝试 {retry_count}/{MAX_RETRIES}): {str(e)}")
                    await asyncio.sleep(5)  # 等待5秒后重试
                else:
                    raise UploadError(f"上传失败，已达到最大重试次数: {str(e)}")

    async def set_schedule_time(self, page: Page, publish_date: datetime) -> None:
        """
        设置定时发布时间
        Args:
            page: Playwright页面对象
            publish_date: 发布时间
        """
        label_element = page.locator(SELECTORS['SCHEDULE_RADIO'])
        await label_element.click()
        await asyncio.sleep(1)
        
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M")
        await page.locator(SELECTORS['SCHEDULE_INPUT']).click()
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date_hour))
        await page.keyboard.press("Enter")
        await asyncio.sleep(1)

    async def handle_upload_error(self, page: Page, file_path: str) -> None:
        """
        处理上传错误
        Args:
            page: Playwright页面对象
            file_path: 视频文件路径
        """
        douyin_logger.info('视频出错了，重新上传中')
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(file_path)

    async def set_thumbnail(self, page: Page, thumbnail_path: str) -> None:
        """
        设置视频封面
        Args:
            page: Playwright页面对象
            thumbnail_path: 封面图片路径
        """
        try:
            douyin_logger.info("开始设置视频封面...")
            
            # 1. 点击选择封面按钮
            # 使用更精确的选择器定位整个封面控制区域
            cover_area = page.locator("div.coverControl-CjlzqC")
            await cover_area.wait_for(state="visible", timeout=10000)
            douyin_logger.info("找到封面控制区域")
            
            # 点击封面选择区域
            cover_btn = cover_area.locator("div.cover-Jg3T4p")
            await cover_btn.wait_for(state="visible", timeout=5000)
            douyin_logger.info("找到封面选择按钮")
            await cover_btn.click()
            
            # 2. 等待模态框出现
            modal = page.locator("div.semi-modal-content.semi-modal-content-animate-show")
            await modal.wait_for(state="visible", timeout=10000)
            douyin_logger.info("模态框已显示")
            
            # 3. 在模态框内查找并点击上传区域
            upload_area = modal.locator("div.semi-upload-drag-area")
            await upload_area.wait_for(state="visible", timeout=10000)
            douyin_logger.info("上传区域已显示")
            
            # 4. 准备文件选择器并上传
            async with page.expect_file_chooser() as fc_info:
                await upload_area.click()
            file_chooser = await fc_info.value
            
            # 上传文件
            douyin_logger.info(f"上传封面图片: {thumbnail_path}")
            await file_chooser.set_files(thumbnail_path)
            
            # 5. 等待上传完成（等待预览图出现）
            try:
                await modal.wait_for_selector("div.background-OpVteV[style*='background-image']", 
                    state="visible", 
                    timeout=10000
                )
                douyin_logger.info("封面预览已显示")
            except Exception as e:
                douyin_logger.warning(f"等待预览图超时: {str(e)}")
            
            # 6. 点击完成按钮
            finish_btn = modal.locator("button.semi-button-primary:has-text('完成')")
            await finish_btn.wait_for(state="visible", timeout=5000)
            await finish_btn.click()
            
            # 7. 等待一小段时间确保处理完成
            await asyncio.sleep(2)
            
            douyin_logger.success("视频封面设置成功")
            
        except Exception as e:
            douyin_logger.error(f"设置视频封面失败: {str(e)}")
            raise UploadError(f"设置封面失败: {str(e)}")

    async def set_location(self, page: Page, location: str = "杭州市") -> None:
        """
        设置视频位置信息
        Args:
            page: Playwright页面对象
            location: 位置信息
        """
        await page.locator(SELECTORS['LOCATION_INPUT']).click()
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(2000)
        await page.keyboard.type(location)
        await page.wait_for_selector('div[role="listbox"] [role="option"]', timeout=5000)
        await page.locator('div[role="listbox"] [role="option"]').first.click()

    @handle_douyin_errors
    async def _perform_upload(
        self,
        page: Page,
        title: str,
        file_path: str,
        tags: List[str],
        mentions: List[str],
        publish_date: datetime,
        thumbnail_path: Optional[str] = None
    ) -> None:
        """执行具体的上传操作"""
        try:
            # 1. 点击上传按钮进入上传页面
            douyin_logger.info(f'[+]正在上传-------{title}')
            
            # 尝试多个可能的选择器来定位上传按钮
            upload_button = None
            for selector in SELECTORS['UPLOAD_BUTTONS']:
                try:
                    douyin_logger.info(f"尝试定位上传按钮: {selector}")
                    if await page.locator(selector).count() > 0:
                        upload_button = page.locator(selector)
                        douyin_logger.info(f"找到上传按钮，使用选择器: {selector}")
                        break
                except Exception as e:
                    douyin_logger.warning(f"尝试选择器 {selector} 失败: {str(e)}")
                    continue
            
            if not upload_button:
                raise BrowserOperationError("无法找到上传按钮")
            
            # 等待按钮可见并点击
            douyin_logger.info("等待上传按钮可见...")
            await upload_button.wait_for(state="visible", timeout=10000)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)  # 额外等待以确保按钮可交互
            
            # 尝试点击按钮
            douyin_logger.info("尝试点击上传按钮...")
            try:
                await upload_button.click(timeout=5000)
            except Exception as e:
                douyin_logger.warning(f"常规点击失败: {str(e)}")
                # 尝试使用JavaScript点击
                douyin_logger.info("尝试使用JavaScript点击...")
                await page.evaluate('selector => document.querySelector(selector).click()', SELECTORS['UPLOAD_BUTTONS'][0])
            
            # 等待进入上传页面
            douyin_logger.info("等待进入上传页面...")
            try:
                await page.wait_for_url(
                    "https://creator.douyin.com/creator-micro/content/upload",
                    timeout=10000,
                    wait_until="networkidle"
                )
                douyin_logger.success("成功进入上传页面")
            except Exception as e:
                douyin_logger.error(f"等待上传页面超时: {str(e)}")
                raise BrowserOperationError("无法进入上传页面")
            
            # 2. 上传视频文件
            douyin_logger.info("准备上传视频文件...")
            # 等待上传区域可见
            upload_container = page.locator(".container-drag-AOMYqU")
            await upload_container.wait_for(state="visible", timeout=10000)
            
            # 找到文件输入框
            file_input = page.locator(".container-drag-AOMYqU input[type='file']")
            await file_input.wait_for(state="attached", timeout=10000)  # 只等待元素存在，不需要可见
            
            # 设置文件
            douyin_logger.info(f"设置视频文件: {file_path}")
            await file_input.set_input_files(file_path)
            
            # 3. 等待进入发布页面
            douyin_logger.info('  [-] 等待进入视频发布页面...')
            await page.wait_for_url(
                "https://creator.douyin.com/creator-micro/content/post/video?enter_from=publish_page",
                timeout=60000  # 设置较长的超时时间
            )
            douyin_logger.success("成功进入发布页面")
            
            # 4. 填写视频信息
            douyin_logger.info('  [-] 正在填充标题和话题...')
            await asyncio.sleep(2)  # 等待页面加载完成
            
            # 设置标题
            title_container = page.get_by_text('作品标题').locator("..").locator("xpath=following-sibling::div[1]").locator("input")
            if await title_container.count():
                await title_container.fill(title[:30])
            else:
                titlecontainer = page.locator(SELECTORS['TITLE_INPUT'])
                await titlecontainer.click()
                await page.keyboard.press("Control+KeyA")
                await page.keyboard.press("Delete")
                await page.keyboard.type(title)
                await page.keyboard.press("Enter")
            
            # 设置标签
            css_selector = SELECTORS['TAGS_INPUT']
            for tag in tags[:5]:
                await page.type(css_selector, "#" + tag)
                await page.press(css_selector, "Space")
            douyin_logger.info(f'总共添加{len(tags)}个话题')
            await page.keyboard.press("Enter")
            for mention in mentions[:5]:
                await page.type(css_selector, "@" + mention)
                await page.press(css_selector, "Space")
            douyin_logger.info(f'总共添加{len(mentions)}个@')
            await page.keyboard.press("Enter")
            

            # 5. 等待视频上传完成
            douyin_logger.info("  [-] 等待视频上传完成...")
            upload_timeout = 300  # 5分钟超时
            start_time = datetime.now()
            
            while True:
                try:
                    if (datetime.now() - start_time).total_seconds() > upload_timeout:
                        raise UploadError("视频上传超时")
                        
                    if await page.locator('[class^="long-card"] div:has-text("重新上传")').count() > 0:
                        douyin_logger.success("  [-]视频上传完毕")
                        break
                        
                    if await page.locator('div.progress-div > div:has-text("上传失败")').count() > 0:
                        raise UploadError("视频上传失败")
                        
                    await asyncio.sleep(2)
                    douyin_logger.info("  [-] 正在上传视频中...")
                except Exception as e:
                    if "上传失败" in str(e):
                        douyin_logger.error("  [-] 发现上传出错了... 准备重试")
                        await self.handle_upload_error(page, file_path)
                    else:
                        raise
            
            # 6. 设置封面
            if thumbnail_path:
                douyin_logger.info("  [-] 设置视频封面...")
                await self.set_thumbnail(page, thumbnail_path)
            
 
            # 9. 设置发布时间
            if publish_date:
                douyin_logger.info("  [-] 设置发布时间...")
                await self.set_schedule_time(page, publish_date)
            
            # 10. 发布视频
            douyin_logger.info("  [-] 正在发布视频...")
            # 使用新的选择器定位发布按钮
            publish_button = page.locator(SELECTORS['PUBLISH_BUTTON'])
            await publish_button.wait_for(state="visible", timeout=10000)
            douyin_logger.info("  [-] 发布按钮已就绪")
            
            # 确保按钮可点击
            await asyncio.sleep(1)
            await publish_button.click()
            
            # 等待页面跳转到管理页面
            await page.wait_for_url(
                "https://creator.douyin.com/creator-micro/content/manage**",
                timeout=30000
            )
            douyin_logger.success("  [-]视频发布成功")
            
        except Exception as e:
            douyin_logger.error(f"执行上传操作失败: {str(e)}")
            raise UploadError(f"上传失败: {str(e)}")

    async def validate_video(
        self,
        file_path: Path,
        video_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str], Optional[List[str]], Optional[Path], Optional[datetime]]:
        """验证视频文件和相关参数"""
        try:
            # 检查文件可访问性
            self._validate_file_accessibility(file_path)
                
            # 验证视频文件
            self._validate_video_file(file_path)
                
            # 获取视频信息
            if video_info:
                title = video_info.get("title", "").strip()
                tags = [tag.strip() for tag in video_info.get("tags", [])]
                mentions = video_info.get("mentions", [])
                
                try:
                    publish_date = datetime.strptime(
                        video_info.get("publish_date", ""),
                        "%Y-%m-%d %H:%M:%S"
                    )
                    # 检查发布时间是否过期
                    if publish_date < datetime.now():
                        douyin_logger.warning(f"发布时间已过期，将使用默认时间")
                        publish_date = None
                except:
                    publish_date = None
            else:
                douyin_logger.warning(f"使用文件名作为标题和标签")
                title = file_path.stem
                tags = [title]
                publish_date = None
                
            # 验证标题
            self._validate_title(title)
                
            # 验证标签
            self._validate_tags(tags)
                
            # 验证发布时间
            if publish_date:
                self._validate_publish_date(publish_date)
                
            # 查找并验证封面图片
            thumbnail_path = self.find_thumbnail(file_path)
            if thumbnail_path:
                self._validate_thumbnail_file(thumbnail_path)
                
            if mentions:
                self._validate_mentions(mentions)
                
            return True, title, tags, mentions, thumbnail_path, publish_date 
        except Exception as e:
            douyin_logger.error(f"验证视频失败: {str(e)}")
            return False, None, None, None, None, None 
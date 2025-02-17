"""
视频号内容抓取模块
专注于已发布内容的获取和数据分析
"""
from typing import List, Dict, Optional, Any
import asyncio
import logging
from pathlib import Path
import warnings
import base64
import re
import random
from datetime import datetime
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from conf import LOCAL_CHROME_PATH
from utils.video_content_db import VideoContentDB
from utils.social_media_db import SocialMediaDB
import sqlite3

# 忽略ResourceWarning
warnings.filterwarnings("ignore", category=ResourceWarning)

logger = logging.getLogger(__name__)

def convert_number_text(text: str) -> int:
    """
    将带单位的数字转换为整数
    
    Args:
        text: 数字文本，如 "1.5万"
        
    Returns:
        int: 转换后的整数
    """
    text = text.strip()
    if not text:
        return 0
        
    # 匹配数字部分
    match = re.match(r'([\d.]+)([万亿])?', text)
    if not match:
        return 0
        
    number = float(match.group(1))
    unit = match.group(2) if match.group(2) else ''
    
    # 处理单位
    if unit == '万':
        number *= 10000
    elif unit == '亿':
        number *= 100000000
        
    return int(number)

class VideoContentCrawler:
    """视频号内容抓取器 - 专注于已发布内容的获取"""
    
    VIDEOS_PER_PAGE = 20  # 每页最多显示的视频数量
    
    def __init__(
        self,
        account_file: str,  # 账号cookie文件
        account_id: int,  # 账号ID
        local_executable_path: str = LOCAL_CHROME_PATH,  # chrome路径
        headless: bool = False,
        save_thumb_as_base64: bool = True,  # 是否将封面图保存为base64
        min_delay: float = 3.0,  # 最小延迟时间(秒)
        max_delay: float = 7.0,  # 最大延迟时间(秒)
        max_retries: int = 3,  # 最大重试次数
        reverse: bool = True  # 是否倒序爬取
    ):
        """
        初始化抓取器
        
        Args:
            account_file: cookie文件路径
            account_id: 账号ID
            local_executable_path: Chrome浏览器可执行文件路径
            headless: 是否使用无头模式
            save_thumb_as_base64: 是否将封面图转换为base64数据
            min_delay: 最小延迟时间(秒)
            max_delay: 最大延迟时间(秒)
            max_retries: 最大重试次数
            reverse: 是否倒序爬取
        """
        self.account_file = account_file
        self.account_id = account_id
        self.local_executable_path = local_executable_path
        self.headless = headless
        self.save_thumb_as_base64 = save_thumb_as_base64
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.reverse = reverse
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._playwright = None
        self.db = VideoContentDB()
        
        # 验证账号ID是否存在
        social_db = SocialMediaDB()
        try:
            # 获取所有账号
            accounts = social_db.get_all_accounts("tencent")
            # 检查ID是否存在
            if not any(acc.get('id') == self.account_id for acc in accounts):
                raise ValueError(f"账号ID {self.account_id} 不存在")
        finally:
            social_db.close()
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.init()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
        
    async def init(self):
        """初始化浏览器和上下文"""
        try:
            self._playwright = await async_playwright().start()
            self.browser = await self._playwright.chromium.launch(
                headless=self.headless,
                executable_path=self.local_executable_path
            )
            self.context = await self.browser.new_context(storage_state=self.account_file)
            self.page = await self.context.new_page()
            
        except Exception as e:
            logger.error(f"初始化失败: {str(e)}")
            await self.close()
            raise
        
    async def close(self):
        """关闭浏览器和清理资源"""
        try:
            if self.page:
                await self.page.close()
                self.page = None
            if self.context:
                await self.context.close()
                self.context = None
            if self.browser:
                await self.browser.close()
                self.browser = None
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
            # 关闭数据库连接
            if self.db:
                self.db.close()
        except Exception as e:
            logger.error(f"关闭资源时出错: {str(e)}")
        
    async def random_delay(self):
        """随机延迟，避免频繁请求"""
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)

    async def check_page_status(self) -> bool:
        """
        检查页面状态
        
        Returns:
            bool: 页面是否正常
        """
        try:
            # 检查是否有错误提示
            error_text = await self.page.text_content(".weui-desktop-dialog__title") or ""
            if "异常" in error_text or "错误" in error_text:
                logger.error(f"页面出现错误: {error_text}")
                return False
                
            # 检查是否需要验证码
            captcha = await self.page.query_selector(".verify-code")
            if captcha:
                logger.error("需要验证码验证")
                return False
                
            return True
        except Exception as e:
            logger.error(f"检查页面状态失败: {str(e)}")
            return False

    async def retry_on_error(self, func, *args, **kwargs):
        """
        错误重试装饰器
        
        Args:
            func: 要执行的异步函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
        """
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(f"操作失败，正在重试({attempt + 1}/{self.max_retries}): {str(e)}")
                await self.random_delay()

    async def get_total_pages(self) -> int:
        """
        获取总页数
        
        Returns:
            int: 总页数
        """
        try:
            # 等待分页元素加载
            await self.page.wait_for_selector(".weui-desktop-pagination__num", timeout=20000)
            
            # 获取所有页码元素
            page_nums = await self.page.query_selector_all(".weui-desktop-pagination__num")
            max_page = 1
            
            # 遍历所有页码，找出最大的数字
            for num in page_nums:
                text = await num.text_content()
                if text.isdigit():
                    max_page = max(max_page, int(text))
                    
            logger.info(f"获取到总页数: {max_page}")
            return max_page
            
        except Exception as e:
            logger.error(f"获取总页数失败: {str(e)}")
            return 1

    async def get_current_page(self) -> int:
        """
        获取当前页码
        
        Returns:
            int: 当前页码
        """
        try:
            # 使用更精确的选择器
            current = await self.page.query_selector(".weui-desktop-pagination__num_current")
            if current:
                page_text = await current.text_content()
                if page_text.isdigit():
                    return int(page_text)
            return 1
        except Exception as e:
            logger.error(f"获取当前页码失败: {str(e)}")
            return 1

    async def get_crawled_page_count(self) -> int:
        """
        获取已爬取的页数
        
        Returns:
            int: 已爬取的页数
        """
        try:
            # 获取该账号已保存的视频数量
            count = self.db.get_video_count(self.account_id)
            # 计算页数（向上取整）
            return (count + self.VIDEOS_PER_PAGE - 1) // self.VIDEOS_PER_PAGE
        except Exception as e:
            logger.error(f"获取已爬取页数失败: {str(e)}")
            return 0
            
    async def jump_to_page(self, target_page: int) -> bool:
        """
        跳转到指定页面
        
        Args:
            target_page: 目标页码
            
        Returns:
            bool: 是否跳转成功
        """
        try:
            # 找到跳转输入框和按钮
            input_field = await self.page.query_selector(".weui-desktop-pagination__input")
            jump_button = await self.page.query_selector(".weui-desktop-pagination__form .weui-desktop-link")
            
            if not input_field or not jump_button:
                return False
                
            # 输入页码
            await input_field.fill(str(target_page))
            # 点击跳转
            await jump_button.click()
            
            # 等待页面加载
            await self.page.wait_for_load_state("networkidle")
            
            # 验证是否跳转成功
            current_page = await self.page.query_selector(".weui-desktop-pagination__num_current")
            if current_page:
                current_page_text = await current_page.text_content()
                return int(current_page_text) == target_page
                
            return False
            
        except Exception as e:
            logger.error(f"跳转到第 {target_page} 页失败: {str(e)}")
            return False

    async def get_video_list(self, max_pages: int = 1) -> List[Dict[str, Any]]:
        """
        获取视频列表
        
        Args:
            max_pages: 最大抓取页数，如果为-1则抓取所有页
            
        Returns:
            List[Dict]: 视频信息列表
        """
        videos = []
        
        try:
            # 访问列表页
            await self.page.goto("https://channels.weixin.qq.com/platform/post/list")
            await self.page.wait_for_load_state("networkidle")
            
            # 等待页面内容加载，使用更通用的选择器
            try:
                await self.page.wait_for_selector("div[class*='post-feed-item']", timeout=20000)
            except Exception as e:
                logger.error("页面内容加载失败")
                return videos
            
            # 如果是倒序爬取，先跳转到最后一页
            if self.reverse:
                # 获取最后一页的页码
                last_page_num = await self.page.query_selector(".weui-desktop-pagination__num:last-child")
                if last_page_num:
                    last_page_text = await last_page_num.text_content()
                    if last_page_text.isdigit():
                        logger.info(f"正在跳转到最后一页: {last_page_text}")
                        if not await self.jump_to_page(int(last_page_text)):
                            logger.error("跳转到最后一页失败")
                            return videos
                        # 等待页面加载和稳定
                        await self.random_delay()
                        
                        # 等待新页面内容加载
                        try:
                            await self.page.wait_for_selector("div[class*='post-feed-item']", timeout=20000)
                        except Exception as e:
                            logger.error("最后一页内容加载失败")
                            return videos
            
            # 获取总页数和已爬取页数
            total_pages = await self.get_total_pages()
            if total_pages <= 0:
                logger.error("获取总页数失败")
                return videos
                
            crawled_pages = await self.get_crawled_page_count()
            
            if max_pages == -1:
                max_pages = total_pages
            else:
                max_pages = min(max_pages, total_pages)
                
            logger.info(f"总页数: {total_pages}, 已爬取: {crawled_pages} 页, 计划抓取: {max_pages} 页")
            
            # 确定起始页和结束页
            if self.reverse:
                start_page = max_pages
                end_page = max(1, max_pages - crawled_pages + 1)
                step = -1
            else:
                start_page = 1
                end_page = max_pages
                step = 1
                
            current_page = start_page
            
            # 如果是倒序且不是最后一页，先跳转到起始页
            if self.reverse and current_page != total_pages:
                if not await self.jump_to_page(start_page):
                    logger.error(f"跳转到第 {start_page} 页失败")
                    return videos
                    
                # 等待新页面内容加载
                try:
                    await self.page.wait_for_selector("div[class*='post-feed-item']", timeout=20000)
                except Exception as e:
                    logger.error("页面内容加载失败")
                    return videos
            
            while (step > 0 and current_page <= end_page) or (step < 0 and current_page >= end_page):
                # 检查页面状态
                if not await self.check_page_status():
                    logger.error(f"页面状态异常，停止采集")
                    break
                
                logger.info(f"正在采集第 {current_page}/{max_pages} 页...")
                
                # 等待页面加载，使用更通用的选择器
                try:
                    await self.page.wait_for_selector("div[class*='post-feed-item']", timeout=20000)
                    items = await self.page.query_selector_all("div[class*='post-feed-item']")
                    logger.info(f"找到 {len(items)} 个视频项")
                except Exception as e:
                    logger.error(f"页面内容加载失败: {str(e)}")
                    break
                
                if not items:
                    logger.error("未找到任何视频项")
                    break
                
                # 处理当前页的视频
                for item in items:
                    try:
                        video_info = await self.retry_on_error(self._extract_video_info, item)
                        if video_info:
                            videos.append(video_info)
                            # 每处理一个视频后短暂延迟
                            await asyncio.sleep(random.uniform(0.5, 1.5))
                    except Exception as e:
                        logger.error(f"提取视频信息失败: {str(e)}")
                        continue
                
                # 处理翻页
                if current_page != end_page:
                    if step > 0:
                        has_next = await self._goto_next_page()
                    else:
                        has_next = await self._goto_prev_page()
                        
                    if not has_next:
                        logger.info("没有更多页面了")
                        break
                        
                    # 翻页后等待
                    await self.random_delay()
                    
                current_page += step
                
        except Exception as e:
            logger.error(f"获取视频列表失败: {str(e)}")
            
        return videos
        
    async def _get_image_as_base64(self, url: str) -> Optional[str]:
        """
        将图片URL转换为base64编码
        
        Args:
            url: 图片URL
            
        Returns:
            Optional[str]: base64编码的图片数据，失败返回None
        """
        try:
            # 创建新页面获取图片
            page = await self.context.new_page()
            try:
                # 获取图片数据
                response = await page.goto(url)
                if response and response.ok:
                    # 获取图片二进制数据
                    image_data = await response.body()
                    # 转换为base64
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                    # 获取Content-Type
                    content_type = response.headers.get('content-type', 'image/jpeg')
                    # 返回完整的base64图片数据
                    return f"data:{content_type};base64,{base64_data}"
                return None
            finally:
                await page.close()
        except Exception as e:
            logger.error(f"获取图片base64数据失败: {str(e)}")
            return None

    async def _extract_video_info(self, item) -> Optional[Dict[str, Any]]:
        """
        提取单个视频信息
        
        Args:
            item: 视频元素
            
        Returns:
            Dict: 视频信息字典，包含标题内容、标签列表和艾特用户列表
        """
        try:
            # 获取视频标题，使用更通用的选择器
            title = await item.query_selector("div[class*='post-title']")
            title_text = await title.text_content() if title else ""
            
            # 解析标题内容、标签和艾特用户
            title_parts = title_text.strip().split("\n")
            main_title = title_parts[0] if title_parts else ""
            
            # 如果有第二部分，解析标签和艾特用户
            tags = []
            mentions = []
            if len(title_parts) > 1:
                # 先提取@用户
                mentions_parts = title_parts[1].split("@")[1:]  # 跳过第一个（分割前的部分）
                for mention in mentions_parts:
                    # 找到下一个分隔符（空格或#）的位置
                    space_pos = mention.find(" ")
                    hash_pos = mention.find("#")
                    
                    # 确定用户名的结束位置
                    end_pos = -1
                    if space_pos != -1 and hash_pos != -1:
                        end_pos = min(space_pos, hash_pos)
                    elif space_pos != -1:
                        end_pos = space_pos
                    elif hash_pos != -1:
                        end_pos = hash_pos
                        
                    # 提取用户名
                    if end_pos != -1:
                        username = mention[:end_pos].strip()
                    else:
                        username = mention.strip()
                        
                    if username:
                        mentions.append(username)
                
                # 再提取标签
                for part in title_parts[1].split("#"):
                    part = part.strip()
                    if not part:
                        continue
                    # 移除可能包含的@用户部分
                    if "@" in part:
                        part = part.split("@")[0]
                    part = part.strip()
                    if part:
                        tags.append(part)
            
            # 获取封面图片，使用更通用的选择器
            thumb = await item.query_selector("div[class*='media'] img")
            thumb_base64 = None
            if thumb and self.save_thumb_as_base64:
                src = await thumb.get_attribute("src")
                if src:
                    thumb_base64 = await self._get_image_as_base64(src)
            
            # 获取发布时间，使用更通用的选择器
            time_element = await item.query_selector("div[class*='post-time'] span")
            publish_time = await time_element.text_content() if time_element else ""
            
            # 获取视频状态，使用更通用的选择器
            status_element = await item.query_selector("div[class*='bandage'] span")
            status = await status_element.text_content() if status_element else ""
            
            # 获取播放数据，使用更通用的选择器
            play_count = await item.query_selector("div[class*='post-data'] .data-item:nth-child(1) .count")
            play_text = await play_count.text_content() if play_count else "0"
            
            # 获取点赞数据
            like_count = await item.query_selector("div[class*='post-data'] .data-item:nth-child(2) .count")
            like_text = await like_count.text_content() if like_count else "0"
            
            # 获取评论数据
            comment_count = await item.query_selector("div[class*='post-data'] .data-item:nth-child(3) .count")
            comment_text = await comment_count.text_content() if comment_count else "0"
            
            # 获取分享数据
            share_count = await item.query_selector("div[class*='post-data'] .data-item:nth-child(4) .count")
            share_text = await share_count.text_content() if share_count else "0"
            
            try:
                # 转换数值
                plays = convert_number_text(play_text)
                likes = convert_number_text(like_text)
                comments = convert_number_text(comment_text)
                shares = convert_number_text(share_text)
                
                # 尝试保存到数据库
                video_id = self.db.add_video_content(
                    account_id=self.account_id,
                    title=main_title.strip(),
                    thumb_base64=thumb_base64,
                    publish_time=publish_time.strip(),
                    status=status.strip(),
                    plays=plays,
                    likes=likes,
                    comments=comments,
                    shares=shares,
                    tags=tags,
                    mentions=mentions
                )
                logger.info(f"成功保存视频内容: {main_title.strip()}")
                return {
                    "id": video_id,
                    "title": main_title.strip(),
                    "tags": tags,
                    "mentions": mentions,
                    "thumb_base64": thumb_base64,
                    "publish_time": publish_time.strip(),
                    "status": status.strip(),
                    "stats": {
                        "plays": plays,
                        "likes": likes,
                        "comments": comments,
                        "shares": shares
                    }
                }
            except sqlite3.IntegrityError:
                # 如果是唯一约束冲突,说明数据已存在,跳过
                logger.info(f"视频内容已存在,跳过: {main_title.strip()}")
                return None
            except Exception as e:
                logger.error(f"保存视频内容失败: {str(e)}")
                return None
            
        except Exception as e:
            logger.error(f"提取视频信息失败: {str(e)}")
            return None
            
    async def _goto_next_page(self) -> bool:
        """
        翻到下一页
        
        Returns:
            bool: 是否成功翻页
        """
        try:
            # 获取当前页码
            current_page = await self.get_current_page()
            total_pages = await self.get_total_pages()
            
            # 如果已经是最后一页，返回False
            if current_page >= total_pages:
                logger.info("已经是最后一页")
                return False
            
            # 检查下一页按钮
            next_button = await self.page.query_selector(
                ".weui-desktop-pagination__nav .weui-desktop-btn_mini:has-text('下一页')"
            )
            if not next_button:
                logger.error("未找到下一页按钮")
                return False
                
            # 检查按钮是否可点击
            button_class = await next_button.get_attribute("class")
            if "weui-desktop-btn_disabled" in (button_class or ""):
                logger.error("下一页按钮已禁用")
                return False
                
            # 点击前确保按钮可见且可点击
            await next_button.scroll_into_view_if_needed()
            await next_button.click()
            
            # 等待页面加载完成
            await self.page.wait_for_load_state("networkidle")
            
            # 等待新页面加载
            try:
                await self.page.wait_for_selector(".post-feed-item", timeout=20000)
            except Exception as e:
                logger.error(f"等待新页面加载失败: {str(e)}")
                return False
            
            # 验证页码是否改变
            new_page = await self.get_current_page()
            if new_page <= current_page:
                logger.error(f"页码未增加: {current_page} -> {new_page}")
                return False
                
            # 检查页面状态
            if not await self.check_page_status():
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"翻页失败: {str(e)}")
            return False

    async def _goto_prev_page(self) -> bool:
        """
        翻到上一页
        
        Returns:
            bool: 是否成功翻页
        """
        try:
            # 获取当前页码
            current_page = await self.get_current_page()
            
            # 如果已经是第一页，返回False
            if current_page <= 1:
                logger.info("已经是第一页")
                return False
            
            # 检查上一页按钮
            prev_button = await self.page.query_selector(
                ".weui-desktop-pagination__nav .weui-desktop-btn_mini:has-text('上一页')"
            )
            if not prev_button:
                logger.error("未找到上一页按钮")
                return False
                
            # 检查按钮是否可点击
            button_class = await prev_button.get_attribute("class")
            if "weui-desktop-btn_disabled" in (button_class or ""):
                logger.error("上一页按钮已禁用")
                return False
                
            # 点击前确保按钮可见且可点击
            await prev_button.scroll_into_view_if_needed()
            await prev_button.click()
            
            # 等待页面加载完成
            await self.page.wait_for_load_state("networkidle")
            
            # 等待新页面加载
            try:
                await self.page.wait_for_selector(".post-feed-item", timeout=20000)
            except Exception as e:
                logger.error(f"等待新页面加载失败: {str(e)}")
                return False
            
            # 验证页码是否改变
            new_page = await self.get_current_page()
            if new_page >= current_page:
                logger.error(f"页码未减少: {current_page} -> {new_page}")
                return False
                
            # 检查页面状态
            if not await self.check_page_status():
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"翻页失败: {str(e)}")
            return False 
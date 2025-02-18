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
from utils.content_deduplication import ContentDeduplication
from utils.log import tencent_logger as logger
import sqlite3

# 忽略ResourceWarning
warnings.filterwarnings("ignore", category=ResourceWarning)

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
        self.db: Optional[VideoContentDB] = None  # 初始化为None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        logger.info("=== 进入异步上下文管理器 ===")
        try:
            logger.info("开始调用init方法...")
            await self.init()
            logger.info("init方法调用完成")
            logger.info("=== 异步上下文管理器初始化完成，返回self ===")
            return self
        except Exception as e:
            logger.error(f"异步上下文管理器初始化失败: {str(e)}")
            # 确保资源被清理
            await self.close()
            raise
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        logger.info("=== 退出异步上下文管理器 ===")
        try:
            await self.close()
            logger.info("=== 异步上下文管理器清理完成 ===")
        except Exception as e:
            logger.error(f"异步上下文管理器清理失败: {str(e)}")
            raise
        
    async def init(self):
        """初始化浏览器和上下文"""
        try:
            # 首先验证账号ID是否存在
            logger.info("验证账号ID...")
            social_db = SocialMediaDB()
            try:
                accounts = social_db.get_all_accounts("tencent")
                if not any(acc.get('id') == self.account_id for acc in accounts):
                    raise ValueError(f"账号ID {self.account_id} 不存在")
                logger.info("账号ID验证通过")
            finally:
                social_db.close()
            
            # 创建数据库连接
            logger.info("创建数据库连接...")
            self.db = VideoContentDB()
            logger.info("数据库连接创建成功")
            
            logger.info("开始初始化Playwright...")
            self._playwright = await async_playwright().start()
            logger.info("Playwright启动成功")
            
            logger.info("开始启动浏览器...")
            self.browser = await self._playwright.chromium.launch(
                headless=self.headless,
                executable_path=self.local_executable_path
            )
            logger.info("浏览器启动成功")
            
            logger.info("开始创建浏览器上下文...")
            self.context = await self.browser.new_context(storage_state=self.account_file)
            logger.info("浏览器上下文创建成功")
            
            logger.info("开始创建新页面...")
            self.page = await self.context.new_page()
            logger.info("新页面创建成功")
            
        except Exception as e:
            logger.error(f"初始化失败: {str(e)}")
            # 确保资源被正确清理
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
                self.db = None
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
        logger.info("=== 进入get_video_list方法 ===")
        logger.info(f"参数: max_pages = {max_pages}")
        
        # 检查组件状态
        if not self.page or not self.context or not self.browser or not self._playwright:
            logger.error("爬虫组件未完全初始化")
            return videos
            
        try:
            # 访问列表页
            logger.info("正在访问视频列表页面...")
            await self.page.goto("https://channels.weixin.qq.com/platform/post/list")
            logger.info("页面导航完成，等待加载...")
            await self.page.wait_for_load_state("networkidle")
            logger.info("页面加载完成，检查登录状态...")
        
            # 等待页面内容加载，使用多个可能的选择器
            logger.info("等待页面内容加载...")
            try:
                # 尝试等待可能的内容选择器
                selectors = [
                    "div[class*='post-feed-item']",
                    ".post-feed-item",
                    ".post-item",
                    "div[class*='weui-desktop-card__bd']"
                ]
                
                content_found = False
                for selector in selectors:
                    try:
                        logger.info(f"尝试查找选择器: {selector}")
                        await self.page.wait_for_selector(selector, timeout=5000)
                        logger.info(f"找到内容元素: {selector}")
                        content_found = True
                        break
                    except Exception as e:
                        logger.warning(f"选择器 {selector} 未找到: {str(e)}")
                        continue
                
                if not content_found:
                    # 如果所有选择器都失败，截图并记录页面内容
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = f"error_screenshot_{timestamp}.png"
                    await self.page.screenshot(path=screenshot_path)
                    page_content = await self.page.content()
                    logger.error(f"页面内容加载失败，已保存截图: {screenshot_path}")
                    logger.debug(f"页面HTML: {page_content[:500]}...")  # 只记录前500个字符
                    return videos
                    
            except Exception as e:
                logger.error(f"页面内容加载失败: {str(e)}")
                return videos
                
            # 检查页面状态
            logger.info("检查页面状态...")
            if not await self.check_page_status():
                logger.error("页面状态异常")
                return videos
                
            # 等待页面完全稳定
            logger.info("等待页面稳定...")
            await self.random_delay()
            
            # 如果是倒序爬取，先跳转到最后一页
            if self.reverse:
                logger.info("开始倒序爬取，尝试跳转到最后一页...")
                # 获取最后一页的页码
                last_page_num = await self.page.query_selector(".weui-desktop-pagination__num:last-child")
                if last_page_num:
                    last_page_text = await last_page_num.text_content()
                    logger.info(f"找到页码元素，内容为: {last_page_text}")
                    if last_page_text.isdigit():
                        logger.info(f"找到最后一页页码: {last_page_text}")
                        if not await self.jump_to_page(int(last_page_text)):
                            logger.error("跳转到最后一页失败")
                            return videos
                        # 等待页面加载和稳定
                        await self.random_delay()
                        
                        # 等待新页面内容加载
                        try:
                            logger.info("等待最后一页内容加载...")
                            await self.page.wait_for_selector("div[class*='post-feed-item']", timeout=20000)
                            # 检查是否真的加载到了内容
                            items = await self.page.query_selector_all("div[class*='post-feed-item']")
                            logger.info(f"最后一页内容已加载，找到 {len(items)} 个视频项")
                            
                            # 检查页面URL和当前页码
                            current_url = self.page.url
                            current_page = await self.get_current_page()
                            logger.info(f"当前页面URL: {current_url}")
                            logger.info(f"当前页码: {current_page}")
                            
                            # 检查页面状态
                            page_status = await self.check_page_status()
                            logger.info(f"页面状态检查结果: {'正常' if page_status else '异常'}")
                            
                            if not items:
                                logger.error("最后一页未找到任何视频内容")
                                # 获取页面源码以供调试
                                page_content = await self.page.content()
                                logger.debug(f"页面源码片段: {page_content[:500]}...")
                                
                        except Exception as e:
                            logger.error(f"最后一页内容加载失败: {str(e)}")
                            # 记录当前页面状态
                            try:
                                screenshot_path = f"error_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                                await self.page.screenshot(path=screenshot_path)
                                logger.error(f"已保存错误截图: {screenshot_path}")
                            except Exception as screenshot_error:
                                logger.error(f"保存错误截图失败: {str(screenshot_error)}")
                            return videos
                else:
                    logger.error("未找到最后一页页码元素")
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
                end_page = 1  # 修改这里：倒序爬取时，结束页永远是第1页
                step = -1
                logger.info(f"倒序爬取: 从第 {start_page} 页到第 {end_page} 页")
            else:
                start_page = 1
                end_page = max_pages
                step = 1
                logger.info(f"正序爬取: 从第 {start_page} 页到第 {end_page} 页")
                
            current_page = start_page
            
            # 如果是倒序且不是最后一页，先跳转到起始页
            if self.reverse and current_page != total_pages:
                logger.info(f"尝试跳转到起始页: {start_page}")
                if not await self.jump_to_page(start_page):
                    logger.error(f"跳转到第 {start_page} 页失败")
                    return videos
                    
                # 等待新页面内容加载
                try:
                    await self.page.wait_for_selector("div[class*='post-feed-item']", timeout=20000)
                    logger.info("起始页内容已加载")
                except Exception as e:
                    logger.error(f"起始页内容加载失败: {str(e)}")
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
                for idx, item in enumerate(items, 1):
                    try:
                        logger.info(f"正在处理第 {idx}/{len(items)} 个视频...")
                        video_info = await self.retry_on_error(self._extract_video_info, item)
                        if video_info:
                            videos.append(video_info)
                            logger.info(f"成功提取视频信息: {video_info['title']}")
                            # 每处理一个视频后短暂延迟
                            await asyncio.sleep(random.uniform(0.5, 1.5))
                        else:
                            logger.warning(f"第 {idx} 个视频信息提取失败或已存在")
                    except Exception as e:
                        logger.error(f"处理第 {idx} 个视频时出错: {str(e)}")
                        continue
                
                # 处理翻页
                if current_page != end_page:
                    logger.info(f"准备翻页: 当前第 {current_page} 页")
                    if step > 0:
                        has_next = await self._goto_next_page()
                        logger.info("尝试前往下一页...")
                    else:
                        has_next = await self._goto_prev_page()
                        logger.info("尝试前往上一页...")
                        
                    if not has_next:
                        logger.info("没有更多页面了")
                        break
                        
                    # 翻页后等待
                    logger.info("翻页成功，等待页面稳定...")
                    await self.random_delay()
                    
                current_page += step
                logger.info(f"页码更新: {current_page}")
                
        except Exception as e:
            logger.error(f"获取视频列表失败: {str(e)}")
            
        logger.info(f"爬取任务完成，共获取 {len(videos)} 个视频信息")
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
            title_element = await item.query_selector("div[class*='post-title']")
            full_text = await title_element.text_content() if title_element else ""
            full_text = full_text.strip()
            
            # 从完整文本中提取标签和@用户
            # 使用正则表达式提取所有@用户
            mentions = re.findall(r'@([a-zA-Z0-9\u4e00-\u9fa5]+?)(?=[@#]|\s|$)', full_text)
            mentions = [mention.strip() for mention in mentions if mention.strip()]
            
            # 使用正则表达式提取所有#标签
            tags = re.findall(r'#([a-zA-Z0-9\u4e00-\u9fa5]+?)(?=[@#]|\s|$)', full_text)
            tags = [tag.strip() for tag in tags if tag.strip()]
            
            # 提取标题（@或#前的所有内容）
            main_title = ""
            first_special_char_index = -1
            
            # 查找第一个@或#的位置
            at_index = full_text.find('@')
            hash_index = full_text.find('#')
            
            if at_index >= 0 and hash_index >= 0:
                first_special_char_index = min(at_index, hash_index)
            elif at_index >= 0:
                first_special_char_index = at_index
            elif hash_index >= 0:
                first_special_char_index = hash_index
                
            # 如果找到了@或#，且它们前面有内容，则提取标题
            if first_special_char_index > 0:
                main_title = full_text[:first_special_char_index].strip()
            
            # 如果标题为空，设置默认值为"null"
            if not main_title:
                main_title = "null"
                logger.info("标题为空，使用默认值: null")
            
            logger.info(f"解析结果 - 完整文本: {full_text}")
            logger.info(f"解析结果 - 标题: {main_title}")
            logger.info(f"解析结果 - 标签: {tags}")
            logger.info(f"解析结果 - 艾特用户: {mentions}")
            
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
                
                # 构建新的内容数据
                new_content = {
                    "account_id": self.account_id,
                    "title": main_title,
                    "thumb_base64": thumb_base64,
                    "publish_time": publish_time.strip(),
                    "status": status.strip(),
                    "plays": plays,
                    "likes": likes,
                    "comments": comments,
                    "shares": shares,
                    "tags": tags,
                    "mentions": mentions
                }
                
                # 从数据库获取已存在的内容
                existing_content = self.db.get_video_content_by_title(self.account_id, main_title)
                
                # 使用去重工具判断
                dedup = ContentDeduplication()
                if existing_content:
                    if dedup.is_content_duplicate(new_content, existing_content):
                        # 检查是否需要更新
                        if dedup.should_update_content(new_content, existing_content):
                            # 更新内容
                            video_id = self.db.update_video_content(
                                existing_content['id'],
                                **new_content
                            )
                            logger.info(f"更新视频内容: {main_title}")
                        else:
                            logger.info(f"内容无变化，跳过: {main_title}")
                            return None
                    else:
                        # 内容不重复，作为新内容保存
                        video_id = self.db.add_video_content(**new_content)
                        logger.info(f"保存新视频内容: {main_title}")
                else:
                    # 不存在，直接保存
                    video_id = self.db.add_video_content(**new_content)
                    logger.info(f"保存新视频内容: {main_title}")
                
                # 为了保持返回数据的一致性，重新构建带有 stats 的内容
                return_content = {
                    **new_content,
                    "id": video_id,
                    "stats": {
                        "plays": plays,
                        "likes": likes,
                        "comments": comments,
                        "shares": shares
                    }
                }
                del return_content["plays"]
                del return_content["likes"]
                del return_content["comments"]
                del return_content["shares"]
                
                return return_content
                
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
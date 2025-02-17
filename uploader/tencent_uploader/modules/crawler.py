"""
微信视频号内容抓取模块
负责从视频号平台抓取已发布的视频内容
"""
from typing import List, Dict, Optional, Any
import asyncio
import logging
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page
from .cookie import CookieManager

logger = logging.getLogger(__name__)

class VideoChannelCrawler:
    """视频号内容抓取器"""
    
    def __init__(
        self,
        cookie_path: Optional[Path] = None,
        headless: bool = False,
        timeout: int = 30000
    ):
        """
        初始化爬虫
        
        Args:
            cookie_path: cookie文件路径
            headless: 是否使用无头模式
            timeout: 超时时间(毫秒)
        """
        self.cookie_path = cookie_path
        self.headless = headless
        self.timeout = timeout
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.cookie_manager = CookieManager(cookie_path) if cookie_path else None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.init()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def init(self):
        """初始化浏览器和页面"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        
        # 设置超时
        self.page.set_default_timeout(self.timeout)
        
        # 如果有cookie，则恢复登录状态
        if self.cookie_manager:
            cookies = self.cookie_manager.load_cookies()
            if cookies:
                await self.page.context.add_cookies(cookies)
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.page = None
    
    async def check_login(self) -> bool:
        """检查是否已登录"""
        try:
            await self.page.goto("https://channels.weixin.qq.com/platform/post/list")
            # 等待页面加载完成
            await self.page.wait_for_load_state("networkidle")
            
            # 检查是否存在登录按钮
            login_button = await self.page.query_selector('text="登录"')
            return not bool(login_button)
            
        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return False
    
    async def get_video_list(self, max_pages: int = 1) -> List[Dict[str, Any]]:
        """
        获取视频列表
        
        Args:
            max_pages: 最大抓取页数
            
        Returns:
            List[Dict]: 视频信息列表
        """
        videos = []
        current_page = 1
        
        try:
            # 确保在列表页面
            await self.page.goto("https://channels.weixin.qq.com/platform/post/list")
            await self.page.wait_for_load_state("networkidle")
            
            while current_page <= max_pages:
                # 等待视频列表加载
                await self.page.wait_for_selector(".post-item", timeout=10000)
                
                # 获取当前页面的所有视频
                video_elements = await self.page.query_selector_all(".post-item")
                
                for element in video_elements:
                    try:
                        # 提取视频信息
                        title = await element.query_selector(".post-title")
                        title_text = await title.text_content() if title else "未知标题"
                        
                        # 提取发布时间
                        time_element = await element.query_selector(".post-time")
                        publish_time = await time_element.text_content() if time_element else ""
                        
                        # 提取播放量等数据
                        stats = await element.query_selector(".post-stats")
                        stats_text = await stats.text_content() if stats else ""
                        
                        videos.append({
                            "title": title_text.strip(),
                            "publish_time": publish_time.strip(),
                            "stats": stats_text.strip()
                        })
                        
                    except Exception as e:
                        logger.error(f"提取视频信息失败: {e}")
                        continue
                
                # 检查是否有下一页
                next_button = await self.page.query_selector("button:has-text('下一页')")
                if not next_button or await next_button.is_disabled():
                    break
                    
                # 点击下一页
                await next_button.click()
                await self.page.wait_for_load_state("networkidle")
                current_page += 1
                
        except Exception as e:
            logger.error(f"获取视频列表失败: {e}")
            
        return videos
    
    async def get_video_details(self, video_url: str) -> Dict[str, Any]:
        """
        获取单个视频的详细信息
        
        Args:
            video_url: 视频详情页URL
            
        Returns:
            Dict: 视频详细信息
        """
        try:
            await self.page.goto(video_url)
            await self.page.wait_for_load_state("networkidle")
            
            # 等待视频信息加载
            await self.page.wait_for_selector(".video-details", timeout=10000)
            
            # 提取详细信息
            title = await self.page.text_content(".video-title") or ""
            description = await self.page.text_content(".video-description") or ""
            publish_time = await self.page.text_content(".publish-time") or ""
            
            # 获取视频统计数据
            likes = await self.page.text_content(".likes-count") or "0"
            comments = await self.page.text_content(".comments-count") or "0"
            shares = await self.page.text_content(".shares-count") or "0"
            
            return {
                "title": title.strip(),
                "description": description.strip(),
                "publish_time": publish_time.strip(),
                "stats": {
                    "likes": likes.strip(),
                    "comments": comments.strip(),
                    "shares": shares.strip()
                }
            }
            
        except Exception as e:
            logger.error(f"获取视频详情失败: {e}")
            return {} 
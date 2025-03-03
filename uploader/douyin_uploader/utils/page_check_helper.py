from typing import Optional, Dict, Any
import asyncio
from datetime import datetime
from playwright.async_api import Page
from loguru import logger

class PageCheckHelper:
    # 配置参数
    PAGE_LOAD_TIMEOUT = 10000  # 总体页面加载超时时间
    ELEMENT_WAIT_TIMEOUT = 5000  # 元素等待超时时间
    CHECK_INTERVAL = 500  # 检查间隔时间
    MAX_RETRIES = 3  # 最大重试次数
    
    @staticmethod
    async def check_element_exists(page: Page, selector: str, timeout: int = ELEMENT_WAIT_TIMEOUT) -> bool:
        """
        检查元素是否存在
        """
        try:
            element = await page.wait_for_selector(selector, timeout=timeout)
            return element is not None
        except Exception as e:
            logger.debug(f"元素 {selector} 检查失败: {str(e)}")
            return False
            
    @staticmethod
    async def check_multiple_elements(page: Page, selectors: list, timeout: int = ELEMENT_WAIT_TIMEOUT) -> bool:
        """
        并行检查多个元素是否存在
        """
        tasks = [PageCheckHelper.check_element_exists(page, selector, timeout) for selector in selectors]
        results = await asyncio.gather(*tasks)
        return all(results)
    
    @staticmethod
    async def check_page_loaded(page: Page) -> bool:
        """
        检查页面是否完全加载
        """
        try:
            # 检查当前URL
            current_url = page.url
            logger.info(f"当前页面URL: {current_url}")
            
            # 如果URL是登录页，说明未登录
            if current_url == "https://creator.douyin.com/":
                logger.info("已跳转到登录页面，未登录状态")
                return False
                
            # 如果URL包含creator-micro，说明已登录
            if "creator-micro" in current_url:
                logger.info("在创作者中心页面，已登录状态")
                return True
            
            # 其他情况，检查页面元素
            containers = [
                ".semi-layout-content",  # 新版容器
                "#douyin-creator-master-side-upload",  # 上传按钮容器
                ".container-vEyGlK"  # 用户信息容器
            ]
            
            for container in containers:
                if await PageCheckHelper.check_element_exists(page, container):
                    logger.info(f"找到创作者中心元素: {container}")
                    return True
            
            logger.warning("未找到创作者中心元素，可能未登录")
            return False
            
        except Exception as e:
            logger.error(f"页面加载检查失败: {str(e)}")
            return False
            
    @staticmethod
    async def verify_login_status(page: Page, max_retries: int = MAX_RETRIES) -> bool:
        """
        验证登录状态,支持重试机制
        """
        for i in range(max_retries):
            try:
                if await PageCheckHelper.check_page_loaded(page):
                    return True
                    
                logger.warning(f"登录验证第 {i+1} 次失败,准备重试...")
                await asyncio.sleep(PageCheckHelper.CHECK_INTERVAL / 1000)  # 转换为秒
                
            except Exception as e:
                logger.error(f"登录验证出错: {str(e)}")
                
        return False
        
    @staticmethod
    async def get_user_info(page: Page) -> Optional[Dict[str, Any]]:
        """
        获取用户信息
        """
        try:
            # 等待用户信息加载
            if not await PageCheckHelper.check_page_loaded(page):
                return None
                
            # 获取用户信息
            user_info = {}
            
            # 获取基本信息
            user_info['nickname'] = (await page.text_content('.name-_lSSDc')) or ''
            douyin_id_text = (await page.text_content('.unique_id-EuH8eA')) or ''
            user_info['douyin_id'] = douyin_id_text.replace('抖音号：', '')  # 移除前缀
            user_info['avatar'] = (await page.get_attribute('.avatar-XoPjK6 img', 'src')) or ''
            
            # 获取签名
            user_info['signature'] = (await page.text_content('.signature-HLGxt7')) or '这个人很懒，没有留下任何签名'
            
            # 获取统计数据
            stats_elements = await page.query_selector_all('.statics-item-MDWoNA')
            for i, element in enumerate(stats_elements[:3]):  # 只取前三个元素
                number = await element.query_selector('.number-No6ev9')
                if number:
                    value = await number.text_content() or '0'
                    if i == 0:
                        user_info['following_count'] = int(value)
                    elif i == 1:
                        user_info['fans_count'] = int(value)
                    elif i == 2:
                        user_info['likes_count'] = int(value)
            
            # 设置默认值
            user_info.setdefault('following_count', 0)
            user_info.setdefault('fans_count', 0)
            user_info.setdefault('likes_count', 0)
            
            # 添加更新时间
            user_info['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return user_info
            
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}")
            return None 
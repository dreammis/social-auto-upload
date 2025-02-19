"""
抖音用户信息获取工具类
提供用户信息获取相关功能
"""

from typing import Optional, Dict, Any
from datetime import datetime
from playwright.async_api import Page
from utils.log import douyin_logger

class UserInfoHelper:
    """抖音用户信息获取助手类"""
    
    @staticmethod
    async def get_user_info(page: Page) -> Optional[Dict[str, Any]]:
        """
        获取抖音用户信息
        Args:
            page: Playwright页面对象
        Returns:
            Optional[Dict[str, Any]]: 用户信息字典，获取失败返回None
        """
        try:
            douyin_logger.info("等待页面加载...")
            # 等待页面加载完成
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(2000)  # 额外等待2秒确保页面完全加载
            
            douyin_logger.info("开始获取用户信息...")
            
            # 获取基本信息
            try:
                # 尝试不同的选择器
                nickname_selectors = [
                    '.name-_lSSDc',  # 精确匹配
                    '.left-zEzdJX .name-_lSSDc',  # 带父级的精确匹配
                    'div[class*="name-"]',  # 模糊匹配
                ]
                
                nickname = None
                for selector in nickname_selectors:
                    try:
                        if await page.locator(selector).count() > 0:
                            nickname = await page.locator(selector).inner_text()
                            douyin_logger.info(f"找到昵称元素: {selector}")
                            break
                    except Exception as e:
                        continue
                
                if not nickname:
                    douyin_logger.error("未找到昵称元素")
                    await page.screenshot(path="debug_screenshot.png", full_page=True)
                    return None
                
                # 获取抖音号
                douyin_id_selectors = [
                    '.unique_id-EuH8eA',  # 精确匹配
                    'div[class*="unique_id-"]',  # 模糊匹配
                ]
                
                douyin_id = None
                for selector in douyin_id_selectors:
                    try:
                        if await page.locator(selector).count() > 0:
                            douyin_id = await page.locator(selector).inner_text()
                            douyin_id = douyin_id.replace('抖音号：', '').strip()
                            douyin_logger.info(f"找到抖音号元素: {selector}")
                            break
                    except Exception as e:
                        continue
                
                if not douyin_id:
                    douyin_logger.error("未找到抖音号元素")
                    return None
                
                # 获取签名
                signature_selectors = [
                    '.signature-HLGxt7',  # 精确匹配
                    'div[class*="signature-"]',  # 模糊匹配
                ]
                
                signature = "这个人很懒，没有留下任何签名"  # 默认签名
                for selector in signature_selectors:
                    try:
                        if await page.locator(selector).count() > 0:
                            temp_sig = await page.locator(selector).inner_text()
                            if temp_sig.strip():
                                signature = temp_sig
                                douyin_logger.info(f"找到签名元素: {selector}")
                                break
                    except Exception as e:
                        continue
                
                # 获取统计信息
                following = "0"
                fans = "0"
                likes = "0"
                
                try:
                    # 尝试获取关注数
                    following_selectors = [
                        '#guide_home_following .number-No6ev9',  # 精确匹配
                        '.statics-item-MDWoNA#guide_home_following .number-No6ev9',  # 完整路径
                        'div[id="guide_home_following"] span[class*="number-"]'  # 备用匹配
                    ]
                    
                    for selector in following_selectors:
                        try:
                            if await page.locator(selector).count() > 0:
                                following = await page.locator(selector).inner_text()
                                douyin_logger.info(f"找到关注数元素: {selector}")
                                break
                        except Exception as e:
                            continue
                    
                    # 尝试获取粉丝数
                    fans_selectors = [
                        '#guide_home_fans .number-No6ev9',  # 精确匹配
                        '.statics-item-MDWoNA#guide_home_fans .number-No6ev9',  # 完整路径
                        'div[id="guide_home_fans"] span[class*="number-"]'  # 备用匹配
                    ]
                    
                    for selector in fans_selectors:
                        try:
                            if await page.locator(selector).count() > 0:
                                fans = await page.locator(selector).inner_text()
                                douyin_logger.info(f"找到粉丝数元素: {selector}")
                                break
                        except Exception as e:
                            continue
                    
                    # 尝试获取获赞数
                    likes_selectors = [
                        '.statics-item-MDWoNA:not([id]) .number-No6ev9',  # 精确匹配无ID的元素
                        '.statics-kyUhqC > div:last-child .number-No6ev9',  # 使用位置选择
                        'div.statics-item-MDWoNA:not([id]) span.number-No6ev9'  # 备用匹配
                    ]
                    
                    for selector in likes_selectors:
                        try:
                            if await page.locator(selector).count() > 0:
                                likes = await page.locator(selector).inner_text()
                                douyin_logger.info(f"找到获赞数元素: {selector}")
                                break
                        except Exception as e:
                            continue
                            
                except Exception as e:
                    douyin_logger.warning(f"获取统计信息时出错: {str(e)}")
                
                # 获取头像URL
                avatar_url = ""
                try:
                    avatar_selectors = [
                        '.img-PeynF_',  # 精确匹配
                        '.avatar-XoPjK6 img',  # 通过父元素定位
                        'img[src*="douyinpic"]'  # 通过src属性匹配
                    ]
                    
                    for selector in avatar_selectors:
                        try:
                            if await page.locator(selector).count() > 0:
                                avatar_url = await page.locator(selector).get_attribute('src') or ""
                                douyin_logger.info(f"找到头像元素: {selector}")
                                break
                        except Exception as e:
                            continue
                            
                except Exception as e:
                    douyin_logger.warning(f"获取头像URL时出错: {str(e)}")
                
                user_info = {
                    'nickname': nickname,
                    'douyin_id': douyin_id,
                    'signature': signature,
                    'following_count': int(following.replace(',', '')),
                    'fans_count': int(fans.replace(',', '')),
                    'likes_count': int(likes.replace(',', '')),
                    'avatar_url': avatar_url,
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                douyin_logger.info(f"获取用户信息成功: {nickname}")
                douyin_logger.info(f"账号信息: {user_info}")
                return user_info
                
            except Exception as e:
                douyin_logger.error(f"解析用户信息时出错: {str(e)}")
                # 保存页面源码以便调试
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(await page.content())
                return None
            
        except Exception as e:
            douyin_logger.error(f"获取用户信息失败: {str(e)}")
            # 保存错误现场
            await page.screenshot(path="error_screenshot.png", full_page=True)
            with open("error_page.html", "w", encoding="utf-8") as f:
                f.write(await page.content())
            return None 
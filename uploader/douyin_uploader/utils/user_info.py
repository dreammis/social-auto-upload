"""
用户信息助手
提供用户信息的获取和处理功能
"""

from typing import Optional, Dict, Any
from datetime import datetime
from playwright.async_api import Page
from utils.log import douyin_logger

class UserInfoHelper:
    """用户信息助手类"""
    
    @staticmethod
    async def get_user_info(page: Page) -> Optional[Dict[str, Any]]:
        """
        获取用户信息
        Args:
            page: Playwright页面对象
        Returns:
            Optional[Dict[str, Any]]: 用户信息字典
        """
        try:
            # 开始获取用户信息
            douyin_logger.info("开始获取用户信息...")
            
            # 获取昵称
            nickname = ""
            nickname_selectors = ['.name-_lSSDc']
            for selector in nickname_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        nickname = await element.text_content() or ""
                        douyin_logger.info(f"找到昵称元素: {selector}")
                        break
                except Exception:
                    continue
            
            # 获取抖音号
            douyin_id = ""
            douyin_id_selectors = ['.unique_id-EuH8eA']
            for selector in douyin_id_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        douyin_id = await element.text_content() or ""
                        douyin_logger.info(f"找到抖音号元素: {selector}")
                        break
                except Exception:
                    continue
            
            # 获取签名
            signature = ""
            signature_selectors = ['.signature-HLGxt7']
            for selector in signature_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        signature = await element.text_content() or ""
                        douyin_logger.info(f"找到签名元素: {selector}")
                        break
                except Exception:
                    continue
            
            # 获取关注数
            following_count = 0
            following_selectors = ['#guide_home_following .number-No6ev9']
            for selector in following_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        following_text = await element.text_content() or "0"
                        following_count = int(following_text)
                        douyin_logger.info(f"找到关注数元素: {selector}")
                        break
                except Exception:
                    continue
            
            # 获取粉丝数
            fans_count = 0
            fans_selectors = ['#guide_home_fans .number-No6ev9']
            for selector in fans_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        fans_text = await element.text_content() or "0"
                        fans_count = int(fans_text)
                        douyin_logger.info(f"找到粉丝数元素: {selector}")
                        break
                except Exception:
                    continue
            
            # 获取获赞数
            likes_count = 0
            likes_selectors = ['.statics-item-MDWoNA:not([id]) .number-No6ev9']
            for selector in likes_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        likes_text = await element.text_content() or "0"
                        likes_count = int(likes_text)
                        douyin_logger.info(f"找到获赞数元素: {selector}")
                        break
                except Exception:
                    continue
            
            # 获取头像URL
            avatar_url = ""
            avatar_selectors = [
                '.img-PeynF_',
                '.avatar-XoPjK6 img',
                'div[class*="avatar"] img'
            ]
            for selector in avatar_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        avatar_url = await element.get_attribute('src') or ""
                        douyin_logger.info(f"找到头像元素: {selector}")
                        break
                except Exception:
                    continue
            
            # 组装用户信息
            user_info = {
                'nickname': nickname,
                'douyin_id': douyin_id,
                'signature': signature,
                'following_count': following_count,
                'fans_count': fans_count,
                'likes_count': likes_count,
                'avatar_url': avatar_url,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 验证必要字段
            if not nickname or not douyin_id:
                douyin_logger.warning("缺少必要的用户信息字段")
                return None
            
            return user_info
            
        except Exception as e:
            douyin_logger.error(f"获取用户信息失败: {str(e)}")
            return None 
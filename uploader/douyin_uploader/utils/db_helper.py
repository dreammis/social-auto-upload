"""
数据库操作助手
提供统一的数据库操作接口
"""

from typing import Optional, Dict, Any, List
from utils.log import douyin_logger
from utils.social_media_db import SocialMediaDB

class DBHelper:
    """数据库操作助手类"""
    
    def __init__(self, platform: str = "douyin"):
        self.db = SocialMediaDB()
        self.platform = platform
    
    def update_account(
        self,
        user_info: Dict[str, Any],
        cookie_file: Optional[str] = None
    ) -> bool:
        """
        更新账号信息
        Args:
            user_info: 用户信息字典
            cookie_file: cookie文件路径
        Returns:
            bool: 更新是否成功
        """
        try:
            # 处理抖音号格式
            account_id = user_info.get('douyin_id', '').replace('抖音号：', '').strip()
            if not account_id:
                douyin_logger.error("账号ID不能为空")
                return False
            
            # 准备账号数据
            account_data = {
                'nickname': user_info.get('nickname', ''),
                'video_count': user_info.get('video_count', 0),
                'follower_count': user_info.get('fans_count', 0),
                'extra': {
                    'douyin_id': account_id,
                    'signature': user_info.get('signature', '这个人很懒，没有留下任何签名'),
                    'following_count': user_info.get('following_count', 0),
                    'likes_count': user_info.get('likes_count', 0),
                    'avatar_url': user_info.get('avatar_url', ''),
                    'updated_at': user_info.get('updated_at', '')
                }
            }
            
            if not account_data['nickname']:
                douyin_logger.error("账号昵称不能为空")
                return False
            
            # 更新账号信息
            if not self.db.add_or_update_account(
                self.platform,
                account_id,
                account_data
            ):
                douyin_logger.error("更新账号信息失败")
                return False
                
            # 如果提供了cookie文件，更新cookie
            if cookie_file:
                if not self.add_cookie(self.platform, account_id, cookie_file):
                    douyin_logger.error("更新cookie失败")
                    return False
                    
            return True
            
        except Exception as e:
            douyin_logger.error(f"更新账号信息失败: {str(e)}")
            return False
            
        finally:
            self.db.close()
    
    def get_account_info(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        获取账号信息
        Args:
            account_id: 账号ID
        Returns:
            Optional[Dict[str, Any]]: 账号信息
        """
        try:
            accounts = self.db.get_all_accounts(self.platform)
            account = next(
                (acc for acc in accounts if acc['account_id'] == account_id),
                None
            )
            return account
            
        except Exception as e:
            douyin_logger.error(f"获取账号信息失败: {str(e)}")
            return None
            
        finally:
            self.db.close()
    
    def get_all_accounts(self) -> List[Dict[str, Any]]:
        """
        获取所有账号信息
        Returns:
            List[Dict[str, Any]]: 账号信息列表
        """
        try:
            return self.db.get_all_accounts(self.platform)
        except Exception as e:
            douyin_logger.error(f"获取所有账号失败: {str(e)}")
            return []
        finally:
            self.db.close()

    def add_cookie(self, platform: str, account_id: str, cookie_file: str) -> bool:
        """
        添加或更新cookie记录
        Args:
            platform: 平台名称
            account_id: 账号ID
            cookie_file: cookie文件路径
        Returns:
            bool: 是否操作成功
        """
        try:
            # 处理account_id格式
            clean_account_id = account_id.replace('抖音号：', '').strip()
            
            # 直接添加/更新cookie记录（使用数据库的UPSERT功能）
            if self.db.add_cookie(platform, clean_account_id, cookie_file):
                douyin_logger.info(f"添加/更新cookie记录成功: {clean_account_id}")
                return True
            else:
                douyin_logger.error(f"添加/更新cookie记录失败: {clean_account_id}")
                return False
            
        except Exception as e:
            douyin_logger.error(f"操作cookie记录失败: {str(e)}")
            return False

    def get_account_cookie_path(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        获取账号的cookie路径信息
        Args:
            account_id: 账号ID
        Returns:
            Optional[Dict[str, Any]]: 账号信息
        """
        try:
            cookie_path = self.db.get_valid_cookies(self.platform, account_id)
            if cookie_path:
                return cookie_path
            else:
                return None
            
        except Exception as e:
            douyin_logger.error(f"获取账号信息失败: {str(e)}")
            return None
            
        finally:
            self.db.close()

    def get_cookie_path_by_nickname(self, nickname: str) -> Optional[str]:
        """
        通过昵称查找账号的cookie路径
        Args:
            nickname: 账号昵称
        Returns:
            Optional[str]: cookie文件路径，如果未找到返回None
        """
        try:
            sql = """
            SELECT ac.cookie_path
            FROM social_media_accounts sma
            JOIN account_cookies ac ON sma.platform = ac.platform 
                AND sma.account_id = ac.account_id
            WHERE sma.platform = ? AND sma.nickname = ? AND ac.is_valid = 1
            ORDER BY ac.last_check DESC
            LIMIT 1
            """
            
            result = self.db.db.query_one(sql, (self.platform, nickname))
            if result:
                douyin_logger.info(f"找到账号 {nickname} 的cookie路径")
                return result['cookie_path']
            else:
                douyin_logger.warning(f"未找到账号 {nickname} 的cookie路径")
                return None
                
        except Exception as e:
            douyin_logger.error(f"查询cookie路径失败: {str(e)}")
            return None
            
        finally:
            self.db.close()
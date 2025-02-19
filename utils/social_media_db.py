"""社交媒体账号数据库管理模块

此模块提供了社交媒体账号信息的数据库操作接口，支持：
1. 账号信息的CRUD操作
2. 账号状态管理
3. Cookie文件关联
4. 数据统计分析
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from utils.sqlite_helper import SQLiteHelper
from utils.log import logger
from conf import BASE_DIR

# Cookie文件大小限制 (100KB)
MAX_COOKIE_FILE_SIZE = 100 * 1024

class CookieError(Exception):
    """Cookie相关错误"""
    pass

class SocialMediaDB:
    """社交媒体账号数据库管理类
    
    提供了一系列方法来管理社交媒体账号信息，包括：
    - 账号信息的增删改查
    - 账号状态更新
    - Cookie文件管理
    - 数据统计
    
    典型用法:
        db = SocialMediaDB()
        db.add_account("tencent", "12345", "测试账号")
        db.add_cookie("tencent", "12345", "cookies/test.json")
    """
    
    def __init__(self, db_path: Union[str, Path] = None):
        """初始化数据库管理类
        
        Args:
            db_path: 数据库文件路径，默认为 BASE_DIR/data/social_media.db
        """
        if db_path is None:
            db_path = BASE_DIR / "data" / "social_media.db"
        
        self.db = SQLiteHelper(db_path)
        self._initialize_db()
    
    def _initialize_db(self):
        """初始化数据库表结构"""
        # 创建账号表
        create_accounts_table_sql = """
        CREATE TABLE IF NOT EXISTS social_media_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            account_id TEXT NOT NULL,
            nickname TEXT NOT NULL,
            video_count INTEGER DEFAULT 0,
            follower_count INTEGER DEFAULT 0,
            last_update TIMESTAMP,
            status INTEGER DEFAULT 1,
            extra TEXT,
            UNIQUE(platform, account_id)
        )
        """
        
        # 创建cookie表
        create_cookies_table_sql = """
        CREATE TABLE IF NOT EXISTS account_cookies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            account_id TEXT NOT NULL,
            cookie_path TEXT NOT NULL,
            is_valid INTEGER DEFAULT 1,
            created_at TIMESTAMP,
            last_check TIMESTAMP,
            UNIQUE(platform, account_id, cookie_path),
            FOREIGN KEY (platform, account_id) 
            REFERENCES social_media_accounts(platform, account_id)
            ON DELETE CASCADE
        )
        """
        
        self.db.create_table(create_accounts_table_sql)
        self.db.create_table(create_cookies_table_sql)
    
    def add_account(self, platform: str, account_id: str, nickname: str,
                   video_count: int = 0, follower_count: int = 0,
                   extra: dict = None) -> bool:
        """添加新的社交媒体账号
        
        Args:
            platform: 平台名称
            account_id: 平台账号ID
            nickname: 账号昵称
            video_count: 视频数量
            follower_count: 粉丝数量
            extra: 额外信息字典
            
        Returns:
            bool: 是否添加成功
        """
        try:
            sql = """
            INSERT INTO social_media_accounts 
            (platform, account_id, nickname, video_count, follower_count, 
             last_update, extra)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            self.db.execute(sql, (
                platform, account_id, nickname, video_count, follower_count,
                datetime.now(), json.dumps(extra or {})
            ))
            return True
        except Exception as e:
            logger.error(f"添加账号失败: {str(e)}")
            return False
    
    def _validate_cookie_file(self, cookie_path: str) -> bool:
        """验证cookie文件
        
        检查:
        1. 文件是否存在
        2. 文件大小是否合理
        3. 文件内容是否是有效的JSON
        
        Args:
            cookie_path: cookie文件路径
            
        Returns:
            bool: 文件是否有效
            
        Raises:
            CookieError: 当cookie文件无效时
        """
        try:
            cookie_file = Path(cookie_path)
            if not cookie_file.exists():
                raise CookieError(f"Cookie文件不存在: {cookie_path}")
                
            # 检查文件大小
            if cookie_file.stat().st_size > MAX_COOKIE_FILE_SIZE:
                raise CookieError(f"Cookie文件过大: {cookie_file.stat().st_size} bytes")
                
            # 验证JSON格式
            with open(cookie_file, 'r', encoding='utf-8') as f:
                json.load(f)
                
            return True
        except json.JSONDecodeError:
            raise CookieError(f"Cookie文件不是有效的JSON格式: {cookie_path}")
        except Exception as e:
            raise CookieError(f"Cookie文件验证失败: {str(e)}")
    
    def add_cookie(self, platform: str, account_id: str, cookie_path: str) -> bool:
        """添加账号的cookie信息
        
        Args:
            platform: 平台名称
            account_id: 平台账号ID
            cookie_path: cookie文件路径
            
        Returns:
            bool: 是否添加成功
        """
        try:
            # 检查账号是否存在
            if not self.get_account(platform, account_id):
                logger.error(f"账号不存在: {platform}/{account_id}")
                return False
            
            # 验证cookie文件
            try:
                self._validate_cookie_file(cookie_path)
            except CookieError as e:
                logger.error(str(e))
                return False
                
            sql = """
            INSERT INTO account_cookies 
            (platform, account_id, cookie_path, created_at, last_check)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(platform, account_id, cookie_path) 
            DO UPDATE SET 
                is_valid = 1,
                last_check = excluded.last_check
            """
            now = datetime.now()
            self.db.execute(sql, (platform, account_id, cookie_path, now, now))
            return True
        except Exception as e:
            logger.error(f"添加cookie失败: {str(e)}")
            return False
    
    def update_cookie_status(self, platform: str, account_id: str, 
                           cookie_path: str, is_valid: bool) -> bool:
        """更新cookie状态
        
        Args:
            platform: 平台名称
            account_id: 平台账号ID
            cookie_path: cookie文件路径
            is_valid: 是否有效
            
        Returns:
            bool: 是否更新成功
        """
        try:
            # 确保cookie_path是字符串
            cookie_path = str(cookie_path)
            
            sql = """
            UPDATE account_cookies 
            SET is_valid = ?, last_check = ?
            WHERE platform = ? AND account_id = ? AND cookie_path = ?
            """
            self.db.execute(sql, (
                1 if is_valid else 0,
                datetime.now(),
                platform, account_id, cookie_path
            ))
            return True
        except Exception as e:
            logger.error(f"更新cookie状态失败: {str(e)}")
            return False
    
    def get_valid_cookies(self, platform: str, account_id: str) -> List[str]:
        """获取账号的有效cookie文件路径列表
        
        Args:
            platform: 平台名称
            account_id: 平台账号ID
            
        Returns:
            List[str]: cookie文件路径列表
        """
        sql = """
        SELECT cookie_path 
        FROM account_cookies
        WHERE platform = ? AND account_id = ? AND is_valid = 1
        ORDER BY last_check DESC
        """
        results = self.db.query_all(sql, (platform, account_id))
        return [result['cookie_path'] for result in results]
    
    def update_account(self, platform: str, account_id: str, 
                      updates: Dict[str, any]) -> bool:
        """更新账号信息
        
        Args:
            platform: 平台名称
            account_id: 平台账号ID
            updates: 需要更新的字段和值的字典
            
        Returns:
            bool: 是否更新成功
        """
        try:
            # 构建UPDATE语句
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            sql = f"""
            UPDATE social_media_accounts 
            SET {set_clause}, last_update = ?
            WHERE platform = ? AND account_id = ?
            """
            
            # 准备参数
            params = list(updates.values())
            params.extend([datetime.now(), platform, account_id])
            
            self.db.execute(sql, tuple(params))
            return True
        except Exception as e:
            logger.error(f"更新账号失败: {str(e)}")
            return False
    
    def get_account(self, platform: str, account_id: str) -> Optional[Dict]:
        """获取账号信息
        
        Args:
            platform: 平台名称
            account_id: 平台账号ID
            
        Returns:
            Dict: 账号信息字典，未找到返回None
        """
        sql = """
        SELECT a.*, GROUP_CONCAT(c.cookie_path) as cookie_paths
        FROM social_media_accounts a
        LEFT JOIN account_cookies c 
            ON a.platform = c.platform 
            AND a.account_id = c.account_id
            AND c.is_valid = 1
        WHERE a.platform = ? AND a.account_id = ?
        GROUP BY a.platform, a.account_id
        """
        result = self.db.query_one(sql, (platform, account_id))
        
        if result:
            if result.get('extra'):
                result['extra'] = json.loads(result['extra'])
            if result.get('cookie_paths'):
                result['cookie_paths'] = result['cookie_paths'].split(',')
            else:
                result['cookie_paths'] = []
        
        return result
    
    def get_all_accounts(self, platform: str = None) -> List[Dict]:
        """获取所有账号信息
        
        Args:
            platform: 平台名称，为None时获取所有平台
            
        Returns:
            List[Dict]: 账号信息列表
        """
        if platform:
            where_clause = "WHERE a.platform = ?"
            params = (platform,)
        else:
            where_clause = ""
            params = ()
            
        sql = f"""
        SELECT a.*, GROUP_CONCAT(c.cookie_path) as cookie_paths
        FROM social_media_accounts a
        LEFT JOIN account_cookies c 
            ON a.platform = c.platform 
            AND a.account_id = c.account_id
            AND c.is_valid = 1
        {where_clause}
        GROUP BY a.platform, a.account_id
        """
        
        results = self.db.query_all(sql, params)
        
        # 解析extra字段和cookie_paths
        for result in results:
            if result.get('extra'):
                result['extra'] = json.loads(result['extra'])
            if result.get('cookie_paths'):
                result['cookie_paths'] = result['cookie_paths'].split(',')
            else:
                result['cookie_paths'] = []
                
        return results
    
    def delete_account(self, platform: str, account_id: str) -> bool:
        """删除账号
        
        Args:
            platform: 平台名称
            account_id: 平台账号ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            sql = "DELETE FROM social_media_accounts WHERE platform = ? AND account_id = ?"
            self.db.execute(sql, (platform, account_id))
            return True
        except Exception as e:
            logger.error(f"删除账号失败: {str(e)}")
            return False
    
    def update_account_status(self, platform: str, account_id: str, 
                            status: int) -> bool:
        """更新账号状态
        
        Args:
            platform: 平台名称
            account_id: 平台账号ID
            status: 状态值(1:正常, 0:异常)
            
        Returns:
            bool: 是否更新成功
        """
        return self.update_account(platform, account_id, {'status': status})
    
    def get_platform_statistics(self, platform: str = None) -> Dict:
        """获取平台账号统计信息
        
        Args:
            platform: 平台名称，为None时统计所有平台
            
        Returns:
            Dict: 统计信息字典
        """
        if platform:
            where_clause = "WHERE platform = ?"
            params = (platform,)
        else:
            where_clause = ""
            params = ()
            
        sql = f"""
        SELECT 
            COUNT(*) as total_accounts,
            SUM(video_count) as total_videos,
            SUM(follower_count) as total_followers,
            SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) as active_accounts
        FROM social_media_accounts
        {where_clause}
        """
        
        return self.db.query_one(sql, params) or {}
    
    
    def get_account_verification_time(self, platform: str, nickname: str) -> Optional[datetime]:
        """获取账号的验证时间
        
        Args:
            platform: 平台名称
            nickname: 账号昵称
            
        Returns:
            Optional[datetime]: 验证时间，未找到返回None
        """
        sql = """
        SELECT ac.last_check  
        FROM account_cookies ac
        INNER JOIN social_media_accounts sma
            ON ac.platform = sma.platform 
            AND ac.account_id = sma.account_id
        WHERE ac.platform = ? AND sma.nickname = ?
        ORDER BY ac.last_check DESC
        LIMIT 1
        """
        result = self.db.query_one(sql, (platform, nickname))
        return result['last_check'] if result else None
    
    def update_account_info(self, platform: str, username: str, info: Dict[str, Any]) -> bool:
        """更新账号信息
        
        Args:
            platform: 平台名称
            username: 用户名
            info: 账号信息字典
            
        Returns:
            bool: 是否更新成功
        """
        try:
            # 获取 kwai_id，如果不存在则使用用户名
            account_id = info.get('kwai_id') or username
            
            # 构建更新数据
            updates = {
                'nickname': info.get('username', ''),
                'follower_count': info.get('followers', 0),
                'extra': json.dumps({
                    'kwai_id': info.get('kwai_id', ''),
                    'username': info.get('username', ''),
                    'following': info.get('following', 0),
                    'likes': info.get('likes', 0),
                    'description': info.get('description', ''),
                    'avatar': info.get('avatar', ''),
                    'updated_at': info.get('updated_at', datetime.now().isoformat())
                })
            }
            
            # 查找账号
            account = self.get_account(platform, account_id)
            if not account:
                # 如果账号不存在，创建新账号
                return self.add_account(
                    platform=platform,
                    account_id=account_id,
                    nickname=updates['nickname'],
                    follower_count=updates['follower_count'],
                    extra=json.loads(updates['extra'])
                )
            
            # 更新现有账号
            return self.update_account(platform, account_id, updates)
            
        except Exception as e:
            logger.error(f"更新账号信息失败: {str(e)}")
            return False

    def close(self):
        """关闭数据库连接"""
        self.db.close() 
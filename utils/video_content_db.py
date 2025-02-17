"""
视频内容数据库操作类
用于管理视频内容数据
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class VideoContentDB:
    def __init__(self, db_path: str = "data/social_media.db"):
        """初始化数据库连接"""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._connect()
        self._init_tables()
        
    def _connect(self):
        """连接数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
        except Exception as e:
            logger.error(f"连接数据库失败: {str(e)}")
            raise
            
    def _init_tables(self):
        """初始化数据表"""
        try:
            # 读取SQL文件
            sql_path = Path(__file__).parent / "video_content.sql"
            with open(sql_path, "r", encoding="utf-8") as f:
                sql = f.read()
            
            # 执行建表语句
            self.cursor.executescript(sql)
            self.conn.commit()
        except Exception as e:
            logger.error(f"初始化数据表失败: {str(e)}")
            raise
            
    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            
    def add_video_content(
        self,
        account_id: int,
        title: str,
        thumb_base64: Optional[str] = None,
        publish_time: Optional[str] = None,
        status: Optional[str] = None,
        plays: int = 0,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
        tags: Optional[List[str]] = None,
        mentions: Optional[List[str]] = None
    ) -> int:
        """
        添加视频内容
        
        Args:
            account_id: 账号ID
            title: 视频标题
            thumb_base64: 封面图片base64数据
            publish_time: 发布时间
            status: 视频状态
            plays: 播放数
            likes: 点赞数
            comments: 评论数
            shares: 分享数
            tags: 标签列表
            mentions: 提及用户列表
            
        Returns:
            int: 视频内容ID
        """
        try:
            # 将标签和提及用户列表转换为JSON字符串
            tags_json = json.dumps(tags or [], ensure_ascii=False)
            mentions_json = json.dumps(mentions or [], ensure_ascii=False)
            
            # 插入视频内容
            self.cursor.execute(
                """
                INSERT INTO video_contents (
                    account_id, title, thumb_base64, publish_time,
                    status, plays, likes, comments, shares, tags, mentions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (account_id, title, thumb_base64, publish_time,
                 status, plays, likes, comments, shares, tags_json, mentions_json)
            )
            
            video_id = self.cursor.lastrowid
            self.conn.commit()
            return video_id
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"添加视频内容失败: {str(e)}")
            raise
            
    def get_video_content(self, video_id: int) -> Optional[Dict[str, Any]]:
        """
        获取视频内容
        
        Args:
            video_id: 视频ID
            
        Returns:
            Dict: 视频内容信息
        """
        try:
            # 获取视频基本信息
            self.cursor.execute(
                """
                SELECT v.*, a.platform, a.nickname
                FROM video_contents v
                JOIN social_media_accounts a ON v.account_id = a.id
                WHERE v.id = ?
                """,
                (video_id,)
            )
            row = self.cursor.fetchone()
            if not row:
                return None
                
            # 解析JSON数据
            tags = json.loads(row[10] or '[]')  # tags列
            mentions = json.loads(row[11] or '[]')  # mentions列
                
            # 构建返回数据
            return {
                "id": row[0],
                "account_id": row[1],
                "title": row[2],
                "thumb_base64": row[3],
                "publish_time": row[4],
                "status": row[5],
                "stats": {
                    "plays": row[6],
                    "likes": row[7],
                    "comments": row[8],
                    "shares": row[9]
                },
                "tags": tags,
                "mentions": mentions,
                "created_at": row[12],
                "updated_at": row[13],
                "platform": row[14],
                "nickname": row[15]
            }
            
        except Exception as e:
            logger.error(f"获取视频内容失败: {str(e)}")
            raise 

    def get_video_count(self, account_id: int) -> int:
        """
        获取指定账号的视频数量
        
        Args:
            account_id: 账号ID
            
        Returns:
            int: 视频数量
        """
        try:
            self.cursor.execute(
                "SELECT COUNT(*) FROM video_contents WHERE account_id = ?",
                (account_id,)
            )
            return self.cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"获取视频数量失败: {str(e)}")
            return 0 
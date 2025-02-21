"""
视频验证模块
提供视频文件、标题、标签等验证功能
"""

import os
from datetime import datetime, timedelta
from typing import List
import re

class VideoValidator:
    """视频验证类"""
    
    @staticmethod
    def validate_video_file(file_path: str) -> bool:
        """
        验证视频文件
        Args:
            file_path: 视频文件路径
        Returns:
            bool: 是否验证通过
        """
        try:
            # 检查文件是否存在且可读
            if not os.path.exists(file_path):
                return False
            if not os.access(file_path, os.R_OK):
                return False
                
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return False
            
            # 视频文件大小限制：10MB - 4GB
            min_size = 10 * 1024 * 1024  # 10MB
            max_size = 4 * 1024 * 1024 * 1024  # 4GB
            if not (min_size <= file_size <= max_size):
                return False
            
            return True
            
        except Exception:
            return False

    @staticmethod
    def validate_thumbnail(file_path: str) -> bool:
        """
        验证封面图片
        Args:
            file_path: 图片文件路径
        Returns:
            bool: 是否验证通过
        """
        try:
            # 检查文件是否存在且可读
            if not os.path.exists(file_path):
                return False
            if not os.access(file_path, os.R_OK):
                return False
                
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return False
            
            # 图片文件大小限制：1KB - 5MB
            min_size = 1 * 1024  # 1KB
            max_size = 5 * 1024 * 1024  # 5MB
            if not (min_size <= file_size <= max_size):
                return False
            
            return True
            
        except Exception:
            return False

    @staticmethod
    def validate_title(title: str) -> bool:
        """
        验证视频标题
        Args:
            title: 视频标题
        Returns:
            bool: 是否验证通过
        """
        try:
            # 标题不能为空
            if not title or not title.strip():
                return False
            
            # 标题长度限制：2-100个字符
            title_length = len(title.strip())
            if not (2 <= title_length <= 100):
                return False
            
            # 标题不能包含特殊字符
            pattern = r'^[a-zA-Z0-9\u4e00-\u9fa5\s,.!?，。！？、:：()（）【】\[\]]+$'
            if not re.match(pattern, title):
                return False
            
            return True
            
        except Exception:
            return False

    @staticmethod
    def validate_tags(tags: List[str]) -> bool:
        """
        验证视频标签
        Args:
            tags: 标签列表
        Returns:
            bool: 是否验证通过
        """
        try:
            # 标签列表不能为空
            if not tags:
                return False
            
            # 标签数量限制：1-20个
            if not (1 <= len(tags) <= 20):
                return False
            
            # 验证每个标签
            for tag in tags:
                # 标签不能为空
                if not tag or not tag.strip():
                    return False
                
                # 标签长度限制：1-20个字符
                tag_length = len(tag.strip())
                if not (1 <= tag_length <= 20):
                    return False
                
                # 标签只能包含中文、英文、数字
                pattern = r'^[a-zA-Z0-9\u4e00-\u9fa5]+$'
                if not re.match(pattern, tag):
                    return False
            
            return True
            
        except Exception:
            return False

    @staticmethod
    def validate_publish_date(publish_date: datetime) -> bool:
        """
        验证发布时间
        Args:
            publish_date: 发布时间
        Returns:
            bool: 是否验证通过
        """
        try:
            # 发布时间不能为空
            if not publish_date:
                return False
            
            # 发布时间不能早于当前时间
            if publish_date < datetime.now():
                return False
            
            # 发布时间不能超过30天
            max_days = 30
            max_date = datetime.now().replace(
                hour=23,
                minute=59,
                second=59,
                microsecond=999999
            ) + timedelta(days=max_days)
            
            if publish_date > max_date:
                return False
            
            return True
            
        except Exception:
            return False 
        
    @staticmethod
    def validate_mentions(mentions: List[str]) -> bool:
        """
        验证@提及
        Args:
            mentions: @提及列表
        """
        try:
            # 提及列表不能为空
            if not mentions:
                return False
            
            # 提及数量限制：1-5个
            if not (1 <= len(mentions) <= 5):
                return False
            
            # 验证每个提及
            for mention in mentions:
                # 提及不能为空
                if not mention or not mention.strip():
                    return False
                
                # 提及长度限制：1-10个字符
                mention_length = len(mention.strip())
                if not (1 <= mention_length <= 10): 
                    return False
            
            return True
            
        except Exception:
            return False
            

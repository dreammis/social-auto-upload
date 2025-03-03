"""
抖音上传参数验证模块
提供视频信息和上传参数的验证功能
"""

import os
from datetime import datetime
from typing import List, Optional

class VideoValidator:
    """视频参数验证器"""
    
    @staticmethod
    def validate_video_file(file_path: str) -> bool:
        """
        验证视频文件是否存在且格式正确
        Args:
            file_path: 视频文件路径
        Returns:
            bool: 验证是否通过
        """
        if not os.path.exists(file_path):
            return False
        
        valid_extensions = ['.mp4', '.mov', '.avi']
        file_ext = os.path.splitext(file_path)[1].lower()
        return file_ext in valid_extensions

    @staticmethod
    def validate_title(title: str) -> bool:
        """
        验证视频标题是否符合要求
        Args:
            title: 视频标题
        Returns:
            bool: 验证是否通过
        """
        if not title or len(title) > 30:
            return False
        return True

    @staticmethod
    def validate_tags(tags: List[str]) -> bool:
        """
        验证标签是否符合要求
        Args:
            tags: 标签列表
        Returns:
            bool: 验证是否通过
        """
        if not tags:
            return False
        
        for tag in tags:
            if len(tag) > 20 or not tag.strip():
                return False
        return True

    @staticmethod
    def validate_publish_date(publish_date: datetime) -> bool:
        """
        验证发布时间是否符合要求
        Args:
            publish_date: 发布时间
        Returns:
            bool: 验证是否通过
        """
        if not publish_date:
            return False
        
        now = datetime.now()
        if publish_date < now:
            return False
        return True

    @staticmethod
    def validate_thumbnail(thumbnail_path: Optional[str]) -> bool:
        """
        验证封面图片是否符合要求
        Args:
            thumbnail_path: 封面图片路径
        Returns:
            bool: 验证是否通过
        """
        if not thumbnail_path:
            return True
        
        if not os.path.exists(thumbnail_path):
            return False
            
        valid_extensions = ['.jpg', '.jpeg', '.png']
        file_ext = os.path.splitext(thumbnail_path)[1].lower()
        return file_ext in valid_extensions

    @classmethod
    def validate_all(cls,
                    title: str,
                    file_path: str,
                    tags: List[str],
                    publish_date: datetime,
                    thumbnail_path: Optional[str] = None) -> tuple[bool, str]:
        """
        验证所有上传参数
        Args:
            title: 视频标题
            file_path: 视频文件路径
            tags: 标签列表
            publish_date: 发布时间
            thumbnail_path: 封面图片路径
        Returns:
            tuple[bool, str]: (验证是否通过, 错误信息)
        """
        if not cls.validate_video_file(file_path):
            return False, "视频文件不存在或格式不正确"
            
        if not cls.validate_title(title):
            return False, "视频标题不符合要求"
            
        if not cls.validate_tags(tags):
            return False, "视频标签不符合要求"
            
        if not cls.validate_publish_date(publish_date):
            return False, "发布时间不符合要求"
            
        if not cls.validate_thumbnail(thumbnail_path):
            return False, "封面图片不存在或格式不正确"
            
        return True, "" 
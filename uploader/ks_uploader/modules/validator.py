# -*- coding: utf-8 -*-
from typing import List, Dict, Any
import os
from datetime import datetime

class KSDataValidator:
    def __init__(self):
        self.title_max_length = 100
        self.max_tags = 3
        self.allowed_video_extensions = ['.mp4', '.mov', '.avi']
        self.max_video_size = 4 * 1024 * 1024 * 1024  # 4GB

    def validate_video_params(self, title: str, tags: List[str], 
                            file_path: str, publish_date: datetime = None) -> Dict[str, Any]:
        """
        验证视频参数
        Returns:
            Dict[str, Any]: {'valid': bool, 'errors': List[str]}
        """
        errors = []

        # 验证标题
        if not title:
            errors.append("标题不能为空")
        elif len(title) > self.title_max_length:
            errors.append(f"标题长度不能超过{self.title_max_length}个字符")

        # 验证标签
        if not tags:
            errors.append("至少需要一个标签")
        elif len(tags) > self.max_tags:
            errors.append(f"标签数量不能超过{self.max_tags}个")

        # 验证文件
        if not os.path.exists(file_path):
            errors.append("视频文件不存在")
        else:
            # 验证文件扩展名
            _, ext = os.path.splitext(file_path)
            if ext.lower() not in self.allowed_video_extensions:
                errors.append(f"不支持的视频格式: {ext}")

            # 验证文件大小
            file_size = os.path.getsize(file_path)
            if file_size > self.max_video_size:
                errors.append(f"视频文件大小不能超过4GB")

        # 验证发布时间
        if publish_date and publish_date < datetime.now():
            errors.append("定时发布时间不能早于当前时间")

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    def validate_upload_result(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证上传结果
        Returns:
            Dict[str, Any]: {'valid': bool, 'errors': List[str]}
        """
        errors = []

        if not response.get('success'):
            errors.append("上传失败")
            if 'error' in response:
                errors.append(f"错误信息: {response['error']}")

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

validator = KSDataValidator() 
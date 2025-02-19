"""
抖音上传器模块
提供抖音视频上传、账号管理等功能
"""

from .modules.video import DouYinVideo
from .modules.account import account_manager
from .utils.user_info import UserInfoHelper

__version__ = "1.0.0"
__author__ = "向阳很有米"

__all__ = [
    "DouYinVideo",
    "account_manager",
    "UserInfoHelper"
]

from pathlib import Path
from conf import BASE_DIR

# 创建必要的目录
Path(BASE_DIR / "cookies" / "douyin_uploader").mkdir(exist_ok=True)
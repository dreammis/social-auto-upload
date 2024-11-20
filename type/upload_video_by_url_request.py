from pydantic import BaseModel
from typing import List, Optional

class Platforms(BaseModel):
    """下面就是每个平台，平台下传递包含id的数组"""
    """bilibili的id"""
    bilibili: Optional[List[str]]

    # def __init__(self, bilibili: Optional[List[str]]) -> None:
    #     self.bilibili = bilibili


class UploadVideoByUrlRequest(BaseModel):
    """UploadVideoByUrlRequest"""
    """简介"""
    description: str
    """下面就是每个平台，平台下传递包含id的数组"""
    platforms: Platforms
    """视频tag"""
    tags: List[str]
    """视频分区"""
    tid: str
    """上传的时间"""
    timestamp: Optional[str]
    """视频标题"""
    title: str
    """视频文件直链"""
    video_url: str
    """视频文件名"""
    video_file_name: str

    # def __init__(self, description: str, platform: Platform, tags: List[str], tid: str, timestamps: Optional[str], title: str, video_file_name: str, video_url: str) -> None:
    #     self.description = description
    #     self.platform = platform
    #     self.tags = tags
    #     self.tid = tid
    #     self.timestamps = timestamps
    #     self.title = title
    #     self.video_file_name = video_file_name
    #     self.video_url = video_url
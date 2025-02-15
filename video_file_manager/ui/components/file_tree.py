"""
文件树组件
"""
import gradio as gr
from pathlib import Path
from typing import Dict, Callable, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def create_file_tree(
    directory_data: Dict,
    on_select: Optional[Callable] = None
) -> gr.Dataframe:
    """
    创建文件列表组件
    
    Args:
        directory_data: 目录数据（未使用）
        on_select: 选择回调函数
        
    Returns:
        gr.Dataframe: 文件列表组件
    """
    from video_file_manager.config import settings
    from video_file_manager.core.file_manager import FileManager
    
    # 扫描视频文件
    file_manager = FileManager()
    videos = file_manager.scan_videos()
    
    # 准备表格数据
    headers = ["名称", "相对路径", "大小", "修改时间"]
    rows = [
        [
            video["name"],
            video["relative_path"],  # 使用从 file_manager 获取的相对路径
            video["size"],
            video["modified"].strftime("%Y-%m-%d %H:%M:%S")
        ]
        for video in videos
        if video  # 只处理有效的文件信息
    ]
    
    logger.debug(f"表格数据: {rows}")
    
    return gr.Dataframe(
        headers=headers,
        datatype=["str", "str", "str", "str"],
        value=rows,
        interactive=False,  # 设置为只读
        wrap=True,  # 允许文本换行
        row_count=len(rows)  # 显示所有行并启用选择功能
    )

def _format_size(size: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def _format_time(timestamp: float) -> str:
    """格式化时间戳"""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S") 
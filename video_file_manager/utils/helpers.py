"""
工具函数
"""
from pathlib import Path
from typing import Union
import logging

logger = logging.getLogger(__name__)

def format_size(size_in_bytes: Union[int, float]) -> str:
    """
    格式化文件大小
    
    Args:
        size_in_bytes: 文件大小（字节）
        
    Returns:
        str: 格式化后的大小
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.1f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.1f} TB"

def setup_logging(log_file: Path = None, level: str = "INFO"):
    """
    设置日志
    
    Args:
        log_file: 日志文件路径
        level: 日志级别
    """
    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 设置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 如果指定了日志文件，添加文件处理器
    if log_file:
        try:
            # 确保日志目录存在
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            logger.error(f"设置日志文件失败: {str(e)}")

def is_video_file(file_path: Path) -> bool:
    """
    检查是否是视频文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否是视频文件
    """
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv'}
    return file_path.is_file() and file_path.suffix.lower() in video_extensions 
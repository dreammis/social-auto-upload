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

def setup_logging(
    log_file: Union[str, Path],
    level: str = "INFO",
    console_level: str = "INFO",
    format_str: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
) -> None:
    """
    配置日志
    
    Args:
        log_file: 日志文件路径
        level: 文件日志级别
        console_level: 控制台日志级别
        format_str: 日志格式
    """
    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 设置为最低级别，让处理器决定要显示的级别
    
    # 清除现有的处理器
    root_logger.handlers.clear()
    
    # 创建格式化器
    formatter = logging.Formatter(format_str)
    
    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(getattr(logging, level.upper()))
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, console_level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 设置第三方库的日志级别
    logging.getLogger("gradio").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)

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
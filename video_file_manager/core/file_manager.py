"""
文件管理核心类
"""
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import logging

from video_file_manager.config import settings

logger = logging.getLogger(__name__)

class FileManager:
    """文件管理器"""
    
    VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv'}
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        初始化文件管理器
        
        Args:
            base_dir: 基础目录路径，如果不指定则使用配置中的 VIDEO_DIR
        """
        self.base_dir = Path(base_dir) if base_dir else settings.VIDEO_DIR
        if not self.base_dir.exists():
            raise ValueError(f"目录不存在: {self.base_dir}")
    
    def scan_videos(self) -> List[Dict]:
        """
        扫描所有视频文件
        
        Returns:
            List[Dict]: 视频文件信息列表
        """
        videos = []
        try:
            logger.debug(f"开始扫描目录: {self.base_dir.resolve()}")
            # 递归扫描目录
            for file_path in self.base_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in self.VIDEO_EXTENSIONS:
                    try:
                        logger.debug(f"处理文件: {file_path}")
                        file_info = self.get_file_info(file_path)
                        if file_info:  # 只添加有效的文件信息
                            logger.debug(f"文件信息: {file_info}")
                            videos.append(file_info)
                    except Exception as e:
                        logger.error(f"处理文件 {file_path} 失败: {str(e)}")
                        continue
            
            # 按修改时间排序
            videos.sort(key=lambda x: x.get('modified', datetime.min), reverse=True)
            logger.info(f"找到 {len(videos)} 个视频文件")
            return videos
        except Exception as e:
            logger.error(f"扫描视频目录失败: {str(e)}")
            return []
    
    def get_file_info(self, file_path: Path) -> Dict:
        """
        获取文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 文件信息
        """
        try:
            stat = file_path.stat()
            # 确保路径都是绝对路径后再计算相对路径
            abs_base_dir = self.base_dir.resolve()
            abs_file_path = file_path.resolve()
            relative_path = abs_file_path.relative_to(abs_base_dir)
            
            logger.debug(f"基础目录: {abs_base_dir}")
            logger.debug(f"文件路径: {abs_file_path}")
            logger.debug(f"相对路径: {relative_path}")
            
            return {
                "name": file_path.name,
                "path": str(abs_file_path),  # 使用绝对路径
                "relative_path": str(relative_path),  # 保存相对路径
                "size": self._format_size(stat.st_size),
                "created": datetime.fromtimestamp(stat.st_ctime),
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "type": file_path.suffix.lower()[1:]
            }
        except Exception as e:
            logger.error(f"获取文件信息失败: {str(e)}")
            return {}
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB" 
"""
文件管理核心类
"""
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FileManager:
    """文件管理器"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        初始化文件管理器
        
        Args:
            base_dir: 基础目录路径，如果不指定则使用当前目录
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        if not self.base_dir.exists():
            raise ValueError(f"目录不存在: {self.base_dir}")
    
    def build_directory_tree(self) -> dict:
        """
        构建目录树结构
        
        Returns:
            dict: 目录树结构
        """
        def build_node(path: Path) -> dict:
            if path.is_file():
                # 只返回视频文件
                if path.suffix.lower() in {'.mp4', '.mov', '.avi', '.mkv'}:
                    return str(path)
                return None
            
            node = {}
            try:
                # 获取子目录和文件
                items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
                for item in items:
                    if item.is_dir():
                        sub_node = build_node(item)
                        if sub_node:  # 只添加非空目录
                            node[item.name] = sub_node
                    else:
                        # 对于文件，检查是否是视频
                        if item.suffix.lower() in {'.mp4', '.mov', '.avi', '.mkv'}:
                            node[item.name] = str(item)
                
                return node if node else None
            except Exception as e:
                logger.error(f"构建目录树失败: {str(e)}")
                return None
        
        try:
            tree = build_node(self.base_dir)
            return tree if tree else {}
        except Exception as e:
            logger.error(f"构建根目录树失败: {str(e)}")
            return {}
    
    def scan_videos(self) -> List[Path]:
        """
        扫描视频文件
        
        Returns:
            List[Path]: 视频文件路径列表
        """
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv'}
        videos = []
        
        try:
            # 递归扫描所有子目录
            for video_file in self.base_dir.rglob('*'):
                if video_file.is_file() and video_file.suffix.lower() in video_extensions:
                    videos.append(video_file)
            
            # 按修改时间排序
            videos.sort(key=lambda x: x.stat().st_mtime, reverse=True)
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
            return {
                "name": file_path.name,
                "path": str(file_path),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime),
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "type": file_path.suffix.lower()[1:],
            }
        except Exception as e:
            logger.error(f"获取文件信息失败: {str(e)}")
            return {} 
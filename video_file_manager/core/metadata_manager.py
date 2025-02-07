"""
元数据管理类
"""
from pathlib import Path
from typing import Dict, Optional
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MetadataManager:
    """元数据管理器"""
    
    def __init__(self):
        """初始化元数据管理器"""
        pass
    
    def read_metadata(self, video_dir: Path) -> Optional[Dict]:
        """
        读取视频元数据
        
        Args:
            video_dir: 视频目录路径
            
        Returns:
            Optional[Dict]: 元数据信息
        """
        info_path = video_dir / "info.json"
        if not info_path.exists():
            return self._create_default_metadata(video_dir)
            
        try:
            with info_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取元数据失败: {str(e)}")
            return self._create_default_metadata(video_dir)
    
    def write_metadata(self, video_dir: Path, metadata: Dict) -> bool:
        """
        写入视频元数据
        
        Args:
            video_dir: 视频目录路径
            metadata: 元数据信息
            
        Returns:
            bool: 是否写入成功
        """
        info_path = video_dir / "info.json"
        try:
            with info_path.open('w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logger.error(f"写入元数据失败: {str(e)}")
            return False
    
    def _create_default_metadata(self, video_dir: Path) -> Dict:
        """
        创建默认元数据
        
        Args:
            video_dir: 视频目录路径
            
        Returns:
            Dict: 默认元数据
        """
        video_files = list(video_dir.glob("*.mp4"))
        if not video_files:
            return {}
            
        video_file = video_files[0]
        return {
            "video_info": {
                "file_name": video_file.name,
                "create_time": datetime.fromtimestamp(video_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "size": video_file.stat().st_size
            },
            "platforms": {}
        } 
# -*- coding: utf-8 -*-
import json
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

from utils.log import logger

class CookieHelper:
    """Cookie 工具类"""
    
    @staticmethod
    def backup_cookie_file(cookie_path: str) -> Optional[str]:
        """备份 Cookie 文件
        
        Args:
            cookie_path: Cookie 文件路径
            
        Returns:
            Optional[str]: 备份文件路径，失败返回 None
        """
        try:
            cookie_file = Path(cookie_path)
            if not cookie_file.exists():
                return None
                
            backup_path = f"{cookie_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            shutil.copy2(cookie_path, backup_path)
            logger.info(f"已创建Cookie文件备份: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"备份Cookie文件失败: {str(e)}")
            return None
    
    @staticmethod
    def validate_cookie_file(cookie_path: str, max_size: int = 100 * 1024) -> bool:
        """验证 Cookie 文件
        
        Args:
            cookie_path: Cookie 文件路径
            max_size: 最大文件大小（字节）
            
        Returns:
            bool: 文件是否有效
        """
        try:
            cookie_file = Path(cookie_path)
            
            # 检查文件是否存在
            if not cookie_file.exists():
                logger.error(f"Cookie文件不存在: {cookie_path}")
                return False
            
            # 检查文件大小
            file_size = cookie_file.stat().st_size
            if file_size > max_size:
                logger.error(f"Cookie文件过大: {file_size} bytes")
                return False
            
            # 检查是否为空
            if file_size == 0:
                logger.error("Cookie文件为空")
                return False
            
            # 验证JSON格式
            with open(cookie_file, 'r', encoding='utf-8') as f:
                json.load(f)
            
            return True
        except json.JSONDecodeError:
            logger.error(f"Cookie文件不是有效的JSON格式: {cookie_path}")
            return False
        except Exception as e:
            logger.error(f"验证Cookie文件失败: {str(e)}")
            return False 
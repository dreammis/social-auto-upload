# -*- coding: utf-8 -*-
import subprocess
from typing import Optional
from pathlib import Path

from utils.log import logger

class PlaywrightHelper:
    """Playwright 工具类"""
    
    @staticmethod
    def install_browser(browser_type: str = "chromium") -> bool:
        """安装 Playwright 浏览器
        
        Args:
            browser_type: 浏览器类型，默认为 chromium
            
        Returns:
            bool: 是否安装成功
        """
        try:
            logger.info(f"正在安装 Playwright {browser_type} 浏览器...")
            subprocess.run(["playwright", "install", browser_type], check=True)
            logger.success(f"Playwright {browser_type} 浏览器安装成功！")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"安装失败: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"安装过程发生异常: {str(e)}")
            return False 
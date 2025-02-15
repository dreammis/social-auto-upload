"""
启动视频文件管理器
"""
import os
from pathlib import Path
import sys
import logging

# 添加项目根目录到 Python 路径
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from video_file_manager.ui.app import create_app
from video_file_manager.utils.helpers import setup_logging
from video_file_manager.config import settings

def main():
    """主函数"""
    # 设置日志
    log_dir = settings.LOG_DIR
    log_dir.mkdir(exist_ok=True)
    
    # 配置日志
    setup_logging(
        log_file=log_dir / "app.log",
        level="DEBUG",  # 强制使用 DEBUG 级别
        console_level="DEBUG"  # 控制台也输出 DEBUG 信息
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"视频目录: {settings.VIDEO_DIR}")
    logger.info(f"日志目录: {settings.LOG_DIR}")
    
    # 创建并启动应用
    app = create_app()
    app.launch(
        server_name=settings.HOST,
        server_port=settings.PORT,
        share=False,            # 不创建公共链接
        show_api=False,         # 不显示API文档
        show_error=True,        # 显示错误信息
        debug=True             # 启用调试模式
    )

if __name__ == "__main__":
    main() 
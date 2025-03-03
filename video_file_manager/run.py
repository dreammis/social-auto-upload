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
    
    # 导入demo实例
    from video_file_manager.ui.app import demo
    
    # 设置允许访问的路径
    allowed_paths = [
        "F:/向阳也有米/24版本/12月",  # 视频根目录
        "F:/向阳也有米/24版本/12月/1125-13-回家1",  # 子目录
        str(root_dir),  # 项目根目录
        str(settings.VIDEO_DIR),  # 配置的视频目录
    ]
    
    # 使用标准配置启动
    demo.queue().launch(
        server_name=settings.HOST,
        server_port=settings.PORT,
        share=False,            # 不创建公共链接
        show_api=False,         # 不显示API文档
        show_error=True,        # 显示错误信息
        debug=True,             # 启用调试模式
        prevent_thread_lock=True,  # 防止线程锁
        ssl_verify=False,       # 禁用SSL验证
        allowed_paths=allowed_paths,  # 允许访问的路径列表
        _frontend=False         # 禁用前端自动打开
    )

if __name__ == "__main__":
    main() 
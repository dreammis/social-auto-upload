"""
启动视频文件管理器
"""
import os
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
root_dir = Path(__file__).parent
sys.path.append(str(root_dir))

from ui.app import create_app
from utils.helpers import setup_logging

def main():
    """主函数"""
    # 设置日志
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    setup_logging(
        log_file=log_dir / "app.log",
        level="DEBUG" if os.getenv("DEBUG") else "INFO"
    )
    
    # 创建并启动应用
    app = create_app()
    app.launch(
        server_name="0.0.0.0",  # 允许外部访问
        server_port=7860,       # 默认端口
        share=False,            # 不创建公共链接
        show_api=False,         # 不显示API文档
        show_error=True,        # 显示错误信息
    )

if __name__ == "__main__":
    main() 
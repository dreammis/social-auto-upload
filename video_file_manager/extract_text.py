"""
提取视频文件中的文字信息
"""
import sys
from pathlib import Path
import logging

# 添加项目根目录到 Python 路径
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from video_file_manager.utils.helpers import extract_text_from_video, setup_logging

if __name__ == "__main__":
    # 设置日志
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    setup_logging(
        log_file=log_dir / "extract_text.log",
        level="DEBUG",
        console_level="DEBUG"
    )
    
    logger = logging.getLogger(__name__)
    
    video_path = "F:/向阳也有米/24版本/12月/112914-7-定义30/1014-7-定义.mp4"
    try:
        logger.info(f"开始处理视频: {video_path}")
        text = extract_text_from_video(video_path)
        logger.info("提取的文字信息:")
        logger.info(text)
        print("提取的文字信息:")
        print(text)
    except Exception as e:
        logger.error(f"提取失败: {str(e)}")
        print(f"提取失败: {str(e)}") 
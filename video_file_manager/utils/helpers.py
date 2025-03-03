"""
工具函数
"""
from pathlib import Path
from typing import Union
import logging
import whisper
import subprocess
import librosa
import numpy as np
from opencc import OpenCC  # 添加OpenCC导入

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

def extract_text_from_video(video_path: str) -> str:
    """
    从视频中提取文本
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        str: 提取的文本内容（带时间戳的分段文本）
    """
    # 初始化繁体转简体转换器
    converter = OpenCC('t2s')  # 繁体到简体
    
    # 确保视频文件存在
    video_file = Path(video_path).resolve()  # 转换为绝对路径
    logger.info(f"检查视频文件: {video_file}")
    if not video_file.is_file():
        raise FileNotFoundError(f"视频文件不存在: {video_file}")
    logger.info(f"视频文件存在: {video_file}")

    # 获取项目根目录
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    logger.info(f"当前文件: {current_file}")
    logger.info(f"项目根目录: {project_root}")
    
    # 提取音频
    audio_path = video_file.parent / f"{video_file.stem}_audio.wav"  # 使用视频所在目录
    audio_path = audio_path.resolve()  # 转换为绝对路径
    # 设置文本输出路径
    text_path = video_file.parent / f"{video_file.stem}_transcript.txt"
    text_path = text_path.resolve()
    
    ffmpeg_path = project_root / "video_file_manager" / "ffmpeg" / "bin" / "ffmpeg.exe"
    ffmpeg_path = ffmpeg_path.resolve()  # 转换为绝对路径
    
    # 检查并创建音频文件的父目录
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"音频输出路径: {audio_path}")
    logger.info(f"文本输出路径: {text_path}")
    logger.info(f"音频目录是否存在: {audio_path.parent.exists()}")
    logger.info(f"使用的FFmpeg路径: {ffmpeg_path}")
    logger.info(f"FFmpeg是否存在: {ffmpeg_path.is_file()}")
    
    if not ffmpeg_path.is_file():
        raise FileNotFoundError(f"找不到FFmpeg: {ffmpeg_path}")
    
    segments_text = []  # 存储带时间戳的分段文本
    
    try:
        # 检查音频文件是否已存在
        if audio_path.is_file():
            audio_size = audio_path.stat().st_size
            if audio_size > 0:
                logger.info(f"音频文件已存在且大小正常({audio_size}字节)，跳过转换步骤")
            else:
                logger.warning(f"已存在的音频文件大小为0，将重新转换")
                audio_path.unlink()  # 删除大小为0的文件
        
        # 如果音频文件不存在或已被删除，则执行转换
        if not audio_path.is_file():
            # 执行FFmpeg命令
            logger.info("开始执行FFmpeg命令...")
            result = subprocess.run(
                [str(ffmpeg_path), '-i', str(video_file), str(audio_path)], 
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("音频提取完成")
            logger.debug(f"FFmpeg输出: {result.stdout}")
            if result.stderr:
                logger.debug(f"FFmpeg错误输出: {result.stderr}")
            
            # 确认音频文件存在
            logger.info(f"检查生成的音频文件: {audio_path}")
            if not audio_path.is_file():
                raise FileNotFoundError(f"音频文件未生成: {audio_path}")
            logger.info(f"音频文件生成成功，大小: {audio_path.stat().st_size} 字节")
            
        # 加载 Whisper 模型
        logger.info("开始加载Whisper模型")
        model = whisper.load_model("base", device="cpu")  # 显式指定使用CPU
        logger.info("Whisper模型加载完成")
        
        # 转录音频
        logger.info(f"开始转录音频: {audio_path}")
        # 再次确认音频文件存在
        if not audio_path.is_file():
            raise FileNotFoundError(f"转录前音频文件丢失: {audio_path}")
        
        # 检查音频文件大小
        audio_size = audio_path.stat().st_size
        logger.info(f"转录前音频文件大小: {audio_size} 字节")
        if audio_size == 0:
            raise ValueError(f"音频文件大小为0: {audio_path}")
            
        # 使用librosa加载音频文件
        logger.info("使用librosa加载音频文件...")
        try:
            audio_array, sampling_rate = librosa.load(str(audio_path), sr=16000)
            logger.info(f"音频加载成功: 采样率={sampling_rate}Hz, 长度={len(audio_array)}采样点")
            
            # 使用加载的音频数据进行转录
            logger.info("开始转录音频数据...")
            result = model.transcribe(
                audio_array,  # 直接使用音频数据
                fp16=False,
                language="zh"
            )
            logger.info("转录完成")
            
            # 保存带时间戳的文本
            segments = result["segments"]
            
            logger.info("保存转录文本...")
            with open(text_path, "w", encoding="utf-8") as f:
                # 只写入带时间戳的分段文本
                for segment in segments:
                    start = segment["start"]
                    end = segment["end"]
                    text = segment["text"]
                    # 将文本转换为简体中文
                    simplified_text = converter.convert(text)
                    segment_line = f"[{start:.2f}s -> {end:.2f}s] {simplified_text}"
                    segments_text.append(segment_line)
                    f.write(segment_line + "\n")
            
            logger.info(f"转录文本已保存到: {text_path}")
            # 返回带时间戳的分段文本
            return "\n".join(segments_text)
            
        except Exception as e:
            logger.error(f"音频加载失败: {e}")
            raise
            
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg处理失败: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"处理过程中出错: {str(e)}")
        logger.error(f"错误类型: {type(e)}")
        logger.error(f"错误详情: {str(e)}")
        raise
    finally:
        # 只有在成功获取文本后才清理临时文件
        if segments_text:
            try:
                if audio_path.exists():
                    audio_path.unlink()
                    logger.info("清理临时音频文件")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {str(e)}")
        else:
            logger.info("保留临时音频文件以供调试") 
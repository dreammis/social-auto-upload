"""
配置文件
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """应用配置"""
    # 基础配置
    DEBUG: bool = False
    
    # 路径配置
    VIDEO_DIR: Path = Path("videos")
    LOG_DIR: Path = Path("logs")
    
    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 7860
    
    # 视频文件类型
    VIDEO_EXTENSIONS: set = {'.mp4', '.mov', '.avi', '.mkv'}
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# 创建全局设置实例
settings = Settings() 
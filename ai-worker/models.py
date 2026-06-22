"""
SQLAlchemy models for the AI Worker Trend Engine.
Matches the eventual TypeORM entity in NestJS for shared DB access.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


class TrendPlatform(str, enum.Enum):
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"


class Trend(Base):
    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(
        SAEnum(TrendPlatform, name="trend_platform_enum", create_type=False),
        nullable=False,
    )
    keyword = Column(String(200), nullable=False)
    volume = Column(Float, nullable=True, comment="Trend volume / search count")
    extracted_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="When data was scraped"
    )

    def __repr__(self):
        return f"<Trend(platform={self.platform}, keyword={self.keyword}, volume={self.volume})>"


class VideoJobStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING_SCRIPT = "generating_script"
    GENERATING_VOICE = "generating_voice"
    RENDERING = "rendering"
    DONE = "done"
    FAILED = "failed"


class VideoJob(Base):
    __tablename__ = "video_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), unique=True, nullable=False, index=True)
    topic = Column(String(500), nullable=False)
    status = Column(
        SAEnum(VideoJobStatus, name="video_job_status_enum", create_type=False),
        nullable=False,
        default=VideoJobStatus.PENDING,
    )
    script = Column(Text, nullable=True, comment="Generated narration script")
    audio_url = Column(String(500), nullable=True, comment="Path to TTS audio file")
    video_url = Column(String(500), nullable=True, comment="Path to final rendered video")
    error_log = Column(Text, nullable=True, comment="Error details if status=failed")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow,
    )

    def __repr__(self):
        return f"<VideoJob(job_id={self.job_id}, status={self.status})>"

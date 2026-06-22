"""
SQLAlchemy models for the Upload Engine (Phase 5).
Connects to the same PostgreSQL used by NestJS + AI Worker.
"""

import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase
import uuid


class UploadBase(DeclarativeBase):
    pass


class UploadJobStatus(str, enum.Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    SUCCESS = "success"
    FAILED = "failed"


class UploadJob(UploadBase):
    """Tracks a single video upload to a social platform."""

    __tablename__ = "upload_jobs"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # References NestJS/FastAPI video_jobs.id (UUID).
    # Keep as raw ID here to avoid cross-service metadata dependency.
    video_job_id = Column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    # References NestJS accounts table (Phase 2).
    # Keep as raw ID here to avoid SQLAlchemy metadata boot dependency.
    account_id = Column(
        Integer,
        nullable=False,
        index=True,
    )
    caption = Column(
        Text,
        nullable=True,
        comment="Post caption including affiliate links",
    )
    proxy_url = Column(
        String(500),
        nullable=True,
        comment="Optional static residential proxy URL for this account/job",
    )
    affiliate_comment = Column(
        Text,
        nullable=True,
        comment="Optional first comment used for affiliate seeding",
    )
    status = Column(
        SAEnum(
            UploadJobStatus,
            name="upload_job_status_enum",
            create_type=True,
        ),
        nullable=False,
        default=UploadJobStatus.PENDING,
    )
    post_url = Column(
        String(500),
        nullable=True,
        comment="Actual Facebook post URL after success",
    )
    error_log = Column(
        Text,
        nullable=True,
        comment="Error details if status=failed",
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def __repr__(self):
        return f"<UploadJob(id={self.id}, status={self.status})>"

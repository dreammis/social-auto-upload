"""
SQLAlchemy engine + session factory for the AI Worker.
Connects directly to the same PostgreSQL database used by NestJS.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "user": os.getenv("DB_USER", "socialflow"),
    "password": os.getenv("DB_PASSWORD", "socialflow_dev"),
    "database": os.getenv("DB_NAME", "socialflow"),
}

DATABASE_URL = (
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# Synchronous engine — sufficient for scheduler-based workers
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # health-check stale connections
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Dependency-style DB session. Caller must close."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


logger.info(f"DB connected to {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")

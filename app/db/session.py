"""SQLAlchemy database session and base model."""

import os
import traceback

from loguru import logger
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from app.core.config import settings

# Determine if running in Celery worker process
# Celery workers typically have CELERY_WORKER or CELERY_APP environment variables
# Or check if _USE_NULL_POOL flag is set (set in celery_app.py)
is_celery_worker = (
    'celery' in os.environ.get('_', '').lower() or
    'CELERY_WORKER' in os.environ or
    'CELERY_APP' in os.environ or
    getattr(settings, '_USE_NULL_POOL', False)
)

# Build engine arguments based on pool type
engine_kwargs = {
    "pool_pre_ping": True,  # Verify connections before using (reconnect if needed)
    "pool_recycle": 3600,  # Recycle connections after 1 hour
    "echo": False,  # Disable SQL query logging
    "connect_args": {
        "connect_timeout": 10,  # Connection timeout in seconds
        "read_timeout": 10,
        "write_timeout": 10,
    }
}

if is_celery_worker:
    # NullPool: no connection pooling, create new connection for each session
    # This is necessary because Celery workers run in separate processes
    # and cannot share connection pools with FastAPI
    engine_kwargs["poolclass"] = NullPool
    logger.debug("Using NullPool for Celery worker (separate process)")
else:
    # QueuePool: connection pooling for FastAPI
    engine_kwargs["poolclass"] = QueuePool
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    logger.debug("Using QueuePool for FastAPI")

# Create database engine with MySQL-specific settings
engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database session.

    Usage in FastAPI:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = None
    try:
        db = SessionLocal()
        yield db
    except OperationalError as e:
        error_str = str(e).lower()
        if 'connection refused' in error_str or 'can\'t connect' in error_str or 'errno 61' in error_str:
            logger.error(
                f"❌ Database connection failed: Cannot connect to MySQL at {settings.DB_HOST}:{settings.DB_PORT}. "
                f"Error: {e}\n"
                f"💡 Please ensure MySQL is running:\n"
                f"   - macOS: brew services start mysql\n"
                f"   - Linux: sudo systemctl start mysql\n"
                f"   - Docker: docker run -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=your_password mysql:8.0"
            )
        else:
            logger.error(
                f"Database connection error: {e}. "
                f"Please check MySQL credentials and database '{settings.DB_NAME}' exists."
            )
        raise
    except Exception as e:
        # DB URL에서 비밀번호 마스킹
        db_url_safe = "N/A"
        if '@' in settings.DATABASE_URL:
            try:
                # mysql+pymysql://user:password@host:port/db -> host:port/db만 표시
                db_url_safe = settings.DATABASE_URL.split('@')[1]
            except Exception:
                db_url_safe = "***"
        
        logger.error(
            f"Database session error: {e}\n"
            f"Error type: {type(e).__name__}\n"
            f"Traceback:\n{traceback.format_exc()}\n"
            f"Engine pool class: {engine.pool.__class__.__name__}\n"
            f"Is Celery worker: {getattr(settings, '_USE_NULL_POOL', False)}\n"
            f"DB URL: {db_url_safe}"
        )
        raise
    finally:
        if db:
            db.close()

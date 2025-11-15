"""Initialize database using Alembic migrations."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from app.db.session import engine, Base
from app.core.config import settings


def init_db():
    """Initialize database by running Alembic migrations."""
    logger.info("Initializing database...")
    logger.info(f"Database URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'hidden'}")
    
    try:
        # Import all models to ensure they're registered with Base.metadata
        from app.models.user import User
        from app.models.email_account import EmailAccount
        from app.models.email import Email
        
        # Create all tables (alternative to Alembic for quick setup)
        # Note: In production, use Alembic migrations instead
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ Database tables created successfully!")
        logger.info("Created tables: users, email_accounts, emails")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


if __name__ == "__main__":
    init_db()


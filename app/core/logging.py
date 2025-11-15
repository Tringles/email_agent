"""Logging configuration using loguru."""

import sys
from loguru import logger
from app.core.config import settings


def setup_logging():
    """
    Configure loguru logger.
    This should be called at application startup.
    """
    # Remove default handler
    logger.remove()
    
    # Add console handler with formatting
    log_level = settings.LOG_LEVEL  # Get property value
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
    )
    
    # Add file handler for errors (only in production)
    if settings.ENVIRONMENT != "dev":
        logger.add(
            "logs/error_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="ERROR",
            rotation="00:00",  # Rotate at midnight
            retention="30 days",
            compression="zip",
        )
        
        logger.add(
            "logs/app_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=log_level,
            rotation="00:00",
            retention="7 days",
            compression="zip",
        )
    
    return logger


# Initialize logger
setup_logging()

# Export logger for use throughout the application
__all__ = ["logger"]

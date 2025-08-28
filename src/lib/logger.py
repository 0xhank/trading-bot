from loguru import logger
import sys
import os


def setup_logger(log_level="INFO", log_file=None):
    """
    Setup loguru logger with custom configuration
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to save logs
    """
    # Remove default handler
    logger.remove()
    
    # Console handler with custom format
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    logger.add(
        sys.stdout,
        format=console_format,
        level=log_level,
        colorize=True
    )
    
    # File handler if specified
    if log_file:
        # Ensure logs directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} | {message}"
        )
        
        logger.add(
            log_file,
            format=file_format,
            level=log_level,
            rotation="10 MB",  # Rotate when file reaches 10MB
            retention="7 days",  # Keep logs for 7 days
            compression="zip"  # Compress rotated files
        )
    
    return logger


def get_subscription_logger():
    """Get logger specifically for subscription data"""
    return logger.bind(module="subscriptions")


def get_trading_logger():
    """Get logger specifically for trading operations"""
    return logger.bind(module="trading")


def get_market_data_logger():
    """Get logger specifically for market data"""
    return logger.bind(module="market_data")


# Initialize default logger
default_logger = setup_logger(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE", "logs/trading_bot.log")
)
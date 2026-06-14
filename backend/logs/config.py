from loguru import logger
import sys
import os

def setup_logging():
    log_path = os.path.join(os.path.dirname(__file__), "system.log")
    
    # Clear default handlers
    logger.remove()
    
    # Add console handler
    logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    # Add file handler
    logger.add(log_path, rotation="10 MB", retention="10 days", level="DEBUG")

    logger.info("Logging initialized.")

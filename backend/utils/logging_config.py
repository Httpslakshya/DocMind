import logging
import sys
from logging.handlers import RotatingFileHandler
from backend.config.settings import settings

def setup_logging():
    """Configures system-wide logging with both file rotation and console output."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    
    # Retrieve base logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Avoid attaching handlers multiple times
    if root_logger.handlers:
        return
        
    # Stream (stdout) handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)
    
    # File handler (10MB rotating limit, max 5 backups)
    log_file_path = settings.LOGS_DIR / "app.log"
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(file_handler)

setup_logging()
logger = logging.getLogger("docmind")

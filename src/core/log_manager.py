# src/core/log_manager.py
import logging
import logging.config
import os
from typing import TYPE_CHECKING, Optional

# --- Configuration Constants ---

# Determine the path for the logs directory relative to this file's location.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', '..', 'logs'))
LOG_FILENAME = 'f-lash.log'
LOG_FILEPATH = os.path.join(LOGS_DIR, LOG_FILENAME)

MAX_BYTES = 10 * 1024 * 1024  # 10 MB for rotation
BACKUP_COUNT = 5              # Keep 5 backup logs
LOG_LEVEL_APP = 'INFO'        # Default level for our application code
LOG_LEVEL_ROOT = 'WARNING'    # Level for third-party libraries (to reduce noise)

# --- Custom Filter for Clean Filename ---
class FilenameCleanerFilter(logging.Filter):
    """
    Strips the '.py' extension from the filename field in the LogRecord for cleaner output.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        """Modifies the log record in place to clean the filename."""
        # Use filename attribute as set by the standard logging module
        if record.filename.endswith('.py'):
            # Removes the last 3 characters: .py
            record.filename = record.filename[:-3] 
        return True # Must return True to allow the record to proceed

# --- Logging Setup Function ---

def setup_logging() -> logging.Logger:
    """
    Initializes and configures the application logging system.
    
    Uses dictConfig for a robust, centralized configuration of file rotation, 
    formatting, and logging levels. The formatter is updated to include 
    the originating filename (%(filename)s) in place of the logger name.
    """
    
    # 1. Ensure the log directory exists
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
    except OSError as e:
        # If directory creation fails, notify and fall back to console logging
        print(f"ERROR: Could not create log directory {LOGS_DIR}. Logging will fall back to basic console output. {e}")
        logging.basicConfig(level=LOG_LEVEL_APP)
        return logging.getLogger('app')

    if 'FilenameCleanerFilter' not in logging.__dict__:
        logging.FilenameCleanerFilter = FilenameCleanerFilter

    # 2. Configuration Dictionary
    config = {
        'version': 1,
        'disable_existing_loggers': False, 
        
        'filters': {
            'clean_filename_filter': {
                '()': 'logging.FilenameCleanerFilter', 
            }
        },

        'formatters': {
            'standard': {
                'format': '[%(asctime)s] [%(levelname)-8s] %(filename)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
        },
        
        'handlers': {
            'file_handler': {
                'level': LOG_LEVEL_APP,
                'formatter': 'standard',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': LOG_FILEPATH,
                'maxBytes': MAX_BYTES,
                'backupCount': BACKUP_COUNT,
                'encoding': 'utf8',
                'filters': ['clean_filename_filter'],
            },
            'console_handler': {
                'level': 'DEBUG', # Display all app logs on console
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',
                'filters': ['clean_filename_filter'],
            }
        },
        
        'loggers': {
            'app': { # The primary logger for our application code
                'handlers': ['file_handler', 'console_handler'], 
                'level': LOG_LEVEL_APP,
                'propagate': False 
            },
        },
        
        'root': { # Default logger for third-party libraries
            'handlers': ['file_handler', 'console_handler'],
            'level': LOG_LEVEL_ROOT,
        }
    }
    
    # 3. Apply the configuration
    try:
        logging.config.dictConfig(config)
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to configure logging system: {e}")
        # Fallback
        logging.basicConfig(level=LOG_LEVEL_APP)

    # 4. Return the configured application logger instance
    return logging.getLogger('app')

# The globally accessible application logger instance
app_logger = setup_logging() 

# Alias for convenience when importing
logger = app_logger


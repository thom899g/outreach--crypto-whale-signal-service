"""
Advanced logging configuration for Project Vault
"""
import logging
import sys
from datetime import datetime
from typing import Optional
import json

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_record = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'module': record.module,
            'function': record.funcName,
            'message': record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_record)

class ProjectVaultLogger:
    """Centralized logger for Project Vault"""
    
    _instance: Optional['ProjectVaultLogger'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize logger configuration"""
        self.logger = logging.getLogger('project_vault')
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # Console handler with JSON format
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(console_handler)
        
        # File handler for persistent logs
        try:
            file_handler = logging.FileHandler(f'logs/project_vault_{datetime.now().strftime("%Y%m%d")}.log')
            file_handler.setFormatter(JSONFormatter())
            self.logger.addHandler(file_handler)
        except (IOError, OSError) as e:
            self.logger.warning(f"Could not create file handler: {e}")
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance"""
        return self.logger
    
    @staticmethod
    def log_operation_start(operation: str, **kwargs):
        """Log the start of an operation"""
        logger = ProjectVaultLogger().get_logger()
        logger.info(f"Starting operation: {operation}", extra={'operation': operation, **kwargs})
    
    @staticmethod
    def log_operation_end(operation: str, duration_seconds: float, **kwargs):
        """Log the end of an operation"""
        logger = ProjectVaultLogger().get_logger()
        logger.info(f"Completed operation: {operation}", 
                   extra={'operation': operation, 'duration_seconds': duration_seconds, **kwargs})
    
    @staticmethod
    def log_error(operation: str, error: Exception, **kwargs):
        """Log an error with context"""
        logger = ProjectVaultLogger().get_logger()
        logger.error(f"Error in {operation}: {str(error)}", 
                    extra={'operation': operation, 'error_type': type(error).__name__, **kwargs},
                    exc_info=True)

# Convenience functions
def get_logger() -> logging.Logger:
    """Get the project logger"""
    return ProjectVaultLogger().get_logger()

def log_operation(operation: str):
    """Decorator to log operation execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            logger = get_logger()
            
            logger.info(f"Starting {operation}")
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"Completed {operation} in {duration:.2f}s")
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                logger.error(f"Failed {operation} after {duration:.2f}s: {str(e)}")
                raise
        return wrapper
    return decorator
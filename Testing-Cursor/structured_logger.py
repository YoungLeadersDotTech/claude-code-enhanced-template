#!/usr/bin/env python3
"""
Structured logging system for Context Exporter
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path
import traceback

from exporter_config import LoggingConfig


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured logs in JSON format"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
            
        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Enhanced text formatter with color support for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and sys.stdout.isatty()
        
    def format(self, record: logging.LogRecord) -> str:
        # Format timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Get color for level
        color = ""
        reset = ""
        if self.use_colors:
            color = self.COLORS.get(record.levelname, '')
            reset = self.COLORS['RESET']
            
        # Build message
        msg = f"{timestamp} {color}[{record.levelname:8}]{reset} {record.name} - {record.getMessage()}"
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            extra_str = " ".join([f"{k}={v}" for k, v in record.extra_fields.items()])
            msg += f" | {extra_str}"
            
        # Add exception info if present
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            msg += f"\n{exc_text}"
            
        return msg


class StructuredLogger:
    """Enhanced logger with structured logging capabilities"""
    
    def __init__(self, name: str, config: LoggingConfig):
        self.logger = logging.getLogger(name)
        self.config = config
        self._setup_logger()
        
    def _setup_logger(self):
        """Configure the logger with handlers and formatters"""
        self.logger.setLevel(getattr(logging, self.config.level))
        
        # Remove existing handlers
        self.logger.handlers = []
        
        # Console handler
        if self.config.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            if self.config.format == "json":
                console_handler.setFormatter(StructuredFormatter())
            else:
                console_handler.setFormatter(TextFormatter())
            self.logger.addHandler(console_handler)
            
        # File handler
        if self.config.log_file:
            # Create log directory if needed
            log_path = Path(self.config.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(self.config.log_file)
            file_handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(file_handler)
            
    def _log_with_context(self, level: str, message: str, **kwargs):
        """Log a message with additional context"""
        extra = {'extra_fields': kwargs} if kwargs else {}
        getattr(self.logger, level)(message, extra=extra)
        
    def debug(self, message: str, **kwargs):
        """Log debug message with context"""
        self._log_with_context('debug', message, **kwargs)
        
    def info(self, message: str, **kwargs):
        """Log info message with context"""
        self._log_with_context('info', message, **kwargs)
        
    def warning(self, message: str, **kwargs):
        """Log warning message with context"""
        self._log_with_context('warning', message, **kwargs)
        
    def error(self, message: str, **kwargs):
        """Log error message with context"""
        self._log_with_context('error', message, **kwargs)
        
    def critical(self, message: str, **kwargs):
        """Log critical message with context"""
        self._log_with_context('critical', message, **kwargs)
        
    def exception(self, message: str, **kwargs):
        """Log exception with traceback"""
        extra = {'extra_fields': kwargs} if kwargs else {}
        self.logger.exception(message, extra=extra)
        
    def log_api_request(self, method: str, url: str, status_code: Optional[int] = None, 
                       duration: Optional[float] = None, error: Optional[str] = None):
        """Log API request with standardized format"""
        log_data = {
            "api_method": method,
            "api_url": url,
            "api_status_code": status_code,
            "api_duration_ms": round(duration * 1000, 2) if duration else None,
            "api_error": error
        }
        
        # Remove None values
        log_data = {k: v for k, v in log_data.items() if v is not None}
        
        if error:
            self.error(f"API request failed: {method} {url}", **log_data)
        else:
            self.info(f"API request: {method} {url}", **log_data)
            
    def log_export_progress(self, export_type: str, current: int, total: int, 
                          item_name: Optional[str] = None):
        """Log export progress"""
        percentage = (current / total * 100) if total > 0 else 0
        log_data = {
            "export_type": export_type,
            "progress_current": current,
            "progress_total": total,
            "progress_percentage": round(percentage, 2),
            "item_name": item_name
        }
        
        # Remove None values
        log_data = {k: v for k, v in log_data.items() if v is not None}
        
        self.info(f"Export progress: {export_type} {current}/{total} ({percentage:.1f}%)", **log_data)
        
    def log_performance_metrics(self, operation: str, duration: float, 
                              items_processed: Optional[int] = None, **kwargs):
        """Log performance metrics"""
        metrics = {
            "operation": operation,
            "duration_seconds": round(duration, 2),
            "items_processed": items_processed,
            "items_per_second": round(items_processed / duration, 2) if items_processed and duration > 0 else None
        }
        
        # Add any additional metrics
        metrics.update(kwargs)
        
        # Remove None values
        metrics = {k: v for k, v in metrics.items() if v is not None}
        
        self.info(f"Performance metrics for {operation}", **metrics)


class LoggerFactory:
    """Factory for creating loggers with consistent configuration"""
    
    _config: Optional[LoggingConfig] = None
    _loggers: Dict[str, StructuredLogger] = {}
    
    @classmethod
    def set_config(cls, config: LoggingConfig):
        """Set the logging configuration"""
        cls._config = config
        
    @classmethod
    def get_logger(cls, name: str) -> StructuredLogger:
        """Get or create a logger with the given name"""
        if cls._config is None:
            # Use default config if not set
            cls._config = LoggingConfig()
            
        if name not in cls._loggers:
            cls._loggers[name] = StructuredLogger(name, cls._config)
            
        return cls._loggers[name]
        
    @classmethod
    def configure_root_logger(cls):
        """Configure the root logger to prevent duplicate logs"""
        if cls._config is None:
            cls._config = LoggingConfig()
            
        root = logging.getLogger()
        root.setLevel(getattr(logging, cls._config.level))
        
        # Clear existing handlers
        root.handlers = []
        
        # Add null handler to prevent propagation
        root.addHandler(logging.NullHandler())
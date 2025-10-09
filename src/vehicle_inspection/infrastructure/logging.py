"""Structured JSON logging configuration for the Vehicle Inspection System."""

import logging
import logging.handlers
import json
import sys
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from contextvars import ContextVar
from pathlib import Path
import os


# Context variable for correlation ID tracking across async requests
correlation_id_context: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationIDFilter(logging.Filter):
    """Add correlation ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to the log record."""
        record.correlation_id = correlation_id_context.get() or "unknown"
        return True


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def __init__(self, service_name: str = "vehicle-inspection-system"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log entry structure
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, 'correlation_id', 'unknown'),
        }

        # Add module and function info
        if record.module:
            log_entry["module"] = record.module
        if record.funcName and record.funcName != '<module>':
            log_entry["function"] = record.funcName
        if record.lineno:
            log_entry["line"] = record.lineno

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None
            }

        # Add extra fields from the log record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in [
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'message', 'exc_info',
                'exc_text', 'stack_info', 'correlation_id'
            ]:
                extra_fields[key] = value

        if extra_fields:
            log_entry["extra"] = extra_fields

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class LoggingConfig:
    """Centralized logging configuration."""

    def __init__(self,
                 log_level: str = "INFO",
                 service_name: str = "vehicle-inspection-system",
                 log_dir: Optional[str] = None,
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5,
                 enable_console: bool = True,
                 enable_file: bool = True):
        """
        Initialize logging configuration.

        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            service_name: Service name for log entries
            log_dir: Directory for log files (defaults to logs/ in project root)
            max_file_size: Maximum size per log file in bytes
            backup_count: Number of backup log files to keep
            enable_console: Whether to enable console logging
            enable_file: Whether to enable file logging
        """
        self.log_level = getattr(logging, log_level.upper())
        self.service_name = service_name
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.enable_console = enable_console
        self.enable_file = enable_file

        # Set up log directory
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            # Default to logs/ directory in project root
            project_root = Path(__file__).parent.parent.parent.parent
            self.log_dir = project_root / "logs"

        # Ensure log directory exists
        if self.enable_file:
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def setup_logging(self) -> None:
        """Configure logging for the application."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Set root logger level
        root_logger.setLevel(self.log_level)

        # Create correlation ID filter
        correlation_filter = CorrelationIDFilter()

        # Create JSON formatter
        json_formatter = JSONFormatter(service_name=self.service_name)

        # Console handler
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)
            console_handler.addFilter(correlation_filter)
            console_handler.setFormatter(json_formatter)
            root_logger.addHandler(console_handler)

        # File handler with rotation
        if self.enable_file:
            log_file = self.log_dir / f"{self.service_name}.log"
            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(self.log_level)
            file_handler.addFilter(correlation_filter)
            file_handler.setFormatter(json_formatter)
            root_logger.addHandler(file_handler)

        # Error file handler (separate file for ERROR and CRITICAL logs)
        if self.enable_file:
            error_log_file = self.log_dir / f"{self.service_name}-errors.log"
            error_handler = logging.handlers.RotatingFileHandler(
                filename=error_log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.addFilter(correlation_filter)
            error_handler.setFormatter(json_formatter)
            root_logger.addHandler(error_handler)

        # Configure third-party loggers to reduce noise
        self._configure_third_party_loggers()

    def _configure_third_party_loggers(self) -> None:
        """Configure third-party library loggers to reduce noise."""
        # SQLAlchemy
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)

        # FastAPI/Uvicorn
        logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
        logging.getLogger('fastapi').setLevel(logging.WARNING)

        # HTTP libraries
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for the current context."""
    correlation_id_context.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID."""
    return correlation_id_context.get()


def clear_correlation_id() -> None:
    """Clear correlation ID from current context."""
    correlation_id_context.set(None)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)


def setup_logging_from_env() -> LoggingConfig:
    """Setup logging configuration from environment variables."""
    config = LoggingConfig(
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        service_name=os.getenv('SERVICE_NAME', 'vehicle-inspection-system'),
        log_dir=os.getenv('LOG_DIR'),
        max_file_size=int(os.getenv('LOG_MAX_FILE_SIZE', '10485760')),  # 10MB
        backup_count=int(os.getenv('LOG_BACKUP_COUNT', '5')),
        enable_console=os.getenv('LOG_ENABLE_CONSOLE', 'true').lower() == 'true',
        enable_file=os.getenv('LOG_ENABLE_FILE', 'true').lower() == 'true'
    )

    config.setup_logging()
    return config


# Convenience functions for common logging patterns
def log_with_extra(logger: logging.Logger, level: int, message: str, **extra) -> None:
    """Log a message with extra fields."""
    logger.log(level, message, extra=extra)


def log_request(logger: logging.Logger, method: str, path: str, **extra) -> None:
    """Log an HTTP request."""
    log_with_extra(
        logger,
        logging.INFO,
        f"HTTP Request: {method} {path}",
        request_method=method,
        request_path=path,
        **extra
    )


def log_response(logger: logging.Logger, method: str, path: str, status_code: int, duration_ms: float, **extra) -> None:
    """Log an HTTP response."""
    log_with_extra(
        logger,
        logging.INFO,
        f"HTTP Response: {method} {path} -> {status_code} ({duration_ms:.2f}ms)",
        request_method=method,
        request_path=path,
        response_status=status_code,
        response_duration_ms=duration_ms,
        **extra
    )


def log_database_operation(logger: logging.Logger, operation: str, table: str, **extra) -> None:
    """Log a database operation."""
    log_with_extra(
        logger,
        logging.DEBUG,
        f"Database {operation}: {table}",
        db_operation=operation,
        db_table=table,
        **extra
    )


def log_authentication_attempt(logger: logging.Logger, email: str, success: bool, **extra) -> None:
    """Log an authentication attempt."""
    level = logging.INFO if success else logging.WARNING
    status = "successful" if success else "failed"
    log_with_extra(
        logger,
        level,
        f"Authentication attempt {status} for {email}",
        auth_email=email,
        auth_success=success,
        **extra
    )


def log_business_rule_violation(logger: logging.Logger, rule: str, details: str, **extra) -> None:
    """Log a business rule violation."""
    log_with_extra(
        logger,
        logging.WARNING,
        f"Business rule violation: {rule} - {details}",
        business_rule=rule,
        violation_details=details,
        **extra
    )


# Example usage and initialization
if __name__ == "__main__":
    # Example of setting up logging
    config = setup_logging_from_env()

    # Get a logger
    logger = get_logger(__name__)

    # Set correlation ID
    set_correlation_id(generate_correlation_id())

    # Example logging
    logger.info("Logging system initialized")
    logger.debug("Debug message with correlation ID")

    # Example with extra fields
    log_with_extra(logger, logging.INFO, "User action", user_id="123", action="login")

    # Example error logging
    try:
        raise ValueError("Example error")
    except Exception:
        logger.exception("An error occurred")

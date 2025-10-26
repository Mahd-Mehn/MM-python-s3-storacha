"""Logging configuration and utilities for S3 to Storacha migration operations."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Union
from enum import Enum
import json
import os


class LogLevel(Enum):
    """Enumeration of supported log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""

    def __init__(self, include_extra: bool = True) -> None:
        """Initialize structured formatter.

        Args:
            include_extra: Whether to include extra fields in log records
        """
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if enabled
        if self.include_extra:
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in {
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "getMessage",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "message",
                }:
                    # Ensure value is JSON serializable
                    try:
                        json.dumps(value)
                        extra_fields[key] = value
                    except (TypeError, ValueError):
                        extra_fields[key] = str(value)

            if extra_fields:
                log_data["extra"] = extra_fields

        return json.dumps(log_data, default=str)


class SimpleFormatter(logging.Formatter):
    """Simple human-readable formatter for console output."""

    def __init__(self) -> None:
        """Initialize simple formatter with timestamp and level colors."""
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


class LoggingConfig:
    """Configuration class for logging setup."""

    def __init__(
        self,
        level: Union[str, LogLevel] = LogLevel.INFO,
        format_type: str = "simple",
        log_file: Optional[Union[str, Path]] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        console_output: bool = True,
        include_extra: bool = True,
    ) -> None:
        """Initialize logging configuration.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_type: Format type ('simple' or 'structured')
            log_file: Path to log file (optional)
            max_file_size: Maximum size of log file before rotation
            backup_count: Number of backup files to keep
            console_output: Whether to output logs to console
            include_extra: Whether to include extra fields in structured logs
        """
        self.level = LogLevel(level) if isinstance(level, str) else level
        self.format_type = format_type
        self.log_file = Path(log_file) if log_file else None
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.console_output = console_output
        self.include_extra = include_extra

    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """Create logging configuration from environment variables."""
        return cls(
            level=os.getenv("S3_STORACHA_LOG_LEVEL", "INFO"),
            format_type=os.getenv("S3_STORACHA_LOG_FORMAT", "simple"),
            log_file=os.getenv("S3_STORACHA_LOG_FILE"),
            console_output=os.getenv("S3_STORACHA_LOG_CONSOLE", "true").lower()
            == "true",
            include_extra=os.getenv("S3_STORACHA_LOG_EXTRA", "true").lower() == "true",
        )

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "LoggingConfig":
        """Create logging configuration from dictionary."""
        return cls(
            level=config_dict.get("level", "INFO"),
            format_type=config_dict.get("format_type", "simple"),
            log_file=config_dict.get("log_file"),
            max_file_size=config_dict.get("max_file_size", 10 * 1024 * 1024),
            backup_count=config_dict.get("backup_count", 5),
            console_output=config_dict.get("console_output", True),
            include_extra=config_dict.get("include_extra", True),
        )


def setup_logging(config: Optional[LoggingConfig] = None) -> None:
    """Set up logging configuration for the application.

    Args:
        config: Logging configuration. If None, uses environment variables.
    """
    if config is None:
        config = LoggingConfig.from_env()

    # Get root logger for the package
    root_logger = logging.getLogger("py_s3_storacha")
    root_logger.setLevel(getattr(logging, config.level.value))

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Create formatter based on format type
    if config.format_type == "structured":
        formatter = StructuredFormatter(include_extra=config.include_extra)
    else:
        formatter = SimpleFormatter()

    # Add console handler if enabled
    if config.console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, config.level.value))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Add file handler if log file is specified
    if config.log_file:
        # Ensure log directory exists
        config.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Use rotating file handler to manage log file size
        file_handler = logging.handlers.RotatingFileHandler(
            filename=config.log_file,
            maxBytes=config.max_file_size,
            backupCount=config.backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, config.level.value))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Prevent propagation to avoid duplicate logs
    root_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the specified module.

    Args:
        name: Logger name (typically __name__ from the calling module)

    Returns:
        Configured logger instance
    """
    # Ensure the logger name is under the package namespace
    if not name.startswith("py_s3_storacha"):
        if name == "__main__":
            name = "py_s3_storacha.main"
        else:
            name = f"py_s3_storacha.{name}"

    return logging.getLogger(name)


def log_function_call(
    logger: logging.Logger,
    func_name: str,
    args: Optional[Dict[str, Any]] = None,
    level: str = "DEBUG",
) -> None:
    """Log function call with arguments.

    Args:
        logger: Logger instance
        func_name: Name of the function being called
        args: Function arguments to log
        level: Log level for the message
    """
    log_level = getattr(logging, level.upper())

    if args:
        # Mask sensitive arguments
        safe_args = {}
        for key, value in args.items():
            if any(
                sensitive in key.lower()
                for sensitive in ["key", "secret", "password", "token"]
            ):
                safe_args[key] = "***MASKED***"
            else:
                safe_args[key] = value

        logger.log(
            log_level, f"Calling {func_name}", extra={"function_args": safe_args}
        )
    else:
        logger.log(log_level, f"Calling {func_name}")


def log_performance(
    logger: logging.Logger,
    operation: str,
    duration_seconds: float,
    additional_metrics: Optional[Dict[str, Any]] = None,
) -> None:
    """Log performance metrics for an operation.

    Args:
        logger: Logger instance
        operation: Name of the operation
        duration_seconds: Duration of the operation in seconds
        additional_metrics: Additional metrics to log
    """
    metrics = {"operation": operation, "duration_seconds": round(duration_seconds, 3)}

    if additional_metrics:
        metrics.update(additional_metrics)

    logger.info(f"Performance: {operation} completed", extra={"performance": metrics})


def configure_third_party_loggers(level: str = "WARNING") -> None:
    """Configure third-party library loggers to reduce noise.

    Args:
        level: Log level to set for third-party loggers
    """
    third_party_loggers = ["urllib3", "requests", "boto3", "botocore", "asyncio"]

    log_level = getattr(logging, level.upper())

    for logger_name in third_party_loggers:
        logging.getLogger(logger_name).setLevel(log_level)


# Default logging setup function for convenience
def setup_default_logging(
    level: str = "INFO", format_type: str = "simple", log_file: Optional[str] = None
) -> None:
    """Set up default logging configuration.

    Args:
        level: Logging level
        format_type: Format type ('simple' or 'structured')
        log_file: Optional log file path
    """
    config = LoggingConfig(level=level, format_type=format_type, log_file=log_file)
    setup_logging(config)
    configure_third_party_loggers()

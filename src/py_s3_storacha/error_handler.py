"""Comprehensive error handling system for S3 to Storacha migration operations."""

import asyncio
import re
import time
from typing import Optional, Dict, Any, Callable, TypeVar, Union
from functools import wraps
import logging

from .exceptions import (
    S3StorachaError,
    JSWrapperError,
    ConfigurationError,
    MigrationError,
)
from .logging_config import get_logger

T = TypeVar("T")


class ErrorHandler:
    """Comprehensive error handling system for S3 to Storacha operations."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """Initialize error handler with optional logger.

        Args:
            logger: Logger instance for error reporting. If None, uses default logger.
        """
        self.logger = logger or get_logger(__name__)

        # JavaScript error patterns for parsing subprocess errors
        self.js_error_patterns = {
            "syntax_error": re.compile(r"SyntaxError:\s*(.+)", re.IGNORECASE),
            "reference_error": re.compile(r"ReferenceError:\s*(.+)", re.IGNORECASE),
            "type_error": re.compile(r"TypeError:\s*(.+)", re.IGNORECASE),
            "network_error": re.compile(
                r"(ECONNREFUSED|ENOTFOUND|ETIMEDOUT|ECONNRESET)", re.IGNORECASE
            ),
            "auth_error": re.compile(
                r"(Unauthorized|Forbidden|Invalid.*credentials)", re.IGNORECASE
            ),
            "not_found": re.compile(
                r"(Not Found|404|NoSuchBucket|NoSuchKey)", re.IGNORECASE
            ),
            "permission_error": re.compile(
                r"(Access Denied|Permission denied|EACCES)", re.IGNORECASE
            ),
        }

    def handle_js_error(
        self, stderr: str, returncode: int, command: Optional[str] = None
    ) -> JSWrapperError:
        """Parse JavaScript subprocess errors and create appropriate Python exceptions.

        Args:
            stderr: Standard error output from JavaScript process
            returncode: Process return code
            command: Command that was executed (optional)

        Returns:
            JSWrapperError: Appropriate exception based on error analysis
        """
        self.logger.error(f"JavaScript wrapper failed with return code {returncode}")
        self.logger.debug(f"JavaScript stderr: {stderr}")

        # Try to parse structured error information
        error_info = self._parse_js_error(stderr)

        # Create appropriate error message
        if error_info["type"] == "network":
            message = f"Network error in JavaScript wrapper: {error_info['message']}"
        elif error_info["type"] == "auth":
            message = (
                f"Authentication error in JavaScript wrapper: {error_info['message']}"
            )
        elif error_info["type"] == "not_found":
            message = (
                f"Resource not found in JavaScript wrapper: {error_info['message']}"
            )
        elif error_info["type"] == "permission":
            message = f"Permission error in JavaScript wrapper: {error_info['message']}"
        elif error_info["type"] in ["syntax", "reference", "type"]:
            message = f"JavaScript {error_info['type']} error: {error_info['message']}"
        else:
            message = f"JavaScript wrapper execution failed: {error_info['message']}"

        # Create exception with parsed information
        error = JSWrapperError.from_process_result(
            return_code=returncode,
            stdout="",  # stdout not provided in this context
            stderr=stderr,
            command=command,
        )
        error.message = message
        error.add_context("error_type", error_info["type"])

        return error

    def handle_network_error(
        self, error: Exception, operation: str = "unknown"
    ) -> MigrationError:
        """Handle network-related errors with appropriate context.

        Args:
            error: Original network exception
            operation: Operation that failed

        Returns:
            MigrationError: Network error with migration context
        """
        self.logger.error(f"Network error during {operation}: {error}")

        # Determine specific network error type
        error_str = str(error).lower()
        if "timeout" in error_str or "timed out" in error_str:
            message = f"Network timeout during {operation}"
        elif "connection refused" in error_str or "econnrefused" in error_str:
            message = f"Connection refused during {operation}"
        elif "not found" in error_str or "enotfound" in error_str:
            message = f"Host not found during {operation}"
        elif "unauthorized" in error_str or "forbidden" in error_str:
            message = f"Authentication failed during {operation}"
        else:
            message = f"Network error during {operation}: {str(error)}"

        return MigrationError.network_error(
            message=message, operation=operation, original_error=error
        )

    def handle_config_error(
        self, config_issue: str, config_type: str = "unknown"
    ) -> ConfigurationError:
        """Handle configuration validation errors.

        Args:
            config_issue: Description of the configuration issue
            config_type: Type of configuration that failed

        Returns:
            ConfigurationError: Configuration error with context
        """
        self.logger.error(f"Configuration error in {config_type}: {config_issue}")

        return ConfigurationError(
            message=f"Configuration validation failed: {config_issue}",
            config_type=config_type,
        )

    def _parse_js_error(self, stderr: str) -> Dict[str, str]:
        """Parse JavaScript error output to extract error type and message.

        Args:
            stderr: Standard error output from JavaScript process

        Returns:
            Dict containing error type and message
        """
        # Default error info
        error_info = {
            "type": "unknown",
            "message": stderr.strip() if stderr else "Unknown JavaScript error",
        }

        if not stderr:
            return error_info

        # Try to match against known error patterns
        for error_type, pattern in self.js_error_patterns.items():
            match = pattern.search(stderr)
            if match:
                error_info["type"] = error_type.replace("_error", "")
                error_info["message"] = (
                    match.group(1) if match.groups() else match.group(0)
                )
                break

        # If no specific pattern matched, try to extract first line as message
        if error_info["type"] == "unknown":
            lines = stderr.strip().split("\n")
            if lines:
                error_info["message"] = lines[0]

        return error_info


class RetryHandler:
    """Handles retry logic for various operations with exponential backoff."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Initialize retry handler with configuration.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_factor: Exponential backoff multiplier
            logger: Logger instance for retry reporting
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.logger = logger or get_logger(__name__)

    def retry_on_error(
        self,
        error_types: Union[type, tuple] = (Exception,),
        exclude_types: Union[type, tuple] = (ConfigurationError,),
    ) -> Callable:
        """Decorator for retrying functions on specific error types.

        Args:
            error_types: Exception types to retry on
            exclude_types: Exception types to never retry

        Returns:
            Decorator function
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                return self._execute_with_retry(
                    func, args, kwargs, error_types, exclude_types
                )

            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                return await self._execute_with_retry_async(
                    func, args, kwargs, error_types, exclude_types
                )

            # Return appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def _execute_with_retry(
        self,
        func: Callable[..., T],
        args: tuple,
        kwargs: dict,
        error_types: Union[type, tuple],
        exclude_types: Union[type, tuple],
    ) -> T:
        """Execute function with retry logic (synchronous).

        Args:
            func: Function to execute
            args: Function arguments
            kwargs: Function keyword arguments
            error_types: Exception types to retry on
            exclude_types: Exception types to never retry

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except exclude_types as e:
                # Don't retry on excluded error types
                self.logger.debug(
                    f"Not retrying excluded error type: {type(e).__name__}"
                )
                raise
            except error_types as e:
                last_exception = e

                if attempt < self.max_retries:
                    delay = min(
                        self.base_delay * (self.backoff_factor**attempt), self.max_delay
                    )
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f} seconds..."
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(
                        f"All {self.max_retries + 1} attempts failed. Last error: {e}"
                    )

        # Re-raise the last exception if all retries failed
        if last_exception:
            raise last_exception

        # This should never be reached, but just in case
        raise RuntimeError("Retry logic failed unexpectedly")

    async def _execute_with_retry_async(
        self,
        func: Callable[..., T],
        args: tuple,
        kwargs: dict,
        error_types: Union[type, tuple],
        exclude_types: Union[type, tuple],
    ) -> T:
        """Execute async function with retry logic.

        Args:
            func: Async function to execute
            args: Function arguments
            kwargs: Function keyword arguments
            error_types: Exception types to retry on
            exclude_types: Exception types to never retry

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except exclude_types as e:
                # Don't retry on excluded error types
                self.logger.debug(
                    f"Not retrying excluded error type: {type(e).__name__}"
                )
                raise
            except error_types as e:
                last_exception = e

                if attempt < self.max_retries:
                    delay = min(
                        self.base_delay * (self.backoff_factor**attempt), self.max_delay
                    )
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f} seconds..."
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(
                        f"All {self.max_retries + 1} attempts failed. Last error: {e}"
                    )

        # Re-raise the last exception if all retries failed
        if last_exception:
            raise last_exception

        # This should never be reached, but just in case
        raise RuntimeError("Retry logic failed unexpectedly")


# Global error handler instance
_error_handler = None
_retry_handler = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance.

    Returns:
        ErrorHandler: Global error handler instance
    """
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def get_retry_handler() -> RetryHandler:
    """Get global retry handler instance.

    Returns:
        RetryHandler: Global retry handler instance
    """
    global _retry_handler
    if _retry_handler is None:
        _retry_handler = RetryHandler()
    return _retry_handler


def with_error_handling(
    operation: str,
    error_types: Union[type, tuple] = (Exception,),
    exclude_types: Union[type, tuple] = (ConfigurationError,),
) -> Callable:
    """Decorator that adds comprehensive error handling to functions.

    Args:
        operation: Name of the operation for error context
        error_types: Exception types to handle and potentially retry
        exclude_types: Exception types to never retry

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        error_handler = get_error_handler()
        retry_handler = get_retry_handler()

        @retry_handler.retry_on_error(
            error_types=error_types, exclude_types=exclude_types
        )
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except JSWrapperError:
                # JSWrapperError is already properly formatted, just re-raise
                raise
            except ConfigurationError:
                # ConfigurationError is already properly formatted, just re-raise
                raise
            except MigrationError:
                # MigrationError is already properly formatted, just re-raise
                raise
            except Exception as e:
                # Handle other exceptions by converting to appropriate error type
                if "network" in str(e).lower() or "connection" in str(e).lower():
                    raise error_handler.handle_network_error(e, operation)
                else:
                    # Wrap in generic S3StorachaError
                    raise S3StorachaError(
                        message=f"Unexpected error during {operation}: {str(e)}",
                        context={"operation": operation},
                        original_error=e,
                    )

        return wrapper

    return decorator


def handle_subprocess_error(
    returncode: int, stderr: str, command: Optional[str] = None
) -> JSWrapperError:
    """Handle subprocess execution errors.

    Args:
        returncode: Process return code
        stderr: Standard error output
        command: Command that was executed

    Returns:
        JSWrapperError: Appropriate exception for the subprocess error
    """
    error_handler = get_error_handler()
    return error_handler.handle_js_error(stderr, returncode, command)


def handle_validation_error(
    message: str,
    config_type: str,
    field_name: Optional[str] = None,
    field_value: Optional[Any] = None,
) -> ConfigurationError:
    """Handle configuration validation errors.

    Args:
        message: Error message
        config_type: Type of configuration
        field_name: Name of the field that failed validation
        field_value: Value that failed validation

    Returns:
        ConfigurationError: Configuration validation error
    """
    if field_name and field_value is not None:
        return ConfigurationError.invalid_field(
            config_type=config_type,
            field_name=field_name,
            field_value=field_value,
            reason=message,
        )
    else:
        return ConfigurationError(
            message=message,
            config_type=config_type,
            field_name=field_name,
            field_value=field_value,
        )

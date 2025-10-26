"""Custom exception classes for S3 to Storacha migration operations."""

from typing import Optional, Dict, Any


class S3StorachaError(Exception):
    """Base exception class for all S3 to Storacha operations."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize base exception with message and optional context.

        Args:
            message: Human-readable error message
            context: Additional context information about the error
            original_error: Original exception that caused this error (if any)
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.original_error = original_error

    def __str__(self) -> str:
        """Return formatted error message with context."""
        base_message = self.message

        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            base_message = f"{base_message} (Context: {context_str})"

        if self.original_error:
            base_message = f"{base_message} (Caused by: {self.original_error})"

        return base_message

    def add_context(self, key: str, value: Any) -> None:
        """Add additional context information to the exception."""
        self.context[key] = value


class JSWrapperError(S3StorachaError):
    """Exception raised when JavaScript wrapper execution fails."""

    def __init__(
        self,
        message: str,
        return_code: Optional[int] = None,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize JavaScript wrapper error.

        Args:
            message: Human-readable error message
            return_code: Process return code
            stdout: Standard output from the JavaScript process
            stderr: Standard error from the JavaScript process
            context: Additional context information
            original_error: Original exception that caused this error
        """
        super().__init__(message, context, original_error)
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr

        # Add process information to context
        if return_code is not None:
            self.add_context("return_code", return_code)
        if stderr:
            self.add_context("stderr", stderr[:500])  # Limit stderr length

    @classmethod
    def from_process_result(
        cls, return_code: int, stdout: str, stderr: str, command: Optional[str] = None
    ) -> "JSWrapperError":
        """Create JSWrapperError from subprocess execution result."""
        message = f"JavaScript wrapper execution failed with return code {return_code}"

        if command:
            message = f"{message} (Command: {command})"

        return cls(
            message=message, return_code=return_code, stdout=stdout, stderr=stderr
        )


class ConfigurationError(S3StorachaError):
    """Exception raised when configuration validation fails."""

    def __init__(
        self,
        message: str,
        config_type: Optional[str] = None,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize configuration error.

        Args:
            message: Human-readable error message
            config_type: Type of configuration that failed (e.g., 'S3Config')
            field_name: Name of the configuration field that failed validation
            field_value: Value that failed validation
            context: Additional context information
            original_error: Original exception that caused this error
        """
        super().__init__(message, context, original_error)
        self.config_type = config_type
        self.field_name = field_name
        self.field_value = field_value

        # Add configuration details to context
        if config_type:
            self.add_context("config_type", config_type)
        if field_name:
            self.add_context("field_name", field_name)
        if field_value is not None:
            # Mask sensitive values
            if field_name and any(
                sensitive in field_name.lower()
                for sensitive in ["key", "secret", "password", "token"]
            ):
                self.add_context("field_value", "***MASKED***")
            else:
                self.add_context("field_value", str(field_value)[:100])

    @classmethod
    def missing_field(cls, config_type: str, field_name: str) -> "ConfigurationError":
        """Create ConfigurationError for missing required field."""
        message = f"Missing required field '{field_name}' in {config_type}"
        return cls(message=message, config_type=config_type, field_name=field_name)

    @classmethod
    def invalid_field(
        cls, config_type: str, field_name: str, field_value: Any, reason: str
    ) -> "ConfigurationError":
        """Create ConfigurationError for invalid field value."""
        message = f"Invalid value for field '{field_name}' in {config_type}: {reason}"
        return cls(
            message=message,
            config_type=config_type,
            field_name=field_name,
            field_value=field_value,
        )


class MigrationError(S3StorachaError):
    """Exception raised during migration operations."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        source_path: Optional[str] = None,
        destination_path: Optional[str] = None,
        objects_processed: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize migration error.

        Args:
            message: Human-readable error message
            operation: Migration operation that failed (e.g., 'upload', 'download')
            source_path: Source path involved in the operation
            destination_path: Destination path involved in the operation
            objects_processed: Number of objects processed before failure
            context: Additional context information
            original_error: Original exception that caused this error
        """
        super().__init__(message, context, original_error)
        self.operation = operation
        self.source_path = source_path
        self.destination_path = destination_path
        self.objects_processed = objects_processed

        # Add migration details to context
        if operation:
            self.add_context("operation", operation)
        if source_path:
            self.add_context("source_path", source_path)
        if destination_path:
            self.add_context("destination_path", destination_path)
        if objects_processed is not None:
            self.add_context("objects_processed", objects_processed)

    @classmethod
    def network_error(
        cls, message: str, operation: str, original_error: Exception
    ) -> "MigrationError":
        """Create MigrationError for network-related failures."""
        return cls(
            message=f"Network error during {operation}: {message}",
            operation=operation,
            original_error=original_error,
        )

    @classmethod
    def timeout_error(
        cls,
        operation: str,
        timeout_seconds: int,
        objects_processed: Optional[int] = None,
    ) -> "MigrationError":
        """Create MigrationError for timeout failures."""
        message = f"Operation '{operation}' timed out after {timeout_seconds} seconds"
        return cls(
            message=message, operation=operation, objects_processed=objects_processed
        )

    @classmethod
    def validation_error(
        cls,
        message: str,
        source_path: Optional[str] = None,
        destination_path: Optional[str] = None,
    ) -> "MigrationError":
        """Create MigrationError for data validation failures."""
        return cls(
            message=f"Validation error: {message}",
            operation="validation",
            source_path=source_path,
            destination_path=destination_path,
        )

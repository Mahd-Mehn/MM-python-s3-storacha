"""Unit tests for custom exception classes."""

import pytest
from typing import Dict, Any

from py_s3_storacha.exceptions import (
    S3StorachaError,
    JSWrapperError,
    ConfigurationError,
    MigrationError,
)


class TestS3StorachaError:
    """Test cases for base S3StorachaError exception."""
    
    def test_basic_error_creation(self):
        """Test creating basic S3StorachaError with message only."""
        error = S3StorachaError("Test error message")
        
        assert error.message == "Test error message"
        assert error.context == {}
        assert error.original_error is None
        assert str(error) == "Test error message"
    
    def test_error_with_context(self):
        """Test S3StorachaError with context information."""
        context = {"operation": "test_op", "file": "test.txt"}
        error = S3StorachaError("Error occurred", context=context)
        
        assert error.context == context
        assert "operation=test_op" in str(error)
        assert "file=test.txt" in str(error)
    
    def test_error_with_original_error(self):
        """Test S3StorachaError with original exception."""
        original = ValueError("Original error")
        error = S3StorachaError("Wrapped error", original_error=original)
        
        assert error.original_error is original
        assert "Caused by: Original error" in str(error)
    
    def test_add_context(self):
        """Test adding context to existing error."""
        error = S3StorachaError("Test error")
        
        error.add_context("key1", "value1")
        error.add_context("key2", 42)
        
        assert error.context["key1"] == "value1"
        assert error.context["key2"] == 42
        assert "key1=value1" in str(error)
        assert "key2=42" in str(error)
    
    def test_error_string_formatting(self):
        """Test complete error string formatting with all components."""
        original = RuntimeError("Original issue")
        context = {"step": "validation", "count": 5}
        error = S3StorachaError(
            "Main error message",
            context=context,
            original_error=original
        )
        
        error_str = str(error)
        assert "Main error message" in error_str
        assert "step=validation" in error_str
        assert "count=5" in error_str
        assert "Caused by: Original issue" in error_str


class TestJSWrapperError:
    """Test cases for JSWrapperError exception."""
    
    def test_basic_js_wrapper_error(self):
        """Test creating basic JSWrapperError."""
        error = JSWrapperError("JavaScript execution failed")
        
        assert error.message == "JavaScript execution failed"
        assert error.return_code is None
        assert error.stdout is None
        assert error.stderr is None
    
    def test_js_wrapper_error_with_process_info(self):
        """Test JSWrapperError with process execution details."""
        error = JSWrapperError(
            "Process failed",
            return_code=1,
            stdout="Some output",
            stderr="Error details"
        )
        
        assert error.return_code == 1
        assert error.stdout == "Some output"
        assert error.stderr == "Error details"
        assert error.context["return_code"] == 1
        assert "Error details" in error.context["stderr"]
    
    def test_js_wrapper_error_stderr_truncation(self):
        """Test that long stderr is truncated in context."""
        long_stderr = "x" * 1000
        error = JSWrapperError(
            "Process failed",
            return_code=1,
            stderr=long_stderr
        )
        
        # stderr should be truncated to 500 chars in context
        assert len(error.context["stderr"]) == 500
        assert error.stderr == long_stderr  # Original should be preserved
    
    def test_from_process_result(self):
        """Test creating JSWrapperError from process result."""
        error = JSWrapperError.from_process_result(
            return_code=127,
            stdout="",
            stderr="Command not found",
            command="node script.js"
        )
        
        assert error.return_code == 127
        assert error.stderr == "Command not found"
        assert "return code 127" in error.message
        assert "Command: node script.js" in error.message
    
    def test_from_process_result_without_command(self):
        """Test from_process_result without command parameter."""
        error = JSWrapperError.from_process_result(
            return_code=1,
            stdout="output",
            stderr="error"
        )
        
        assert "return code 1" in error.message
        assert "Command:" not in error.message


class TestConfigurationError:
    """Test cases for ConfigurationError exception."""
    
    def test_basic_configuration_error(self):
        """Test creating basic ConfigurationError."""
        error = ConfigurationError("Invalid configuration")
        
        assert error.message == "Invalid configuration"
        assert error.config_type is None
        assert error.field_name is None
        assert error.field_value is None
    
    def test_configuration_error_with_details(self):
        """Test ConfigurationError with field details."""
        error = ConfigurationError(
            "Invalid value",
            config_type="S3Config",
            field_name="region",
            field_value="invalid-region"
        )
        
        assert error.config_type == "S3Config"
        assert error.field_name == "region"
        assert error.field_value == "invalid-region"
        assert error.context["config_type"] == "S3Config"
        assert error.context["field_name"] == "region"
        assert "invalid-region" in error.context["field_value"]
    
    def test_configuration_error_masks_sensitive_fields(self):
        """Test that sensitive field values are masked in context."""
        sensitive_fields = ["api_key", "secret_key", "password", "token", "Secret_Access_Key"]
        
        for field_name in sensitive_fields:
            error = ConfigurationError(
                "Sensitive field error",
                config_type="TestConfig",
                field_name=field_name,
                field_value="super_secret_value_123"
            )
            
            assert error.field_value == "super_secret_value_123"  # Original preserved
            assert error.context["field_value"] == "***MASKED***"  # Context masked
    
    def test_configuration_error_non_sensitive_field(self):
        """Test that non-sensitive fields are not masked."""
        error = ConfigurationError(
            "Invalid region",
            config_type="S3Config",
            field_name="region",
            field_value="us-invalid-1"
        )
        
        assert error.context["field_value"] == "us-invalid-1"
    
    def test_configuration_error_long_value_truncation(self):
        """Test that long field values are truncated in context."""
        long_value = "x" * 200
        error = ConfigurationError(
            "Value too long",
            config_type="TestConfig",
            field_name="description",
            field_value=long_value
        )
        
        assert len(error.context["field_value"]) == 100
        assert error.field_value == long_value  # Original preserved
    
    def test_missing_field_factory(self):
        """Test missing_field factory method."""
        error = ConfigurationError.missing_field("S3Config", "access_key_id")
        
        assert "Missing required field 'access_key_id'" in error.message
        assert "S3Config" in error.message
        assert error.config_type == "S3Config"
        assert error.field_name == "access_key_id"
    
    def test_invalid_field_factory(self):
        """Test invalid_field factory method."""
        error = ConfigurationError.invalid_field(
            "StorachaConfig",
            "timeout",
            -10,
            "must be positive"
        )
        
        assert "Invalid value for field 'timeout'" in error.message
        assert "StorachaConfig" in error.message
        assert "must be positive" in error.message
        assert error.config_type == "StorachaConfig"
        assert error.field_name == "timeout"
        assert error.field_value == -10


class TestMigrationError:
    """Test cases for MigrationError exception."""
    
    def test_basic_migration_error(self):
        """Test creating basic MigrationError."""
        error = MigrationError("Migration failed")
        
        assert error.message == "Migration failed"
        assert error.operation is None
        assert error.source_path is None
        assert error.destination_path is None
        assert error.objects_processed is None
    
    def test_migration_error_with_details(self):
        """Test MigrationError with operation details."""
        error = MigrationError(
            "Upload failed",
            operation="upload",
            source_path="s3://bucket/file.txt",
            destination_path="storacha://space/file.txt",
            objects_processed=42
        )
        
        assert error.operation == "upload"
        assert error.source_path == "s3://bucket/file.txt"
        assert error.destination_path == "storacha://space/file.txt"
        assert error.objects_processed == 42
        assert error.context["operation"] == "upload"
        assert error.context["objects_processed"] == 42
    
    def test_network_error_factory(self):
        """Test network_error factory method."""
        original = ConnectionError("Connection refused")
        error = MigrationError.network_error(
            "Failed to connect",
            "download",
            original
        )
        
        assert "Network error during download" in error.message
        assert "Failed to connect" in error.message
        assert error.operation == "download"
        assert error.original_error is original
    
    def test_timeout_error_factory(self):
        """Test timeout_error factory method."""
        error = MigrationError.timeout_error(
            "upload",
            300,
            objects_processed=15
        )
        
        assert "timed out after 300 seconds" in error.message
        assert "upload" in error.message
        assert error.operation == "upload"
        assert error.objects_processed == 15
    
    def test_timeout_error_without_objects_processed(self):
        """Test timeout_error without objects_processed."""
        error = MigrationError.timeout_error("sync", 600)
        
        assert "timed out after 600 seconds" in error.message
        assert error.objects_processed is None
    
    def test_validation_error_factory(self):
        """Test validation_error factory method."""
        error = MigrationError.validation_error(
            "File size mismatch",
            source_path="s3://bucket/file.txt",
            destination_path="storacha://space/file.txt"
        )
        
        assert "Validation error: File size mismatch" in error.message
        assert error.operation == "validation"
        assert error.source_path == "s3://bucket/file.txt"
        assert error.destination_path == "storacha://space/file.txt"
    
    def test_validation_error_without_paths(self):
        """Test validation_error without path parameters."""
        error = MigrationError.validation_error("Invalid format")
        
        assert "Validation error: Invalid format" in error.message
        assert error.source_path is None
        assert error.destination_path is None


class TestExceptionInheritance:
    """Test exception inheritance and polymorphism."""
    
    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from S3StorachaError."""
        assert issubclass(JSWrapperError, S3StorachaError)
        assert issubclass(ConfigurationError, S3StorachaError)
        assert issubclass(MigrationError, S3StorachaError)
    
    def test_all_exceptions_inherit_from_exception(self):
        """Test that all custom exceptions inherit from Exception."""
        assert issubclass(S3StorachaError, Exception)
        assert issubclass(JSWrapperError, Exception)
        assert issubclass(ConfigurationError, Exception)
        assert issubclass(MigrationError, Exception)
    
    def test_catch_specific_exception(self):
        """Test catching specific exception types."""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Config error")
        
        with pytest.raises(JSWrapperError):
            raise JSWrapperError("JS error")
        
        with pytest.raises(MigrationError):
            raise MigrationError("Migration error")
    
    def test_catch_base_exception(self):
        """Test catching base exception catches all custom exceptions."""
        exceptions = [
            ConfigurationError("Config error"),
            JSWrapperError("JS error"),
            MigrationError("Migration error")
        ]
        
        for exc in exceptions:
            with pytest.raises(S3StorachaError):
                raise exc
    
    def test_exception_context_preserved_through_inheritance(self):
        """Test that context functionality works in all exception types."""
        exceptions = [
            JSWrapperError("JS error", return_code=1),
            ConfigurationError("Config error", config_type="TestConfig"),
            MigrationError("Migration error", operation="test")
        ]
        
        for exc in exceptions:
            exc.add_context("test_key", "test_value")
            assert exc.context["test_key"] == "test_value"
            assert "test_key=test_value" in str(exc)

"""A tool for migrating objects from AWS S3 to Storacha"""

__version__ = "0.0.1"

# Setup and authentication helpers
from .setup_helpers import (
    install_js_dependencies,
    verify_installation,
    print_installation_status,
    check_nodejs_installed,
    check_js_dependencies_installed,
)

from .auth_helper import StorachaAuthHelper

# Configuration classes
from .config import (
    S3Config,
    StorachaConfig,
    MigrationConfig,
    ConfigurationParser,
)

# Exception classes
from .exceptions import (
    S3StorachaError,
    JSWrapperError,
    ConfigurationError,
    MigrationError,
)

# Error handling
from .error_handler import (
    ErrorHandler,
    RetryHandler,
    get_error_handler,
    get_retry_handler,
    with_error_handling,
    handle_subprocess_error,
    handle_validation_error,
)

# JavaScript wrapper management
from .js_wrapper import (
    JSWrapperManager,
    validate_nodejs_environment,
    find_js_script,
)

# Data models
from .models import (
    MigrationRequest,
    MigrationResult,
    MigrationProgress,
    MigrationStatus,
    S3Object,
    ProgressCallback,
)

# API layer
from .api import (
    S3ToStorachaMigrator,
    migrate_s3_to_storacha,
)

# Progress reporting
from .progress import (
    ProgressReporter,
    ProgressTracker,
    create_console_progress_callback,
    create_logging_progress_callback,
)

# CLI interface
from .cli import main as cli_main

__all__ = [
    # Configuration
    "S3Config",
    "StorachaConfig",
    "MigrationConfig",
    "ConfigurationParser",
    # Exceptions
    "S3StorachaError",
    "JSWrapperError",
    "ConfigurationError",
    "MigrationError",
    # Error handling
    "ErrorHandler",
    "RetryHandler",
    "get_error_handler",
    "get_retry_handler",
    "with_error_handling",
    "handle_subprocess_error",
    "handle_validation_error",
    # JavaScript wrapper
    "JSWrapperManager",
    "validate_nodejs_environment",
    "find_js_script",
    # Data models
    "MigrationRequest",
    "MigrationResult",
    "MigrationProgress",
    "MigrationStatus",
    "S3Object",
    "ProgressCallback",
    # API layer
    "S3ToStorachaMigrator",
    "migrate_s3_to_storacha",
    # Progress reporting
    "ProgressReporter",
    "ProgressTracker",
    "create_console_progress_callback",
    "create_logging_progress_callback",
    # CLI interface
    "cli_main",
    # Setup and authentication helpers
    "install_js_dependencies",
    "verify_installation",
    "print_installation_status",
    "check_nodejs_installed",
    "check_js_dependencies_installed",
    "StorachaAuthHelper",
]

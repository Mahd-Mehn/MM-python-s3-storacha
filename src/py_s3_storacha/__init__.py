"""A tool for migrating objects from AWS S3 to Storacha"""

__version__ = "0.0.1"

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
]

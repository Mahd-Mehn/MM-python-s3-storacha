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
]

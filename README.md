# py-s3-storacha

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/py-s3-storacha.svg)](https://badge.fury.io/py/py-s3-storacha)

A Python library and CLI tool for migrating objects from AWS S3 to Storacha storage. This library wraps an existing JavaScript implementation, providing both programmatic API access and command-line interface for seamless data migration.

## 🚀 Features

- **🐍 Python API**: Integrate S3 to Storacha migration into your Python applications
- **⚡ CLI Tool**: Command-line interface for standalone usage and automation
- **🔄 Automatic Retry**: Built-in retry logic with exponential backoff for transient failures
- **📊 Progress Tracking**: Real-time progress reporting during migration operations
- **🛡️ Error Handling**: Comprehensive error handling with meaningful error messages
- **🔧 Configurable**: Flexible configuration via arguments, environment variables, or config files
- **📝 Type Hints**: Full type hint support for better development experience
- **🌐 Cross-Platform**: Works on Windows, macOS, and Linux

## 📋 Requirements

- **Python 3.10+**
- **Node.js 14+** (for JavaScript wrapper execution)
- **AWS S3 credentials** (access key, secret key, region)
- **Storacha API credentials** (API key, space name)

## 🔧 Installation

### From PyPI (Recommended)

```bash
pip install py-s3-storacha
```

### From Source

```bash
git clone https://github.com/Mahd-Mehn/MM-python-s3-storacha.git
cd MM-python-s3-storacha
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/Mahd-Mehn/MM-python-s3-storacha.git
cd MM-python-s3-storacha
pip install -e ".[dev]"
```

## 🚀 Quick Start

### CLI Usage

```bash
# Basic migration
py-s3-storacha \
  --s3-bucket my-bucket \
  --s3-region us-east-1 \
  --storacha-space my-space \
  --storacha-key YOUR_API_KEY \
  --source-path folder/ \
  --dest-path backup/

# Migration with patterns
py-s3-storacha \
  --s3-bucket my-bucket \
  --s3-region us-east-1 \
  --storacha-space my-space \
  --storacha-key YOUR_API_KEY \
  --source-path folder/ \
  --dest-path backup/ \
  --include-pattern "*.jpg" \
  --exclude-pattern "temp/*"

# Dry run with verbose output
py-s3-storacha \
  --s3-bucket my-bucket \
  --s3-region us-east-1 \
  --storacha-space my-space \
  --storacha-key YOUR_API_KEY \
  --source-path folder/ \
  --dest-path backup/ \
  --dry-run --verbose
```

### Python API Usage

```python
import asyncio
from py_s3_storacha import (
    S3Config, 
    StorachaConfig, 
    MigrationConfig,
    migrate_s3_to_storacha
)

async def main():
    # Configure S3
    s3_config = S3Config(
        access_key_id="your-access-key",
        secret_access_key="your-secret-key",
        region="us-east-1",
        bucket_name="my-bucket"
    )
    
    # Configure Storacha
    storacha_config = StorachaConfig(
        api_key="your-storacha-api-key",
        endpoint_url="https://api.storacha.network",
        space_name="my-space"
    )
    
    # Configure migration options
    migration_config = MigrationConfig(
        batch_size=50,
        timeout_seconds=600,
        retry_attempts=3,
        verbose=True
    )
    
    # Execute migration
    result = await migrate_s3_to_storacha(
        s3_config=s3_config,
        storacha_config=storacha_config,
        source_path="folder/",
        destination_path="backup/",
        migration_config=migration_config
    )
    
    print(f"Migration completed: {result.objects_migrated} objects migrated")
    print(f"Total size: {result.total_size_bytes} bytes")
    print(f"Duration: {result.duration_seconds:.2f} seconds")

# Run the migration
asyncio.run(main())
```

### Advanced Usage with Progress Tracking

```python
import asyncio
from py_s3_storacha import (
    S3ToStorachaMigrator,
    MigrationRequest,
    MigrationProgress
)

def progress_callback(progress: MigrationProgress):
    """Handle progress updates"""
    print(f"Progress: {progress.progress_percentage:.1f}% "
          f"({progress.objects_completed}/{progress.total_objects} objects)")

async def advanced_migration():
    # Create migrator instance
    migrator = S3ToStorachaMigrator(
        s3_config=s3_config,
        storacha_config=storacha_config,
        migration_config=migration_config
    )
    
    # Create migration request
    request = MigrationRequest(
        source_path="data/",
        destination_path="backup/data/",
        include_pattern="*.json",
        overwrite_existing=False,
        verify_checksums=True
    )
    
    # Execute with progress tracking
    result = await migrator.migrate(
        request=request,
        progress_callback=progress_callback
    )
    
    return result

asyncio.run(advanced_migration())
```

## ⚙️ Configuration

### Environment Variables

Set these environment variables to avoid passing credentials via command line:

```bash
# S3 Configuration
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
export S3_ENDPOINT_URL="https://custom-s3-endpoint.com"  # Optional

# Storacha Configuration
export STORACHA_API_KEY="your-storacha-api-key"
export STORACHA_ENDPOINT_URL="https://api.storacha.network"  # Optional
```

### Configuration File

Create a configuration file (JSON, YAML, or TOML):

```json
{
  "s3": {
    "access_key_id": "your-access-key",
    "secret_access_key": "your-secret-key",
    "region": "us-east-1",
    "bucket_name": "my-bucket"
  },
  "storacha": {
    "api_key": "your-storacha-api-key",
    "endpoint_url": "https://api.storacha.network",
    "space_name": "my-space"
  },
  "migration": {
    "batch_size": 100,
    "timeout_seconds": 300,
    "retry_attempts": 3,
    "verbose": true
  }
}
```

Use with CLI:
```bash
py-s3-storacha --config-file config.json --source-path folder/ --dest-path backup/
```

## 📖 CLI Reference

### Required Arguments

- `--s3-bucket`: S3 bucket name
- `--storacha-space`: Storacha space name  
- `--source-path`: Source path in S3 (e.g., "folder/" or "file.txt")
- `--dest-path`: Destination path in Storacha

### S3 Configuration

- `--s3-access-key`: S3 access key ID (or use `AWS_ACCESS_KEY_ID`)
- `--s3-secret-key`: S3 secret access key (or use `AWS_SECRET_ACCESS_KEY`)
- `--s3-region`: S3 region (or use `AWS_DEFAULT_REGION`, default: us-east-1)
- `--s3-endpoint-url`: Custom S3 endpoint URL (or use `S3_ENDPOINT_URL`)

### Storacha Configuration

- `--storacha-api-key`: Storacha API key (or use `STORACHA_API_KEY`)
- `--storacha-endpoint-url`: Storacha endpoint URL (or use `STORACHA_ENDPOINT_URL`)

### Migration Options

- `--include-pattern`: Include only objects matching this pattern (glob syntax)
- `--exclude-pattern`: Exclude objects matching this pattern (glob syntax)
- `--overwrite-existing`: Overwrite existing objects in destination
- `--no-verify-checksums`: Skip checksum verification during migration
- `--batch-size`: Number of objects to process in each batch (default: 100)
- `--timeout`: Timeout for migration operation in seconds (default: 300)
- `--retry-attempts`: Number of retry attempts for failed operations (default: 3)
- `--dry-run`: Show what would be migrated without actually doing it
- `--verbose`: Enable verbose output
- `--quiet`: Suppress progress output (errors still shown)
- `--config-file`: Load configuration from file (JSON, YAML, or TOML)

## 🛡️ Error Handling

The library provides comprehensive error handling with automatic retries:

### Error Types

- **ConfigurationError**: Invalid or missing configuration
- **JSWrapperError**: JavaScript execution failures
- **MigrationError**: Migration operation failures
- **NetworkError**: Network connectivity issues

### Retry Logic

- **Network operations**: 3 retries with exponential backoff
- **JavaScript subprocess failures**: 2 retries with process restart
- **Configuration errors**: No retries (immediate failure)

### Example Error Handling

```python
from py_s3_storacha import (
    ConfigurationError,
    MigrationError,
    JSWrapperError
)

try:
    result = await migrate_s3_to_storacha(...)
except ConfigurationError as e:
    print(f"Configuration error: {e}")
except MigrationError as e:
    print(f"Migration failed: {e}")
    print(f"Objects processed: {e.objects_processed}")
except JSWrapperError as e:
    print(f"JavaScript wrapper error: {e}")
    print(f"Return code: {e.return_code}")
```

## 🧪 Testing

Run the test suite:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=py_s3_storacha

# Run specific test categories
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/MM-python-s3-storacha.git`
3. Create a virtual environment: `python -m venv venv`
4. Activate it: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
5. Install in development mode: `pip install -e ".[dev]"`
6. Run tests: `pytest`

### Code Quality

We use several tools to maintain code quality:

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking
pyright
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built on top of existing JavaScript S3 to Storacha implementation
- Uses [hatchling](https://hatch.pypa.io/) for modern Python packaging
- Inspired by the need for seamless data migration between cloud storage providers

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Mahd-Mehn/MM-python-s3-storacha/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Mahd-Mehn/MM-python-s3-storacha/discussions)
- **Documentation**: [Full Documentation](https://github.com/Mahd-Mehn/MM-python-s3-storacha/wiki)

## 🗺️ Roadmap

- [ ] Support for additional cloud storage providers
- [ ] GUI interface for non-technical users
- [ ] Incremental sync capabilities
- [ ] Advanced filtering and transformation options
- [ ] Performance optimizations for large-scale migrations

---

**Made with ❤️ by the py-s3-storacha team**
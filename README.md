# py-s3-storacha

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)

A Python library for migrating files from AWS S3 to Storacha (IPFS). Upload your S3 data to the decentralized web with a simple Python API or CLI tool.

## ✨ What is This?

This library makes it easy to migrate your files from Amazon S3 to Storacha, a decentralized storage network built on IPFS. Your files become permanently accessible via IPFS gateways and content-addressed by their CID (Content Identifier).

## 🚀 Features

- **Simple Python API** - Integrate S3 to Storacha migration in a few lines of code
- **Async Support** - Built on asyncio for efficient concurrent operations
- **Progress Tracking** - Real-time progress callbacks during migration
- **Error Handling** - Comprehensive error handling with automatic retries
- **Flexible Configuration** - Environment variables, config files, or direct parameters
- **Type Safe** - Full type hints for better IDE support
- **IPFS Integration** - Files become permanently accessible via IPFS gateways

## 📋 Requirements

- Python 3.10 or higher
- Node.js 18 or higher (required by Storacha client)
- AWS S3 credentials
- Storacha account (sign up at [storacha.network](https://storacha.network))

## 🔧 Installation

### Quick Install (Recommended)

```bash
# 1. Install the package
pip install git+https://github.com/Mahd-Mehn/MM-python-s3-storacha.git

# 2. Install JavaScript dependencies (automatic helper)
python -m py_s3_storacha.setup_helpers

# 3. Set up Storacha authentication (interactive)
python -m py_s3_storacha.auth_helper --setup
```

### Manual Install

```bash
# 1. Clone and install
git clone https://github.com/Mahd-Mehn/MM-python-s3-storacha.git
cd MM-python-s3-storacha
pip install -e ".[dev]"

# 2. Install JavaScript dependencies
py-s3-storacha-setup

# 3. Set up authentication
py-s3-storacha-auth --setup
```

### Verify Installation

```bash
# Check installation status
py-s3-storacha-setup --check

# Check authentication status
py-s3-storacha-auth --status
```

### What Gets Installed

The installation process:
1. ✅ Installs Python package
2. ✅ Checks for Node.js 18+ (required)
3. ✅ Installs `@storacha/client` and `@aws-sdk/client-s3` via npm
4. ✅ Sets up Storacha authentication (email-based)
5. ✅ Creates a Storacha space for your uploads

## 🚀 Quick Start

### Step 1: Authenticate with Storacha

First time only - authenticate with your email:

```bash
# Install Storacha CLI
npm install -g @storacha/cli

# Login (check your email for verification)
storacha login your-email@example.com

# Create a space
storacha space create my-migration-space
```

### Step 2: Set Up Configuration

Create a `.env` file:

```bash
# S3 Configuration
S3_ACCESS_KEY_ID=your_aws_access_key
S3_SECRET_ACCESS_KEY=your_aws_secret_key
S3_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name

# Storacha Configuration
STORACHA_API_KEY=your-email@example.com
STORACHA_ENDPOINT_URL=https://api.storacha.network
STORACHA_SPACE_NAME=my-migration-space

# Migration Settings (optional)
MIGRATION_DRY_RUN=false
MIGRATION_VERBOSE=true
```

### Step 3: Run Migration

```python
import asyncio
from py_s3_storacha import (
    S3Config,
    StorachaConfig,
    MigrationRequest,
    S3ToStorachaMigrator,
)

async def migrate():
    # Load configuration from environment
    s3_config = S3Config.from_env()
    storacha_config = StorachaConfig.from_env()

    # Create migrator
    migrator = S3ToStorachaMigrator(s3_config, storacha_config)

    # Create migration request
    request = MigrationRequest(
        source_path="my-folder/",
        destination_path="backup/"
    )

    # Execute migration
    result = await migrator.migrate(request)

    # Access your files via IPFS
    print(f"✓ Migrated {result.objects_migrated} files")
    print(f"✓ Access via: https://{result.root_cid}.ipfs.storacha.link/")

    return result

# Run it
asyncio.run(migrate())
```

That's it! Your files are now on IPFS.

## 📖 API Reference

### Configuration Classes

#### S3Config

```python
from py_s3_storacha import S3Config

# Create from parameters
config = S3Config(
    access_key_id="your_key",
    secret_access_key="your_secret",
    region="us-east-1",
    bucket_name="my-bucket",
    endpoint_url="https://s3.amazonaws.com"  # Optional
)

# Or load from environment variables
config = S3Config.from_env(prefix="S3_")

# Or from dictionary
config = S3Config.from_dict({
    "access_key_id": "your_key",
    "secret_access_key": "your_secret",
    "region": "us-east-1",
    "bucket_name": "my-bucket"
})
```

#### StorachaConfig

```python
from py_s3_storacha import StorachaConfig

# Create from parameters
config = StorachaConfig(
    api_key="your-email@example.com",  # Your email for authentication
    endpoint_url="https://api.storacha.network",
    space_name="my-space"
)

# Or load from environment
config = StorachaConfig.from_env(prefix="STORACHA_")
```

#### MigrationConfig

```python
from py_s3_storacha import MigrationConfig

config = MigrationConfig(
    batch_size=100,           # Objects per batch
    timeout_seconds=300,      # Operation timeout
    retry_attempts=3,         # Retry failed operations
    verbose=True,             # Detailed logging
    dry_run=False            # Set True to test without uploading
)
```

### Migration Classes

#### S3ToStorachaMigrator

Main class for performing migrations:

```python
from py_s3_storacha import S3ToStorachaMigrator, MigrationRequest

# Create migrator
migrator = S3ToStorachaMigrator(
    s3_config=s3_config,
    storacha_config=storacha_config,
    migration_config=migration_config  # Optional
)

# Create request
request = MigrationRequest(
    source_path="folder/",
    destination_path="backup/",
    include_pattern="*.jpg",      # Optional: only migrate matching files
    exclude_pattern="temp/*",     # Optional: skip matching files
    overwrite_existing=False,     # Optional: skip existing files
    verify_checksums=True         # Optional: verify file integrity
)

# Execute migration
result = await migrator.migrate(request)
```

#### MigrationResult

Returned after migration completes:

```python
result.success              # bool: True if successful
result.objects_migrated     # int: Number of files migrated
result.total_size_bytes     # int: Total bytes transferred
result.duration_seconds     # float: Time taken
result.errors               # list: Any errors encountered
result.warnings             # list: Warnings (includes root CID)
result.skipped_objects      # list: Files skipped
result.failed_objects       # list: Files that failed
```

### Progress Tracking

```python
from py_s3_storacha import MigrationProgress

def on_progress(progress: MigrationProgress):
    print(f"Progress: {progress.progress_percentage:.1f}%")
    print(f"Files: {progress.objects_completed}/{progress.total_objects}")
    print(f"Bytes: {progress.bytes_transferred}/{progress.total_bytes}")

result = await migrator.migrate(request, progress_callback=on_progress)
```

## � Authentication

### Storacha Authentication

Storacha uses email-based authentication with UCAN delegations. The first time you run a migration:

1. **The script sends a verification email** to the address you provide
2. **Click the verification link** in your email
3. **The script continues automatically** once verified
4. **Credentials are stored** for future use

```python
# First run - requires email verification
storacha_config = StorachaConfig(
    api_key="your-email@example.com",  # Your email
    endpoint_url="https://api.storacha.network",
    space_name="my-space"
)

# Subsequent runs - uses stored credentials automatically
```

### Alternative: Use Storacha CLI

If you prefer, authenticate once with the CLI:

```bash
npm install -g @storacha/cli
storacha login your-email@example.com
storacha space create my-space
```

Then the library will use those credentials automatically.

### S3 Authentication

Standard AWS credentials:

```bash
# Option 1: Environment variables
export S3_ACCESS_KEY_ID=your_key
export S3_SECRET_ACCESS_KEY=your_secret

# Option 2: AWS credentials file (~/.aws/credentials)
# Option 3: IAM role (if running on EC2/ECS)
```

## 🛡️ Error Handling

### Exception Types

```python
from py_s3_storacha import (
    S3StorachaError,        # Base exception
    ConfigurationError,     # Invalid configuration
    MigrationError,         # Migration failures
    JSWrapperError         # JavaScript execution errors
)

try:
    result = await migrator.migrate(request)
except ConfigurationError as e:
    print(f"Config error: {e}")
    print(f"Context: {e.context}")
except MigrationError as e:
    print(f"Migration failed: {e}")
    print(f"Failed objects: {e.failed_objects}")
except S3StorachaError as e:
    print(f"Error: {e}")
```

### Automatic Retries

The library automatically retries failed operations:

- **Network errors**: 3 retries with exponential backoff
- **Transient failures**: Automatic retry with backoff
- **Configuration errors**: No retry (fail fast)

### Accessing Error Details

```python
try:
    result = await migrator.migrate(request)
except MigrationError as e:
    # Get error context
    print(f"Operation: {e.operation}")
    print(f"Source: {e.source_path}")
    print(f"Destination: {e.destination_path}")
    print(f"Objects processed: {e.objects_processed}")

    # Get original error
    if e.original_error:
        print(f"Caused by: {e.original_error}")
```

## 🛠️ Helper Commands

The library includes helper commands for setup and authentication:

### Setup Helper

```bash
# Install JavaScript dependencies
py-s3-storacha-setup

# Force reinstall
py-s3-storacha-setup --force

# Check installation status
py-s3-storacha-setup --check
```

### Authentication Helper

```bash
# Interactive setup
py-s3-storacha-auth --setup

# Setup with specific email
py-s3-storacha-auth --setup --email you@example.com

# Check authentication status
py-s3-storacha-auth --status
```

### Programmatic Usage

```python
from py_s3_storacha import (
    install_js_dependencies,
    verify_installation,
    StorachaAuthHelper
)

# Install JS dependencies
install_js_dependencies()

# Check installation
status = verify_installation()
print(f"Ready: {status['ready']}")

# Setup authentication
helper = StorachaAuthHelper()
helper.setup_authentication(email="you@example.com")
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

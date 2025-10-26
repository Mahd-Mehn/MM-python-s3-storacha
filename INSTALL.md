# Installation Guide

## Automated Installation

Run these commands in order:

```bash
# 1. Install Python package
pip install -e ".[dev]"

# 2. Install JavaScript dependencies
python -m py_s3_storacha.setup_helpers

# 3. Set up Storacha authentication
python -m py_s3_storacha.auth_helper --setup
```

## What Each Step Does

### Step 1: Python Package
- Installs py-s3-storacha Python library
- Installs Python dependencies (httpx, aioboto3)
- Creates CLI commands

### Step 2: JavaScript Dependencies
- Checks for Node.js 18+ (required)
- Installs @storacha/client
- Installs @aws-sdk/client-s3
- Verifies installation

### Step 3: Storacha Authentication
- Installs Storacha CLI (if needed)
- Authenticates with your email
- Creates a space for uploads
- Stores credentials for future use

## Verification

```bash
# Check everything is installed
py-s3-storacha-setup --check

# Check authentication
py-s3-storacha-auth --status
```

## Troubleshooting

### Node.js Not Found

```bash
# macOS
brew install node

# Ubuntu/Debian
sudo apt install nodejs npm

# Or download from https://nodejs.org
```

### npm Install Fails

```bash
# Clear cache and retry
npm cache clean --force
python -m py_s3_storacha.setup_helpers --force
```

### Authentication Issues

```bash
# Re-authenticate
storacha login your-email@example.com

# Or use the helper
py-s3-storacha-auth --setup --email your-email@example.com
```

## Using the Library

After installation, you can:

```python
from py_s3_storacha import (
    S3Config,
    StorachaConfig,
    S3ToStorachaMigrator,
    MigrationRequest
)

# Your code here...
```

Or use the CLI:

```bash
py-s3-storacha --help
```

## Helper Commands

```bash
# Install/reinstall JS dependencies
py-s3-storacha-setup
py-s3-storacha-setup --force  # Force reinstall

# Check installation
py-s3-storacha-setup --check

# Set up authentication
py-s3-storacha-auth --setup

# Check auth status
py-s3-storacha-auth --status

# Set up with specific email
py-s3-storacha-auth --setup --email you@example.com --space my-space
```

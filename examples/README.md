# Examples

This directory contains example scripts and utilities for using the S3 to Storacha migration library.

## Quick Start

### 1. Set Up Configuration

Copy the example config and edit with your credentials:

```bash
cp config.example.json config.json
# Edit config.json with your credentials
```

Or create a `.env` file:

```bash
# S3 Configuration
S3_ACCESS_KEY_ID=your_aws_access_key
S3_SECRET_ACCESS_KEY=your_aws_secret_key
S3_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name

# Storacha Configuration
STORACHA_API_KEY=your-email@example.com
STORACHA_ENDPOINT_URL=https://api.storacha.network
STORACHA_SPACE_NAME=your-space-name

# Migration Settings
MIGRATION_DRY_RUN=false
MIGRATION_VERBOSE=true
```

### 2. Authenticate with Storacha

Run the setup script:

```bash
./setup_storacha.sh
```

This will guide you through:
- Installing Storacha CLI (if needed)
- Logging in with your email
- Creating a space

### 3. Run Migration

```bash
python migrate.py "source-folder/" "destination-folder/"
```

## Files

### Scripts

- **`migrate.py`** - Main migration script
  ```bash
  # Basic usage
  python migrate.py "folder/" "backup/"
  
  # Uses configuration from .env file
  ```

- **`diagnose_s3.py`** - Diagnose S3 connection issues
  ```bash
  python diagnose_s3.py
  
  # Tests different S3 endpoint configurations
  # Helps identify connection problems
  ```

- **`setup_storacha.sh`** - Set up Storacha authentication
  ```bash
  ./setup_storacha.sh
  
  # Interactive setup for Storacha
  ```

- **`setup_localstack_test.sh`** - Set up LocalStack for testing
  ```bash
  ./setup_localstack_test.sh
  
  # Creates local S3 environment for testing
  ```

### Configuration Files

- **`config.example.json`** - Example JSON configuration
- **`config.json`** - Your actual configuration (gitignored)
- **`.env`** - Environment variables (gitignored)

## Usage Examples

### Basic Migration

```bash
# Set up environment
export S3_BUCKET_NAME=my-bucket
export STORACHA_API_KEY=me@example.com
export STORACHA_SPACE_NAME=my-space

# Run migration
python migrate.py "data/" "backup/"
```

### Dry Run

```bash
# Test without actually migrating
export MIGRATION_DRY_RUN=true
python migrate.py "data/" "backup/"
```

### With Configuration File

```bash
# Edit config.json with your settings
python migrate.py "data/" "backup/"
```

## Testing with LocalStack

For local testing without AWS:

```bash
# 1. Start LocalStack
docker run -d -p 4566:4566 localstack/localstack

# 2. Run setup
./setup_localstack_test.sh

# 3. Update .env to use LocalStack
S3_ENDPOINT_URL=http://localhost:4566

# 4. Run migration
python migrate.py "test-data/" "migrated/"
```

## Troubleshooting

### S3 Connection Issues

```bash
# Diagnose S3 connection
python diagnose_s3.py

# This will test different endpoint configurations
# and show which one works
```

### Storacha Authentication

```bash
# Re-authenticate
./setup_storacha.sh

# Or manually
storacha login your-email@example.com
storacha space ls
```

### Check Configuration

```bash
# Verify environment variables
env | grep -E "(S3_|STORACHA_|MIGRATION_)"

# Test configuration loading
python -c "
from py_s3_storacha import S3Config, StorachaConfig
s3 = S3Config.from_env()
storacha = StorachaConfig.from_env()
print(f'S3 Bucket: {s3.bucket_name}')
print(f'Storacha Space: {storacha.space_name}')
"
```

## Next Steps

After successful migration:

1. **Access your files via IPFS**
   - Check the migration output for the root CID
   - Access via: `https://{cid}.ipfs.storacha.link/`

2. **Verify the migration**
   - Check file count matches
   - Verify file sizes
   - Test file accessibility

3. **Integrate into your application**
   - See the main README for API usage
   - Use the migration script as a template

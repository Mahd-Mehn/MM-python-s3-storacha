# JavaScript Implementation for S3 to Storacha Migration

This directory contains the JavaScript implementation that performs the actual S3 to Storacha migration.

## Prerequisites

- Node.js 18+ (required by @storacha/client)
- npm 7+

## Installation

Install the required dependencies:

```bash
cd src/py_s3_storacha/js
npm install
```

This will install:
- `@storacha/client` - Storacha JavaScript client
- `@aws-sdk/client-s3` - AWS SDK for S3 operations

## Usage

The script reads JSON configuration from stdin and outputs JSON results to stdout.

### Standalone Usage

```bash
echo '{
  "s3": {
    "accessKeyId": "test",
    "secretAccessKey": "test",
    "region": "us-east-1",
    "bucketName": "test-bucket",
    "endpointUrl": "http://localhost:4566"
  },
  "storacha": {
    "apiKey": "your_api_key",
    "endpointUrl": "https://api.storacha.network",
    "spaceName": "test-space"
  },
  "migration": {
    "sourcePath": "test-data/",
    "destinationPath": "migrated/",
    "batchSize": 100,
    "timeoutSeconds": 300,
    "retryAttempts": 3,
    "verbose": true,
    "dryRun": true
  }
}' | node s3-to-storacha.js
```

### From Python

The Python wrapper automatically calls this script and handles stdin/stdout communication:

```python
from py_s3_storacha import S3ToStorachaMigrator, MigrationRequest

migrator = S3ToStorachaMigrator(s3_config, storacha_config)
request = MigrationRequest(source_path="data/", destination_path="backup/")
result = await migrator.migrate(request)
```

## Input Format

```json
{
  "s3": {
    "accessKeyId": "string (required)",
    "secretAccessKey": "string (required)",
    "region": "string (required)",
    "bucketName": "string (required)",
    "endpointUrl": "string (optional, for LocalStack/MinIO)"
  },
  "storacha": {
    "apiKey": "string (required)",
    "endpointUrl": "string (required)",
    "spaceName": "string (required)"
  },
  "migration": {
    "sourcePath": "string (required)",
    "destinationPath": "string (required)",
    "batchSize": "number (optional, default: 100)",
    "timeoutSeconds": "number (optional, default: 300)",
    "retryAttempts": "number (optional, default: 3)",
    "verbose": "boolean (optional, default: false)",
    "dryRun": "boolean (optional, default: false)",
    "overwriteExisting": "boolean (optional, default: false)",
    "verifyChecksums": "boolean (optional, default: true)",
    "includePattern": "string (optional, regex pattern)",
    "excludePattern": "string (optional, regex pattern)"
  }
}
```

## Output Format

```json
{
  "success": true,
  "objectsMigrated": 10,
  "totalSizeBytes": 1024000,
  "errors": [],
  "warnings": ["Files uploaded with root CID: bafybeiabc123..."],
  "skippedObjects": [],
  "failedObjects": []
}
```

## Features

- ✅ Lists objects from S3 bucket with prefix filtering
- ✅ Downloads files from S3 (supports LocalStack/MinIO)
- ✅ Uploads files to Storacha as a directory
- ✅ Batch processing for efficient uploads
- ✅ Include/exclude pattern filtering
- ✅ Dry run mode for testing
- ✅ Detailed error reporting
- ✅ Progress logging to stderr (doesn't interfere with JSON output)

## Storacha Integration

The script uses the official `@storacha/client` library to upload files to Storacha. Files are uploaded as a directory, which creates a single root CID that can be used to access all files via IPFS gateways.

### Accessing Uploaded Files

After a successful upload, files can be accessed via:

```
https://{root-cid}.ipfs.storacha.link/{file-path}
```

The root CID is included in the warnings array of the output.

## Authentication

### Storacha Authentication

The current implementation expects the Storacha client to be pre-authenticated. For production use, you'll need to:

1. **Option 1: Email Login** (Interactive)
   ```javascript
   const account = await client.login("your-email@example.com");
   await account.plan.wait();
   ```

2. **Option 2: Delegation** (Automated)
   - Create a space and delegation on your development machine
   - Export the delegation
   - Load it in the production environment

3. **Option 3: Environment Variables**
   - Store authentication tokens in environment variables
   - Load them when creating the client

See the [Storacha documentation](https://docs.storacha.network) for more details.

## Error Handling

- Errors are logged to stderr
- Failed objects are tracked in the `failedObjects` array
- The script exits with code 1 on failure, 0 on success
- All errors are included in the JSON output

## Development

### Testing

Test with LocalStack:

```bash
# Start LocalStack
docker run -d -p 4566:4566 localstack/localstack

# Create test bucket and upload files
aws --endpoint-url=http://localhost:4566 s3 mb s3://test-bucket
echo "test content" > test.txt
aws --endpoint-url=http://localhost:4566 s3 cp test.txt s3://test-bucket/

# Test the script
echo '{...config...}' | node s3-to-storacha.js
```

### Debugging

Enable verbose logging by setting `verbose: true` in the migration config. Logs are written to stderr and won't interfere with JSON output.

## Limitations

- Maximum file size depends on available memory (files are loaded into memory)
- Large directories may take significant time to upload
- Storacha rate limits may apply
- Authentication must be handled separately for production use

## Future Enhancements

- [ ] Streaming uploads for large files
- [ ] Parallel uploads with configurable concurrency
- [ ] Resume capability for interrupted migrations
- [ ] Checksum verification
- [ ] Progress reporting via separate channel
- [ ] Support for Storacha delegation-based auth
src 
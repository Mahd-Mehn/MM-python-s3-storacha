#!/usr/bin/env node
/**
 * S3 to Storacha Migration Script
 * 
 * This script reads JSON configuration from stdin, downloads files from S3,
 * and uploads them to Storacha. It outputs JSON results to stdout.
 * 
 * Input JSON format:
 * {
 *   "s3": {
 *     "accessKeyId": "...",
 *     "secretAccessKey": "...",
 *     "region": "...",
 *     "bucketName": "...",
 *     "endpointUrl": "..." (optional)
 *   },
 *   "storacha": {
 *     "apiKey": "...",
 *     "endpointUrl": "...",
 *     "spaceName": "..."
 *   },
 *   "migration": {
 *     "sourcePath": "...",
 *     "destinationPath": "...",
 *     "batchSize": 100,
 *     "timeoutSeconds": 300,
 *     "retryAttempts": 3,
 *     "verbose": false,
 *     "dryRun": false,
 *     "overwriteExisting": false,
 *     "verifyChecksums": true,
 *     "includePattern": "..." (optional),
 *     "excludePattern": "..." (optional)
 *   }
 * }
 * 
 * Output JSON format:
 * {
 *   "success": true,
 *   "objectsMigrated": 10,
 *   "totalSizeBytes": 1024000,
 *   "errors": [],
 *   "warnings": [],
 *   "skippedObjects": [],
 *   "failedObjects": []
 * }
 */

import { S3Client, ListObjectsV2Command, GetObjectCommand } from '@aws-sdk/client-s3';
import * as StorachaClient from '@storacha/client';
import { Readable } from 'stream';
import { Buffer } from 'buffer';

/**
 * Read JSON input from stdin
 */
async function readStdin() {
  return new Promise((resolve, reject) => {
    let data = '';
    
    process.stdin.setEncoding('utf8');
    
    process.stdin.on('data', (chunk) => {
      data += chunk;
    });
    
    process.stdin.on('end', () => {
      try {
        const parsed = JSON.parse(data);
        resolve(parsed);
      } catch (error) {
        reject(new Error(`Failed to parse JSON input: ${error.message}`));
      }
    });
    
    process.stdin.on('error', (error) => {
      reject(new Error(`Failed to read stdin: ${error.message}`));
    });
  });
}

/**
 * Write JSON output to stdout
 */
function writeOutput(data) {
  process.stdout.write(JSON.stringify(data, null, 2));
}

/**
 * Log verbose messages to stderr (won't interfere with JSON output)
 */
function log(message, verbose = false) {
  if (verbose) {
    process.stderr.write(`[INFO] ${message}\n`);
  }
}

/**
 * Log error messages to stderr
 */
function logError(message) {
  process.stderr.write(`[ERROR] ${message}\n`);
}

/**
 * Create S3 client from configuration
 */
function createS3Client(config) {
  const clientConfig = {
    region: config.region,
    credentials: {
      accessKeyId: config.accessKeyId,
      secretAccessKey: config.secretAccessKey,
    },
  };
  
  if (config.endpointUrl) {
    clientConfig.endpoint = config.endpointUrl;
    clientConfig.forcePathStyle = true; // Required for LocalStack/MinIO
  }
  
  return new S3Client(clientConfig);
}

/**
 * Create Storacha client from configuration
 * 
 * The apiKey in config should be an email address for authentication.
 * The spaceName will be used to find or create the space.
 */
async function createStorachaClient(config) {
  try {
    log(`Creating Storacha client...`, true);
    
    // Create a client with persistent store
    const client = await StorachaClient.create();
    
    log(`Storacha client created`, true);
    
    // Check if we already have spaces (from previous authentication)
    let spaces = client.spaces();
    log(`Found ${spaces.length} existing space(s) in client store`, true);
    
    // If no spaces, we need to authenticate
    if (spaces.length === 0) {
      log(`No existing spaces found, authentication required`, true);
      
      // The apiKey should be an email address for login
      // Check if it looks like an email
      if (!config.apiKey || !config.apiKey.includes('@')) {
        throw new Error(
          'Authentication required: Please provide an email address as STORACHA_API_KEY.\n' +
          'Example: STORACHA_API_KEY=your-email@example.com\n\n' +
          'The first time you run this, you will need to:\n' +
          '1. Check your email for a verification link\n' +
          '2. Click the link to authorize\n' +
          '3. The script will continue automatically\n\n' +
          'Subsequent runs will use the stored credentials.'
        );
      }
      
      log(`Logging in with email: ${config.apiKey}`, true);
      log(`⚠️  Check your email for verification link!`, true);
      
      try {
        // Login with email - this will send a verification email
        const account = await client.login(config.apiKey);
        log(`✓ Login successful!`, true);
        
        // Wait for payment plan (required for space creation)
        log(`Waiting for payment plan...`, true);
        await account.plan.wait();
        log(`✓ Payment plan confirmed`, true);
        
        // Create a space
        log(`Creating space: ${config.spaceName}`, true);
        const space = await client.createSpace(config.spaceName, { account });
        log(`✓ Space created: ${space.did()}`, true);
        
        // Refresh spaces list
        spaces = client.spaces();
        
      } catch (loginError) {
        throw new Error(
          `Login failed: ${loginError.message}\n\n` +
          'Make sure to:\n' +
          '1. Check your email for the verification link\n' +
          '2. Click the link within the timeout period\n' +
          '3. Ensure you have a payment plan set up\n\n' +
          'If you already authenticated with the CLI, the CLI and JavaScript client\n' +
          'use separate credential stores. You need to authenticate the JavaScript\n' +
          'client separately by providing your email as STORACHA_API_KEY.'
        );
      }
    }
    
    // Find the space to use
    let targetSpace = null;
    
    if (config.spaceName) {
      // Try to find space by name
      // Note: spaces might be objects with different structures
      targetSpace = spaces.find(s => {
        const name = typeof s.name === 'function' ? s.name() : s.name;
        return name === config.spaceName;
      });
      
      if (targetSpace) {
        const spaceName = typeof targetSpace.name === 'function' ? targetSpace.name() : targetSpace.name;
        log(`Found space by name: ${spaceName}`, true);
      } else {
        log(`Space '${config.spaceName}' not found, using first available`, true);
        targetSpace = spaces[0];
      }
    } else {
      // Use first available space
      targetSpace = spaces[0];
      log(`Using first available space`, true);
    }
    
    // Get the DID
    const spaceDid = typeof targetSpace.did === 'function' ? targetSpace.did() : targetSpace.did;
    const spaceName = typeof targetSpace.name === 'function' ? targetSpace.name() : (targetSpace.name || '(unnamed)');
    
    // Set the current space
    await client.setCurrentSpace(spaceDid);
    log(`✓ Current space set to: ${spaceDid}`, true);
    log(`  Space name: ${spaceName}`, true);
    
    return client;
    
  } catch (error) {
    throw new Error(`Failed to create Storacha client: ${error.message}`);
  }
}

/**
 * List objects in S3 bucket with optional prefix
 */
async function listS3Objects(s3Client, bucketName, prefix, verbose) {
  const objects = [];
  let continuationToken = undefined;
  
  log(`Listing objects in s3://${bucketName}/${prefix}`, verbose);
  
  do {
    const command = new ListObjectsV2Command({
      Bucket: bucketName,
      Prefix: prefix,
      ContinuationToken: continuationToken,
    });
    
    try {
      const response = await s3Client.send(command);
      
      if (response.Contents) {
        objects.push(...response.Contents);
      }
      
      continuationToken = response.NextContinuationToken;
    } catch (error) {
      throw new Error(`Failed to list S3 objects: ${error.message}`);
    }
  } while (continuationToken);
  
  log(`Found ${objects.length} objects`, verbose);
  return objects;
}

/**
 * Download object from S3
 */
async function downloadS3Object(s3Client, bucketName, key, verbose) {
  log(`Downloading s3://${bucketName}/${key}`, verbose);
  
  const command = new GetObjectCommand({
    Bucket: bucketName,
    Key: key,
  });
  
  try {
    const response = await s3Client.send(command);
    
    // Convert stream to buffer
    const chunks = [];
    for await (const chunk of response.Body) {
      chunks.push(chunk);
    }
    const buffer = Buffer.concat(chunks);
    
    log(`Downloaded ${buffer.length} bytes`, verbose);
    return buffer;
  } catch (error) {
    throw new Error(`Failed to download ${key}: ${error.message}`);
  }
}

/**
 * Upload file to Storacha
 */
async function uploadToStoracha(client, fileName, data, verbose) {
  log(`Uploading ${fileName} to Storacha (${data.length} bytes)`, verbose);
  
  try {
    // Create a File object from the buffer
    const file = new File([data], fileName, { type: 'application/octet-stream' });
    
    // Upload the file
    const cid = await client.uploadFile(file);
    
    log(`Uploaded ${fileName} with CID: ${cid}`, verbose);
    return cid.toString();
  } catch (error) {
    throw new Error(`Failed to upload ${fileName}: ${error.message}`);
  }
}

/**
 * Upload directory to Storacha
 */
async function uploadDirectoryToStoracha(client, files, verbose) {
  log(`Uploading ${files.length} files as directory to Storacha`, verbose);
  
  try {
    // Create File objects
    const fileObjects = files.map(({ name, data }) => 
      new File([data], name, { type: 'application/octet-stream' })
    );
    
    // Upload the directory
    const cid = await client.uploadDirectory(fileObjects);
    
    log(`Uploaded directory with root CID: ${cid}`, verbose);
    return cid.toString();
  } catch (error) {
    throw new Error(`Failed to upload directory: ${error.message}`);
  }
}

/**
 * Check if object matches include/exclude patterns
 */
function shouldIncludeObject(key, includePattern, excludePattern) {
  if (excludePattern && new RegExp(excludePattern).test(key)) {
    return false;
  }
  
  if (includePattern && !new RegExp(includePattern).test(key)) {
    return false;
  }
  
  return true;
}

/**
 * Main migration function
 */
async function migrate(config) {
  const { s3, storacha, migration } = config;
  const verbose = migration.verbose || false;
  
  const result = {
    success: false,
    objectsMigrated: 0,
    totalSizeBytes: 0,
    errors: [],
    warnings: [],
    skippedObjects: [],
    failedObjects: [],
  };
  
  try {
    log('Starting S3 to Storacha migration', verbose);
    
    // Validate configuration
    if (!s3.accessKeyId || !s3.secretAccessKey || !s3.region || !s3.bucketName) {
      throw new Error('Invalid S3 configuration: missing required fields');
    }
    
    if (!storacha.apiKey || !storacha.endpointUrl || !storacha.spaceName) {
      throw new Error('Invalid Storacha configuration: missing required fields');
    }
    
    // Create clients
    log('Creating S3 client', verbose);
    const s3Client = createS3Client(s3);
    
    log('Creating Storacha client', verbose);
    const storachaClient = await createStorachaClient(storacha);
    
    // Dry run check
    if (migration.dryRun) {
      log('DRY RUN MODE - No actual migration will occur', verbose);
      result.warnings.push('Dry run mode - no actual migration performed');
    }
    
    // List objects in S3
    const objects = await listS3Objects(
      s3Client,
      s3.bucketName,
      migration.sourcePath || '',
      verbose
    );
    
    if (objects.length === 0) {
      result.warnings.push('No objects found in source path');
      result.success = true;
      return result;
    }
    
    // Filter objects based on patterns
    const filteredObjects = objects.filter(obj => 
      shouldIncludeObject(
        obj.Key,
        migration.includePattern,
        migration.excludePattern
      )
    );
    
    if (filteredObjects.length < objects.length) {
      const skipped = objects.length - filteredObjects.length;
      result.warnings.push(`Skipped ${skipped} objects due to include/exclude patterns`);
    }
    
    log(`Processing ${filteredObjects.length} objects`, verbose);
    
    // Collect files for batch upload
    const filesToUpload = [];
    
    for (const obj of filteredObjects) {
      try {
        // Skip directories (keys ending with /)
        if (obj.Key.endsWith('/')) {
          log(`Skipping directory: ${obj.Key}`, verbose);
          result.skippedObjects.push(obj.Key);
          continue;
        }
        
        if (migration.dryRun) {
          log(`[DRY RUN] Would migrate: ${obj.Key} (${obj.Size} bytes)`, verbose);
          result.objectsMigrated++;
          result.totalSizeBytes += obj.Size || 0;
          continue;
        }
        
        // Download from S3
        const data = await downloadS3Object(s3Client, s3.bucketName, obj.Key, verbose);
        
        // Prepare file for upload
        const fileName = obj.Key.replace(migration.sourcePath || '', '');
        const destinationPath = migration.destinationPath 
          ? `${migration.destinationPath}/${fileName}`.replace(/\/+/g, '/')
          : fileName;
        
        filesToUpload.push({
          name: destinationPath,
          data: data,
          originalKey: obj.Key,
          size: data.length,
        });
        
        result.totalSizeBytes += data.length;
        
      } catch (error) {
        logError(`Failed to process ${obj.Key}: ${error.message}`);
        result.errors.push(`${obj.Key}: ${error.message}`);
        result.failedObjects.push(obj.Key);
      }
    }
    
    // Upload to Storacha (batch upload as directory)
    if (!migration.dryRun && filesToUpload.length > 0) {
      try {
        log(`Uploading ${filesToUpload.length} files to Storacha`, verbose);
        
        const rootCid = await uploadDirectoryToStoracha(
          storachaClient,
          filesToUpload,
          verbose
        );
        
        result.objectsMigrated = filesToUpload.length;
        result.warnings.push(`Files uploaded with root CID: ${rootCid}`);
        result.warnings.push(`Access via: https://${rootCid}.ipfs.storacha.link/`);
        
      } catch (error) {
        logError(`Failed to upload to Storacha: ${error.message}`);
        result.errors.push(`Storacha upload failed: ${error.message}`);
        result.failedObjects.push(...filesToUpload.map(f => f.originalKey));
      }
    }
    
    // Determine success
    result.success = result.errors.length === 0 && result.failedObjects.length === 0;
    
    if (result.success) {
      log('Migration completed successfully', verbose);
    } else {
      log(`Migration completed with ${result.errors.length} errors`, verbose);
    }
    
    return result;
    
  } catch (error) {
    logError(`Migration failed: ${error.message}`);
    result.errors.push(error.message);
    result.success = false;
    return result;
  }
}

/**
 * Main entry point
 */
async function main() {
  try {
    // Read configuration from stdin
    const config = await readStdin();
    
    // Perform migration
    const result = await migrate(config);
    
    // Write result to stdout
    writeOutput(result);
    
    // Exit with appropriate code
    process.exit(result.success ? 0 : 1);
    
  } catch (error) {
    logError(`Fatal error: ${error.message}`);
    
    // Write error result to stdout
    writeOutput({
      success: false,
      objectsMigrated: 0,
      totalSizeBytes: 0,
      errors: [error.message],
      warnings: [],
      skippedObjects: [],
      failedObjects: [],
    });
    
    process.exit(1);
  }
}

// Run main function
main();

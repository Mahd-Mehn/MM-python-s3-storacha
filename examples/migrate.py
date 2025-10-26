#!/usr/bin/env python3
"""
List all files in S3 bucket and migrate them to Storacha
"""

import json
import sys
from py_s3_storacha import (
    S3Config,
    StorachaConfig,
    MigrationConfig,
    S3ToStorachaMigrator,
    MigrationRequest,
)


def load_config(config_path: str = "examples/config.json"):
    """Load configuration from JSON file"""
    with open(config_path, "r") as f:
        return json.load(f)


def list_s3_files(s3_config: S3Config, prefix: str = ""):
    """List all files in S3 bucket"""
    import boto3
    from botocore.exceptions import ClientError

    print("\n" + "=" * 70)
    print("📂 Listing S3 Bucket Contents")
    print("=" * 70)
    print(f"Bucket: {s3_config.bucket_name}")
    print(f"Region: {s3_config.region}")
    if prefix:
        print(f"Prefix: {prefix}")
    print()

    # Create S3 client
    client_config = {
        "aws_access_key_id": s3_config.access_key_id,
        "aws_secret_access_key": s3_config.secret_access_key,
        "region_name": s3_config.region,
    }

    if s3_config.endpoint_url:
        client_config["endpoint_url"] = s3_config.endpoint_url

    s3 = boto3.client("s3", **client_config)

    try:
        # List all objects
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=s3_config.bucket_name, Prefix=prefix)

        all_objects = []
        total_size = 0

        for page in pages:
            if "Contents" in page:
                for obj in page["Contents"]:
                    all_objects.append(obj)
                    total_size += obj["Size"]

        if not all_objects:
            print("⚠️  No files found in bucket")
            return []

        # Display results
        print(f"✅ Found {len(all_objects)} files")
        print(f"💾 Total size: {total_size:,} bytes ({total_size / (1024**2):.2f} MB)")
        print()
        print("Files:")
        print("-" * 70)

        for i, obj in enumerate(all_objects, 1):
            size_mb = obj["Size"] / (1024**2)
            modified = obj["LastModified"].strftime("%Y-%m-%d %H:%M:%S")
            print(f"{i:3d}. {obj['Key']}")
            print(f"     Size: {size_mb:.2f} MB | Modified: {modified}")

        print("-" * 70)

        return all_objects

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_msg = e.response["Error"]["Message"]
        print(f"❌ Error: {error_code} - {error_msg}")

        if error_code == "AccessDenied":
            print("\n💡 Check your AWS credentials and IAM permissions")
        elif error_code == "NoSuchBucket":
            print("\n💡 Bucket doesn't exist or is in a different region")

        return []

    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
        return []


def migrate_to_storacha(
    s3_config: S3Config,
    storacha_config: StorachaConfig,
    migration_config: MigrationConfig,
    source_prefix: str = "",
    dest_prefix: str = "files/",
):
    """Migrate files from S3 to Storacha"""

    print("\n" + "=" * 70)
    print("🚀 Starting Migration to Storacha")
    print("=" * 70)
    print(f"Source: s3://{s3_config.bucket_name}/{source_prefix}")
    print(f"Destination: storacha://{storacha_config.space_name}/{dest_prefix}")
    print()

    if migration_config.dry_run:
        print("⚠️  DRY RUN MODE - No actual migration will occur")
    else:
        print("⚠️  ACTUAL MIGRATION - Data will be transferred to Storacha!")

    print()

    # Create migrator
    print("🔧 Creating migrator...")
    migrator = S3ToStorachaMigrator(
        s3_config=s3_config,
        storacha_config=storacha_config,
        migration_config=migration_config,
    )

    # Create migration request
    request = MigrationRequest(source_path=source_prefix, destination_path=dest_prefix)

    # Start migration
    print("⏳ Starting migration...")
    print("-" * 70)

    # Run async migration
    import asyncio

    result = asyncio.run(migrator.migrate(request))

    print("-" * 70)

    # Display results
    print("\n" + "=" * 70)
    print("📊 Migration Results")
    print("=" * 70)

    if result.success:
        print("✅ Status: SUCCESS")
    else:
        print("❌ Status: FAILED")
        if result.errors:
            print(f"Errors: {', '.join(result.errors)}")

    print(f"📦 Objects migrated: {result.objects_migrated}")
    print(
        f"💾 Total size: {result.total_size_bytes:,} bytes ({result.total_size_bytes / (1024**2):.2f} MB)"
    )
    print(f"⏱️  Duration: {result.duration_seconds:.2f} seconds")

    if result.warnings:
        print(f"\n⚠️  Warnings ({len(result.warnings)}):")
        for i, warning in enumerate(result.warnings, 1):
            print(f"{i}. {warning}")

    if result.errors:
        print(f"\n❌ Errors ({len(result.errors)}):")
        for i, error in enumerate(result.errors, 1):
            print(f"{i}. {error}")

    if result.skipped_objects:
        print(f"\n⏭️  Skipped ({len(result.skipped_objects)}):")
        for obj in result.skipped_objects[:5]:
            print(f"  - {obj}")
        if len(result.skipped_objects) > 5:
            print(f"  ... and {len(result.skipped_objects) - 5} more")

    if result.failed_objects:
        print(f"\n❌ Failed ({len(result.failed_objects)}):")
        for obj in result.failed_objects[:5]:
            print(f"  - {obj}")
        if len(result.failed_objects) > 5:
            print(f"  ... and {len(result.failed_objects) - 5} more")

    print("=" * 70)

    return result


def main():
    print("=" * 70)
    print("S3 to Storacha Migration Tool")
    print("=" * 70)

    # Load configuration
    try:
        config = load_config()
        print("✓ Configuration loaded")
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return 1

    # Create config objects
    s3_config = S3Config(
        access_key_id=config["s3"]["access_key_id"],
        secret_access_key=config["s3"]["secret_access_key"],
        region=config["s3"]["region"],
        bucket_name=config["s3"]["bucket_name"],
        endpoint_url=config["s3"].get("endpoint_url"),
    )

    storacha_config = StorachaConfig(
        api_key=config["storacha"]["api_key"],
        endpoint_url=config["storacha"]["endpoint_url"],
        space_name=config["storacha"]["space_name"],
    )

    migration_config = MigrationConfig(
        batch_size=config["migration"]["batch_size"],
        timeout_seconds=config["migration"]["timeout_seconds"],
        retry_attempts=config["migration"]["retry_attempts"],
        verbose=config["migration"]["verbose"],
        dry_run=config["migration"]["dry_run"],
    )

    # Step 1: List all files in S3
    objects = list_s3_files(s3_config)

    if not objects:
        print("\n❌ No files to migrate")
        return 1

    # Step 2: Ask for confirmation
    print("\n" + "=" * 70)
    print("⚠️  Migration Confirmation")
    print("=" * 70)
    print(f"You are about to migrate {len(objects)} files from S3 to Storacha")
    print(f"Total size: {sum(obj['Size'] for obj in objects) / (1024**2):.2f} MB")

    if migration_config.dry_run:
        print("\n✓ Running in DRY RUN mode - no actual migration will occur")
        response = "y"
    else:
        print("\n⚠️  This will upload data to Storacha/IPFS")
        response = input("\nProceed with migration? (y/n): ").lower().strip()

    if response != "y":
        print("\n❌ Migration cancelled")
        return 0

    # Step 3: Migrate to Storacha
    # Use empty string for root (not "/") to match all objects
    result = migrate_to_storacha(
        s3_config=s3_config,
        storacha_config=storacha_config,
        migration_config=migration_config,
        source_prefix="Aunty Funke documents/",  # Migrate files from this folder
        dest_prefix="migrated/",
    )

    if result.success:
        print("\n🎉 Migration completed successfully!")
        print("Your files are now on Storacha/IPFS!")
        return 0
    else:
        print("\n❌ Migration failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

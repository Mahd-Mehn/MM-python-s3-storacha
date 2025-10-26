#!/usr/bin/env python3
"""
Example migration script - demonstrates how to use the library
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from py_s3_storacha import (
    S3Config,
    StorachaConfig,
    MigrationConfig,
    MigrationRequest,
    S3ToStorachaMigrator,
)


async def main():
    print("="*70)
    print("S3 to Storacha Migration Example")
    print("="*70)
    print()
    
    # Load configuration from environment
    s3_config = S3Config.from_env(prefix="S3_")
    storacha_config = StorachaConfig.from_env(prefix="STORACHA_")
    migration_config = MigrationConfig(
        batch_size=int(os.getenv("MIGRATION_BATCH_SIZE", "100")),
        timeout_seconds=int(os.getenv("MIGRATION_TIMEOUT_SECONDS", "300")),
        retry_attempts=int(os.getenv("MIGRATION_RETRY_ATTEMPTS", "3")),
        verbose=os.getenv("MIGRATION_VERBOSE", "true").lower() == "true",
        dry_run=os.getenv("MIGRATION_DRY_RUN", "true").lower() == "true"
    )
    
    print(f"✓ Configuration loaded")
    print(f"  S3 Bucket: {s3_config.bucket_name}")
    print(f"  Storacha Space: {storacha_config.space_name}")
    print(f"  Mode: {'DRY RUN' if migration_config.dry_run else 'ACTUAL MIGRATION'}")
    print()
    
    # Get source and destination from command line or use defaults
    source_path = sys.argv[1] if len(sys.argv) > 1 else "/"
    destination_path = sys.argv[2] if len(sys.argv) > 2 else "migrated/"
    
    print("="*70)
    print(f"📂 Source: s3://{s3_config.bucket_name}/{source_path}")
    print(f"📂 Destination: storacha://{storacha_config.space_name}/{destination_path}")
    print("="*70)
    print()
    
    if migration_config.dry_run:
        print("ℹ️  DRY RUN MODE - No actual data will be transferred")
    else:
        print("⚠️  ACTUAL MIGRATION - Data will be transferred to Storacha!")
    
    print()
    
    try:
        # Create migrator
        print("🔧 Creating migrator...")
        migrator = S3ToStorachaMigrator(
            s3_config=s3_config,
            storacha_config=storacha_config,
            migration_config=migration_config
        )
        
        # Create request
        request = MigrationRequest(
            source_path=source_path,
            destination_path=destination_path
        )
        
        # Run migration
        print("⏳ Starting migration...")
        print("-" * 70)
        result = await migrator.migrate(request)
        print("-" * 70)
        print()
        
        # Display results
        print("="*70)
        print("📊 Migration Results")
        print("="*70)
        print()
        
        if result.success:
            print("✅ Status: SUCCESS")
        else:
            print("❌ Status: FAILED")
        
        print()
        print(f"📦 Objects migrated: {result.objects_migrated}")
        print(f"💾 Total size: {result.total_size_bytes:,} bytes ({result.total_size_bytes / (1024*1024):.2f} MB)")
        print(f"⏱️  Duration: {result.duration_seconds:.2f} seconds")
        
        if result.warnings:
            print()
            print(f"⚠️  Warnings ({len(result.warnings)}):")
            for i, warning in enumerate(result.warnings, 1):
                print(f"  {i}. {warning}")
        
        if result.errors:
            print()
            print(f"❌ Errors ({len(result.errors)}):")
            for i, error in enumerate(result.errors, 1):
                print(f"  {i}. {error}")
        
        print()
        print("="*70)
        
        if result.success and not migration_config.dry_run:
            print()
            print("🎉 Migration completed successfully!")
            print()
            print("Your files are now on Storacha/IPFS!")
            print("Check the warnings above for the root CID and gateway URL.")
        elif result.success and migration_config.dry_run:
            print()
            print("✅ Dry run completed successfully!")
            print()
            print("To perform actual migration:")
            print("  Set MIGRATION_DRY_RUN=false in your .env file")
        
        print()
        
        return 0 if result.success else 1
        
    except Exception as e:
        print()
        print("="*70)
        print("❌ Migration Failed")
        print("="*70)
        print()
        print(f"Error: {type(e).__name__}: {e}")
        
        if hasattr(e, 'context') and e.context:
            print()
            print("Context:")
            for key, value in e.context.items():
                value_str = str(value)
                if len(value_str) > 200:
                    value_str = value_str[:200] + "..."
                print(f"  {key}: {value_str}")
        
        print()
        print("="*70)
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration cancelled by user")
        sys.exit(130)

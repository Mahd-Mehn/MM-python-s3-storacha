#!/usr/bin/env python3
"""
Diagnose S3 connection and test different endpoint configurations
"""

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError
from dotenv import load_dotenv
import os

load_dotenv()


def test_s3_connection(
    access_key, secret_key, region, bucket, endpoint=None, service_name="S3"
):
    """Test S3 connection with given configuration"""

    print(f"\n{'=' * 70}")
    print(f"Testing {service_name}")
    print(f"{'=' * 70}")
    print(f"Bucket: {bucket}")
    print(f"Region: {region}")
    print(f"Endpoint: {endpoint or 'Default AWS'}")
    print()

    try:
        # Create S3 client
        config = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "region_name": region,
        }

        if endpoint:
            config["endpoint_url"] = endpoint

        s3 = boto3.client("s3", **config)

        # Test 1: List buckets
        print("Test 1: Listing all buckets...")
        try:
            response = s3.list_buckets()
            buckets = [b["Name"] for b in response.get("Buckets", [])]
            print(f"✓ Success! Found {len(buckets)} buckets")
            if buckets:
                print(f"  Buckets: {', '.join(buckets[:5])}")
                if len(buckets) > 5:
                    print(f"  ... and {len(buckets) - 5} more")
        except ClientError as e:
            print(
                f"✗ Failed: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
            )
        except Exception as e:
            print(f"✗ Failed: {type(e).__name__}: {e}")

        # Test 2: Get bucket location
        print(f"\nTest 2: Getting bucket location for '{bucket}'...")
        try:
            response = s3.get_bucket_location(Bucket=bucket)
            location = response.get("LocationConstraint") or "us-east-1"
            print(f"✓ Success! Bucket location: {location}")
        except ClientError as e:
            print(
                f"✗ Failed: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
            )
        except Exception as e:
            print(f"✗ Failed: {type(e).__name__}: {e}")

        # Test 3: List objects in bucket
        print(f"\nTest 3: Listing objects in bucket '{bucket}'...")
        try:
            response = s3.list_objects_v2(Bucket=bucket, MaxKeys=10)
            count = response.get("KeyCount", 0)
            print(f"✓ Success! Found {count} objects (showing first 10)")

            if "Contents" in response:
                for obj in response["Contents"][:5]:
                    size_mb = obj["Size"] / (1024 * 1024)
                    print(f"  - {obj['Key']} ({size_mb:.2f} MB)")
                if count > 5:
                    print(f"  ... and {count - 5} more")

            return True

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_msg = e.response["Error"]["Message"]
            print(f"✗ Failed: {error_code} - {error_msg}")

            if error_code == "AccessDenied":
                print("\n  💡 Possible causes:")
                print("     - IAM user lacks s3:ListBucket permission")
                print("     - Bucket policy denies access")
                print("     - Credentials are invalid or expired")
            elif error_code == "NoSuchBucket":
                print("\n  💡 Possible causes:")
                print("     - Bucket name is incorrect")
                print("     - Bucket is in a different region")
                print("     - Bucket doesn't exist")

            return False

        except EndpointConnectionError as e:
            print(f"✗ Connection Failed: {e}")
            print("\n  💡 Possible causes:")
            print("     - Endpoint URL is incorrect")
            print("     - Network connectivity issues")
            print("     - Firewall blocking connection")
            return False

        except Exception as e:
            print(f"✗ Failed: {type(e).__name__}: {e}")
            return False

    except Exception as e:
        print(f"✗ Failed to create S3 client: {type(e).__name__}: {e}")
        return False


def main():
    print("=" * 70)
    print("S3 Connection Diagnostics")
    print("=" * 70)

    # Load credentials from .env
    access_key = os.getenv("S3_ACCESS_KEY_ID")
    secret_key = os.getenv("S3_SECRET_ACCESS_KEY")
    region = os.getenv("S3_REGION", "us-east-1")
    bucket = os.getenv("S3_BUCKET_NAME")
    custom_endpoint = os.getenv("S3_ENDPOINT_URL")

    if not all([access_key, secret_key, bucket]):
        print("\n❌ Missing required environment variables:")
        print("   S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_BUCKET_NAME")
        return 1

    print("\nCredentials loaded from .env:")
    print(f"  Access Key: {access_key[:10]}...")
    print(f"  Bucket: {bucket}")
    print(f"  Region: {region}")
    if custom_endpoint:
        print(f"  Custom Endpoint: {custom_endpoint}")

    # Test different endpoint configurations
    test_configs = []

    # 1. Custom endpoint from .env (if provided)
    if custom_endpoint:
        test_configs.append(
            {"name": "Custom Endpoint (from .env)", "endpoint": custom_endpoint}
        )

    # 2. Standard AWS S3 (no custom endpoint)
    test_configs.append({"name": "Standard AWS S3", "endpoint": None})

    # 3. AWS S3 with explicit regional endpoint
    test_configs.append(
        {
            "name": "AWS S3 Regional Endpoint",
            "endpoint": f"https://s3.{region}.amazonaws.com",
        }
    )

    # 4. AWS S3 with path-style endpoint
    test_configs.append(
        {"name": "AWS S3 Path-Style", "endpoint": f"https://s3.{region}.amazonaws.com"}
    )

    # 5. LocalStack (if it looks like local testing)
    if custom_endpoint and "localhost" in custom_endpoint:
        test_configs.append({"name": "LocalStack", "endpoint": "http://localhost:4566"})

    # Run tests
    results = []
    for config in test_configs:
        success = test_s3_connection(
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            bucket=bucket,
            endpoint=config["endpoint"],
            service_name=config["name"],
        )
        results.append((config["name"], success))

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    successful = [name for name, success in results if success]
    failed = [name for name, success in results if not success]

    if successful:
        print(f"\n✅ Working configurations ({len(successful)}):")
        for name in successful:
            print(f"   - {name}")

    if failed:
        print(f"\n❌ Failed configurations ({len(failed)}):")
        for name in failed:
            print(f"   - {name}")

    # Recommendations
    print("\n" + "=" * 70)
    print("Recommendations")
    print("=" * 70)

    if successful:
        print("\n✅ Use this configuration in your .env:")
        winning_config = [c for c in test_configs if c["name"] == successful[0]][0]

        if winning_config["endpoint"]:
            print(f"\nS3_ENDPOINT_URL={winning_config['endpoint']}")
        else:
            print("\n# Remove or comment out S3_ENDPOINT_URL for standard AWS")
            print("# S3_ENDPOINT_URL=")

        print(f"S3_REGION={region}")
        print(f"S3_BUCKET_NAME={bucket}")

    else:
        print("\n❌ No working configuration found. Possible issues:")
        print("\n1. Check AWS Credentials:")
        print("   - Verify access key and secret key are correct")
        print("   - Check if credentials have expired")
        print("   - Ensure IAM user has necessary permissions")

        print("\n2. Check Bucket Configuration:")
        print("   - Verify bucket name is correct")
        print("   - Check if bucket exists in the specified region")
        print("   - Verify bucket is not in a different AWS account")

        print("\n3. Check IAM Permissions:")
        print("   Required permissions:")
        print("   - s3:ListBucket")
        print("   - s3:GetObject")
        print("   - s3:GetBucketLocation")

        print("\n4. Test with AWS CLI:")
        print(f"   aws s3 ls s3://{bucket}/ --region {region}")

    print("\n" + "=" * 70)

    return 0 if successful else 1


if __name__ == "__main__":
    exit(main())

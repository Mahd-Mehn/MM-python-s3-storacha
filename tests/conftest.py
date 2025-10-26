"""Shared pytest fixtures and configuration for all tests."""

import pytest
from typing import Dict, Any


@pytest.fixture
def valid_s3_config_dict() -> Dict[str, Any]:
    """Fixture providing valid S3 configuration dictionary."""
    return {
        "access_key_id": "AKIAIOSFODNN7EXAMPLE",
        "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "region": "us-east-1",
        "bucket_name": "test-bucket"
    }


@pytest.fixture
def valid_storacha_config_dict() -> Dict[str, Any]:
    """Fixture providing valid Storacha configuration dictionary."""
    return {
        "api_key": "storacha_test_key_123",
        "endpoint_url": "https://api.storacha.network",
        "space_name": "test-space"
    }


@pytest.fixture
def valid_migration_config_dict() -> Dict[str, Any]:
    """Fixture providing valid migration configuration dictionary."""
    return {
        "batch_size": 100,
        "timeout_seconds": 300,
        "retry_attempts": 3,
        "verbose": False,
        "dry_run": False
    }


@pytest.fixture
def complete_config_dict(
    valid_s3_config_dict,
    valid_storacha_config_dict,
    valid_migration_config_dict
) -> Dict[str, Any]:
    """Fixture providing complete configuration dictionary with all sections."""
    return {
        "s3": valid_s3_config_dict,
        "storacha": valid_storacha_config_dict,
        "migration": valid_migration_config_dict
    }

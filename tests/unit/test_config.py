"""Unit tests for configuration data classes and validation."""

import pytest
import os
import json
import tempfile
from pathlib import Path
from typing import Dict, Any

from py_s3_storacha.config import (
    S3Config,
    StorachaConfig,
    MigrationConfig,
    ConfigurationParser,
)


class TestS3Config:
    """Test cases for S3Config data class."""
    
    def test_valid_s3_config(self):
        """Test creating S3Config with valid parameters."""
        config = S3Config(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-east-1",
            bucket_name="test-bucket"
        )
        
        assert config.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert config.secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert config.region == "us-east-1"
        assert config.bucket_name == "test-bucket"
        assert config.endpoint_url is None
    
    def test_s3_config_with_endpoint(self):
        """Test S3Config with custom endpoint URL."""
        config = S3Config(
            access_key_id="test_key",
            secret_access_key="test_secret",
            region="us-west-2",
            bucket_name="test-bucket",
            endpoint_url="https://s3.custom.endpoint.com"
        )
        
        assert config.endpoint_url == "https://s3.custom.endpoint.com"
    
    def test_s3_config_missing_access_key(self):
        """Test S3Config validation fails with missing access_key_id."""
        with pytest.raises(ValueError, match="access_key_id is required"):
            S3Config(
                access_key_id="",
                secret_access_key="test_secret",
                region="us-east-1",
                bucket_name="test-bucket"
            )
    
    def test_s3_config_missing_secret_key(self):
        """Test S3Config validation fails with missing secret_access_key."""
        with pytest.raises(ValueError, match="secret_access_key is required"):
            S3Config(
                access_key_id="test_key",
                secret_access_key="",
                region="us-east-1",
                bucket_name="test-bucket"
            )
    
    def test_s3_config_missing_region(self):
        """Test S3Config validation fails with missing region."""
        with pytest.raises(ValueError, match="region is required"):
            S3Config(
                access_key_id="test_key",
                secret_access_key="test_secret",
                region="",
                bucket_name="test-bucket"
            )
    
    def test_s3_config_missing_bucket_name(self):
        """Test S3Config validation fails with missing bucket_name."""
        with pytest.raises(ValueError, match="bucket_name is required"):
            S3Config(
                access_key_id="test_key",
                secret_access_key="test_secret",
                region="us-east-1",
                bucket_name=""
            )
    
    def test_s3_config_from_dict(self):
        """Test creating S3Config from dictionary."""
        data = {
            "access_key_id": "test_key",
            "secret_access_key": "test_secret",
            "region": "eu-west-1",
            "bucket_name": "my-bucket",
            "endpoint_url": "https://custom.endpoint.com"
        }
        
        config = S3Config.from_dict(data)
        
        assert config.access_key_id == "test_key"
        assert config.secret_access_key == "test_secret"
        assert config.region == "eu-west-1"
        assert config.bucket_name == "my-bucket"
        assert config.endpoint_url == "https://custom.endpoint.com"
    
    def test_s3_config_from_dict_missing_fields(self):
        """Test S3Config.from_dict with missing fields raises validation error."""
        data = {
            "access_key_id": "test_key",
            "region": "us-east-1"
        }
        
        with pytest.raises(ValueError):
            S3Config.from_dict(data)
    
    def test_s3_config_from_env(self, monkeypatch):
        """Test creating S3Config from environment variables."""
        monkeypatch.setenv("S3_ACCESS_KEY_ID", "env_key")
        monkeypatch.setenv("S3_SECRET_ACCESS_KEY", "env_secret")
        monkeypatch.setenv("S3_REGION", "ap-south-1")
        monkeypatch.setenv("S3_BUCKET_NAME", "env-bucket")
        monkeypatch.setenv("S3_ENDPOINT_URL", "https://env.endpoint.com")
        
        config = S3Config.from_env()
        
        assert config.access_key_id == "env_key"
        assert config.secret_access_key == "env_secret"
        assert config.region == "ap-south-1"
        assert config.bucket_name == "env-bucket"
        assert config.endpoint_url == "https://env.endpoint.com"
    
    def test_s3_config_from_env_custom_prefix(self, monkeypatch):
        """Test S3Config.from_env with custom prefix."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "aws_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws_secret")
        monkeypatch.setenv("AWS_REGION", "us-west-1")
        monkeypatch.setenv("AWS_BUCKET_NAME", "aws-bucket")
        
        config = S3Config.from_env(prefix="AWS_")
        
        assert config.access_key_id == "aws_key"
        assert config.secret_access_key == "aws_secret"
        assert config.region == "us-west-1"
        assert config.bucket_name == "aws-bucket"


class TestStorachaConfig:
    """Test cases for StorachaConfig data class."""
    
    def test_valid_storacha_config(self):
        """Test creating StorachaConfig with valid parameters."""
        config = StorachaConfig(
            api_key="storacha_api_key_123",
            endpoint_url="https://api.storacha.network",
            space_name="my-space"
        )
        
        assert config.api_key == "storacha_api_key_123"
        assert config.endpoint_url == "https://api.storacha.network"
        assert config.space_name == "my-space"
    
    def test_storacha_config_missing_api_key(self):
        """Test StorachaConfig validation fails with missing api_key."""
        with pytest.raises(ValueError, match="api_key is required"):
            StorachaConfig(
                api_key="",
                endpoint_url="https://api.storacha.network",
                space_name="my-space"
            )
    
    def test_storacha_config_missing_endpoint_url(self):
        """Test StorachaConfig validation fails with missing endpoint_url."""
        with pytest.raises(ValueError, match="endpoint_url is required"):
            StorachaConfig(
                api_key="test_key",
                endpoint_url="",
                space_name="my-space"
            )
    
    def test_storacha_config_missing_space_name(self):
        """Test StorachaConfig validation fails with missing space_name."""
        with pytest.raises(ValueError, match="space_name is required"):
            StorachaConfig(
                api_key="test_key",
                endpoint_url="https://api.storacha.network",
                space_name=""
            )
    
    def test_storacha_config_from_dict(self):
        """Test creating StorachaConfig from dictionary."""
        data = {
            "api_key": "dict_api_key",
            "endpoint_url": "https://dict.endpoint.com",
            "space_name": "dict-space"
        }
        
        config = StorachaConfig.from_dict(data)
        
        assert config.api_key == "dict_api_key"
        assert config.endpoint_url == "https://dict.endpoint.com"
        assert config.space_name == "dict-space"
    
    def test_storacha_config_from_env(self, monkeypatch):
        """Test creating StorachaConfig from environment variables."""
        monkeypatch.setenv("STORACHA_API_KEY", "env_api_key")
        monkeypatch.setenv("STORACHA_ENDPOINT_URL", "https://env.storacha.com")
        monkeypatch.setenv("STORACHA_SPACE_NAME", "env-space")
        
        config = StorachaConfig.from_env()
        
        assert config.api_key == "env_api_key"
        assert config.endpoint_url == "https://env.storacha.com"
        assert config.space_name == "env-space"


class TestMigrationConfig:
    """Test cases for MigrationConfig data class."""
    
    def test_default_migration_config(self):
        """Test MigrationConfig with default values."""
        config = MigrationConfig()
        
        assert config.batch_size == 100
        assert config.timeout_seconds == 300
        assert config.retry_attempts == 3
        assert config.verbose is False
        assert config.dry_run is False
    
    def test_custom_migration_config(self):
        """Test MigrationConfig with custom values."""
        config = MigrationConfig(
            batch_size=50,
            timeout_seconds=600,
            retry_attempts=5,
            verbose=True,
            dry_run=True
        )
        
        assert config.batch_size == 50
        assert config.timeout_seconds == 600
        assert config.retry_attempts == 5
        assert config.verbose is True
        assert config.dry_run is True
    
    def test_migration_config_invalid_batch_size(self):
        """Test MigrationConfig validation fails with invalid batch_size."""
        with pytest.raises(ValueError, match="batch_size must be greater than 0"):
            MigrationConfig(batch_size=0)
        
        with pytest.raises(ValueError, match="batch_size must be greater than 0"):
            MigrationConfig(batch_size=-10)
    
    def test_migration_config_invalid_timeout(self):
        """Test MigrationConfig validation fails with invalid timeout_seconds."""
        with pytest.raises(ValueError, match="timeout_seconds must be greater than 0"):
            MigrationConfig(timeout_seconds=0)
        
        with pytest.raises(ValueError, match="timeout_seconds must be greater than 0"):
            MigrationConfig(timeout_seconds=-100)
    
    def test_migration_config_invalid_retry_attempts(self):
        """Test MigrationConfig validation fails with negative retry_attempts."""
        with pytest.raises(ValueError, match="retry_attempts must be non-negative"):
            MigrationConfig(retry_attempts=-1)
    
    def test_migration_config_zero_retry_attempts(self):
        """Test MigrationConfig allows zero retry_attempts."""
        config = MigrationConfig(retry_attempts=0)
        assert config.retry_attempts == 0
    
    def test_migration_config_from_dict(self):
        """Test creating MigrationConfig from dictionary."""
        data = {
            "batch_size": 200,
            "timeout_seconds": 900,
            "retry_attempts": 10,
            "verbose": True,
            "dry_run": False
        }
        
        config = MigrationConfig.from_dict(data)
        
        assert config.batch_size == 200
        assert config.timeout_seconds == 900
        assert config.retry_attempts == 10
        assert config.verbose is True
        assert config.dry_run is False
    
    def test_migration_config_from_dict_partial(self):
        """Test MigrationConfig.from_dict with partial data uses defaults."""
        data = {"batch_size": 150}
        
        config = MigrationConfig.from_dict(data)
        
        assert config.batch_size == 150
        assert config.timeout_seconds == 300  # default
        assert config.retry_attempts == 3  # default


class TestConfigurationParser:
    """Test cases for ConfigurationParser utility class."""
    
    def test_parse_json_file(self):
        """Test parsing configuration from JSON file."""
        config_data = {
            "s3": {
                "access_key_id": "json_key",
                "secret_access_key": "json_secret",
                "region": "us-east-1",
                "bucket_name": "json-bucket"
            },
            "storacha": {
                "api_key": "json_storacha_key",
                "endpoint_url": "https://json.storacha.com",
                "space_name": "json-space"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            parsed = ConfigurationParser.parse_from_file(temp_path)
            assert parsed == config_data
        finally:
            os.unlink(temp_path)
    
    def test_parse_env_file(self):
        """Test parsing configuration from .env style file."""
        env_content = """
# Comment line
S3_ACCESS_KEY_ID=env_key
S3_SECRET_ACCESS_KEY="env_secret"
S3_REGION='us-west-2'
S3_BUCKET_NAME=env-bucket

STORACHA_API_KEY=env_storacha_key
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(env_content)
            temp_path = f.name
        
        try:
            parsed = ConfigurationParser.parse_from_file(temp_path)
            assert parsed["S3_ACCESS_KEY_ID"] == "env_key"
            assert parsed["S3_SECRET_ACCESS_KEY"] == "env_secret"
            assert parsed["S3_REGION"] == "us-west-2"
            assert parsed["S3_BUCKET_NAME"] == "env-bucket"
            assert parsed["STORACHA_API_KEY"] == "env_storacha_key"
        finally:
            os.unlink(temp_path)
    
    def test_parse_nonexistent_file(self):
        """Test parsing nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            ConfigurationParser.parse_from_file("/nonexistent/path/config.json")
    
    def test_create_configs_from_dict(self):
        """Test creating all config objects from dictionary."""
        data = {
            "s3": {
                "access_key_id": "test_key",
                "secret_access_key": "test_secret",
                "region": "us-east-1",
                "bucket_name": "test-bucket"
            },
            "storacha": {
                "api_key": "test_storacha_key",
                "endpoint_url": "https://test.storacha.com",
                "space_name": "test-space"
            },
            "migration": {
                "batch_size": 250,
                "timeout_seconds": 450
            }
        }
        
        s3_config, storacha_config, migration_config = ConfigurationParser.create_configs_from_dict(data)
        
        assert s3_config.access_key_id == "test_key"
        assert s3_config.bucket_name == "test-bucket"
        assert storacha_config.api_key == "test_storacha_key"
        assert storacha_config.space_name == "test-space"
        assert migration_config.batch_size == 250
        assert migration_config.timeout_seconds == 450
    
    def test_create_configs_from_file(self):
        """Test creating all config objects from JSON file."""
        config_data = {
            "s3": {
                "access_key_id": "file_key",
                "secret_access_key": "file_secret",
                "region": "eu-central-1",
                "bucket_name": "file-bucket"
            },
            "storacha": {
                "api_key": "file_storacha_key",
                "endpoint_url": "https://file.storacha.com",
                "space_name": "file-space"
            },
            "migration": {
                "batch_size": 75,
                "verbose": True
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            s3_config, storacha_config, migration_config = ConfigurationParser.create_configs_from_file(temp_path)
            
            assert s3_config.access_key_id == "file_key"
            assert s3_config.region == "eu-central-1"
            assert storacha_config.endpoint_url == "https://file.storacha.com"
            assert migration_config.batch_size == 75
            assert migration_config.verbose is True
        finally:
            os.unlink(temp_path)

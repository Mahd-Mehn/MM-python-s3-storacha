"""Configuration data classes and validation for S3 to Storacha migration."""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Union
import os
import json
from pathlib import Path


@dataclass
class S3Config:
    """Configuration for S3 connection and authentication."""

    access_key_id: str
    secret_access_key: str
    region: str
    bucket_name: str
    endpoint_url: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate S3 configuration after initialization."""
        if not self.access_key_id:
            raise ValueError("S3 access_key_id is required")
        if not self.secret_access_key:
            raise ValueError("S3 secret_access_key is required")
        if not self.region:
            raise ValueError("S3 region is required")
        if not self.bucket_name:
            raise ValueError("S3 bucket_name is required")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "S3Config":
        """Create S3Config from dictionary."""
        return cls(
            access_key_id=data.get("access_key_id", ""),
            secret_access_key=data.get("secret_access_key", ""),
            region=data.get("region", ""),
            bucket_name=data.get("bucket_name", ""),
            endpoint_url=data.get("endpoint_url"),
        )

    @classmethod
    def from_env(cls, prefix: str = "S3_") -> "S3Config":
        """Create S3Config from environment variables."""
        return cls(
            access_key_id=os.getenv(f"{prefix}ACCESS_KEY_ID", ""),
            secret_access_key=os.getenv(f"{prefix}SECRET_ACCESS_KEY", ""),
            region=os.getenv(f"{prefix}REGION", ""),
            bucket_name=os.getenv(f"{prefix}BUCKET_NAME", ""),
            endpoint_url=os.getenv(f"{prefix}ENDPOINT_URL"),
        )


@dataclass
class StorachaConfig:
    """Configuration for Storacha connection and authentication."""

    api_key: str
    endpoint_url: str
    space_name: str

    def __post_init__(self) -> None:
        """Validate Storacha configuration after initialization."""
        if not self.api_key:
            raise ValueError("Storacha api_key is required")
        if not self.endpoint_url:
            raise ValueError("Storacha endpoint_url is required")
        if not self.space_name:
            raise ValueError("Storacha space_name is required")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StorachaConfig":
        """Create StorachaConfig from dictionary."""
        return cls(
            api_key=data.get("api_key", ""),
            endpoint_url=data.get("endpoint_url", ""),
            space_name=data.get("space_name", ""),
        )

    @classmethod
    def from_env(cls, prefix: str = "STORACHA_") -> "StorachaConfig":
        """Create StorachaConfig from environment variables."""
        return cls(
            api_key=os.getenv(f"{prefix}API_KEY", ""),
            endpoint_url=os.getenv(f"{prefix}ENDPOINT_URL", ""),
            space_name=os.getenv(f"{prefix}SPACE_NAME", ""),
        )


@dataclass
class MigrationConfig:
    """Configuration for migration-specific settings."""

    batch_size: int = 100
    timeout_seconds: int = 300
    retry_attempts: int = 3
    verbose: bool = False
    dry_run: bool = False

    def __post_init__(self) -> None:
        """Validate migration configuration after initialization."""
        if self.batch_size <= 0:
            raise ValueError("batch_size must be greater than 0")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0")
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts must be non-negative")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MigrationConfig":
        """Create MigrationConfig from dictionary."""
        return cls(
            batch_size=data.get("batch_size", 100),
            timeout_seconds=data.get("timeout_seconds", 300),
            retry_attempts=data.get("retry_attempts", 3),
            verbose=data.get("verbose", False),
            dry_run=data.get("dry_run", False),
        )


class ConfigurationParser:
    """Utility class for parsing configuration from various sources."""

    @staticmethod
    def parse_from_file(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Parse configuration from JSON or environment file."""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        if path.suffix.lower() == ".json":
            with open(path, "r") as f:
                return json.load(f)

        # Handle .env style files
        config = {}
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip().strip("\"'")

        return config

    @staticmethod
    def create_configs_from_dict(
        data: Dict[str, Any],
    ) -> tuple[S3Config, StorachaConfig, MigrationConfig]:
        """Create all configuration objects from a single dictionary."""
        s3_data = data.get("s3", {})
        storacha_data = data.get("storacha", {})
        migration_data = data.get("migration", {})

        s3_config = S3Config.from_dict(s3_data)
        storacha_config = StorachaConfig.from_dict(storacha_data)
        migration_config = MigrationConfig.from_dict(migration_data)

        return s3_config, storacha_config, migration_config

    @staticmethod
    def create_configs_from_file(
        file_path: Union[str, Path],
    ) -> tuple[S3Config, StorachaConfig, MigrationConfig]:
        """Create all configuration objects from a configuration file."""
        data = ConfigurationParser.parse_from_file(file_path)
        return ConfigurationParser.create_configs_from_dict(data)

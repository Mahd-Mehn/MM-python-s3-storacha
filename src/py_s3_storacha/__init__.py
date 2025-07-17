"""A tool for migrating objects from AWS S3 to Storacha"""

from typing import NamedTuple

__version__ = "0.0.1"


class S3Config(NamedTuple):
    bucket_name: str
    region: str
    access_key_id: str
    secret_access_key: str


class StorachaConfig(NamedTuple):
    email: str


class RetryConfig(NamedTuple):
    max_attempts: int
    back_off_ms: int
    max_back_off_ms: int


class BatchConfig(NamedTuple):
    concurrency: int
    size: int


class MigratorConfig(NamedTuple):
    s3: S3Config
    storacha: StorachaConfig
    retry: RetryConfig
    batch: BatchConfig

"""A tool for migrating objects from AWS S3 to Storacha"""

from dataclasses import dataclass
from typing import NamedTuple

from py_s3_storacha.managers.conn import ConnectionManager

__version__ = "0.0.1"


class S3Config(NamedTuple):
    bucket_name: str
    region: str
    access_key_id: str
    secret_access_key: str


class StorachaConfig(NamedTuple):
    space_did: str
    auth_secret: str
    authorization_key: str


class MigratorConfig(NamedTuple):
    s3: S3Config
    storacha: StorachaConfig


@dataclass
class Migrator:
    config: MigratorConfig
    _conn: ConnectionManager | None = None

    def __post_init__(self):
        # register useful callbacks
        ...


    @property
    def conn(self) -> ConnectionManager:
        # Initialize connection lazily or only on first-use
        if self._conn is None:
            self._conn: ConnectionManager = ConnectionManager(config=self.config)
        return self._conn

    async def initialize(self):
        await self._conn.initialize_conns()

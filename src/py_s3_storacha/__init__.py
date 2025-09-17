"""A tool for migrating objects from AWS S3 to Storacha"""

from dataclasses import dataclass
from typing import NamedTuple
import io

import ipld_car
from multiformats import multihash, CID

from py_s3_storacha.managers.conn import ConnectionManager
from py_s3_storacha.storacha import StorachaClient

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
    _conn: ConnectionManager = None  # pyright: ignore[reportAssignmentType]
    _bridge: StorachaClient = None # pyright: ignore[reportAssignmentType]

    def __post_init__(self):
        # register useful callbacks
        ...

    @property
    def conn(self) -> ConnectionManager:
        # Initialize connection lazily or only on first-use
        if self._conn is None:
            self._conn = ConnectionManager(config=self.config)
        return self._conn

    async def initialize(self):
        """
        Initialize S3 and Storacha (HTTP bridge) sessions
        """
        await self._conn.initialize_conns()

    async def _prepare_car(self, key: str) -> tuple[CID, io.BytesIO, int]:
        """
        Fetches the S3 object, packages it into a CAR in-memory, and computes its root CID.
        Returns (root_cid, car_stream, size_bytes).
        """
        # Download from S3
        response = await self._conn.s3.get_object(
            Bucket=self._conn._config.s3.bucket_name, Key=key
        )
        size = response.get("ContentLength")
        body = await response["Body"].read()

        # TODO: make sure len(body) is less than 4gb

        # write the car file in-memory
        digest = multihash.digest(data=body, hashfun="sha2-256")
        file_cid = CID("base32", 1, "raw", digest)
        block = (file_cid, body)
        car = ipld_car.encode([block[0]], [block])
        car_cid = CID("base32", 1, "raw", car)
        size = len(car)
        return car_cid, io.BytesIO(car), size

    async def migrate_file(self, key: str):
        """
        Streams an S3 object directly into Storacha via the HTTP bridge.

        1. Fetches the object from S3 as an async stream.
        2. Creates a UCAN task to obtain status, signed PUT URL, and headers.
        3. If status is "upload", streams the data into Storacha without buffering locally.
           If status is "done", skips upload.
        """
        root_cid, car_stream, size = await self._prepare_car(key)
        status, upload_url, upload_headers = await self._bridge.create_store_task()

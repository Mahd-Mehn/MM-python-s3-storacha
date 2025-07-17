import re

import aioboto3
import aiohttp

from py_s3_storacha import MigratorConfig


class AsyncConnectionError(Exception):
    pass


class ConnectionManager():
    def __init__(self, config: MigratorConfig) -> None:
        self._config: MigratorConfig = config
        self._s3_session: aioboto3.Session | None  = None
        self._s3_client = None
        self._http_session: aiohttp.ClientSession | None = None


    async def initialize_conns(self):
        self._s3_session = aioboto3.Session()
        self._s3_client = await self._s3_session.client(
            service_name="s3",
            region_name=self._config.s3.region,
            aws_access_key_id=self._config.s3.access_key_id,
            aws_secret_access_key=self._config.s3.secret_access_key
        ).__aenter__()  # enter the client's async context

        # validate email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", self._config.storacha.email):
            raise AsyncConnectionError("Invalid Storacha email format")

        # http session for storacha http-bridge
        self._http_session = aiohttp.ClientSession(headers={"Authorization": f"Bearer {self._config.storacha.email}"})

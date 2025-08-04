from typing import TYPE_CHECKING

import aioboto3
import aiohttp

if TYPE_CHECKING:
    from py_s3_storacha import MigratorConfig


class AsyncConnectionError(Exception):
    pass


class ConnectionManager:
    def __init__(self, config: MigratorConfig) -> None:
        self._config: MigratorConfig = config
        self._s3_client = None
        self._http_session: aiohttp.ClientSession | None = None

    async def initialize_conns(self) -> None:
        s3_session = aioboto3.Session()
        self._s3_client = await s3_session.client(
            service_name="s3",
            region_name=self._config.s3.region,
            aws_access_key_id=self._config.s3.access_key_id,
            aws_secret_access_key=self._config.s3.secret_access_key,
        ).__aenter__()  # enter the client's async context

        # http session for storacha http-bridge
        self._http_session = aiohttp.ClientSession(
            headers={
                "X-Auth-Secret": f"{self._config.storacha.auth_secret}",
                "Authorization": f"{self._config.storacha.authorization_key}",
            }
        )

    async def close_connections(self):
        if self._http_session:
            await self._http_session.close()
            self._http_session = None

        if self._s3_client:
            await self._s3_client.__aexit__(None, None, None)
            self._s3_client = None
        self._s3_session = None

    @property
    def s3(self):
        if not self._s3_client:
            raise AsyncConnectionError("S3 client not initialized")
        return self._s3_client

    @property
    def storacha(self):
        if not self._http_session:
            raise AsyncConnectionError("Storacha HTTP session not initialized")
        return self._http_session

from aiohttp import ClientSession


class StorachaClient:
    def __init__(self, session: ClientSession, auth_secret: str, auth_key: str) -> None:
        self.session = session
        self.auth_secret = auth_secret
        self.auth_key = auth_key

    async def create_store_task(self, root_cid: str, size: int):
        """
            Initiates the UCAN "store/add" task via the HTTP bridge to obtain a signed PUT URL.
        """
        payload = {
            "tasks": [
                [
                    "store/add",
                    None,
                    { "link": { "/": root_cid }, "size": size }
                ]
            ]
        }

        headers = {
            "X-Auth-Secret": self.auth_secret,
            "Authorization": self.auth_key,
            "Content-Type": "application/json"
        }
        resp = await self.session.post(
            "https://up.storacha.network/bridge",
            json=payload,
            headers=headers
        )
        resp.raise_for_status()
        data = await resp.json()
        out = data[0]["p"]["out"]["ok"]

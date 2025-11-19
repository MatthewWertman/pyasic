from __future__ import annotations

import asyncio
import hashlib
import json
import random
import time
import warnings
from typing import Any

import httpx

from pyasic import settings
from pyasic.errors import APIError
from pyasic.web.base import BaseWebAPI


def generate_php_session_id() -> str:
    random.seed(time.time_ns())
    data = bytearray(random.randbytes(10))

    h = hashlib.new("sha1", data=data)
    return h.hexdigest()[:26]


class SealminerWebAPI(BaseWebAPI):
    def __init__(self, ip: str) -> None:
        super().__init__(ip)
        self.username = "seal"
        self.pwd = settings.get("default_sealminer_web_password", "seal")
        self.token: str | None = None

    async def auth(self) -> str | None:
        async with httpx.AsyncClient(transport=settings.transport()) as client:
            session_id = generate_php_session_id()
            headers = {"Cookie": "userLanguage=en; PHPSESSID=" + session_id}
            try:
                auth = await client.post(
                    f"http://{self.ip}:{self.port}/cgi-bin/login.php",
                    data={"username": self.username, "origin_pwd": self.pwd},
                    headers=headers,
                )
            except httpx.HTTPError:
                warnings.warn(f"Could not authenticate web token with miner: {self}")
            else:
                if auth.status_code == 200:
                    try:
                        json_auth = auth.json()
                        if "state" in json_auth and json_auth["state"] == 0:
                            self.token = session_id
                    except json.JSONDecodeError:
                        return None
        return self.token

    async def send_command(
        self,
        command: str,
        ignore_errors: bool = False,
        allow_warning: bool = True,
        privileged: bool = False,
        **parameters: Any,
    ) -> dict:
        if self.token is None:
            await self.auth()
        async with httpx.AsyncClient(transport=settings.transport()) as client:
            if self.token is None:
                raise APIError(f"Could not authenticate web token with miner: {self}")
            url = f"http://{self.ip}:{self.port}/cgi-bin/{command}.php"
            headers = {
                "Cookie": f"username=seal; userLanguage=en; PHPSESSID={self.token}"
            }

            try:
                if parameters and "data" in parameters:
                    response = await client.post(
                        url, headers=headers, data=parameters["data"]
                    )
                elif parameters:
                    response = await client.post(url, headers=headers, json=parameters)
                else:
                    response = await client.get(
                        url,
                        headers=headers,
                    )
                if response.status_code == 200:
                    return response.json()
            except httpx.HTTPError:
                pass
        raise APIError(f"Command failed: {command}")

    async def multicommand(
        self, *commands: str, ignore_errors: bool = False, allow_warning: bool = True
    ) -> dict:
        return await super().multicommand(
            *commands, ignore_errors=ignore_errors, allow_warning=allow_warning
        )

    async def get_miner_poolconf(self) -> dict:
        return await self.send_command("get_miner_poolconf")

    async def set_miner_poolconf(self, conf: dict) -> dict:
        return await self.send_command("set_miner_poolconf", **conf)

    async def get_system_info(self) -> dict:
        return await self.send_command("get_system_info")

    async def get_network_info(self) -> dict:
        return await self.send_command("get_network_info")

    async def get_miner_monitor_status(self) -> dict:
        return await self.send_command("get_miner_monitor_status")

    async def get_mining_mode(self) -> dict:
        return await self.send_command("get_mining_mode")

    async def get_miner_type(self) -> dict:
        return await self.send_command("get_miner_type")

    async def get_miner_error_code(self) -> dict:
        return await self.send_command("get_miner_error_code")

    async def restart_mining(self) -> dict:
        data = "{parama_data:1}"
        return await self.send_command("mining_setting", data=data)

    async def stop_mining(self) -> dict:
        data = "{parama_data:0}"
        return await self.send_command("mining_setting", data=data)

    async def reboot(self) -> dict:
        return await self.send_command("reboot")

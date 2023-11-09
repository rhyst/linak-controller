"""
Contains the REST API endpoints.
"""

import asyncio
import re
from bleak import BleakClient
from aiohttp import web
from .desk import Desk
from .util import Height
from .config import config
from json import JSONDecodeError


class RestApi:
    favourite_name_pattern = re.compile("^[a-zA-Z0-9_-]+$")

    def __init__(self, client: BleakClient, router):
        self._client = client

        router.add_get("/rest/desk", self.get_desk)
        router.add_post("/rest/desk", self.post_desk)
        router.add_get("/rest/desk/height", self.get_desk_height)
        router.add_post("/rest/desk/height", self.post_desk_height)
        router.add_get("/rest/desk/speed", self.get_desk_speed)
        router.add_post("/rest/desk/favourite", self.post_desk_favourite)

    @property
    def client(self):
        return self._client


    async def get_desk(self, _):
        current_height, current_speed = await Desk.get_height_speed(self.client)

        return web.Response(
            text='{{"height": {:.0f}, "speed": {:.0f}}}'.format(current_height.human, current_speed.human),
            content_type="application/json"
        )

    async def post_desk(self, request: web.Request):
        if (not request.body_exists) or (not request.can_read_body):
            return web.Response(status=400)

        try:
            target_height = (await request.json())['height']
        except (JSONDecodeError, KeyError):
            return web.Response(status=400)

        return await self.common_post_height(target_height)

    async def get_desk_height(self, _):
        current_height, _ = await Desk.get_height_speed(self.client)

        return web.Response(
            text='{:.0f}'.format(current_height.human),
            content_type="text/plain"
        )

    async def post_desk_height(self, request: web.Request):
        if (not request.body_exists) or (not request.can_read_body):
            return web.Response(status=400)

        return await self.common_post_height(await request.text())

    async def get_desk_speed(self, _):
        _, current_speed = await Desk.get_height_speed(self.client)

        return web.Response(
            text='{:.0f}'.format(current_speed.human),
            content_type="text/plain"
        )

    async def post_desk_favourite(self, request: web.Request):
        if (not request.body_exists) or (not request.can_read_body):
            return web.Response(status=400)

        favourite_name = await request.text()

        if not self.favourite_name_pattern.match(favourite_name):
            return web.Response(status=400)

        if favourite_name not in config.favourites:
            return web.Response(status=422)

        return await self.common_post_height(config.favourites.get(favourite_name))


    async def common_post_height(self, target_height):
        try:
            target_height_int = int(target_height)
        except ValueError:
            return web.Response(status=400)

        if target_height_int < config.base_height:
            return web.Response(status=422)

        loop = asyncio.get_running_loop()
        loop.create_task(Desk.move_to(self.client, Height(target_height_int, True)))

        return web.Response(status=202)

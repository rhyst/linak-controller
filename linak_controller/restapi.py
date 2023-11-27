"""
Contains the REST API endpoints.
"""

import asyncio
import re
from bleak import BleakClient
from aiohttp import web
from typing import Tuple
from .desk import Desk
from .util import Height, Speed
from .config import config
from json import JSONDecodeError


class RestApi:
    favourite_name_pattern = re.compile("^[a-zA-Z0-9_-]+$")

    currentHeight: Height = Height(0)
    currentSpeed: Speed = Speed(0)


    def __init__(self, client: BleakClient, router):
        self.client = client

        router.add_get("/rest/desk", self.get_desk)
        router.add_post("/rest/desk", self.post_desk)
        router.add_get("/rest/desk/height", self.get_desk_height)
        router.add_post("/rest/desk/height", self.post_desk_height)
        router.add_post("/rest/desk/height/favourite", self.post_desk_height_favourite)
        router.add_get("/rest/desk/speed", self.get_desk_speed)

        def callback(height, speed):
            self.currentHeight = height
            self.currentSpeed = speed

        async def fetchInitialValues():
            current_height, current_speed = await Desk.get_height_speed(client)
            callback(current_height, current_speed)

        loop = asyncio.get_running_loop()
        loop.create_task(fetchInitialValues())
        loop.create_task(Desk.watch_height_speed(client, callback))


    def get_desk(self, _):
        current_height, current_speed = self.common_get_from_desk()

        return web.Response(
            text='{{"height": {:.0f}, "speed": {:.0f}}}'.format(
                current_height.human, current_speed.human
            ),
            content_type="application/json",
        )

    async def post_desk(self, request: web.Request):
        if (not request.body_exists) or (not request.can_read_body):
            return web.Response(status=400)

        try:
            target_height = (await request.json())["height"]
        except (JSONDecodeError, KeyError):
            return web.Response(status=400)

        return await self.common_post_height(target_height)

    def get_desk_height(self, _):
        current_height, _ = self.common_get_from_desk()

        return web.Response(
            text="{:.0f}".format(current_height.human), content_type="text/plain"
        )

    async def post_desk_height(self, request: web.Request):
        if (not request.body_exists) or (not request.can_read_body):
            return web.Response(status=400)

        return await self.common_post_height(await request.text())

    async def post_desk_height_favourite(self, request: web.Request):
        if (not request.body_exists) or (not request.can_read_body):
            return web.Response(status=400)

        favourite_name = await request.text()

        if not self.favourite_name_pattern.match(favourite_name):
            return web.Response(status=400)

        if favourite_name not in config.favourites:
            return web.Response(status=422)

        return await self.common_post_height(config.favourites.get(favourite_name))

    def get_desk_speed(self, _):
        _, current_speed = self.common_get_from_desk()

        return web.Response(
            text="{:.0f}".format(current_speed.human), content_type="text/plain"
        )


    def common_get_from_desk(self) -> Tuple[Height, Speed]:
        return self.currentHeight, self.currentSpeed

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

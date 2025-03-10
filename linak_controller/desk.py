"""
High level helper class to organise methods for performing actions with a Linak Desk.
"""

import asyncio
from bleak import BleakClient
from bleak.exc import BleakDBusError
from typing import Tuple
from .gatt import (
    DPGService,
    ControlService,
    ReferenceInputService,
    ReferenceOutputService,
)
from .config import Config
from .util import logger, bytes_to_hex, Height, Speed
import struct


class Desk:
    client: BleakClient = None
    config: Config = None
    disconnecting = False

    def __init__(self, config: Config, client: BleakClient):
        self.client = client
        self.config = config

    @classmethod
    async def initialise(cls, config: Config, client: BleakClient) -> None:
        desk = cls(config, client)

        # Read capabilities
        capabilities = desk.decode_capabilities(
            await DPGService.dpg_command(client, DPGService.DPG.CMD_GET_CAPABILITIES)
        )
        logger.log("Capabilities: {}".format(capabilities))

        # Read the user id
        user_id = await DPGService.dpg_command(client, DPGService.DPG.CMD_USER_ID)
        logger.log("User ID: {}".format(bytes_to_hex(user_id)))
        if user_id and user_id[0] != 1:
            # For DPG1C it is important that the first byte is set to 1
            # The other bytes do not seem to matter
            user_id[0] = 1
            logger.log("Setting user ID to {}".format(bytes_to_hex(user_id)))
            await DPGService.dpg_command(client, DPGService.DPG.CMD_USER_ID, user_id)

        # Check if base height should be taken from controller
        if config["base_height"] == None:
            resp = await DPGService.dpg_command(client, DPGService.DPG.CMD_BASE_OFFSET)
            if resp:
                base_height = struct.unpack("<H", resp[1:])[0] / 10
                desk.config["base_height"] = base_height
        else:
            desk.config["base_height"] = config["base_height"]
        logger.log("Base height:{:4.0f}mm".format(desk.config["base_height"]))

        return desk

    async def wakeup(self) -> None:
        await ControlService.COMMAND.write_command(
            self.client, ControlService.COMMAND.CMD_WAKEUP
        )

    async def move_to(self, target: Height) -> None:
        initial_height, speed = await ReferenceOutputService.get_height_speed(self.client)
        initial_height.base_height = self.config["base_height"]
        if initial_height.value == target.value:
            return

        await self.wakeup()
        await self.stop()

        data = ReferenceInputService.encode_height(target.value)

        while True:
            await ReferenceInputService.ONE.write(self.client, data)
            await asyncio.sleep(self.config["move_command_period"])
            height, speed = await ReferenceOutputService.get_height_speed(self.client)
            height.base_height = self.config["base_height"]
            if speed.value == 0:
                break
            logger.log(
                "Height:{:4.0f}mm Speed: {:2.0f}mm/s".format(height.human, speed.human)
            )

    async def get_height_speed(self) -> Tuple[Height, Speed]:
        height, speed = await ReferenceOutputService.get_height_speed(self.client)
        height.base_height = self.config["base_height"]
        return height, speed

    async def watch_height_speed(self) -> None:
        """Listen for height changes"""

        def callback(sender, data):
            height, speed = ReferenceOutputService.decode_height_speed(data)
            height.base_height = self.config["base_height"]
            logger.log(
                "Height:{:4.0f}mm Speed: {:2.0f}mm/s".format(height.human, speed.human)
            )

        await ReferenceOutputService.ONE.subscribe(self.client, callback)
        await asyncio.Future()

    async def stop(self) -> None:
        try:
            await ControlService.COMMAND.write_command(
                self.client, ControlService.COMMAND.CMD_STOP
            )
        except BleakDBusError as e:
            # Harmless exception that happens on Raspberry Pis
            # bleak.exc.BleakDBusError: [org.bluez.Error.NotPermitted] Write acquired
            pass

    @classmethod
    def decode_capabilities(self, caps: bytearray) -> dict:
        if len(caps) < 2:
            return {}
        capByte = caps[0]
        refByte = caps[1]
        return {
            "memSize": capByte & 7,
            "autoUp": (capByte & 8) != 0,
            "autoDown": (capByte & 16) != 0,
            "bleAllow": (capByte & 32) != 0,
            "hasDisplay": (capByte & 64) != 0,
            "hasLight": (capByte & 128) != 0,
        }

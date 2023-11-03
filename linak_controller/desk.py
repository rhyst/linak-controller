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
from .config import config
from .util import bytes_to_hex, Height, Speed
import struct


class Desk:
    @classmethod
    async def initialise(cls, client: BleakClient) -> None:
        # Read capabilities
        capabilities = cls.decode_capabilities(
            await DPGService.dpg_command(client, DPGService.DPG.CMD_GET_CAPABILITIES)
        )
        print("Capabilities: {}".format(capabilities))

        # Read the user id
        user_id = await DPGService.dpg_command(client, DPGService.DPG.CMD_USER_ID)
        print("User ID: {}".format(bytes_to_hex(user_id)))
        if user_id and user_id[0] != 1:
            # For DPG1C it is important that the first byte is set to 1
            # The other bytes do not seem to matter
            user_id[0] = 1
            print("Setting user ID to {}".format(bytes_to_hex(user_id)))
            await DPGService.dpg_command(client, DPGService.DPG.CMD_USER_ID, user_id)

        # Check if base height should be taken from controller
        if config.base_height == None:
            resp = await DPGService.dpg_command(client, DPGService.DPG.CMD_BASE_OFFSET)
            if resp:
                base_height = struct.unpack("<H", resp[1:])[0] / 10
                print("Base height from desk: {:4.0f}mm".format(base_height))
                config.base_height = base_height

    @classmethod
    async def wakeup(cls, client: BleakClient) -> None:
        await ControlService.COMMAND.write_command(
            client, ControlService.COMMAND.CMD_WAKEUP
        )

    @classmethod
    async def move_to(cls, client: BleakClient, target: Height) -> None:
        initial_height, speed = await ReferenceOutputService.get_height_speed(client)
        if initial_height.value == target.value:
            return

        await cls.wakeup(client)
        await cls.stop(client)

        data = ReferenceInputService.encode_height(target.value)

        while True:
            await ReferenceInputService.ONE.write(client, data)
            await asyncio.sleep(config.move_command_period)
            height, speed = await ReferenceOutputService.get_height_speed(client)
            if speed.value == 0:
                break
            config.log(
                "Height: {:4.0f}mm Speed: {:2.0f}mm/s".format(height.human, speed.human)
            )

    @classmethod
    async def get_height_speed(cls, client: BleakClient) -> Tuple[Height, Speed]:
        return await ReferenceOutputService.get_height_speed(client)

    @classmethod
    async def watch_height_speed(cls, client: BleakClient) -> None:
        """Listen for height changes"""

        def callback(sender, data):
            height, speed = ReferenceOutputService.decode_height_speed(data)
            config.log(
                "Height: {:4.0f}mm Speed: {:2.0f}mm/s".format(height.human, speed.human)
            )

        await ReferenceOutputService.ONE.subscribe(client, callback)
        await asyncio.Future()

    @classmethod
    async def stop(cls, client: BleakClient) -> None:
        try:
            await ControlService.COMMAND.write_command(
                client, ControlService.COMMAND.CMD_STOP
            )
        except BleakDBusError as e:
            # Harmless exception that happens on Raspberry Pis
            # bleak.exc.BleakDBusError: [org.bluez.Error.NotPermitted] Write acquired
            pass

    @classmethod
    def decode_capabilities(cls, caps: bytearray) -> dict:
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

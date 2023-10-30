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


class Desk:
    @classmethod
    async def initialise(cls, client: BleakClient) -> None:
        # Read the user id

        capabilities =  cls.decode_capabilities(await DPGService.dpg_command(client, DPGService.DPG.CMD_GET_CAPABILITIES))
        print("Capabilities: {}".format(capabilities))
        
        user_id = (await DPGService.dpg_command(client, DPGService.DPG.CMD_USER_ID))[2:]
        user_id_hex = bytes_to_hex(user_id)
        print("User ID: {}".format(user_id_hex))
        if user_id_hex != config.user_id:
            print("Setting user ID to".format(config.user_id))
            await DPGService.dpg_command(client, DPGService.DPG.CMD_USER_ID, bytearray.fromhex(config.user_id))
            


    @classmethod
    async def wakeup(cls, client: BleakClient) -> None:
        await ControlService.COMMAND.write_command(client, ControlService.COMMAND.CMD_WAKEUP)


    @classmethod
    async def move_to(cls, client: BleakClient, target: Height) -> None:
        initial_height, speed = await ReferenceOutputService.get_height_speed(client)
        if initial_height.value == target.value:
            return

        await ControlService.wakeup(client)
        await ControlService.stop(client)

        data = ReferenceInputService.encode_height(target.value)

        while True:
            await ReferenceInputService.ONE.write(client, data)
            await asyncio.sleep(0.5)
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
            await ControlService.COMMAND.write_command(client, ControlService.COMMAND.CMD_STOP)
        except BleakDBusError as e:
            # Harmless exception that happens on Raspberry Pis
            # bleak.exc.BleakDBusError: [org.bluez.Error.NotPermitted] Write acquired
            pass

    @classmethod
    def decode_capabilities(cls, data: bytearray) -> dict:
        caps = data[2:]
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
            "hasLight": (capByte & 128) != 0
        }

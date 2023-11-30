"""
Low level helper classes to organise methods for interacting with the GATT services/characteristics provided by Linak Desks.
"""

import struct
from bleak import BleakClient
import asyncio
from typing import Optional, Tuple, Union
from .util import Height, Speed, make_iter
from .config import config


class Characteristic:
    uuid = None

    @classmethod
    async def read(cls, client: BleakClient) -> bytearray:
        return await client.read_gatt_char(cls.uuid)

    @classmethod
    async def write(cls, client: BleakClient, value: bytearray) -> None:
        return await client.write_gatt_char(cls.uuid, value)

    @classmethod
    async def subscribe(cls, client: BleakClient, callback) -> None:
        """Listen for notifications on a characteristic"""
        await client.start_notify(cls.uuid, callback)

    @classmethod
    async def unsubscribe(cls, client: BleakClient) -> None:
        """Stop listenening for notifications on a characteristic"""
        await client.stop_notify(cls.uuid)


class Service:
    uuid = None


# Generic Access


class GenericAccessDeviceNameCharacteristic(Characteristic):
    uuid = "00002A00-0000-1000-8000-00805F9B34FB"


class GenericAccessServiceChangedCharacteristic(Characteristic):
    uuid = "00002A05-0000-1000-8000-00805F9B34FB"


class GenericAccessManufacturerCharacteristic(Characteristic):
    uuid = "00002A29-0000-1000-8000-00805F9B34FB"


class GenericAccessModelNumberCharacteristic(Characteristic):
    uuid = "00002A24-0000-1000-8000-00805F9B34FB"


class GenericAccessService(Service):
    uuid = "00001800-0000-1000-8000-00805F9B34FB"

    DEVICE_NAME = GenericAccessDeviceNameCharacteristic
    SERVICE_CHANGED = GenericAccessServiceChangedCharacteristic
    MANUFACTURER = GenericAccessManufacturerCharacteristic
    MODEL_NUMBER = GenericAccessModelNumberCharacteristic


# Reference Input


class ReferenceInputOneCharacteristic(Characteristic):
    uuid = "99fa0031-338a-1024-8a49-009c0215f78a"


class ReferenceInputService(Service):
    uuid = "99fa0030-338a-1024-8a49-009c0215f78a"

    ONE = ReferenceInputOneCharacteristic

    @classmethod
    def encode_height(cls, height: Union[int, str]) -> bytearray:
        try:
            return bytearray(struct.pack("<H", int(height)))
        except struct.error:
            raise ValueError("Height must be an integer between 0 and 65535")


# Reference Output


class ReferenceOutputOneCharacteristic(Characteristic):
    uuid = "99fa0021-338a-1024-8a49-009c0215f78a"


class ReferenceOutputService(Service):
    uuid = "99fa0020-338a-1024-8a49-009c0215f78a"

    ONE = ReferenceOutputOneCharacteristic

    @classmethod
    def decode_height_speed(cls, data: bytearray) -> Tuple[Height, Speed]:
        height, speed = struct.unpack("<Hh", data)
        return Height(height), Speed(speed)

    @classmethod
    async def get_height_speed(cls, client: BleakClient) -> Tuple[Height, Speed]:
        data = await cls.ONE.read(client)
        return cls.decode_height_speed(data)


# Control


class ControlCommandCharacteristic(Characteristic):
    uuid = "99fa0002-338a-1024-8a49-009c0215f78a"

    CMD_MOVE_DOWN = 70
    CMD_MOVE_UP = 71
    CMD_WAKEUP = 254
    CMD_STOP = 255

    @classmethod
    async def write_command(cls, client: BleakClient, command: int) -> None:
        await client.write_gatt_char(cls.uuid, bytearray(struct.pack("BB", command, 0)))


class ControlErrorCharacteristic(Characteristic):
    uuid = "99fa0003-338a-1024-8a49-009c0215f78a"


class ControlService(Service):
    uuid = "99fa0001-338a-1024-8a49-009c0215f78a"

    COMMAND = ControlCommandCharacteristic
    ERROR = ControlErrorCharacteristic


# DPG


class DPGDPGCharacteristic(Characteristic):
    uuid = "99fa0011-338a-1024-8a49-009c0215f78a"

    CMD_GET_CAPABILITIES = 128
    CMD_BASE_OFFSET = 129
    CMD_USER_ID = 134

    @classmethod
    async def read_command(cls, client: BleakClient, command: int) -> bytearray:
        await cls.write(client, bytearray(struct.pack("BBB", 127, command, 0)))
        return await client.read_gatt_char(cls.uuid)

    @classmethod
    async def write_command(
        cls, client: BleakClient, command: int, data: bytearray
    ) -> None:
        header = struct.pack("BBB", 127, command, 128)
        buffer = bytes()
        for val in data:
            buffer += struct.pack("B", val)
        buffer = header + buffer
        await cls.write(client, buffer)


class DPGService(Service):
    uuid = "99fa0010-338a-1024-8a49-009c0215f78a"

    DPG = DPGDPGCharacteristic

    @classmethod
    def is_valid_response(self, response: bytearray) -> bool:
        return response[0] == 0x1

    @classmethod
    def is_valid_data(self, data: bytearray) -> bool:
        return data[1] > 0x1

    @classmethod
    async def dpg_command(
        cls, client: BleakClient, command: int, data: Optional[bytearray] = None
    ) -> bytearray:
        iter, callback = make_iter()
        await cls.DPG.subscribe(client, callback)
        if data:
            await cls.DPG.write_command(client, command, data)
        else:
            await cls.DPG.read_command(client, command)
        async for sender, data in iter:
            # Return the first response from the callback
            await cls.DPG.unsubscribe(client)
            if data[0] == 1:
                return data[2:]
            else:
                return None

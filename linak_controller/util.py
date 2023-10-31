"""
Random helpers and util.
"""

import asyncio
from .config import config


def bytes_to_hex(bytes: bytearray) -> str:
    return bytes.hex(" ")


def hex_to_bytes(hex: str) -> bytearray:
    return bytearray.fromhex(hex)


def bytes_to_int(bytes: bytearray) -> int:
    return int.from_bytes(bytes, byteorder="little")


def bytes_to_utf8(bytes: bytearray) -> str:
    return bytes.decode("utf-8")


def make_iter():
    loop = asyncio.get_event_loop()
    queue = asyncio.Queue()

    def put(*args):
        loop.call_soon_threadsafe(queue.put_nowait, args)

    async def get():
        while True:
            yield await queue.get()

    return get(), put


class Height:
    value: int

    def __init__(self, height: int, convertFromHuman: bool = False):
        if convertFromHuman:
            self.value = self.height_to_internal_height(height)
        else:
            self.value = height  # Relative height in 10ths of a mm

    @classmethod
    def height_to_internal_height(cls, height: int):
        return (height - config.base_height) * 10

    @classmethod
    def internal_height_to_height(cls, height: int):
        return (height / 10) + config.base_height

    @property
    def human(self) -> int:
        return self.internal_height_to_height(self.value)


class Speed:
    value: int

    def __init__(self, speed: int, convert: bool = False):
        if convert:
            self.value = self.speed_to_internal_speed(speed)
        else:
            self.value = speed  # Speed in 100ths of a mm/s

    @classmethod
    def speed_to_internal_speed(cls, speed: int):
        return speed * 100

    @classmethod
    def internal_speed_to_speed(cls, speed: int):
        return speed / 100

    @property
    def human(self) -> int:
        return self.internal_speed_to_speed(self.value)

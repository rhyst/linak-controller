"""
Random helpers and util.
"""

import asyncio

class Logger:
    def log(self, message, end="\n"):
        print(message, end=end)

logger = Logger()

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
    value: int # internal height in 10ths of a mm
    base_height: int = 0 # height of the desk at the lowest position in mm

    def __init__(self, height: int, base_height: int = 0, convertFromHuman: bool = False):
        self.base_height = base_height
        if convertFromHuman:
            self.value = self.height_to_internal_height(height)
        else:
            self.value = height

    def height_to_internal_height(self, height: int):
        return (height - self.base_height) * 10

    def internal_height_to_height(self, height: int):
        return (height / 10) + self.base_height

    @property
    def human(self) -> int:
        return self.internal_height_to_height(self.value)


class Speed:
    value: int # internal speed in 100ths of a mm/s

    def __init__(self, speed: int, convert: bool = False):
        if convert:
            self.value = self.speed_to_internal_speed(speed)
        else:
            self.value = speed  # Speed in 100ths of a mm/s

    def speed_to_internal_speed(self, speed: int):
        return speed * 100

    def internal_speed_to_speed(self, speed: int):
        return speed / 100

    @property
    def human(self) -> int:
        return self.internal_speed_to_speed(self.value)

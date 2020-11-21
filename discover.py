import asyncio
from bleak import BleakScanner, BleakError


async def run_scan(adapter_name: str) -> list:
    """Scan for discoverable bluetooth devices."""
    try:
        scanner = BleakScanner()
        devices = await scanner.discover(device=adapter_name)
        return devices
    except BleakError:
        return None


def get_devices(adapter_name: str):
    loop = asyncio.get_event_loop()
    devices = loop.run_until_complete(run_scan(adapter_name))
    return devices

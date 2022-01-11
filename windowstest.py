import os
os.environ["BLEAK_LOGGING"] = "1"
import asyncio
from bleak import BleakClient, BleakScanner

address = "E8:5B:5B:24:22:E4" # YOUR MAC ADDRESS

async def run(address):
    device = await BleakScanner.find_device_by_address(address)
    client = BleakClient(device)
    print(await client.connect(timeout=30))
    # scanner = BleakScanner()
    # found = None
    # devices = await scanner.discover(timeout=10)
    # for device in devices:
    #     if (device.address == address):
    #         print('found')
    #         found = device
    # if found:
    #     client = BleakClient(device)
    #     print(await client.connect(timeout=30))
    # else:
    #     print('not found')

asyncio.run(run(address))
#!/usr/bin/env python3
import os
import sys
import shutil
import struct
import argparse
import yaml
import asyncio
import aiohttp
from aiohttp import web
from bleak import BleakClient, BleakError, BleakScanner
import json
from functools import partial
from appdirs import user_config_dir

IS_WINDOWS = sys.platform == "win32"

# HELPER FUNCTIONS


def mmToRaw(mm):
    return (mm - BASE_HEIGHT) * 10


def rawToMM(raw):
    return (raw / 10) + BASE_HEIGHT


def rawToSpeed(raw):
    return raw / 100


# GATT CHARACTERISTIC AND COMMAND DEFINITIONS

UUID_HEIGHT = "99fa0021-338a-1024-8a49-009c0215f78a"
UUID_COMMAND = "99fa0002-338a-1024-8a49-009c0215f78a"
UUID_REFERENCE_INPUT = "99fa0031-338a-1024-8a49-009c0215f78a"

COMMAND_STOP = bytearray(struct.pack("<H", 255))
COMMAND_WAKEUP = bytearray(struct.pack("<H", 254))

# OTHER DEFINITIONS
DEFAULT_CONFIG_DIR = user_config_dir("idasen-controller")
DEFAULT_CONFIG_PATH = os.path.join(DEFAULT_CONFIG_DIR, "config.yaml")

# CONFIGURATION SETUP

# Default config
if not os.path.isfile(DEFAULT_CONFIG_PATH):
    os.makedirs(os.path.dirname(DEFAULT_CONFIG_PATH), exist_ok=True)
    shutil.copyfile(
        os.path.join(os.path.dirname(__file__), "example", "config.yaml"),
        DEFAULT_CONFIG_PATH,
    )

# Height of the desk at it's lowest (in mm)
DEFAULT_BASE_HEIGHT = 620
# And how high it can rise above that (same for all desks)
DEFAULT_MOVEMENT_RANGE = 650

config = {
    "mac_address": None,
    "base_height": DEFAULT_BASE_HEIGHT,
    "movement_range": DEFAULT_MOVEMENT_RANGE,
    "adapter_name": "hci0",
    "scan_timeout": 5,
    "connection_timeout": 10,
    "movement_timeout": 30,
    "server_address": "127.0.0.1",
    "server_port": 9123,
    "favourites": {},
}

parser = argparse.ArgumentParser(description="")

# Config via command line options

parser.add_argument(
    "--mac-address", dest="mac_address", type=str, help="Mac address of the Idasen desk"
)
parser.add_argument(
    "--base-height",
    dest="base_height",
    type=int,
    help="The height of tabletop above ground at lowest position (mm)",
)
parser.add_argument(
    "--movement-range",
    dest="movement_range",
    type=int,
    help="How far above base-height the desk can extend (mm)",
)
parser.add_argument(
    "--adapter", dest="adapter_name", type=str, help="The bluetooth adapter device name"
)
parser.add_argument(
    "--scan-timeout",
    dest="scan_timeout",
    type=int,
    help="The timeout for bluetooth scan (seconds)",
)
parser.add_argument(
    "--connection-timeout",
    dest="connection_timeout",
    type=int,
    help="The timeout for bluetooth connection (seconds)",
)
parser.add_argument(
    "--movement-timeout",
    dest="movement_timeout",
    type=int,
    help="The timeout for waiting for the desk to reach the specified height (seconds)",
)
parser.add_argument(
    "--forward",
    dest="forward",
    action="store_true",
    help="Forward any commands to a server",
)
parser.add_argument(
    "--server-address",
    dest="server_address",
    type=str,
    help="The address the server should run at",
)
parser.add_argument(
    "--server_port",
    dest="server_port",
    type=int,
    help="The port the server should run on",
)
parser.add_argument(
    "--config",
    dest="config",
    type=str,
    help="File path to the config file (Default: {})".format(DEFAULT_CONFIG_PATH),
    default=DEFAULT_CONFIG_PATH,
)

# Command to run

cmd = parser.add_mutually_exclusive_group()
cmd.add_argument(
    "--watch",
    dest="watch",
    action="store_true",
    help="Watch for changes to desk height and speed and print them",
)
cmd.add_argument(
    "--move-to",
    dest="move_to",
    help="Move desk to specified height (mm) or to a favourite position",
)
cmd.add_argument(
    "--scan",
    dest="scan_adapter",
    action="store_true",
    help="Scan for devices using the configured adapter",
)
cmd.add_argument(
    "--server",
    dest="server",
    action="store_true",
    help="Run as a server to accept forwarded commands",
)
cmd.add_argument(
    "--tcp-server",
    dest="tcp_server",
    action="store_true",
    help="Run as a simple TCP server to accept forwarded commands",
)

args = {k: v for k, v in vars(parser.parse_args()).items() if v is not None}

# Overwrite config from config.yaml
config_file = {}
config_file_path = os.path.join(args["config"])
if config_file_path and os.path.isfile(config_file_path):
    with open(config_file_path, "r") as stream:
        try:
            config_file = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print("Reading config.yaml failed")
            exit(1)
else:
    print("No config file found")
config.update(config_file)

# Overwrite config from command line args
config.update(args)

# recompute base and max height
BASE_HEIGHT = config["base_height"]
MAX_HEIGHT = BASE_HEIGHT + config["movement_range"]

if not config["mac_address"]:
    parser.error("Mac address must be provided")

if "sit_height_offset" in config:
    if not (0 <= config["sit_height_offset"] <= config["movement_range"]):
        parser.error(
            "Sit height offset must be within [0, {}]".format(config["movement_range"])
        )
    config["sit_height"] = BASE_HEIGHT + config["sit_height_offset"]

if "stand_height_offset" in config:
    if not (0 <= config["stand_height_offset"] <= config["movement_range"]):
        parser.error(
            "Stand height offset must be within [0, {}]".format(
                config["movement_range"]
            )
        )
    config["stand_height"] = BASE_HEIGHT + config["stand_height_offset"]

config["mac_address"] = config["mac_address"].upper()

if IS_WINDOWS:
    # Windows doesn't use this parameter so rename it so it looks nice for the logs
    config["adapter_name"] = "default adapter"

# MAIN PROGRAM


async def get_height_speed(client):
    return struct.unpack("<Hh", await client.read_gatt_char(UUID_HEIGHT))


def get_height_data_from_notification(sender, data, log=print):
    height, speed = struct.unpack("<Hh", data)
    print(
        "Height: {:4.0f}mm Speed: {:2.0f}mm/s".format(
            rawToMM(height), rawToSpeed(speed)
        )
    )


async def wakeUp(client):
    await client.write_gatt_char(UUID_COMMAND, COMMAND_WAKEUP)


async def move_to_target(client, target):
    encoded_target = bytearray(struct.pack("<H", int(target)))
    await client.write_gatt_char(UUID_REFERENCE_INPUT, encoded_target)


async def stop(client):
    try:
        await client.write_gatt_char(UUID_COMMAND, COMMAND_STOP)
    except BleakError as e:
        # This seems to result in a an error on Raspberry Pis but it does not affect movement
        # bleak.exc.BleakDBusError: [org.bluez.Error.NotPermitted] Write acquired
        pass


async def subscribe(client, uuid, callback):
    """Listen for notifications on a characteristic"""
    await client.start_notify(uuid, callback)


async def unsubscribe(client, uuid):
    """Stop listenening for notifications on a characteristic"""
    try:
        await client.stop_notify(uuid)
    except KeyError:
        # This happens on windows, I don't know why
        pass


async def move_to(client, target, log=print):
    """Move the desk to a specified height"""

    initial_height, speed = struct.unpack(
        "<Hh", await client.read_gatt_char(UUID_HEIGHT)
    )

    if initial_height == target:
        return

    await wakeUp(client)
    await stop(client)

    while True:
        await move_to_target(client, target)
        await asyncio.sleep(0.5)
        height, speed = await get_height_speed(client)
        log(
            "Height: {:4.0f}mm Speed: {:2.0f}mm/s".format(
                rawToMM(height), rawToSpeed(speed)
            )
        )
        if speed == 0:
            break

    await unsubscribe(client, UUID_HEIGHT)


async def scan():
    """Scan for a bluetooth device with the configured address and return it or return all devices if no address specified"""
    print("Scanning\r", end="")
    devices = await BleakScanner().discover(
        device=config["adapter_name"], timeout=config["scan_timeout"]
    )
    print("Found {} devices using {}".format(len(devices), config["adapter_name"]))
    for device in devices:
        print(device)
    return devices


async def connect(client=None, attempt=0):
    """Attempt to connect to the desk"""
    try:
        print("Connecting\r", end="")
        if not client:
            client = BleakClient(config["mac_address"], device=config["adapter_name"])
        await client.connect(timeout=config["connection_timeout"])
        print("Connected {}".format(config["mac_address"]))
        return client
    except BleakError as e:
        print("Connecting failed")
        print(e)
        os._exit(1)


async def disconnect(client):
    """Attempt to disconnect cleanly"""
    if client.is_connected:
        await client.disconnect()


async def run_command(client, config, log=print):
    """Begin the action specified by command line arguments and config"""
    # Always print current height
    initial_height, speed = struct.unpack(
        "<Hh", await client.read_gatt_char(UUID_HEIGHT)
    )
    log("Height: {:4.0f}mm".format(rawToMM(initial_height)))
    target = None
    if config.get("watch"):
        # Print changes to height data
        log("Watching for changes to desk height and speed")
        await subscribe(
            client, UUID_HEIGHT, partial(get_height_data_from_notification, log=log)
        )
        wait = asyncio.get_event_loop().create_future()
        await wait
    elif config.get("move_to"):
        # Move to custom height
        favouriteValue = config.get("favourites", {}).get(config["move_to"])
        if favouriteValue:
            target = mmToRaw(favouriteValue)
            log(f'Moving to favourite height: {config["move_to"]}')
        else:
            try:
                target = mmToRaw(int(config["move_to"]))
                log(f'Moving to height: {config["move_to"]}')
            except ValueError:
                log(f'Not a valid height or favourite position: {config["move_to"]}')
                return
        await move_to(client, target, log=log)
    if target:
        final_height, speed = struct.unpack(
            "<Hh", await client.read_gatt_char(UUID_HEIGHT)
        )
        # If we were moving to a target height, wait, then print the actual final height
        log(
            "Final height: {:4.0f}mm (Target: {:4.0f}mm)".format(
                rawToMM(final_height), rawToMM(target)
            )
        )


async def run_tcp_server(client, config):
    """Start a simple tcp server to listen for commands"""

    def disconnect_callback(client, _=None):
        print("Lost connection with {}".format(client.address))
        asyncio.create_task(connect(client))

    client.set_disconnected_callback(disconnect_callback)
    server = await asyncio.start_server(
        partial(run_tcp_forwarded_command, client, config),
        config["server_address"],
        config["server_port"],
    )
    print("TCP Server listening")
    await server.serve_forever()


async def run_tcp_forwarded_command(client, config, reader, writer):
    """Run commands received by the tcp server"""
    print("Received command")
    request = (await reader.read()).decode("utf8")
    forwarded_config = json.loads(str(request))
    merged_config = {**config, **forwarded_config}
    await run_command(client, merged_config)
    writer.close()


async def run_server(client, config):
    """Start a server to listen for commands via websocket connection"""

    def disconnect_callback(client, _=None):
        print("Lost connection with {}".format(client.address))
        asyncio.create_task(connect(client))

    client.set_disconnected_callback(disconnect_callback)

    app = web.Application()
    app.router.add_get("/", partial(run_forwarded_command, client, config))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config["server_address"], config["server_port"])
    await site.start()
    print("Server listening")
    while True:
        await asyncio.sleep(1000)


async def run_forwarded_command(client, config, request):
    """Run commands received by the server"""
    print("Received command")
    ws = web.WebSocketResponse()

    def log(message, end="\n"):
        print(message, end=end)
        asyncio.create_task(ws.send_str(str(message)))

    await ws.prepare(request)
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            forwarded_config = json.loads(msg.data)
            merged_config = {**config, **forwarded_config}
            await run_command(client, merged_config, log)
        break
    await asyncio.sleep(1)  # Allows final messages to send on web socket
    await ws.close()
    return ws


async def forward_command(config):
    """Send commands to a server instance of this script"""
    allowed_keys = ["move_to"]
    forwarded_config = {key: config[key] for key in allowed_keys if key in config}
    session = aiohttp.ClientSession()
    ws = await session.ws_connect(
        f'http://{config["server_address"]}:{config["server_port"]}'
    )
    await ws.send_str(json.dumps(forwarded_config))
    while True:
        msg = await ws.receive()
        if msg.type == aiohttp.WSMsgType.text:
            print(msg.data)
        elif msg.type in [aiohttp.WSMsgType.closed, aiohttp.WSMsgType.error]:
            break
    await ws.close()
    await session.close()


async def main():
    """Set up the async event loop and signal handlers"""
    try:
        client = None
        # Forward and scan don't require a connection so run them and exit
        if config["forward"]:
            await forward_command(config)
        elif config["scan_adapter"]:
            await scan()
        else:
            # Server and other commands do require a connection so set one up
            client = await connect()
            if config["server"]:
                await run_server(client, config)
            elif config.get("tcp_server"):
                await run_tcp_server(client, config)
            else:
                await run_command(client, config, print)
    except Exception as e:
        print("\nSomething unexpected went wrong:")
        print(e)
    finally:
        if client:
            print("\rDisconnecting\r", end="")
            await stop(client)
            await disconnect(client)
            print("Disconnected         ")


def init():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    init()

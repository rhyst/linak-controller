#!/usr/bin/env python3
import os
import traceback
import asyncio
import aiohttp
from aiohttp import web
from bleak import BleakClient, BleakError, BleakScanner
import json
from functools import partial
from .config import config, Commands
from .util import Height
from .desk import Desk


async def scan():
    """Scan for a bluetooth device with the configured address and return it or return all devices if no address specified"""
    print("Scanning\r", end="")
    devices = await BleakScanner().discover(
        device=config.adapter_name, timeout=config.scan_timeout
    )
    print("Found {} devices using {}".format(len(devices), config.adapter_name))
    for device in devices:
        print(device)
    return devices


def disconnect_callback(client, _=None):
    if not config.disconnecting:
        print("Lost connection with {}".format(client.address))
        asyncio.create_task(connect(client))


async def connect(client=None, attempt=0):
    """Attempt to connect to the desk"""
    try:
        print("Connecting\r", end="")
        if not client:
            client = BleakClient(
                config.mac_address,
                device=config.adapter_name,
                disconnected_callback=disconnect_callback,
            )
        await client.connect(timeout=config.connection_timeout)
        print("Connected {}".format(config.mac_address))

        await Desk.initialise(client)

        return client
    except BleakError as e:
        print("Connecting failed")
        if "was not found" in str(e):
            print(e)
        else:
            print(traceback.format_exc())
        os._exit(1)
    except asyncio.exceptions.TimeoutError as e:
        print("Connecting failed - timed out")
        os._exit(1)
    except OSError as e:
        print(e)
        os._exit(1)


async def disconnect(client):
    """Attempt to disconnect cleanly"""
    if client.is_connected:
        config.disconnecting = True
        await client.disconnect()


async def run_command(client: BleakClient):
    """Begin the action specified by command line arguments and config"""
    # Always print current height
    initial_height, _ = await Desk.get_height_speed(client)
    config.log("Height: {:4.0f}mm".format(initial_height.human))
    target = None
    if config.command == Commands.watch:
        # Print changes to height data
        config.log("Watching for changes to desk height and speed")
        await Desk.watch_height_speed(client)
    elif config.command == Commands.move_to:
        # Move to custom height
        if config.move_to in config.favourites:
            target = Height(config.favourites.get(config.move_to), True)
            config.log(
                f"Moving to favourite height: {config.move_to} ({target.human} mm)"
            )
        elif str(config.move_to).isnumeric():
            target = Height(int(config.move_to), True)
            config.log(f"Moving to height: {config.move_to}")
        else:
            config.log(f"Not a valid height or favourite position: {config.move_to}")
            return
        if target.value == initial_height.value:
            config.log(f"Nothing to do - already at specified height")
            return
        await Desk.move_to(client, target)
    if target:
        final_height, _ = await Desk.get_height_speed(client)
        # If we were moving to a target height, wait, then print the actual final height
        config.log(
            "Final height: {:4.0f}mm (Target: {:4.0f}mm)".format(
                final_height.human, target.human
            )
        )


async def run_tcp_server(client):
    """Start a simple tcp server to listen for commands"""

    server = await asyncio.start_server(
        partial(run_tcp_forwarded_command, client),
        config.server_address,
        config.server_port,
    )
    print("TCP Server listening")
    await server.serve_forever()


async def run_tcp_forwarded_command(client, reader, writer):
    """Run commands received by the tcp server"""
    print("Received command")
    request = (await reader.read()).decode("utf8")
    forwarded_config = json.loads(str(request))
    for key in forwarded_config:
        setattr(config, key, forwarded_config[key])
    await run_command(client)
    writer.close()


async def run_server(client: BleakClient):
    """Start a server to listen for commands via websocket connection"""
    app = web.Application()
    app.router.add_get("/", partial(run_forwarded_command, client))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.server_address, config.server_port)
    await site.start()
    print("Server listening")
    await asyncio.Future()


async def run_forwarded_command(client: BleakClient, request):
    """Run commands received by the server"""
    print("Received command")
    ws = web.WebSocketResponse()

    def log(message, end="\n"):
        print(message, end=end)
        asyncio.create_task(ws.send_str(str(message)))

    config.log = log

    await ws.prepare(request)
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            forwarded_config = json.loads(msg.data)
            for key in forwarded_config:
                setattr(config, key, forwarded_config[key])
            await run_command(client)
        break
    await asyncio.sleep(1)  # Allows final messages to send on web socket
    await ws.close()
    return ws


async def forward_command():
    """Send commands to a server instance of this script"""
    allowed_commands = [None, Commands.move_to]
    if config.command not in allowed_commands:
        print(f"Command must be one of {allowed_commands}")
        return
    config_dict = config.__dict__
    allowed_keys = ["command", "move_to"]
    forwarded_config = {
        key: config_dict[key] for key in allowed_keys if key in config_dict
    }
    session = aiohttp.ClientSession()
    ws = await session.ws_connect(
        f"http://{config.server_address}:{config.server_port}"
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
        if config.forward:
            await forward_command()
        elif config.command == Commands.scan_adapter:
            await scan()
        else:
            # Server and other commands do require a connection so set one up
            client = await connect()
            if config.command == Commands.server:
                await run_server(client)
            elif config.command == Commands.tcp_server:
                await run_tcp_server(client)
            else:
                await run_command(client)
    except Exception as e:
        print("\nSomething unexpected went wrong:")
        print(traceback.format_exc())
    finally:
        if client:
            print("\rDisconnecting\r", end="")
            await Desk.stop(client)
            await disconnect(client)
            print("Disconnected         ")


def init():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    init()

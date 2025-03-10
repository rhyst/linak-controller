#!/usr/bin/env python3
import os
import traceback
import asyncio
import aiohttp
from aiohttp import web
from bleak import BleakClient, BleakError, BleakScanner
import json
from functools import partial
from .config import get_config, Config, Command, Commands
from .util import Height, logger
from .desk import Desk


async def scan(config: Config):
    """Scan for a bluetooth device with the configured address and return it or return all devices if no address specified"""
    logger.log("Scanning\r", end="")
    devices = await BleakScanner().discover(
        device=config["adapter_name"], timeout=config["scan_timeout"]
    )
    logger.log("Found {} devices using {}".format(len(devices), config["adapter_name"]))
    for device in devices:
        logger.log(device)
    return devices

desk_for_disconnect = None

def disconnect_callback(client: BleakClient, _=None):
    global desk_for_disconnect
    if not desk_for_disconnect.disconnecting:
        logger.log("Lost connection with {}".format(client.address))
        asyncio.create_task(connect(desk_for_disconnect.config, desk_for_disconnect))


async def connect(config: Config, desk=None, attempt=0):
    """Attempt to connect to the desk"""
    try:
        logger.log("Connecting\r", end="")
        if not desk:
            client = BleakClient(
                config["mac_address"],
                device=config["adapter_name"],
                disconnected_callback=disconnect_callback,
            )
            await client.connect(timeout=config["connection_timeout"])
            logger.log("Connected: {}".format(config["mac_address"]))
            desk = await Desk.initialise(config, client)
            global desk_for_disconnect
            desk_for_disconnect = desk
        else:
            await desk.client.connect(timeout=config["connection_timeout"])
            logger.log("Reconnected: {}".format(config["mac_address"]))
        return desk
    except BleakError as e:
        logger.log("Connecting failed")
        if "was not found" in str(e):
            logger.log(e)
        else:
            logger.log(traceback.format_exc())
        os._exit(1)
    except asyncio.exceptions.TimeoutError as e:
        logger.log("Connecting failed - timed out")
        os._exit(1)
    except OSError as e:
        logger.log(e)
        os._exit(1)


async def disconnect(desk: Desk):
    """Attempt to disconnect cleanly"""
    if desk.client.is_connected:
        desk.disconnecting = True
        await desk.client.disconnect()


async def run_command(desk: Desk, command: Command):
    """Begin the action specified by command line arguments and config"""
    # Always print current height
    initial_height, _ = await desk.get_height_speed()
    logger.log("Height: {:4.0f}mm".format(initial_height.human))
    target = None
    
    if command["key"] == Commands.watch:
        # Print changes to height data
        logger.log("Watching for changes to desk height and speed")
        await desk.watch_height_speed()
    elif command["key"] == Commands.move_to:
        # Move to custom height
        if command["value"] in desk.config["favourites"]:
            target = Height(
                desk.config["favourites"].get(command["value"]), desk.base_height, True
            )
            logger.log(
                f"""Moving to favourite height: {command["value"]} ({target.human} mm)"""
            )
        elif str(command["value"]).isnumeric():
            target = Height(int(command["value"]), desk.config["base_height"], True)
            logger.log(f"""Moving to height: {command["value"]}""")
        else:
            logger.log(
                f"""Not a valid height or favourite position: {command["value"]}"""
            )
            return
        if target.value == initial_height.value:
            logger.log(f"Nothing to do - already at specified height")
            return
        await desk.move_to(target)
    if target:
        final_height, _ = await desk.get_height_speed()
        # If we were moving to a target height, wait, then print the actual final height
        logger.log(
            "Final height: {:4.0f}mm (Target: {:4.0f}mm)".format(
                final_height.human, target.human
            )
        )


async def run_tcp_server(desk: Desk):
    """Start a simple tcp server to listen for commands"""

    server = await asyncio.start_server(
        partial(run_tcp_forwarded_command, desk),
        desk.config["server_address"],
        desk.config["server_port"],
    )
    logger.log("TCP Server listening")
    await server.serve_forever()


async def run_tcp_forwarded_command(desk: Desk, reader, writer):
    """Run commands received by the tcp server"""
    logger.log("Received command")
    request = (await reader.read()).decode("utf8")
    command = json.loads(str(request))
    await run_command(desk, command)
    writer.close()


async def run_http_server(desk: Desk):
    """Start a server to listen for commands via websocket connection"""
    app = web.Application()
    app.router.add_post("/", partial(run_forwarded_http_command, desk))
    app.router.add_get("/ws", partial(run_forwarded_ws_command, desk))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, desk.config["server_address"], desk.config["server_port"])
    await site.start()
    logger.log("Server listening")
    await asyncio.Future()


async def run_forwarded_http_command(desk: Desk, request):
    """Run commands received by the server"""
    logger.log("Received command")
    command = await request.json()
    await run_command(desk, command)
    return web.Response(text="OK")


async def run_forwarded_ws_command(desk: Desk, request):
    """
    Run commands received by the server via websocket connection
    This allows live streaming of the logs back to the client
    """
    logger.log("Received ws command")
    ws = web.WebSocketResponse()

    def log(message, end="\n"):
        logger.log(message, end=end)
        asyncio.create_task(ws.send_str(str(message)))

    logger.log = log

    await ws.prepare(request)
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            command = json.loads(msg.data)
            await run_command(desk, command)
        break
    await asyncio.sleep(1)  # Allows final messages to send on web socket
    await ws.close()
    return ws


async def forward_command(config: Config, command: Command):
    """Send commands to a server instance of this script"""
    allowed_commands = [None, Commands.move_to]
    if command["key"] not in allowed_commands:
        logger.log(f"Command must be one of {allowed_commands}")
        return
    session = aiohttp.ClientSession()
    ws = await session.ws_connect(
        f"""http://{config["server_address"]}:{config["server_port"]}/ws"""
    )
    await ws.send_str(json.dumps(command))
    while True:
        msg = await ws.receive()
        if msg.type == aiohttp.WSMsgType.text:
            logger.log(msg.data)
        elif msg.type in [aiohttp.WSMsgType.closed, aiohttp.WSMsgType.error]:
            break
    await ws.close()
    await session.close()


async def main():
    """Set up the async event loop and signal handlers"""
    desk = None
    try:
        config, command = get_config()
        # Forward and scan don't require a connection so run them and exit
        if config["forward"]:
            await forward_command(config, command)
        elif command["key"] == Commands.scan_adapter:
            await scan(config)
        else:
            # Server and other commands do require a connection so set one up
            desk = await connect(config)
            if command["key"] == Commands.server:
                await run_http_server(desk)
            elif command["key"] == Commands.tcp_server:
                await run_tcp_server(desk)
            else:
                await run_command(desk, command)
    except Exception as e:
        logger.log("\nSomething unexpected went wrong:")
        logger.log(traceback.format_exc())
    finally:
        if desk:
            logger.log("\rDisconnecting\r", end="")
            await desk.stop()
            await disconnect(desk)
            logger.log("Disconnected         ")


def init():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    init()

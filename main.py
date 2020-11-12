#!python3
import os
import sys
import struct
import argparse
import yaml
import asyncio
import traceback 
from signal import SIGINT, SIGTERM
from bleak import BleakClient, discover, BleakError
import atexit

IS_WINDOWS = os.name == 'nt'
IS_LINUX = os.name == 'posix'

# HELPER FUNCTIONS

def mmToRaw(mm):
    return (mm - BASE_HEIGHT) * 10

def rawToMM(raw):
    return (raw / 10) + BASE_HEIGHT

def rawToSpeed(raw):
    return (raw / 100)

# GATT CHARACTERISTIC AND COMMAND DEFINITIONS

UUID_HEIGHT = '99fa0021-338a-1024-8a49-009c0215f78a'
UUID_COMMAND = '99fa0002-338a-1024-8a49-009c0215f78a'
UUID_REFERENCE_INPUT = '99fa0031-338a-1024-8a49-009c0215f78a'

COMMAND_UP = bytearray(struct.pack("<H", 71))
COMMAND_DOWN = bytearray(struct.pack("<H", 70))
COMMAND_STOP = bytearray(struct.pack("<H", 255))

COMMAND_REFERENCE_INPUT_STOP = bytearray(struct.pack("<H", 32769))
COMMAND_REFERENCE_INPUT_UP = bytearray(struct.pack("<H", 32768))
COMMAND_REFERENCE_INPUT_DOWN = bytearray(struct.pack("<H", 32767))

# CONFIGURATION SETUP

# Height of the desk at it's lowest (in mm)
# I assume this is the same for all Idasen desks
BASE_HEIGHT = 620
MAX_HEIGHT = 1270  # 6500

# Default config
config = {
    "mac_address": None,
    "stand_height": BASE_HEIGHT + 420,
    "sit_height": BASE_HEIGHT + 63,
    "adapter_name": 'hci0',
    "sit": False,
    "stand": False,
    "monitor": False,
    "move_to": None
}

# Overwrite from config.yaml
config_file = {}
config_file_path = os.path.join(os.path.dirname(
    os.path.realpath(__file__)), 'config.yaml')
if (config_file_path):
    with open(config_file_path, 'r') as stream:
        try:
            config_file = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print("Reading config.yaml failed")
            exit(1)
config.update(config_file)

# Overwrite from command line args
parser = argparse.ArgumentParser(description='')
parser.add_argument('--mac-address', dest='mac_address',
                    type=str, help="Mac address of the Idasen desk")
parser.add_argument('--stand-height', dest='stand_height', type=int,
                    help="The height the desk should be at when standing")
parser.add_argument('--sit-height', dest='sit_height', type=int,
                    help="The height the desk should be at when sitting")
parser.add_argument('--adapter', dest='adapter_name', type=str,
                    help="The bluetooth adapter device name")
cmd = parser.add_mutually_exclusive_group()
cmd.add_argument('--sit', dest='sit', action='store_true',
                 help="Move the desk to sitting height")
cmd.add_argument('--stand', dest='stand', action='store_true',
                 help="Move the desk to standing height")
cmd.add_argument('--monitor', dest='monitor', action='store_true',
                 help="Monitor desk height and speed")
cmd.add_argument('--move-to',dest='move_to', type=int,
                 help="Move desk to specified height (mm above ground)")

args = {k: v for k, v in vars(parser.parse_args()).items() if v is not None}
config.update(args)

if not config['mac_address']:
    parser.error("Mac address must be provided")

if config['sit_height'] >= config['stand_height']:
    parser.error("Sit height must be less than stand height")

if config['sit_height'] < BASE_HEIGHT:
    parser.error("Sit height must be greater than {}".format(BASE_HEIGHT))

if config['stand_height'] > MAX_HEIGHT:
    parser.error("Stand height must be less than {}".format(MAX_HEIGHT))

config['stand_height_raw'] = mmToRaw(config['stand_height'])
config['sit_height_raw'] = mmToRaw(config['sit_height'])
if config['move_to']:
    config['move_to_raw'] = mmToRaw(config['move_to'])

# MAIN PROGRAM

def print_height_data(sender, data):
    height, speed = struct.unpack("<Hh", data)
    print("Current height: {}mm, speed: {}".format(rawToMM(height), rawToSpeed(speed)))

def has_reached_target(height, target):
    # The notified height values seem a bit behind so try to stop before
    # reaching the target value to prevent overshooting
    return (abs(height - target) <= 20)

async def move_up(client):
    await client.write_gatt_char(UUID_COMMAND, COMMAND_UP)

async def move_down(client):
    await client.write_gatt_char(UUID_COMMAND, COMMAND_DOWN)

async def stop(client):
    # This emulates the behaviour of the app. Stop commands are sent to both
    # Reference Input and Command characteristics.
    await client.write_gatt_char(UUID_COMMAND, COMMAND_STOP)
    if IS_LINUX:
        # It doesn't like this on windows
        await client.write_gatt_char(UUID_REFERENCE_INPUT, COMMAND_REFERENCE_INPUT_STOP)

unsubscribe_flag = False

def should_unsubscribe():
    global unsubscribe_flag
    return unsubscribe_flag

def ask_unsubscribe():
    print('Disconnecting')
    global unsubscribe_flag
    unsubscribe_flag = True


async def subscribe(client, uuid, callback):
    """Listen for notifications on a characteristic"""
    await client.start_notify(uuid, callback)

    while not should_unsubscribe():
        await asyncio.sleep(0.1)

    await client.stop_notify(uuid)

async def move_to(client, target):
    """Move the desk to a specified height"""

    initial_height, speed = struct.unpack("<Hh", await client.read_gatt_char(UUID_HEIGHT))

    # Initialise by setting the movement direction
    direction = "UP" if target > initial_height else "DOWN"
    
    # Set up callback to run when the desk height changes. It will resend
    # movement commands until the desk has reached the target height.
    global count
    count = 0
    def _move_to(sender, data):
        global count
        height, speed = struct.unpack("<Hh", data)
        count = count + 1
        # Stop if we have reached the target
        if has_reached_target(height, target):
            print("Stopping at height: {}mm (target: {}mm)".format(rawToMM(height), rawToMM(target)))
            asyncio.create_task(stop(client))
            ask_unsubscribe()
        # Or resend the movement command if we have not yet reached the
        # target.
        # Each movement command seems to run the desk motors for about 1
        # second if uninterrupted and the height value is updated about 16
        # times.
        # Resending the command on the 6th update seems a good balance
        # between helping to avoid overshoots and preventing stutterinhg
        # (the motor seems to slow if no new move command has been sent)
        elif direction == "UP" and count == 6:
            asyncio.create_task(move_up(client))
            count = 0
        elif direction == "DOWN" and count == 6:
            asyncio.create_task(move_down(client))
            count = 0

    # Listen for changes to desk height and send first move command (if we are 
    # not) already at the target height.
    if not has_reached_target(initial_height, target):
        tasks = [ subscribe(client, UUID_HEIGHT, _move_to) ]
        if direction == "UP":
            tasks.append(move_up(client))
        elif direction == "DOWN":
            tasks.append(move_down(client))
        await asyncio.gather(*[task for task in tasks])

if IS_LINUX:
    client = BleakClient(config['mac_address'], timeout=10, device=config['adapter_name'])
if IS_WINDOWS:
    client = BleakClient(config['mac_address'], timeout=10)

async def run():
    """Begin the action specified by command line arguments and config"""
    try:
        print('Connecting')
        await client.connect()

        def disconnect_callback(client):
            print("Lost connection with {}".format(client.address))
            ask_unsubscribe()
        client.set_disconnected_callback(disconnect_callback)

        print("Connected {}".format(config['mac_address']))
        # Always print current height
        initial_height, speed = struct.unpack("<Hh", await client.read_gatt_char(UUID_HEIGHT))
        print("Initial height: {}mm".format(rawToMM(initial_height)))
        if config['monitor']:
            # Print changes to height data
            await subscribe(client, UUID_HEIGHT, print_height_data)
        elif config['sit']:
            # Move to configured sit height
            await move_to(client, config['sit_height_raw'])
        elif config['stand']:
            # Move to configured stand height
            await move_to(client, config['stand_height_raw'])
        elif config['move_to']:
            # Move to custom height
            await move_to(client, config['move_to_raw'])
    except BleakError as e:
        print(e)
    except Exception as e:
        traceback.print_exc() 

def main():
    """Set up the async event loop and signal handlers"""
    loop = asyncio.get_event_loop()

    if IS_LINUX:
        for sig in (SIGINT, SIGTERM):
            # We must run client.disconnect() so attempt to exit gracefully
            loop.add_signal_handler(sig, ask_unsubscribe)

    loop.run_until_complete(run())

    if client:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(client.disconnect())
        print('Disconnected')

    loop.stop()
    loop.close()

if __name__ == "__main__":
    main()

#!python3
import gatt
import struct
import argparse
import os
import yaml

UUID_HEIGHT = '99fa0021-338a-1024-8a49-009c0215f78a'
UUID_COMMAND = '99fa0002-338a-1024-8a49-009c0215f78a'
UUID_REFERENCE_INPUT = '99fa0031-338a-1024-8a49-009c0215f78a'

COMMAND_UP = struct.pack("<H", 71)
COMMAND_DOWN = struct.pack("<H", 70)
COMMAND_STOP = struct.pack("<H", 255)

COMMAND_REFERENCE_INPUT_STOP = struct.pack("<H", 32769)
COMMAND_REFERENCE_INPUT_UP = struct.pack("<H", 32768)
COMMAND_REFERENCE_INPUT_DOWN = struct.pack("<H", 32767)

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
    "stand": False
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


def mmToRaw(mm):
    return (mm - BASE_HEIGHT) * 10


def rawToMM(raw):
    return (raw / 10) + BASE_HEIGHT


config['stand_height_raw'] = mmToRaw(config['stand_height'])
config['sit_height_raw'] = mmToRaw(config['sit_height'])


class Desk(gatt.Device):
    def __init__(self, mac_address, manager, config):
        self.config = config
        self.direction = None
        self.height = None
        self.target = None
        self.count = 0
        super().__init__(mac_address, manager)

    def connect_succeeded(self):
        super().connect_succeeded()
        print("[%s] Connected" % (self.mac_address))

    def connect_failed(self, error):
        super().connect_failed(error)
        print("[%s] Connection failed: %s" % (self.mac_address, str(error)))

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        print("[%s] Disconnected, will reconnect" % (self.mac_address))
        self.connect()

    def services_resolved(self):
        super().services_resolved()

        if self.config['sit']:
            self.target = self.config['sit_height_raw']
        if self.config['stand']:
            self.target = self.config['stand_height_raw']

        for service in self.services:
            for characteristic in service.characteristics:
                if characteristic.uuid == UUID_HEIGHT:
                    self.height_characteristic = characteristic
                    self.height_characteristic.enable_notifications()
                    # Reading the value triggers self.characteristic_value_updated
                    self.height_characteristic.read_value()
                if characteristic.uuid == UUID_COMMAND:
                    self.command_characteristic = characteristic
                if characteristic.uuid == UUID_REFERENCE_INPUT:
                    self.reference_input_characteristic = characteristic

    def characteristic_value_updated(self, characteristic, value):
        if characteristic.uuid == UUID_HEIGHT:
            height, speed = struct.unpack("<Hh", value)
            self.count += 1
            self.height = height

            # No target specified so print current height
            if not self.target:
                print("Current height: {}mm".format(rawToMM(height)))
                self.stop()
                return

            # Initialise by setting the movement direction and asking to send
            # move commands
            if not self.direction:
                print("Initial height: {}mm".format(rawToMM(height)))
                self.direction = "UP" if self.target > self.height else "DOWN"
                self.move_to_target()

            # If already moving then stop if we have reached the target
            if self.has_reached_target():
                print("Stopping at height: {}mm (target: {}mm)".format(
                    rawToMM(height), rawToMM(self.target)))
                self.stop()
            # Or resend the movement command if we have not yet reached the
            # target.
            # Each movement command seems to run the desk motors for about 1
            # second if uninterrupted and the height value is updated about 16
            # times.
            # Resending the command on the 12th update seems a good balance
            # between helping to avoid overshoots and preventing stutterinhg
            # (the motor seems to slow if no new move command has been sent)
            elif self.count == 12:
                self.count = 0
                self.move_to_target()

    def characteristic_write_value_succeeded(self, characteristic):
        if characteristic.uuid == UUID_COMMAND and self.target:
            pass
        if characteristic.uuid == UUID_REFERENCE_INPUT:
            pass

    def characteristic_write_value_failed(self, characteristic, error):
        print("Error ", error)
        self.stop()

    def has_reached_target(self):
        # The notified height values seem a bit behind so try to stop before
        # reaching the target value to prevent overshooting
        return (abs(self.height - self.target) <= 20)

    def move_to_target(self):
        if self.has_reached_target():
            return
        elif self.direction == "DOWN" and self.height > self.target:
            self.move_down()
        elif self.direction == "UP" and self.height < self.target:
            self.move_up()

    def move_up(self):
        self.command_characteristic.write_value(COMMAND_UP)

    def move_down(self):
        self.command_characteristic.write_value(COMMAND_DOWN)

    def stop(self):
        # This emulates the behaviour of the app. Stop commands are sent to both
        # Reference Input and Command characteristics.
        self.command_characteristic.write_value(COMMAND_STOP)
        self.reference_input_characteristic.write_value(
            COMMAND_REFERENCE_INPUT_STOP)
        manager.stop()


manager = gatt.DeviceManager(adapter_name=config['adapter_name'])
device = Desk(mac_address=config['mac_address'],
              manager=manager, config=config)
device.connect()
try:
    manager.run()
except KeyboardInterrupt:
    device.stop()
    manager.stop()

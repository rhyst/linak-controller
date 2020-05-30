import gatt
import struct
import argparse


STAND_HEIGHT = 4402
SIT_HEIGHT = 630

parser = argparse.ArgumentParser(description='')
parser.add_argument('--stand', dest='stand', action='store_true')
parser.set_defaults(stand=False)
args = parser.parse_args()

# Pick your adapter
manager = gatt.DeviceManager(adapter_name='hci0')

class AnyDevice(gatt.Device):
    def __init__(self, mac_address, manager):
        self.direction = None
        self.target = None
        self.height = None
        super().__init__(mac_address, manager)

    def connect_succeeded(self):
        super().connect_succeeded()
        print("[%s] Connected" % (self.mac_address))

    def connect_failed(self, error):
        super().connect_failed(error)
        print("[%s] Connection failed: %s" % (self.mac_address, str(error)))

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        print("[%s] Disconnected" % (self.mac_address))

    def services_resolved(self):
        super().services_resolved()

        for service in self.services:
            for characteristic in service.characteristics:
                if characteristic.uuid == '99fa0021-338a-1024-8a49-009c0215f78a':
                    # raw = characteristic.read_value()
                    # print("Inital height: {}".format(int.from_bytes(bytes([int(raw[0])]) + bytes([int(raw[1])]), 'little')))
                    characteristic.enable_notifications()
                    characteristic.read_value()
                if characteristic.uuid == '99fa0002-338a-1024-8a49-009c0215f78a':
                    self.command = characteristic

    def characteristic_value_updated(self, characteristic, value):
        height, speed = struct.unpack("<HH", value)
        print("Height change: {}".format(height))
        self.height = height
        #if self.has_reached_target():
            #self.command.write_value(struct.pack("<H", 255))
        if not self.direction:
            self.move_to_target()

    def characteristic_write_value_succeeded(self, characteristic):
        self.move_to_target()

    def characteristic_write_value_failed(self, characteristic, error):
        print("Error ", error)

    def has_reached_target(self):
        return (self.direction == "DOWN" and self.height <= self.target) or (self.direction == "UP" and self.height >= self.target)

    def set_target(self, target):
        self.target = target
        self.direction = None

    def move_to_target(self):
        if not self.direction: 
            self.direction = "UP" if self.target > self.height else "DOWN"
        if self.has_reached_target():
            self.command.write_value(struct.pack("<H", 255))
            manager.stop()
        elif self.direction == "DOWN" and self.height > self.target:
            self.command.write_value(struct.pack("<H", 70))
        elif self.direction == "UP" and self.height < self.target:
            self.command.write_value(struct.pack("<H", 71))

device = AnyDevice(mac_address='E8:5B:5B:24:22:E4', manager=manager)
device.connect()
if args.stand:
    device.set_target(STAND_HEIGHT)
else:
    device.set_target(SIT_HEIGHT)

try:
    manager.run()
except KeyboardInterrupt:
    manager.stop()
    print("\rExiting")
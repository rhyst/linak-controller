# idasen-controller

The Idasen is a Linak standing desk sold by Ikea. It can be controlled by a physical switch on the desk or via bluetooth using an phone app. This is a script to control the Idasen via bluetooth from a computer.

## Set up

### Prerequisites

The desk should be connected and paired to the computer.

### Install

Install the Python requirements found in `requirements.txt`:

```
pip install -r requirements.txt
```

### Configuration

Configuration can either be provided with a file, or via command line arguments. Use `--help` to see the command line arguments help. Edit `config.yaml` if you prefer your config to be in a file.

Config options:

- `mac_address` - The MAC address of the desk. This is required.
- `stand_height` - The standing height (mm) from the floor of the desk Default `1040`.
- `sit_height` - The standing height (mm) from the floor of the desk. Default `683`.
- `adapter_name` - The adapter name for the bluetooth adapter to use for the connection (Linux only). Default `hci0`
- `height_tolerance` - Distance (mm) between reported height and target height before ceasing move commands. Default `2.0`
- `scan_timeout` - Timeout to scan for the device (seconds). Default `5`
- `connection_timeout` - Timeout to obtain connection (seconds). Default `10`

Device MAC addresses can be found using `bluetoothctl` and blueooth adapter names can be found with `hcitool dev` on linux, and on Windows you can use [Bluetooth LE Explorer](https://www.microsoft.com/en-us/p/bluetooth-le-explorer/9n0ztkf1qd98?activetab=pivot:overviewtab).

## Usage

### Command Line

To print the current desk height:

```
python3 main.py
```

To monitor for changes to height (and speed):

```
python3 main.py --monitor
```

Assuming the config file is populated to move the desk to standing position:

```
python3 main.py --stand
```

Assuming the config file is populated to move the desk to sitting position:

```
python3 main.py --sit
```

Move the desk to a certain height (mm) above the floor:

```
python3 main.py --move-to 800
```

Listing available bluetooth devices:

```
python main.py --scan ADAPTER_NAME
```

## Recipes

There is a page with a few examples of different ways to use the script: [RECIPES](RECIPES.md)

## Desk Internals

### Connection and Commands

Connecting and pairing can be done by any bluetooth device and there is no authentication. Once connected the desk communicates using Bluetooth LE, using the GATT protocol. GATT is quite complex and I do not understand much of it but the useful bit is that the desk advertises some `characteristics` which are addresses that bytes can be written to and read from. There's various other things like `services` and `descriptors` but they were not relevant to getting this working.

Python has several packages available for communicating over GATT so the only tricky bit is working out what each of the characteristics do and what data they want. It seems like in general they're expecting quite simple data to be exchanged.

The desk is from Ikea but it is a rebranded Linak device, and Linak publish an app to control it. I was able to examine the app to find out missing information. This included mapping the characteristic UUIDs to functionality (the two important ones being the characteristic that accepts commands to control the desk, and the characteristic that broadcasts the current height of the desk), and also finding out the command codes and the format they needed to be in.

For example to move the desk up you encode `71` into bytes as an unsigned little endian short and write that to the characteristic identified by the UUID `99fa0002-338a-1024-8a49-009c0215f78a`. The other command codes are similar short numbers. For some reason there is another characteristic (reference input) that accepts up/down/stop commands but it requires signed little endian shorts. I don't understand why it is like this.

### Behaviour

Sending move commands to the desk seems to make the motors run for about one second in the desired direction. If another move command is sent within that second then the motion continues with no slowing or stopping. If no move command is recieved in that second then the motor slows down towards the end and then stops. If you send a move command late, then there will some stuttering as the desk may have already started to slow the motors. You can stop the motion part way through by sending a stop command though it sometimes does not respond immediately. As the desk moves it sends notifications of the current height to a characteristic. This can be monitored to work out when to stop moving, but it also seems to be a little bit slow and the final notified value is often not the same as the actual final value if a measuremment is made at rest.

The height values the desk provides are in 10ths of a millimetre, and correspond to the height above the desks lowest setting i.e. if you lower the desk as far as it will go then the desk will report its height as being zero. The minimum raw height value is zero and the maximum height is 6500. This corresponds to a range of 620mm to 1270mm off the floor.

The desk appears to be pretty good at not doing anything stupid if you send it stupid commands. It won't try to go below the minimum height or above the maximum height and it doesn't do much if you send lots of commands in quick succession. The usual hit detection works, and it will stop moving if it hits an object and will not respond to further commands until a stop command is sent.

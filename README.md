# idasen-controller

The Idasen is a Linak standing desk sold by Ikea. It can be controlled by a physical switch on the desk or via bluetooth using an phone app. This is a script to control the Idasen via bluetooth from a non-Android device.

## Set up

### Prerequisites

- Windows / Linux / Mac
- The device should have Python 3 (the script has been tested down to 3.7.3)
- The desk should be paired to the device.

### Install

Install using pip:

```
pip3 install idasen-controller
```

### Configuration

Configuration can be provided with a file, or via command line arguments. Use `--help` to see the command line arguments help. Edit `<config_dir>/config.yaml` if you prefer your config to be in a file. `<config_dir>` is normally:

- `~/.config/idasen-controller` on Linux
- `C:\Users\<user>\AppData\Local\idasen-controller\idasen-controller` on Windows
- `~/Library/Application Support/idasen-controller` on MacOS

Config options:

- `mac_address` - The MAC address of the desk. This is required.
- `base_height` - The lowest possible height (mm) of the desk top from the floor. Default `620`.
- `movement_range` - How far above base-height the desk can extend (mm). Default `650`.
- `stand_height` - The standing height (mm) from the floor of the desk Default `1040`.
- `sit_height` - The sitting height (mm) from the floor of the desk. Default `683`.
- `stand_height_offset` - The standing height (mm) as an offset from base_height. Overrides `stand_height` if specified.
- `sit_height_offset` - The sitting height (mm) as an offset from base_height. Overrides `sit_height` if specified.
- `adapter_name` - The adapter name for the bluetooth adapter to use for the connection (Linux only). Default `hci0`
- `height_tolerance` - Distance (mm) between reported height and target height before ceasing move commands. Default `2.0`
- `scan_timeout` - Timeout to scan for the device (seconds). Default `5`
- `connection_timeout` - Timeout to obtain connection (seconds). Default `10`
- `movement_timeout` - Timeout for waiting for the desk to reach the specified height (seconds). Default `30`
- `server_address` - The address the server should run at (if running server). Default `127.0.0.1`
- `server_port` - The port the server should run on (if running server). Default `9123`

#### Device MAC addresses

- On Linux, device MAC addresses can be found using `bluetoothctl` and bluetooth adapter names can be found with `hcitool dev`
- On Windows you can use [Bluetooth LE Explorer](https://www.microsoft.com/en-us/p/bluetooth-le-explorer/9n0ztkf1qd98?activetab=pivot:overviewtab).
- On MacOS you can pair the device with [Bluetility](https://github.com/jnross/Bluetility), but you must use the UUID instead of the Mac Address.

## Usage

### Command Line

To print the current desk height:

```
idasen-controller
```

To monitor for changes to height (and speed):

```
idasen-controller --monitor
```

Assuming the config file is populated to move the desk to standing position:

```
idasen-controller --stand
```

Assuming the config file is populated to move the desk to sitting position:

```
idasen-controller --sit
```

Move the desk to a certain height (mm) above the floor:

```
idasen-controller --move-to 800
```

Listing available bluetooth devices (using the configured `adapter_name`):

```
idasen-controller --scan
```

To run the script as a server, which will maintain the connection and provide quicker response times:

```
idasen-controller --server
```

And to send commands to the server add the forward argument:

```
idasen-controller --forward --stand
```

To specify a path to a config file:

```
idasen-controller --config <path>
```

## Troubleshooting

### Connection failed

The initial connection can fail for a variety of reasons, here are some things to try if it happens repeatedly:

- Try ensuring that the desk is paired but _not_ connected before using the script.
- Try increasing the `scan-timeout` and `connection-timeout`.

### Connection / commands are slow

- Try reducing the `connection-timeout`. I have found that it can work well set to just `1` second. You may find that a low connection timeout results in failed connections sometimes though.
- Use the server mode. Run the script once with `--server` which will start a persistent server and maintain a connection to the desk. Then when sending commands (like `--stand` or `--sit`) just add the additional argument `--forward` to forward the command to the server. The server should already have a connection so the desk should respond much quicker.

### "abort" on MacOS

On MacOS the process may quit with a vague message like `abort`. This could be because the application running the process doesn't have access to Bluetooth. To provide access, open `System Preferences -> Security & Privacy -> Privacy -> Bluetooth` and drag the application running the process into the list (eg. Terminal or iTerm2). [More info at the `bleak` issue](https://github.com/hbldh/bleak/issues/438#issuecomment-787125189)

### Scanning returns no devices on MacOS 12 (Monterey)

It seems like it is no longer possible to scan for devices on MacOS 12, [see this bleak issue for more info](https://github.com/hbldh/bleak/issues/635#issuecomment-988054876). You should acquire the UUID of your device using [Bluetility](https://github.com/jnross/Bluetility) or similair and avoid using the `--scan` function.

## Recipes

There is a page with a few examples of different ways to use the script: [RECIPES](RECIPES.md)

## Development

To run the script without installing via pip first install the requirements:

```
pip3 install -r requirements.txt
```

Then you can run all the same commands with:

```
python3 idasen_controller/main.py <command>
```

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

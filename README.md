# idasen-controller

The Idasen is a Linak standing desk sold by Ikea. It can be controlled by a physical switch on the desk or via bluetooth using an phone app. This is a script to control the Idasen via bluetooth from any other device.

Note: This script may work with other Linak desks but it is not guaranteed - see below

## Set up

### Prerequisites

- Windows / Linux / Mac
- The device should have Python 3 (the script has been tested down to 3.7.3)
- The desk should be paired to the device.

### Working Desks

- Ikea Idasen - the only desk I can confidently say works because I have one
- iMovr Lander - reportedly works because it is the same as an Idasen Desk [43](https://github.com/rhyst/idasen-controller/issues/43)
- Linak DPG1C - Sporadic success reported with this device (help from anyone with this appreciated) [32](https://github.com/rhyst/idasen-controller/issues/32)

If you find another desk model that works please make an issue to report it!

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

| Option                | Description                                                                                    | Default     |
| --------------------- | ---------------------------------------------------------------------------------------------- | ----------- |
| `mac_address`         | The MAC address of the desk. This is required.                                                 |             |
| `base_height`         | The lowest possible height (mm) of the desk top from the floor.                                | `620`.      |
| `movement_range`      | How far above base height the desk can extend (mm).                                            | `650`.      |
| `stand_height`        | The standing height (mm) from the floor of the desk                                            | `1040`      |
| `sit_height`          | The sitting height (mm) from the floor of the desk.                                            | `683`.      |
| `stand_height_offset` | The standing height (mm) as an offset from base_height. Overrides `stand_height` if specified. |             |
| `sit_height_offset`   | The sitting height (mm) as an offset from base_height. Overrides `sit_height` if specified.    |             |
| `adapter_name`        | The adapter name for the bluetooth adapter to use for the connection (Linux only).             | `hci0`      |
| `scan_timeout`        | Timeout to scan for the device (seconds).                                                      | `5`         |
| `connection_timeout`  | Timeout to obtain connection (seconds).                                                        | `10`        |
| `movement_timeout`    | Timeout for waiting for the desk to reach the specified height (seconds).                      | `30`        |
| `server_address`      | The address the server should run at (if running server).                                      | `127.0.0.1` |
| `server_port`         | The port the server should run on (if running server).                                         | `9123`      |

All of these options can be set on the command line, just replace any `_` with `-` e.g. `mac_address` becomes `--mac-address`.

#### Device MAC addresses

- On Linux, device MAC addresses can be found using `bluetoothctl` and bluetooth adapter names can be found with `hcitool dev`
- On Windows you can use [Bluetooth LE Explorer](https://www.microsoft.com/en-us/p/bluetooth-le-explorer/9n0ztkf1qd98?activetab=pivot:overviewtab).
- On MacOS you can pair the device with [Bluetility](https://github.com/jnross/Bluetility), but you must use the UUID instead of the Mac Address.

## Usage

### Commands

The script accepts a number of commands:

| Command                      | Description                                                                                       |
| ---------------------------- | ------------------------------------------------------------------------------------------------- |
|                              | Running without any command will print the current desk height                                    |
| `--monitor`                  | Monitor for changes to height (and speed)                                                         |
| `--stand`                    | Move the desk to the standing height specified in config                                          |
| `--sit`                      | Move the desk to the sitting height specified in config                                           |
| `--move-to <value>`          | Move the desk to a certain height (mm) above the floor                                            |
| `--scan`                     | List available bluetooth devices (using the configured `adapter_name`)                            |
| `--server`                   | Run the script as a server, which will maintain the connection and provide quicker response times |
| `--forward <other commands>` | Send commands to a server                                                                         |
| `--config <path>`            | Specify a path to a config file                                                                   |

For example to move to a particular height you can run:

```
idasen-controller --move-to 800
```

Or to move to a sitting position via a server you can run:

```
idasen-controller --forward --sit
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

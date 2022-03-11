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

| Option               | Description                                                                        | Default                     |
| -------------------- | ---------------------------------------------------------------------------------- | --------------------------- |
| `mac_address`        | The MAC address (or UUID on MacOS) of the desk. This is required.                  |                             |
| `base_height`        | The lowest possible height (mm) of the desk top from the floor.                    | `620`.                      |
| `movement_range`     | How far above base height the desk can extend (mm).                                | `650`.                      |
| `adapter_name`       | The adapter name for the bluetooth adapter to use for the connection (Linux only). | `hci0`                      |
| `scan_timeout`       | Timeout to scan for the device (seconds).                                          | `5`                         |
| `connection_timeout` | Timeout to obtain connection (seconds).                                            | `10`                        |
| `movement_timeout`   | Timeout for waiting for the desk to reach the specified height (seconds).          | `30`                        |
| `server_address`     | The address the server should run at (if running server).                          | `127.0.0.1`                 |
| `server_port`        | The port the server should run on (if running server).                             | `9123`                      |
| `favourites`         | Favourite heights object where the key is the name and the value is the height     | `{ sit: 683, stand: 1040 }` |

All of these options (except `favourites`) can be set on the command line, just replace any `_` with `-` e.g. `mac_address` becomes `--mac-address`.

#### Device MAC addresses

- On Linux, device MAC addresses can be found using `bluetoothctl` and bluetooth adapter names can be found with `hcitool dev`
- On Windows you can use [Bluetooth LE Explorer](https://www.microsoft.com/en-us/p/bluetooth-le-explorer/9n0ztkf1qd98?activetab=pivot:overviewtab).
- On MacOS you can pair the device with [Bluetility](https://github.com/jnross/Bluetility), but you must use the UUID instead of the Mac Address.

## Usage

The script accepts a number of commands:

| Command                      | Description                                                                                       |
| ---------------------------- | ------------------------------------------------------------------------------------------------- |
|                              | Running without any command will print the current desk height                                    |
| `--watch`                    | Watch desk and print changes to height (and speed)                                                |
| `--move-to <value>`          | Move the desk to a certain height (mm) above the floor                                            |
| `--scan`                     | List available bluetooth devices (using the configured `adapter_name`)                            |
| `--server`                   | Run the script as a server, which will maintain the connection and provide quicker response times |
| `--tcp-server`               | Run the script as a simpler tcp only server                                                       |
| `--forward <other commands>` | Send commands to a server                                                                         |
| `--config <path>`            | Specify a path to a config file                                                                   |

### Moving the desk

To move to a particular height you can run:

```
idasen-controller --move-to 800
```

If you have configured favourite values in the `config.yaml` like this:

```
favourites:
  sit: 683
  stand: 1040
```

Then you can also pass the favourite name to the `--move-to` command:

```
idasen-controller --move-to sit
```

### Using the Server

You can run the script in a server mode. This will maintain a persistent connection to the desk and then listen on the specified port for commands. This has a number of uses, one of which is making the response time a lot quicker. Both the server and client will print the current height and speed of the desk as it moves.

Remember to ensure that the ports and IPs are configured in both the server and client `config.yaml` files (or provide them as command line arguments).

You can start the server like this:

```
idasen-controller --server
```

And then on the same or different device:

```
idasen-controller --forward --move-to 800
```

You can also use any of the favourites that are configured on the server:

```
idasen-controller --forward --move-to stand
```

There is also a simpler TCP server mode which allows you to send commands without needing a copy of the script on the client. You can start the tcp server with:

```
idasen-controller --tcp-server
```

And then use any tool you like to send commands. For example you could use `nc` on linux:

```
echo '{"move_to": 640}' | nc -w 1 127.0.0.1 9123
```

In this mode the client will not receive any height or speed values.

## Troubleshooting

### Connection failed

The initial connection can fail for a variety of reasons, here are some things to try if it happens repeatedly:

- Try ensuring that the desk is paired but _not_ connected before using the script.
- Try increasing the `scan-timeout` and `connection-timeout`.

### Connection / commands are slow

- Try reducing the `connection-timeout`. I have found that it can work well set to just `1` second. You may find that a low connection timeout results in failed connections sometimes though.
- Use the server mode. Run the script once with `--server` which will start a persistent server and maintain a connection to the desk. Then when sending commands (like `--move-to sit` or `--move-to 800`) just add the additional argument `--forward` to forward the command to the server. The server should already have a connection so the desk should respond much quicker.

### Error message "abort" on MacOS

On MacOS the process may quit with a vague message like `abort`. This could be because the application running the process doesn't have access to Bluetooth. To provide access, open `System Preferences -> Security & Privacy -> Privacy -> Bluetooth` and drag the application running the process into the list (eg. Terminal or iTerm2). [More info at the `bleak` issue](https://github.com/hbldh/bleak/issues/438#issuecomment-787125189)

### Scanning and connection issues on MacOS 12 (Monterey)

There was a bug with MacOS 12 that prevents connecting to bluetooth devices with this script [see this issue](https://github.com/rhyst/idasen-controller/issues/33) or [this bleak issue for more info](https://github.com/hbldh/bleak/issues/635#issuecomment-988054876).

You should update to MacOS 12.3 which fixes this issue.

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

## Projects using this project

Other useful projects that make use of this one:

- [Home Assistant Integration](https://github.com/j5lien/esphome-idasen-desk-controller) by @j5lien

## Attribution

Some ideas stolen from:

- [idasen-controller](https://github.com/pfilipp/idasen-controller) by @pfilipp for working out the functionality of the REFERENCE_INPUT characteristic which allows more accurate movement.

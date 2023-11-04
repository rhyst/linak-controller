"""
Config parsing for this script. Parses command line arguments and config.yaml.
"""

import os
import sys
import shutil
import argparse
import yaml
from appdirs import user_config_dir
from typing import Optional
from enum import Enum


class Commands(str, Enum):
    watch = "watch"
    move_to = "move_to"
    scan_adapter = "scan_adapter"
    server = "server"
    tcp_server = "tcp_server"


class Config:
    # Config
    mac_address: Optional[str] = None
    base_height: Optional[int] = None
    adapter_name: str = "hci0"
    scan_timeout: int = 5
    connection_timeout: int = 10
    server_address: str = "127.0.0.1"
    server_port: int = 9123
    favourites: dict = {}
    forward: bool = False
    move_to: Optional[str] = None
    move_command_period: float = 0.4


    # Command
    command: Commands = None

    # State
    disconnecting: bool = False

    def __init__(self):
        OLD_CONFIG_DIR = user_config_dir("idasen-controller")
        OLD_CONFIG_PATH = os.path.join(OLD_CONFIG_DIR, "config.yaml")

        DEFAULT_CONFIG_DIR = user_config_dir("linak-controller")
        DEFAULT_CONFIG_PATH = os.path.join(DEFAULT_CONFIG_DIR, "config.yaml")

        # Default config
        if not os.path.isfile(DEFAULT_CONFIG_PATH):
            os.makedirs(os.path.dirname(DEFAULT_CONFIG_PATH), exist_ok=True)
            if os.path.isfile(OLD_CONFIG_PATH):
                shutil.copyfile(OLD_CONFIG_PATH, DEFAULT_CONFIG_PATH)
            else:
                shutil.copyfile(
                    os.path.join(os.path.dirname(__file__), "example", "config.yaml"),
                    DEFAULT_CONFIG_PATH,
                )

        parser = argparse.ArgumentParser(description="")

        # Config via command line options

        parser.add_argument(
            "--mac-address",
            dest="mac_address",
            type=str,
            help="Mac address of the Linak desk",
        )
        parser.add_argument(
            "--base-height",
            dest="base_height",
            type=int,
            help="The height of tabletop above ground at lowest position (mm)",
        )
        parser.add_argument(
            "--adapter",
            dest="adapter_name",
            type=str,
            help="The bluetooth adapter device name",
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
            "--move-command-period",
            dest="move_command_period",
            type=float,
            help="The period between each move command (seconds)",
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
            help="File path to the config file (Default: {})".format(
                DEFAULT_CONFIG_PATH
            ),
            default=DEFAULT_CONFIG_PATH,
        )

        # Command to run

        cmd = parser.add_mutually_exclusive_group()
        cmd.add_argument(
            "--watch",
            dest="command",
            action="store_const",
            const=Commands.watch,
            help="Watch for changes to desk height and speed and print them",
        )
        cmd.add_argument(
            "--move-to",
            dest="move_to",
            action="store",
            type=str,
            help="Move desk to specified height (mm) or to a favourite position",
        )
        cmd.add_argument(
            "--scan",
            dest="command",
            action="store_const",
            const=Commands.scan_adapter,
            help="Scan for devices using the configured adapter",
        )
        cmd.add_argument(
            "--server",
            dest="command",
            action="store_const",
            const=Commands.server,
            help="Run as a server to accept forwarded commands",
        )
        cmd.add_argument(
            "--tcp-server",
            dest="command",
            action="store_const",
            const=Commands.tcp_server,
            help="Run as a simple TCP server to accept forwarded commands",
        )

        args = {k: v for k, v in vars(parser.parse_args()).items() if v is not None}

        if args.get("move_to"):
            args["command"] = Commands.move_to

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

        for key in config_file:
            setattr(self, key, config_file[key])

        # Overwrite config from command line args
        for key in args:
            setattr(self, key, args[key])

        if not self.mac_address:
            parser.error("Mac address must be provided")

        self.mac_address = self.mac_address.upper()

        IS_WINDOWS = sys.platform == "win32"

        if IS_WINDOWS:
            # Windows doesn't use this parameter so rename it so it looks nice for the logs
            self.adapter_name = "default adapter"

    def log(self, message, end="\n"):
        print(message, end=end)


config = Config()

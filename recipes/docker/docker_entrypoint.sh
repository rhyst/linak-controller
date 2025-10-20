#!/bin/bash

# From https://stackoverflow.com/a/64126744
service dbus start
bluetoothd &

/bin/bash

uv run -m linak_controller.main --config config.yaml --tcp-server

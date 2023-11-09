#!/bin/bash

# From https://stackoverflow.com/a/64126744
service dbus start
bluetoothd &

/bin/bash

poetry run python -m linak_controller.main --config config.yaml --server

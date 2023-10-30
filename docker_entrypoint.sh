# From https://stackoverflow.com/a/64126744
#!/bin/bash

service dbus start
bluetoothd &

/bin/bash

poetry run python -m idasen_controller.main --config config.yaml --tcp-server

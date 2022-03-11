# Recipes

## Linux

### Albert Launcher

You can use the [albert](https://github.com/albertlauncher/albert) launcher along with two `.desktop` files to allow you to trigger this script from the launcher. An example of a desktop file for this is:

```
[Desktop Entry]
Name=Desk - Sit
Exec=/path/to/idasen-controller --sit
Icon=/home/user/idasen-controller/sit-icon.png
Type=Application
Comment=Lower desk to sitting height.

```

(You can find the `idasen-controller` path with `where idasen-controller`)

### Scheduled standing periods

You can add some cron jobs to automatically raise and lower your desk. This way, the healthier habit is automatic.
The following cron raises the desk at 10 AM and 3 PM, and lowers it an hour later, Monday through Friday.

```
00 10 * * 1-5 python3 idasen-controller --stand
00 11 * * 1-5 python3 idasen-controller --sit
00 15 * * 1-5 python3 idasen-controller --stand
00 16 * * 1-5 python3 idasen-controller --sit
```

## Windows

### Autohotkey

A AutoHotkey script from @aienabled to drive the desk to stand and sit mode by pressing Ctrl+Alt+Shift+Up or Down arrow respectively:

```
;Idasen Desk - Stand
^!+Up::Run "C:\Users\...\Desk - Stand.lnk"

;Idasen Desk - Sit
^!+Down::Run "C:\Users\...\Desk - Sit.lnk"
```

These are shortcut files on the desktop but it's not necessary and could be simple python calls.

## Docker

You can run the script from within a docker file like this example:

```
FROM ubuntu

RUN apt update -y && apt upgrade -y

RUN apt install python3 python3-pip -y

ENV TZ=Europe/London

RUN ln -snf /usr/share/zoneinfo/$CONTAINER_TIMEZONE /etc/localtime && echo $CONTAINER_TIMEZONE > /etc/timezone

RUN apt install bluez -y

RUN apt install build-essential libglib2.0-dev libical-dev libreadline-dev libudev-dev libdbus-1-dev libdbus-glib-1-dev bluetooth libbluetooth-dev usbutils -y

RUN pip3 install idasen-controller

COPY config.yaml .

ENTRYPOINT ["idasen-contoller", "--config", "config.yaml"]
```

Build the image:

```
docker build -t idasen-controller .
```

And then run it with the usual commands:

```
docker run -it --rm --privileged \
    --cap-add=SYS_ADMIN \
    --cap-add=NET_ADMIN \
    --net=host \
    -v /dev/bus/usb:/dev/bus/usb \
    -v /var/run/dbus:/var/run/dbus \
    idasen-controller --watch
```

From @maxime1992

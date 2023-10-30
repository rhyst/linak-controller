FROM python:3.10

WORKDIR /app
# allows Python's output to be seen in the log:
ENV PYTHONUNBUFFERED=1

# install required bluetooth packages:
RUN apt-get update && \
    apt-get install -y bluez bluetooth
#        build-essential libglib2.0-dev libical-dev libreadline-dev libudev-dev libdbus-1-dev libdbus-glib-1-dev libbluetooth-dev usbutils
RUN pip install poetry

# idasen-controller dependencies:
COPY poetry.lock pyproject.toml .
RUN poetry install

COPY . .

ENTRYPOINT sh docker_entrypoint.sh

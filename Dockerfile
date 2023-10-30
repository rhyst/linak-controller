FROM python:3.10

WORKDIR /app
# allows Python's output to be seen in the log:
ENV PYTHONUNBUFFERED=1

# install required packages:
RUN apt-get update && \
    apt-get install -y bluez bluetooth
RUN pip install poetry

# idasen-controller dependencies:
COPY poetry.lock pyproject.toml ./
RUN poetry install

COPY ./ ./

ENTRYPOINT sh docker_entrypoint.sh

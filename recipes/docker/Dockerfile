FROM python:3.14

WORKDIR /app
# allows Python's output to be seen in the log:
ENV PYTHONUNBUFFERED=1

# install required packages:
RUN apt-get update && \
    apt-get install -y bluez bluetooth
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_UNMANAGED_INSTALL="/usr/bin" sh

# linak-controller dependencies:
COPY uv.lock pyproject.toml ./
COPY ./ ./
RUN uv sync

ENTRYPOINT ["sh", "recipes/docker/docker_entrypoint.sh"]

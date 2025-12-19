ARG PYTHON_VERSION=3.11

# build stage
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0 UV_FROZEN=1

# install dependencies
WORKDIR /app
COPY pyproject.toml uv.lock /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev

# copy and install project
COPY mymodule/ /app/mymodule
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# run stage
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

# copy the application from the builder
COPY --from=builder --chown=app:app /app /app

WORKDIR /app

# add venv executables to PATH
ENV PATH="/app/.venv/bin:$PATH"

# set command/entrypoint, adapt to fit your needs
ENTRYPOINT ["python", "-m", "mymodule.cli"]

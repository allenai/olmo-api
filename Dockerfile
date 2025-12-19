# Taken from https://github.com/astral-sh/uv-docker-example/blob/main/multistage.Dockerfile

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Omit development dependencies
ENV UV_NO_DEV=1
# Disable Python downloads, because we want to use the system interpreter
# across both images. If using a managed Python version, it needs to be
# copied from the build image into the final image; see `standalone.Dockerfile`
# for an example.
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /api

COPY vendor vendor
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY . /api

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

FROM python:3.11-slim-bookworm AS runner
# It is important to use the image that matches the builder, as the path to the
# Python executable must be the same, e.g., using `python:3.11-slim-bookworm`
# will fail.

# Setup a non-root user
RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot


# Copy the application from the builder
COPY --from=builder --chown=nonroot:nonroot /api /api

# Place executables in the environment at the front of the path
ENV PATH="/api/.venv/bin:$PATH"

WORKDIR /api

RUN apt-get update -qq && apt-get install ffmpeg -y

USER nonroot

ENTRYPOINT [ "/api/start.sh" ]

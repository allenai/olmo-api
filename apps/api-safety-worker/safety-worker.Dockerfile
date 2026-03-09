FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app
COPY vendor vendor

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-workspace --package=api

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --package=api


FROM python:3.14-slim-bookworm AS runner

RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot

COPY --from=builder --chown=nonroot:nonroot /app /app

ENV PATH="/app/.venv/bin:$PATH"

FROM runner AS dev
WORKDIR /app

USER nonroot

ENTRYPOINT ["./apps/api-safety-worker/dev-safety-worker.sh"]

FROM runner AS prod
WORKDIR /app

USER nonroot

ENTRYPOINT ["./apps/api-safety-worker/start-safety-worker.sh"]

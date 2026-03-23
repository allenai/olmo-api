default:
  just --list

install:
  uv sync --all-packages --all-groups

test:
  ENV=test uv run pytest --ignore ./apps/api/e2e

test-e2e:
  ENV=test uv run pytest ./apps/api/e2e

# Formatting, linting, type checking
verify: format lint type-check

format *ARGS:
  uv run ruff format {{ARGS}}

lint *ARGS:
  uv run ruff check {{ARGS}}

type-check-apps:
  uv run mypy apps

type-check-packages:
  uv run mypy packages

type-check: type-check-api type-check-packages

dev:
  ENV=development uv run fastapi dev ./apps/api/main.py --port 8888
